"""
@module electrodevice.custom.cst_netlist

cst-1 (PROTOTYPING_VIEWS_PLAN.md §2 phase 1, §8): ONE `.op` SPICE DECK PER CIRCUIT STATE, built from the same circuit rows the bench renders
(electrodevice.circuit_netlist_seed's element rules and constants) with the state's modes applied:

  * a switch in mode closed / open  -> the renderer's near-short / near-open resistor (SWITCH_CLOSED_OHMS / SWITCH_OPEN_OHMS)
  * a pin driven-high / driven-low  -> an ideal source (5 V / 0 V) through a 0 V ammeter `Vam_<pin>` — the WORST-CASE upper bound on the pin's current
                                       (a real output has tens of ohms of drive impedance; the datasheet's VOH test current sets the limit it is judged by)
  * a pin input-pullup              -> the internal pull-up as a resistor to 5 V (`pullup_ohms`: the datasheet's 20 kΩ and 50 kΩ ends, DS40002061B Table 30-1,
                                       both runs kept) through a 0 V ammeter
  * a pin input-hiz / high-z        -> nothing: an input draws no current; a net with no driver, no pull and no closed switch to a rail is FLOATING (the
                                       structural rule in cst_verdict says so)
  * GND                             -> ngspice's own ground (a 0 V source to node 0 would be a short): the ground return = the sum of the rail sources' currents
                                       (every V<pin> / Vpu_<pin> is probed; cst_verdict reports it as i(gnd-return) against the VCC/GND budget)
  * the LED                         -> the renderer's own `polari_led` model, with a 0 V ammeter in series (`Vam_LED1`)

Probes: `print i(vam_*) i(vgnd) v(<net>)` — ngspice's `-b` output is parsed by circuit_netlist_seed.run_netlist (name = value). Node 0 is SPICE's; the
rows' nets keep their names.
"""
import json

from electrodevice.circuit_netlist_seed import SWITCH_CLOSED_OHMS, SWITCH_OPEN_OHMS, run_netlist
from electrodevice.custom.spice_run import LED_MODEL, capability

VCC = 5.0
PULLUP_OHMS = (20000, 50000)   # ATmega328P RPU 20..50 kΩ (DS40002061B Table 30-1, p.323)


def _ref(prefix, name):
    return prefix + name.replace('-', '_').replace(':', '_')


def _node(name):
    """A SPICE node name: no '-' or ':' (ngspice reads them as part of a parameter)."""
    return name.replace('-', '_').replace(':', '_')


def _led_model(name, dv):
    """msv-1: the renderer's LED model with its forward voltage moved by dv at any current (Is scaled by exp(-dv / (N Vt)); Vt at ngspice's 27 C)."""
    import math
    import re
    f = dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+0-9.eE]+)', LED_MODEL))
    vt = 1.380649e-23 * 300.15 / 1.602176634e-19
    return '.model polari_led_%s D(Is=%.6g N=%g Rs=%g)' % (_node(name), f['Is'] * math.exp(-dv / (f['N'] * vt)), f['N'], f['Rs'])


