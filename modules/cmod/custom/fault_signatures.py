"""
@module cmod.custom.fault_signatures

msv-2 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 4, "Telling a mistake apart"): WHICH BUILD MISTAKE BEST EXPLAINS A UNIT'S READINGS. The
cst slice's ngspice .op of each node's circuit state is run again with one usual build fault injected (electrodevice cst_netlist's fault keys), and
every fault is scored against ALL of the unit's current readings at once. One faulty part normally moves several points, so the ranking sharpens as
readings come in. It is a SUGGESTION with its evidence ([knobs-and-suggestions]); the person still rules (cmod.custom.variance_rulings).

  faults(cat)            -> the faults of a circuit: {id, kind, cause, words, vary}
  rank(manager, unit)    -> {ranked: [...], next: the point that best tells the leaders apart | None, skipped, basis, runs}

The faults (each from the circuit rows, nothing typed per bench):
  open        each part's each leg, and each used header pin's joint (cst_netlist.OPEN_OHMS, the plan's 1 GOhm)
  bridge      each pair of the circuit's nets (cst_netlist.BRIDGE_OHMS, 0.1 Ohm). KNOB: every pair - a superset of the layout's adjacency on a circuit
              this small; the wm arc's wire routes narrow it once they exist
  value       each resistor at its E12 neighbours and one decade either side (a misread multiplier band is the classic one)
  reversed    each LED / diode turned round
  wrong pin   each used pin's wire on a header neighbour: on a used pin that joins the two nets; on an unused pin it reads exactly as the open joint, so
              it is named in that fault's words instead of ranked twice
A V reading is predicted with the meter in the deck (its cited input resistance, else FAULT_METER_OHMS): a fault that leaves a net floating reads
whatever the meter pulls it to, not what the bare circuit does.

The score: each reading's residual = (read - predicted) / scale, scale = the largest of its instrument band, half its tolerance band (the parts move a
faulty build too) and FLOOR (KNOBs). A fault EXPLAINS a reading when |residual| <= 1. Ranked by readings explained, then by the mean squared
residual. "none" (a correct build) is ranked with the rest, so a unit whose readings fit no fault better says so.
"""
import itertools
import math

from cmod.custom import config_rows as R

FAULT_METER_OHMS = 10e6                 # KNOB: a handheld DMM's usual 10 MOhm V input, when the reading's meter has none cited
FLOOR = {'V': 0.02, 'A': 20e-6}         # KNOB: the smallest scale a residual is divided by (20 mV, 20 uA)
E12 = (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)
CAUSE = {'open': 'open', 'open-pin': 'open', 'bridge': 'bridge', 'value': 'wrong-part-value', 'reversed': 'reversed-polarity', 'wrong-pin': 'wrong-pin', 'none': ''}
_RUNS = {}


def _e12_neighbours(ohms):
    if ohms <= 0:
        return []
    dec = 10 ** math.floor(math.log10(ohms) + 1e-9)
    m = ohms / dec
    i = min(range(len(E12)), key=lambda k: abs(E12[k] - m))
    out = []
    for k in (i - 1, i + 1):
        d = dec * (0.1 if k < 0 else 10 if k >= len(E12) else 1)
        out.append(round(E12[k % len(E12)] * d, 9))
    return sorted(set(out + [ohms * 10, ohms / 10]))


def _fmt_ohm(o):
    return ('%gk' % (o / 1000)) if o >= 1000 else '%g' % o


