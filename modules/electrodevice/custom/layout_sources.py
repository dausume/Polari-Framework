"""
@module electrodevice.custom.layout_sources

lay-1: WHERE A BUILT CONFIG'S LAYOUT INPUT COMES FROM — the one file of the layout engine that reaches into the board and cmod modules (lazily, at call time, so electrodevice
still loads without them). A config is a firmware variant (`board.custom.variants`); its input is
  - the PARTS its routes need (`cmod` isotope variants' `parts_json`: the `_pt` kit parts, each with the KitPart key it is),
  - its PIN ASSIGNMENT (the variant's own knobs: led_pin, button_pin, sense_pin; the sense pin only when the config has the sense feature),
  - its CIRCUIT NETS (the electrodevice circuit `uno-button-clock`: the physical bench as rows, with `board_pins_refs_json` naming the BoardPin rows on each net).
The output is a DESIGN: components with named terminals, and the nets (terminal sets) a correct layout must reproduce. Nothing here is typed per config: a config that needs
a part the circuit rows do not hold is REFUSED in words (a second circuit is a row to add, not code).

STAND-IN: a config with no sense feature on this branch whose name has an entry in STAND_INS borrows that other variant's sense pin (uno-light -> uno-light-sense-poll's
D6->D3), and the design says so (`notes`). The moment the config itself carries the sense feature (smp-1), its own `sense_pin` knob is read and the stand-in is not used.
"""
import json
import types

from electrodevice.custom.layout_words import LayoutRefused

CIRCUIT = 'uno-button-clock'
BOARD = 'arduino-uno-r3'
KIT = 'arduino-starter-kit'
#: config -> the variant whose sense wiring stands in while the config itself has none (S1 = uno-light + the sense jumper; the sense line lands on branch dev-smp)
STAND_INS = {'uno-light': 'uno-light-sense-poll'}
#: the jobs whose routes bring parts onto the breadboard
PART_JOBS = ('read-button', 'drive-led', 'sense-led-line', 'read-temperature')
#: kit part class -> the circuit component kind that realises it on the breadboard
KIND_OF_PART = {'pushbutton': 'switch', 'led': 'led', 'resistors': 'resistor'}


def _j(s, d):
    try:
        return json.loads(s) if isinstance(s, str) and s else (s if s is not None else d)
    except ValueError:
        return d


def _rows(manager, cls):
    t = ((getattr(manager, 'objectTables', None) or {}).get(cls) or {}) if manager is not None else {}
    return list(t.values()) if isinstance(t, dict) else list(t)


def _g(row, key, default=''):
    return row.get(key, default) if isinstance(row, dict) else getattr(row, key, default)


# ------------------------------------------------------------------ the config
def variant_of(manager, config):
    from cmod.custom import fsc_link
    configs = fsc_link.configs(manager)
    v = configs.get(config)
    if v is None:
        raise LayoutRefused("no built config %r (configs: %s)" % (config, ', '.join(sorted(configs))), status=404)
    if (v.get('board_definition') or BOARD) != BOARD:
        raise LayoutRefused("config %r is for the board %s: layouts are built for the %s only so far" % (config, v.get('board_definition'), BOARD))
    return v


def pin_assignment(manager, config):
    """-> {led, button, sense (each 'D<n>' | None), 'notes': [words], 'standin': variant | ''}."""
    from board.custom import variants as V
    v = variant_of(manager, config)
    f, k = _j(v.get('features_json'), {}), _j(v.get('knobs_json'), {})
    notes, standin = [], ''

    def pin(key, default_key):
        n = k.get(key, V.DEFAULT_KNOBS.get(default_key))
        return 'D%d' % n if isinstance(n, int) else None
    out = {'led': pin('led_pin', 'led_pin') if f.get('led') else None, 'button': pin('button_pin', 'button_pin') if f.get('button') else None, 'sense': None}
    if f.get('sense'):
        out['sense'] = pin('sense_pin', 'sense_pin')
    elif f.get('led') and config in STAND_INS:
        other = variant_of(manager, STAND_INS[config])
        ok = _j(other.get('knobs_json'), {})
        n = ok.get('sense_pin', V.DEFAULT_KNOBS.get('sense_pin'))
        out['sense'], standin = 'D%d' % n, STAND_INS[config]
        notes.append("config %s has no sense line on this branch (its features: %s), so the sense jumper is STAND-IN wiring from %s: D%s -> %s. "
                     "When %s itself carries the sense feature, its own sense_pin is read instead."
                     % (config, ', '.join(sorted(x for x, on in f.items() if on)), STAND_INS[config], out['led'].lstrip('D'), out['sense'], config))
    return dict(out, notes=notes, standin=standin, features=f, knobs=k, variant=v)