def deck(state, cat, pullup_ohms=PULLUP_OHMS[0], vary=None):
    """-> (netlist text, probes) for one state over the catalogue's circuit rows.

    msv-1 `vary` (None = the nominal deck, unchanged): {'vcc': V, 'r_scale': {resistor: factor}, 'r_out_high': ohm, 'r_out_low': ohm (a driven pin's
    output resistance), 'led_dv': {led: V (its forward voltage moved)}, 'meter_v': (net, ohm) (a voltmeter's input to GND), 'meter_i': (part, ohm) (an
    ammeter's burden in series with the part)} - the tolerance corners and the meter's loading (cmod.custom.measure_bands)."""
    v = vary or {}
    vcc = float(v.get('vcc', VCC))
    lines = ['* cst-1: .op of circuit %s in state %s (config %s) — built from the CircuitComponentDefinition / CircuitNetDefinition / BoardPinNet rows; edit the rows, not this file'
             % (cat['circuit'], state['name'], state['config']), LED_MODEL]
    if v:
        lines.append('* msv-1 varied: %s' % ', '.join('%s=%s' % (k, v[k]) for k in sorted(v)))
        lines += [_led_model(n, dv) for n, dv in sorted((v.get('led_dv') or {}).items())]
    probes = []
    need_gnd = False
    nets_driven = set()
    for name, comp in cat['components'].items():
        kind, nets = comp['kind'], comp['nets']
        row = next((c for c in _components(cat) if c['name'] == name), None)
        params = json.loads((row or {}).get('params_json') or '{}')
        if kind == 'switch':
            mode = state['modes'].get(name, comp['at_init'])
            ohms = SWITCH_CLOSED_OHMS if mode == 'closed' else SWITCH_OPEN_OHMS
            lines.append('%s %s %s ; %s %s' % (_ref('R', name), ' '.join(nets), ohms, name, mode))
            if mode == 'closed' and 'GND' in nets:
                nets_driven |= set(nets)
        elif kind in ('led', 'diode'):
            a, k = nets[0], nets[1] if len(nets) > 1 else '0'
            mi = v.get('meter_i')
            if mi and mi[0] == name:   # msv-1: the ammeter's burden in series, before the probe ammeter
                lines.append('Rmeter_%s %s n_%s_m %g ; the meter\'s burden in series with %s' % (_node(name), a, _node(name), mi[1], name))
                a = 'n_%s_m' % _node(name)
            lines.append('%s %s n_%s_k DC 0 ; ammeter in series with %s' % (_ref('Vam_', name), a, _node(name), name))
            model = 'polari_led_%s' % _node(name) if name in (v.get('led_dv') or {}) else params.get('model', 'polari_led')
            lines.append('%s n_%s_k %s %s' % (_ref('D', name), _node(name), k, model))
            probes.append('i(%s)' % _ref('Vam_', name).lower())
        elif kind == 'resistor':
            ohms = params.get('ohms', '?')
            if name in (v.get('r_scale') or {}) and ohms != '?':
                ohms = '%g' % (float(ohms) * v['r_scale'][name])
            lines.append('%s %s %s' % (_ref('R', name), ' '.join(nets), ohms))
        elif kind == 'vsource':
            lines.append('%s %s DC %s' % (_ref('V', name), ' '.join(nets), params.get('dc', VCC)))
            nets_driven |= set(nets)
        if 'GND' in nets:
            need_gnd = True
    for pin, d in cat['pins'].items():
        mode = state['modes'].get(pin, d['at_init'])
        net = d['net']
        if mode in ('driven-high', 'driven-low'):
            rout = v.get('r_out_high' if mode == 'driven-high' else 'r_out_low', 0)
            src = 'n_%s_src' % pin if rout else 'n_%s' % pin
            lines.append('%s %s 0 DC %s ; %s %s (ideal source: the worst-case bound)' % (_ref('V', pin), src, vcc if mode == 'driven-high' else 0, pin, mode))
            if rout:
                lines.append('Rout_%s %s n_%s %g ; %s output resistance (msv-1 corner)' % (pin, src, pin, rout, pin))
            lines.append('%s n_%s %s DC 0 ; ammeter: the current %s sources (+) or sinks (-)' % (_ref('Vam_', pin), pin, net, pin))
            probes.append('i(%s)' % _ref('Vam_', pin).lower())
            nets_driven.add(net)
        elif mode == 'input-pullup':
            lines.append('%s n_%s_vcc 0 DC %s ; %s pull-up supply' % (_ref('Vpu_', pin), pin, vcc, pin))
            lines.append('%s n_%s_vcc n_%s %s ; %s internal pull-up RPU (%s ohm end of 20k..50k)' % (_ref('Rpu_', pin), pin, pin, pullup_ohms, pin, pullup_ohms))
            lines.append('%s n_%s %s DC 0 ; ammeter: the pull-up current through %s' % (_ref('Vam_', pin), pin, net, pin))
            probes.append('i(%s)' % _ref('Vam_', pin).lower())
            nets_driven.add(net)
        else:
            lines.append('* %s %s: no element (an input draws no current)' % (pin, mode))
    # GND is ngspice's own ground alias (a 'Vgnd GND 0' would be a shorted source): the ground return is the sum of what the rail sources deliver, so every
    # rail source is probed too (cst_verdict adds them up as i(gnd-return))
    for ln in lines:
        if ln.startswith(('VD', 'Vpu_', 'VA')) and ' DC ' in ln and not ln.startswith('Vam_'):
            probes.append('i(%s)' % ln.split()[0].lower())
    for n in cat['nets'].values():
        if n['net'] != 'GND':
            probes.append('v(%s)' % n['net'])
    mv = v.get('meter_v')
    if mv:   # msv-1: the voltmeter's input resistance from the probed net to GND
        lines.append('Rmeter_v %s 0 %g ; the meter\'s input resistance' % (mv[0], mv[1]))
    # a net nothing drives would leave the matrix singular: tie every undriven, non-ground net to 0 through a huge resistor and say so (the structural rule flags it)
    for n in cat['nets'].values():
        if n['net'] not in nets_driven and n['net'] != 'GND' and not _reaches_driven(n['net'], cat, state, nets_driven):
            lines.append('Rfloat_%s %s 0 1e12 ; %s has no driver, pull or closed switch in this state: FLOATING (a tie for the solver only)' % (_node(n['net']), n['net'], n['net']))
    lines += ['.control', 'op'] + ['print %s' % p for p in probes] + ['quit', '.endc', '.end', '']
    return '\n'.join(lines), probes