def faults(cat):
    import json
    from cmod.custom import test_procedures as TP
    from electrodevice.custom import cst_netlist as N
    out = [{'id': 'none', 'kind': 'none', 'cause': '', 'words': 'no fault: a correct build (the nominal)', 'vary': {}}]
    params = {c['name']: json.loads(c.get('params_json') or '{}') for c in N._components(cat)}
    for name, comp in cat['components'].items():
        for i, net in enumerate(comp['nets']):
            out.append({'id': 'open:%s:%s' % (name, net), 'kind': 'open', 'cause': 'open', 'vary': {'open_leg': (name, i)},
                        'words': '%s\'s %s leg open (a cold or missing joint, or the lead not in its hole)' % (name, net)})
        if comp['kind'] == 'resistor':
            try:
                ohms = float(params.get(name, {}).get('ohms'))
            except (TypeError, ValueError):
                ohms = 0.0
            for o in _e12_neighbours(ohms):
                out.append({'id': 'value:%s=%s' % (name, _fmt_ohm(o)), 'kind': 'value', 'cause': 'wrong-part-value', 'vary': {'r_scale': {name: o / ohms}},
                            'words': '%s is %s ohm, not %s (the wrong resistor; check its bands)' % (name, _fmt_ohm(o), _fmt_ohm(ohms))})
        if comp['kind'] in ('led', 'diode'):
            out.append({'id': 'reversed:%s' % name, 'kind': 'reversed', 'cause': 'reversed-polarity', 'vary': {'reverse': name},
                        'words': '%s turned round (the long leg is the anode)' % name})
    pins = cat['pins']
    for pin, d in pins.items():
        unused, used = [], []
        for q in TP._neighbours(pin):
            (used if q in pins else unused).append(q)
        out.append({'id': 'open-pin:%s' % pin, 'kind': 'open-pin', 'cause': 'open', 'vary': {'open_pin': pin},
                    'words': 'the wire at %s open (the header joint)%s' % (pin, (' - or the wire on %s instead, an unused pin: it reads the same' % ' / '.join(unused)) if unused else '')})
        for q in used:
            if pins[q]['net'] != d['net']:
                out.append({'id': 'wrong-pin:%s>%s' % (pin, q), 'kind': 'wrong-pin', 'cause': 'wrong-pin',
                            'vary': {'open_pin': pin, 'bridges': [(d['net'], pins[q]['net'])]},
                            'words': 'the wire meant for %s is on %s (its neighbour): %s joins %s' % (pin, q, d['net'], pins[q]['net'])})
    nets = sorted(n['net'] for n in cat['nets'].values())
    for a, b in itertools.combinations(nets, 2):
        out.append({'id': 'bridge:%s|%s' % (a, b), 'kind': 'bridge', 'cause': 'bridge', 'vary': {'bridges': [(a, b)]},
                    'words': '%s bridged to %s (a solder bridge, a stray strand, two leads in one row)' % (a, b)})
    return out


def _probe(p):
    if p['quantity'] == 'V dc':
        return 'v(%s)' % p['plus_at'].lower()
    return 'i(vam_%s)' % p['plus_at'].replace('-', '_').replace(':', '_').lower()


def _meter(p, acc):
    if p['quantity'] == 'V dc':
        ohms = float((acc or {}).get('input_ohms') or -1)
        return ('meter_v', (p['plus_at'], ohms if ohms > 0 else FAULT_METER_OHMS))
    burden = float((acc or {}).get('burden_v_per_a') or -1)
    return ('meter_i', (p['plus_at'], burden)) if burden > 0 else (None, None)


def predict(cat, state, fault, p, acc=None):
    """-> the value the point reads with this fault in the build (SI), or None."""
    from electrodevice.custom import cst_netlist as N
    mk, mv = _meter(p, acc)
    key = (cat['circuit'], state['name'], fault['id'], _probe(p), mk, mv)
    if key not in _RUNS:
        vary = dict(fault['vary'])
        if mk:
            vary[mk] = mv
        r = N.run(state, cat, N.PULLUP_OHMS[0], vary)
        v = r.get('measurements', {}).get(_probe(p)) if r.get('ok') else None
        _RUNS[key] = None if v is None else float(v)
    return _RUNS[key]


def _f(v, unit):
    return '0 %s' % unit if abs(v) < (1e-9 if unit == 'A' else 1e-6) else __import__('cmod.custom.measure_readings', fromlist=['fmt']).fmt(v, unit)


def _scale(p, j):
    half = ((j['tol_hi'] - j['tol_lo']) / 2.0) if j.get('tol_lo') is not None else 0.0
    return max(j.get('band') or 0.0, half, FLOOR.get(p['si_unit'], 0.0))