def route_parts(manager, config):
    """-> [{job, route, class, kit_key, spec, why}] the parts the config's routes need (deduplicated by class + spec)."""
    from cmod.custom import fsc_link
    from cmod.custom import isotope_variants as IV
    v = variant_of(manager, config)
    routes = fsc_link.config_routes(v)
    by = {x['name']: x for x in IV.variants(manager)}
    out, seen = [], set()
    for job in PART_JOBS:
        for route in routes.get(job, []):
            row = by.get('%s:%s' % (job, route))
            if row is None:
                raise LayoutRefused("config %s: no route variant %s:%s in the catalogue" % (config, job, route))
            for p in _j(row.get('parts_json'), []):
                key = (p['class'], json.dumps(p.get('spec'), sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                out.append({'job': job, 'route': route, 'class': p['class'], 'kit_key': (p.get('kit_keys') or [''])[0], 'spec': p.get('spec') or {}, 'why': p.get('why', '')})
    return out


# ------------------------------------------------------------------ the circuit nets
def circuit_rows(manager, name=CIRCUIT):
    from electrodevice.objects.circuit._shared import SEED_CIRCUIT_COMPONENTS, SEED_CIRCUIT_NETS
    comps = [r for r in _rows(manager, 'CircuitComponentDefinition') if _g(r, 'circuit_name') == name] or [types.SimpleNamespace(**r) for r in SEED_CIRCUIT_COMPONENTS if r['circuit_name'] == name]
    nets = [r for r in _rows(manager, 'CircuitNetDefinition') if _g(r, 'circuit_name') == name] or [types.SimpleNamespace(**dict({'is_ground': False}, **r)) for r in SEED_CIRCUIT_NETS if r['circuit_name'] == name]
    if not comps:
        raise LayoutRefused("no circuit rows named %r" % name, status=404)
    return comps, nets


TERMINALS = {'switch': ('1', '2'), 'resistor': ('1', '2'), 'led': ('anode', 'cathode')}


def _ref(row_name):
    return row_name.split('-', 1)[-1].upper()


def design_of(manager, config):
    """The DESIGN of a built config: {'config', 'components': [{ref, row, kind, kit_key, kit_part, params, terminals:[{id, name, net}]}], 'attach': {net: [{pin, role}]},
    'ground_net', 'supply_nets', 'nets': {net: sorted terminal ids}, 'notes', 'drift', 'assignment'}."""
    asg = pin_assignment(manager, config)
    parts = route_parts(manager, config)
    comps, net_rows = circuit_rows(manager)
    ground = next((_g(n, 'net') for n in net_rows if _g(n, 'is_ground', False)), 'GND')
    wanted, unmapped = [], []
    for p in parts:
        if p['class'] == 'jumper wire':
            continue                       # the sense jumper is a wire between pins, not a part with holes (the placer draws it)
        kind = KIND_OF_PART.get(p['kit_key'])
        ohms = (p['spec'] or {}).get('ohms')
        hit = next((c for c in comps if _g(c, 'kind') == kind and (kind != 'resistor' or _j(_g(c, 'params_json'), {}).get('ohms') == ohms)), None) if kind else None
        if hit is None:
            unmapped.append('%s (%s%s, for %s:%s)' % (p['class'], p['kit_key'] or 'no kit key', ' %s ohm' % ohms if ohms else '', p['job'], p['route']))
        else:
            wanted.append((p, hit))
    if unmapped:
        raise LayoutRefused("config %s needs part(s) the circuit rows of %s do not hold: %s. Add the circuit (rows) for this build; the placer reads nets from circuit rows and "
                            "does not invent a connection." % (config, CIRCUIT, '; '.join(unmapped)))
    if not wanted:
        raise LayoutRefused("config %s has no part that goes on a breadboard (its routes need none)" % config)
    kit = _kit_rows()
    components = []
    for p, row in sorted(wanted, key=lambda w: _g(w[1], 'name')):
        kind = _g(row, 'kind')
        pins = _j(_g(row, 'pins_json'), [])
        names = TERMINALS[kind]
        ref = _ref(_g(row, 'name'))
        components.append({'ref': ref, 'row': _g(row, 'name'), 'kind': kind, 'kit_key': p['kit_key'], 'kit_part': kit.get('%s:%s' % (KIT, p['kit_key']), {}),
                           'params': _j(_g(row, 'params_json'), {}), 'job': p['job'],
                           'terminals': [{'id': '%s.%s' % (ref, n), 'name': n, 'net': net} for n, net in zip(names, pins)]})
    nets = {}
    for c in components:
        for t in c['terminals']:
            nets.setdefault(t['net'], []).append(t['id'])
    # the board side: which header pin sits on which net, by the config's own pin assignment
    sw = next((c for c in components if c['kind'] == 'switch'), None)
    r1 = next((c for c in components if c['kind'] == 'resistor'), None)
    attach = {}
    if asg['led'] and r1:
        attach.setdefault(r1['terminals'][0]['net'], []).append({'pin': asg['led'], 'role': 'output'})
        if asg['sense']:
            attach[r1['terminals'][0]['net']].append({'pin': asg['sense'], 'role': 'input'})
    elif asg['sense'] or asg['led']:
        raise LayoutRefused("config %s drives an LED but its circuit has no series resistor row to hang the LED pin on" % config)
    if asg['button'] and sw:
        sig = next(t['net'] for t in sw['terminals'] if t['net'] != ground)
        attach.setdefault(sig, []).append({'pin': asg['button'], 'role': 'input'})
    if ground in nets:
        attach.setdefault(ground, []).append({'pin': 'GND', 'role': 'ground'})
    for net, atts in attach.items():
        nets.setdefault(net, []).extend('hdr:%s' % a['pin'] for a in atts)
    # drift: the circuit net rows list their BoardPin refs by hand; the config's own assignment is the authority, a difference is said, never silent
    drift = []
    for n in net_rows:
        refs = sorted(r.rsplit(':', 1)[-1] for r in _j(_g(n, 'board_pins_refs_json'), []))
        have = sorted(a['pin'] for a in attach.get(_g(n, 'net'), []) if a['role'] != 'ground')
        if refs != have and _g(n, 'net') in nets:
            drift.append("circuit net %s lists BoardPin(s) %s but config %s puts %s on it: the config's pin assignment is used" % (_g(n, 'net'), refs or 'none', config, have or 'none'))
    return {'config': config, 'board': BOARD, 'components': components, 'attach': attach, 'ground_net': ground, 'supply_nets': [], 'nets': {k: sorted(v) for k, v in nets.items()},
            'notes': list(asg['notes']), 'drift': drift, 'assignment': {k: asg[k] for k in ('led', 'button', 'sense', 'standin')}, 'circuit': CIRCUIT,
            'sense_pin': asg['sense']}


# ------------------------------------------------------------------ board / part facts (lazy reads of the board module)
_KIT = {}


def _kit_rows():
    if 'k' not in _KIT:
        from board.custom import kit_parts
        _KIT['k'] = {r['name']: r for r in kit_parts.rows()}
    return _KIT['k']


def board_pins(manager, board=BOARD):
    """{canonical: BoardPin dict} of the board (the live rows when a manager holds them, else the seeds)."""
    from board.custom import board_object as bo
    live = bo.tables_from_manager(manager) if manager is not None and (getattr(manager, 'objectTables', None) or {}).get('BoardPin') else None
    return {p['canonical']: p for p in bo.rows_for(board, live)['pins']}


def pin_family(manager, label, board=BOARD):
    """The pin-view family of a header pin and its hex (board.custom.pv_families: the BoardPin's function -> family -> the token's fallback hex), or ('', '') for a power label."""
    from board.custom import pv_families as F
    bp = board_pins(manager, board).get(label)
    fam = F.role_family(bp['function']) if bp else ''
    return fam, F.FALLBACK_HEX.get(fam, '')


def pin_where(manager, label, board=BOARD):
    """'DIGITAL_L header, pin 7' for a BoardPin; the first connector pin that carries a power label (GND -> POWER header, pin 6)."""
    bp = board_pins(manager, board).get(label)
    if bp and bp.get('connector_pin'):
        c, _, n = bp['connector_pin'].partition(':')
        return '%s header, pin %s' % (c, n)
    from board.custom import board_uno
    for conn, (_ref, _kind, _fp, labels, _order) in board_uno.CONNECTORS.items():
        if label in labels:
            return '%s header, pin %d' % (conn, labels.index(label) + 1)
    return 'the %s header' % board


def power_label(kind):
    return {'ground': 'GND', 'supply': '+5V'}[kind]