def _components(cat):
    return cat.get('_components') or []


def _reaches_driven(net, cat, state, driven):
    """Does `net` connect to a driven net through a resistor / closed switch / the LED? (one hop of passive parts is enough for this bench)"""
    for name, comp in cat['components'].items():
        if net in comp['nets']:
            if comp['kind'] == 'switch' and state['modes'].get(name) != 'closed':
                continue
            if any(n in driven or n == 'GND' for n in comp['nets'] if n != net):
                return True
    return False


def floating_nets(state, cat):
    """The nets no driver, pull or closed switch reaches in this state (the structural rule)."""
    driven = set()
    for pin, d in cat['pins'].items():
        if state['modes'].get(pin, d['at_init']) in ('driven-high', 'driven-low', 'input-pullup'):
            driven.add(d['net'])
    for name, comp in cat['components'].items():
        if comp['kind'] == 'vsource':
            driven |= set(comp['nets'])
    out = []
    for n in cat['nets'].values():
        if n['net'] != 'GND' and n['net'] not in driven and not _reaches_driven(n['net'], cat, state, driven):
            inputs = [p for p, d in cat['pins'].items() if d['net'] == n['net'] and state['modes'].get(p, d['at_init']) in ('input-hiz', 'input-pullup', 'high-z')]
            out.append({'net': n['net'], 'inputs': inputs})
    return out


def run(state, cat, pullup_ohms=PULLUP_OHMS[0], vary=None):
    """One .op run -> {'ok', 'measurements', 'netlist', 'pullup_ohms', 'error'?}. No engine -> ok False with the capability words."""
    text, probes = deck(state, cat, pullup_ohms, vary)
    cap = capability()
    if not cap['available']:
        return {'ok': False, 'netlist': text, 'probes': probes, 'pullup_ohms': pullup_ohms, 'measurements': {}, 'error': 'ngspice not available on this node', 'capability': cap}
    r = run_netlist(text, label='cst-%s-%s' % (state['config'], state['name']))
    r.update(netlist=text, probes=probes, pullup_ohms=pullup_ohms)
    return r
