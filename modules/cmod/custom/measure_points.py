"""
@module cmod.custom.measure_points

msv-0 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 2): WHAT TO MEASURE AT A NODE, and what the simulation says it should read - DERIVED from
the node's electrical circuit state, nothing typed by hand. The state is the one the node's latest reached run left behind (its electrical collateral's
words name it: "electrical circuit: ok - circuit uno-button-clock in state led-on ..."); the prediction is the cst slice's ngspice .op of that state over
the same circuit rows the bench renders (electrodevice cst_netlist), plus the rail under the node's load (node_electrical's supply knobs).

  derive(manager, node)   -> the node's points (upserted, origin derived; a person's points are kept beside them; a derived point the circuit no longer
                             gives is kept and marked origin stale - readings name it)
  points(manager, node)   -> the node's points in order

One point per:
  V dc  a net to GND (every non-ground net of the circuit; the probe words name the board pins on the net, else the net's own description)
  I dc  in series with a part (each part the deck puts an ammeter on: the LED branch) - the words say where to break the circuit
  V dc  the 5 V rail to GND (VCC minus the node's ground-return current over R_supply - both knobs, said; a reading of it measures R_supply)

The deck is the WORST-CASE bound (ideal pin sources: a real pin's output resistance lowers a driven net and its current). Until msv-1's tolerance band,
the nominal is that bound and the basis says so.
"""
import json
import re

from cmod.custom import config_rows as R

_STATE_RE = re.compile(r'electrical circuit: (\S+) - circuit (\S+) in state (\S+)')


def _slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def _latest_reached(manager, node):
    runs = sorted((r for r in R.rows(manager, 'StructNodeRun', node=node) if r['outcome'] == 'reached'), key=lambda r: (len(r['name']), r['name']))
    return runs[-1] if runs else None


def _state_of(manager, run):
    """-> (verdict, circuit, state) from the run's last edge's electrical collateral words, or None."""
    edges = sorted(R.rows(manager, 'StructNodeRunEdge', run=run['name']), key=lambda e: int(e.get('order') or 0))
    for e in reversed(edges):
        m = _STATE_RE.search(e.get('collaterals') or '')
        if m:
            return m.groups()
    return None


def _variant(manager, node_row):
    from cmod.custom import bench_events as E
    from cmod.custom import catom_config as CF
    return E.variant_of(manager, CF.context(manager, node_row['bench_solution'])['firmware_solution'])


def _pins_on(net_row):
    try:
        refs = json.loads(net_row.get('board_pins_refs_json') or '[]')
    except ValueError:
        refs = []
    return [r.split(':')[-1] for r in refs]


def derive(manager, node):
    from cmod.custom import node_electrical as NE
    from electrodevice.custom import cst_netlist as N
    from electrodevice.custom import cst_verdict as V
    n = R.get(manager, 'StructNode', node)
    if n is None:
        raise R.ConfigRefused('no node %r' % node, status=404)
    run = _latest_reached(manager, node)
    if run is None:
        raise R.ConfigRefused('node %s has no reached run: run it first - its points come from the circuit state the run leaves behind' % node, status=409)
    got = _state_of(manager, run)
    if got is None:
        raise R.ConfigRefused('run %s kept no electrical collateral naming a circuit state (run it again on a build with the bss-12 check)' % run['name'], status=409)
    verdict, circuit, state_name = got
    variant = _variant(manager, n)
    c = NE.circuit(variant)
    if 'cat' not in c:
        raise R.ConfigRefused('no circuit for %s: %s' % (variant, c.get('refused')), status=409)
    cat = c['cat']
    state = next((s for s in c['states'] if s['name'] == state_name), None)
    if state is None:
        raise R.ConfigRefused('circuit %s has no state %s' % (cat['circuit'], state_name), status=409)
    op = N.run(state, cat, N.PULLUP_OHMS[0])
    if not op.get('ok'):
        raise R.ConfigRefused('the .op of %s did not run: %s' % (state_name, op.get('error', '')), status=409)
    meas = op['measurements']
    src = 'ngspice .op of circuit %s in state %s (run %s)' % (cat['circuit'], state_name, run['name'].split('#')[-1])
    basis = ('the worst-case bound: the pins as ideal sources, the pull-up at its %d ohm end (a real pin\'s output resistance lowers a driven net and its '
             'current); no tolerance band yet (msv-1)' % N.PULLUP_OHMS[0])
    want = []
    nets = {nr['net'].lower(): nr for nr in cat['nets'].values() if nr['net'] != 'GND'}
    for key, val in meas.items():
        m = re.fullmatch(r'v\((.+)\)', key)
        if m and m.group(1) in nets:
            nr = nets[m.group(1)]
            pins = _pins_on(nr)
            where = ('red probe on %s (the net %s), black on GND' % (' or '.join(pins), nr['net'])) if pins else \
                    ('red probe on the net %s - no board pin sits on it: %s - black on GND' % (nr['net'], (nr.get('description') or '').split(' (')[0]))
            want.append(('v-%s' % _slug(nr['net']), 'V dc', nr['net'], 'GND', where, float(val), 'V'))
    for name, comp in cat['components'].items():
        key = 'i(%s)' % ('vam_' + name.replace('-', '_').replace(':', '_')).lower()
        if key in meas:
            a = comp['nets'][0]
            want.append(('i-%s' % _slug(name), 'I dc', name, comp['nets'][1] if len(comp['nets']) > 1 else 'GND',
                         'break the circuit at %s\'s %s leg and put the meter in series: red toward %s (current mode, the A / mA jack)' % (name, a, a), float(meas[key]), 'A'))
    j = V.judge(state, op, cat, c['lim'])
    gnd = j['currents'].get('i(gnd-return)')
    if gnd is not None:
        rail = NE.VCC_V - gnd * 1e-3 * NE.R_SUPPLY_OHMS
        want.append(('v-5v-rail', 'V dc', '5V', 'GND', 'red probe on the 5V header pin, black on a GND header pin (this reading measures R_supply)', rail, 'V'))
    names = set()
    for order, (slug, q, plus, minus, where, nominal, unit) in enumerate(want):
        name = '%s-mp-%s' % (node, slug)
        names.add(name)
        b = basis if slug != 'v-5v-rail' else ('VCC %g V minus %.3f mA x R_supply %g ohm - both knobs (node_electrical), R_supply undetermined: this point measures it'
                                                % (NE.VCC_V, gnd, NE.R_SUPPLY_OHMS))
        R.upsert(manager, 'MeasurementPoint', name, node=node, quantity=q, plus_at=plus, minus_at=minus, where=where, nominal=nominal, si_unit=unit,
                 source=src if slug != 'v-5v-rail' else 'node_electrical supply (%s)' % src, basis=b, run=run['name'], hex_sha256=run.get('hex_sha256') or '',
                 state=state_name, origin='derived', order=order)
    for p in R.rows(manager, 'MeasurementPoint', node=node, origin='derived'):
        if p['name'] not in names:
            R.upsert(manager, 'MeasurementPoint', p['name'], origin='stale', basis='no longer derived: the circuit state %s does not give it (kept: readings name it)' % state_name)
    return points(manager, node)


def points(manager, node):
    return sorted(R.rows(manager, 'MeasurementPoint', node=node), key=lambda p: (p['origin'] == 'stale', int(p.get('order') or 0), p['name']))