def rank(manager, unit, top=8):
    from cmod.custom import measure_readings as MR
    u = R.get(manager, 'BuiltUnit', unit)
    if u is None:
        raise R.ConfigRefused('no built unit %r' % unit, status=404)
    used, skipped, cat = [], [], None
    for r in MR.readings(manager, unit, standing=False):
        if not r['current']:
            continue
        p = R.get(manager, 'MeasurementPoint', r['point'])
        if r['stale']:
            skipped.append('%s: read on another build' % r['point'])
            continue
        if p is None or p['name'].endswith('-mp-v-5v-rail'):
            skipped.append('%s: the rail is the supply\'s (R_supply), not the circuit\'s - no fault moves it here' % r['point'])
            continue
        c, state = MR._circuit_state(manager, p)
        if state is None:
            skipped.append('%s: no circuit state' % r['point'])
            continue
        cat = cat or c
        _b, _w, acc = MR.band(manager, r.get('instrument') or '', p['quantity'], float(r['value']), r.get('range_max'))
        used.append((r, p, state, acc, _scale(p, r)))
    from electrodevice.custom import cst_netlist as N
    basis = ('ngspice .op per fault (cst_netlist: open %g ohm, bridge %g ohm), a V reading with the meter in the deck (cited, else FAULT_METER_OHMS %g ohm '
             'KNOB); residual / max(instrument band, half the tolerance band, FLOOR %g V / %g A KNOB); a SUGGESTION - the person rules'
             % (N.OPEN_OHMS, N.BRIDGE_OHMS, FAULT_METER_OHMS, FLOOR['V'], FLOOR['A']))
    if not used:
        return {'unit': unit, 'readings': 0, 'ranked': [], 'next': None, 'skipped': skipped, 'basis': basis,
                'words': 'no reading to rank against yet: measure a point of a node first'}
    fl = faults(cat)
    scored = []
    for f in fl:
        rows, ss, ok = [], 0.0, 0
        for r, p, state, acc, sc in used:
            pred = predict(cat, state, f, p, acc)
            if pred is None:
                continue
            res = (float(r['value']) - pred) / sc
            ss += res * res
            ok += abs(res) <= 1.0
            rows.append({'point': p['name'], 'read': float(r['value']), 'predicted': pred, 'residual': res,
                         'words': '%s: read %s, predicts %s' % (p['name'].split('-mp-')[-1], _f(float(r['value']), p['si_unit']), _f(pred, p['si_unit']))})
        if rows:
            scored.append(dict(f, explains=ok, of=len(rows), score=ss / len(rows), predictions=rows))
    scored.sort(key=lambda f: (-f['explains'], f['score'], f['id'] != 'none', f['id']))
    out, prev, rank_no = [], None, 0
    for i, f in enumerate(scored[:top]):
        sig = tuple(round(x['predicted'] / max(_scale_of(used, x['point']), 1e-15), 3) for x in f['predictions'])
        if sig != prev:
            rank_no = i + 1
        prev = sig
        out.append({'rank': rank_no, 'fault': f['id'], 'kind': f['kind'], 'cause': f['cause'], 'explains': f['explains'], 'of': f['of'],
                    'score': round(f['score'], 4), 'words': '%s - explains %d of %d reading(s): %s' % (f['words'], f['explains'], f['of'],
                                                                                                  '; '.join(x['words'] for x in f['predictions'])),
                    'predictions': f['predictions']})
    leaders = [f for f in scored if f['explains'] == scored[0]['explains'] and abs(f['score'] - scored[0]['score']) <= max(1.0, scored[0]['score'])][:6]
    nxt = _next_point(manager, u, cat, used, leaders) if len(leaders) > 1 else None
    first = out[0]
    tied = [x['fault'] for x in out if x['rank'] == 1]
    if len(tied) > 1:
        words = '%d faults tie first (%s): the readings so far do not tell them apart' % (len(tied), ', '.join(tied))
    elif first['fault'] != 'none':
        words = '%s ranks first: %s' % (first['fault'], first['words'])
    else:
        words = 'a correct build explains these readings best (no fault fits them better)'
    if nxt:
        words += '; to tell them apart, %s' % nxt['words']
    return {'unit': unit, 'readings': len(used), 'faults': len(fl), 'ranked': out, 'next': nxt, 'skipped': skipped, 'basis': basis, 'words': words}


def _scale_of(used, point):
    return next((sc for _r, p, _s, _a, sc in used if p['name'] == point), 1.0)


def _next_point(manager, u, cat, used, leaders):
    """The unread point (of any node of the unit's Bench Solution) where the leading faults' predictions differ most, in units of its scale."""
    from cmod.custom import measure_readings as MR
    read = {p['name'] for _r, p, _s, _a, _sc in used}
    best = None
    for node in R.rows(manager, 'StructNode', bench_solution=u['bench_solution']):
        for p in R.rows(manager, 'MeasurementPoint', node=node['name']):
            if p['name'] in read or p['origin'] == 'stale' or p['name'].endswith('-mp-v-5v-rail') or not p.get('state'):
                continue
            c, state = MR._circuit_state(manager, p)
            if state is None or c['circuit'] != cat['circuit']:
                continue
            sc = max((float(p['band_hi']) - float(p['band_lo'])) / 2.0, FLOOR.get(p['si_unit'], 0.0))
            preds = [(f['id'], predict(cat, state, f, p)) for f in leaders]
            preds = [(i, v) for i, v in preds if v is not None]
            if len(preds) < 2:
                continue
            spread = (max(v for _i, v in preds) - min(v for _i, v in preds)) / sc
            if best is None or spread > best['spread']:
                best = {'point': p['name'], 'where': p['where'], 'spread': round(spread, 3),
                        'words': 'measure %s (%s): %s' % (p['name'].split('-mp-')[-1], p['where'],
                                                          '; '.join('%s predicts %s' % (i, _f(v, p['si_unit'])) for i, v in preds))}
    return best if best and best['spread'] > 1.0 else None
