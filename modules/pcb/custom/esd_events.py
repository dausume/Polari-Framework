"""
@module pcb.custom.esd_events

esd-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md; the user's words 2026-10-31: "establish simulations for testing where we emulate ESD events and check that the
drive conditions handle it smoothly and do not break the circuits"): AN ESD EVENT ON A PCB'S CIRCUIT. The deck is Polari's own (pcb.custom.kicad_spice);
the discharge network is the standard's own (MODELS) - a capacitor charged to the test level, switched at `t_event` into the flagged net through the
standard's resistor (ngspice voltage-controlled switches, so the circuit starts from its real operating point and is mid-operation when it is hit).
The SAME deck with the capacitor charged to 0 V is the baseline (same topology, no event). Both runs are kept (SpiceRun, event_json says which).

  MODELS                         hbm (ANSI/ESDA/JEDEC JS-001: 100 pF, 1.5 kOhm) | iec-contact (IEC 61000-4-2: 150 pF, 330 Ohm) - each with its levels
  event_lines(node, model, level_v, t_event) -> deck lines (the network + a 0 V source measuring the discharge current, vector vesdmeas#branch)
  run_event(manager, board, area, model=None, level_v=None, t_event=None, runner=None, rows=None) -> result
      the area's network at its level (or the given ones), injected at its net; t_event default = a quarter of the deck's own .tran stop (after
      start-up); -> {ok, run, baseline, summary, rows} or a refusal in words
  results(manager, run) -> (summary, rows, why)   recomputed from the kept vectors: per node its peak, its rise over the baseline, the break check
      against the area's abs max, the recovery time and whether it meets the area's criterion
  chart(manager, run, max_points=600) -> (rows, why)   long form: each protected node with the event and without it, against time

The plain IEC 61000-4-2 network reproduces the standard's main discharge, NOT its sub-nanosecond first current peak (the gun's own waveform) - said in
every summary until a published waveform-matched network is adopted (esd-4). Checked 2026-10-31 on econ-core's libngspice: the deck's own time
step resolves the HBM event (the rectifier's anode peak 3.43 V and 1.332 A equal a forced 2 ns step's, 1.332 A = 2000 V / 1500 Ohm).
"""
import json

MODELS = {
    'hbm': {'c_f': 100e-12, 'r_ohm': 1500.0, 'levels': [500.0, 1000.0, 2000.0, 4000.0],
            'standard': 'human body model, ANSI/ESDA/JEDEC JS-001: 100 pF discharged through 1.5 kOhm (tau 150 ns)', 'caveat': ''},
    'iec-contact': {'c_f': 150e-12, 'r_ohm': 330.0, 'levels': [2000.0, 4000.0, 6000.0, 8000.0],
                    'standard': 'IEC 61000-4-2 contact discharge: 150 pF through 330 Ohm, levels 1-4 = 2 / 4 / 6 / 8 kV',
                    'caveat': 'the plain 150 pF / 330 Ohm network gives the main discharge, not the standard\'s sub-nanosecond first current peak'},
}
SW_MODEL = '.model esdsw sw vt=0.5 vh=0 ron=0.01 roff=1e12'


def event_lines(node, model, level_v, t_event):
    m = MODELS[model]
    return ['* esd-1: %s at %g V into %s at %g s (pcb.custom.esd_events)' % (model, level_v, node, t_event),
            'Vesdchg esd_chg 0 DC %g' % level_v, 'Resdchg esd_chg esd_k 1', 'Sesdchg esd_k esd_c esd_off 0 esdsw', 'Cesd esd_c 0 %g' % m['c_f'],
            'Sesddis esd_c esd_r esd_on 0 esdsw', 'Resd esd_r esd_m %g' % m['r_ohm'], 'Vesdmeas esd_m %s DC 0' % node,
            'Vesdon esd_on 0 PULSE(0 1 %g 1n 1n 1 2)' % t_event, 'Vesdoff esd_off 0 PULSE(1 0 %g 1n 1n 1 2)' % t_event, SW_MODEL]


def _tran(deck):
    from pcb.custom.thermal import spice_number
    for line in deck.splitlines():
        p = line.split()
        if p and p[0].lower() == '.tran' and len(p) >= 3:
            return spice_number(p[1]), spice_number(p[2])
    return None, None


def _area(manager, name):
    from board.custom import esd_areas as EA
    o = EA._find(manager, name)
    return {k: EA._get(o, k) for k in EA._fields()} if o is not None else None


def _nets_of(rows, area):
    """(inject net, protected nets, why) from the area's scope and target."""
    if area['scope'] == 'net':
        inject, protected = area['inject_net'] or area['target'], [area['target']]
    elif area['scope'] == 'foothold':
        f = next((x for x in rows.get('BoardFoothold') or [] if x.get('foothold') == area['target']), None)
        if f is None or not f.get('net'):
            return '', [], 'foothold %r has no net on this board' % area['target']
        inject, protected = area['inject_net'] or f['net'], [f['net']]
    else:
        protected = sorted({e['net'] for e in rows.get('NetEndpoint') or [] if e['ref'] == area['target'] and e['net'] not in ('GND', '0')})
        inject = area['inject_net']
        if not inject:
            return '', protected, 'a part-scope area needs inject_net (which of %s pins\' nets the discharge enters: %s)' % (area['target'], ', '.join(protected))
    return inject, protected, ''


def _rows(manager, board, rows):
    from pcb.custom.thermal import _rows_of
    rows = dict(rows) if rows is not None else _rows_of(manager, board, ('SchematicSymbol', 'NetEndpoint', 'KiCadArtifact'))
    if 'BoardFoothold' not in rows:   # a PCB's stored footholds (board module) - a foothold-scope area names one
        from board.custom import footholds as FH
        rows['BoardFoothold'] = FH.for_definition('layers', board, manager=manager)[0]
    return rows


def run_event(manager, board, area, model=None, level_v=None, t_event=None, runner=None, rows=None):
    import socket
    from electrodevice.custom import ngspice_shared as NS
    from pcb.custom import kicad_spice as P
    from pcb.custom import spice_runs as SR
    a = _area(manager, area)
    if a is None:
        return {'ok': False, 'status': 404, 'error': 'no ESD area %r' % area}
    if a['definition_kind'] != 'layers' or a['definition'] != board:
        return {'ok': False, 'status': 409, 'error': 'area %r belongs to %s/%s - an event runs on a PCB\'s circuit (layers/%s)'
                % (area, a['definition_kind'], a['definition'], board)}
    model = model or a['model']
    if model not in MODELS:
        return {'ok': False, 'status': 400, 'error': 'model must be one of %s' % ', '.join(MODELS)}
    level = float(level_v if level_v is not None else a['level_v'])
    rows = _rows(manager, board, rows)
    if not rows.get('SchematicSymbol'):
        return {'ok': False, 'status': 404, 'error': 'no ingested schematic for %r' % board}
    inject, protected, why = _nets_of(rows, a)
    if why:
        return {'ok': False, 'status': 422, 'error': why}
    d = P.build_deck(rows)
    node = P.node_name(inject)
    if node not in {n for e in d['elements'].values() for n in e['nodes']}:
        return {'ok': False, 'status': 422, 'error': 'net %r (node %s) is not in the circuit\'s deck' % (inject, node)}
    _, tstop = _tran(d['deck'])
    if not tstop:
        return {'ok': False, 'status': 422, 'error': 'the deck has no .tran analysis - an ESD event needs a transient run'}
    te = float(t_event) if t_event else tstop / 4.0
    if not 0 < te < tstop:
        return {'ok': False, 'status': 400, 'error': 't_event must be inside the run (0 .. %g s)' % tstop}
    files = {x['path']: x['content'] for x in rows.get('KiCadArtifact') or [] if x['path'] in d['includes']}
    host = socket.gethostname()
    out = {}
    for which, v in (('baseline', 0.0), ('event', level)):
        deck = d['deck'].replace('\n.end\n', '\n' + '\n'.join(event_lines(node, model, v, te)) + '\n.end\n')
        res = (runner or NS.run)(deck, files)
        ev = {'area': area, 'model': model, 'level_v': v, 'net': inject, 'node': node, 't_event': te, 'protected': protected, 'role': which,
              'baseline': out.get('baseline', {}).get('run', '')}
        out[which] = dict(res, run=SR.store(manager, board, deck, res, 'local', host, event=ev))
    ok = bool(out['event'].get('ok') and out['baseline'].get('ok'))
    if not ok:
        bad = out['event'] if not out['event'].get('ok') else out['baseline']
        return {'ok': False, 'status': 503 if 'refused' in bad else 422, 'error': bad.get('refused') or '; '.join(bad.get('errors') or []) or 'no vectors',
                'run': out['event']['run'], 'baseline': out['baseline']['run']}
    summary, result_rows, why = results(manager, out['event']['run'])
    return {'ok': not why, 'run': out['event']['run'], 'baseline': out['baseline']['run'], 'summary': summary, 'rows': result_rows, 'error': why}


def _vectors(manager, run):
    from pcb.custom import spice_runs as SR
    return {v['vector'].lower(): json.loads(v['values_json']) for v in SR._table(manager, 'SpiceVector') if v['run'] == run}


def _event(manager, run):
    from pcb.custom import spice_runs as SR
    r = next((x for x in SR._table(manager, 'SpiceRun') if x['name'] == run), None)
    return (r, json.loads(r.get('event_json') or '{}')) if r else (None, {})


def results(manager, run):
    import numpy as np
    r, ev = _event(manager, run)
    if r is None or not ev or ev.get('role') != 'event':
        return None, [], 'run %r is not a kept ESD event run' % run
    a = _area(manager, ev['area']) or {'abs_max_v': -1.0, 'recover_pct': 5.0, 'recover_mv': 50.0, 'recover_us': 10.0}
    e, b = _vectors(manager, run), _vectors(manager, ev['baseline'])
    if 'time' not in e or 'time' not in b:
        return None, [], 'the event run or its baseline kept no time vector'
    t, t0, te = np.array(e['time']), np.array(b['time']), float(ev['t_event'])
    after = t >= te
    m = MODELS[ev['model']]
    i_pk = float(np.abs(np.array(e.get('vesdmeas#branch', [0.0]))[after]).max()) if 'vesdmeas#branch' in e else -1.0
    protected = {n.lower() for n in ev['protected']}
    from pcb.custom import kicad_spice as P
    protected_nodes = {P.node_name(n).lower() for n in ev['protected']}
    abs_max, pct, mv, us = float(a['abs_max_v']), float(a['recover_pct']), float(a['recover_mv']), float(a['recover_us'])
    rows = []
    for name in sorted(k for k in e if k != 'time' and '#branch' not in k and not k.startswith('esd_') and k in b):
        y, y0 = np.array(e[name]), np.interp(t, t0, np.array(b[name]))
        k = int(np.argmax(np.abs(y) * after))
        diff = np.abs(y - y0)
        tol = np.maximum(pct / 100.0 * np.abs(y0), mv / 1000.0)
        out_idx = np.where(after & (diff > tol))[0]
        if not len(out_idx):
            rec = 0.0
        elif out_idx[-1] == len(t) - 1:
            rec = -1.0
        else:
            rec = float(t[out_idx[-1] + 1] - te)
        is_p = name in protected or name in protected_nodes
        breaks = ('undetermined - no absolute maximum given' if abs_max < 0 else
                  'BREAKS: %.4g V is above the %g V absolute maximum' % (abs(y[k]), abs_max) if abs(y[k]) > abs_max else 'no')
        recovered = ('yes' if 0 <= rec <= us * 1e-6 else
                     'NO - not back by the end of the run (%.4g s after the event)' % (t[-1] - te) if rec < 0 else
                     'NO - back after %.4g s (the criterion is %g us)' % (rec, us))
        rows.append({'node': name, 'protected': is_p, 'peak_v': float(y[k]), 'peak_at_s': float(t[k]), 'baseline_at_peak_v': float(y0[k]),
                     'rise_v': float(diff[after].max()), 'abs_max_v': abs_max, 'breaks': breaks if is_p else '(not protected)',
                     'recovered_after_s': rec, 'recovered': recovered if is_p else '(not protected)', 'final_offset_v': float(y[-1] - y0[-1]),
                     'run': run})
    rows.sort(key=lambda x: (not x['protected'], x['node']))
    prot = [x for x in rows if x['protected']]
    summary = {'run': run, 'baseline': ev['baseline'], 'area': ev['area'], 'model': ev['model'], 'level_v': float(ev['level_v']), 'net': ev['net'],
               't_event_s': te, 'peak_current_a': i_pk, 'expected_current_a': float(ev['level_v']) / m['r_ohm'],
               'energy_j': 0.5 * m['c_f'] * float(ev['level_v']) ** 2,
               'verdict': ('BREAKS' if any(x['breaks'].startswith('BREAKS') for x in prot) else
                           'does not recover in time' if any(x['recovered'].startswith('NO') for x in prot) else
                           'survives, recovers in time' + ('' if abs_max >= 0 else ' (break check undetermined: no absolute maximum)')),
               'basis': ('%s; injected at %s at %g s through a 0 V meter (peak current against level / R); compared point by point with the same deck '
                         'and network charged to 0 V (run %s); criterion: %s%s'
                         % (m['standard'], ev['net'], te, ev['baseline'], _crit(a), ('; ' + m['caveat']) if m['caveat'] else ''))}
    return summary, rows, ''


def _crit(a):
    from board.custom.esd_areas import criterion_words
    return criterion_words(a)


def chart(manager, run, max_points=600):
    import numpy as np
    r, ev = _event(manager, run)
    if r is None or ev.get('role') != 'event':
        return [], 'run %r is not a kept ESD event run' % run
    from pcb.custom import kicad_spice as P
    e, b = _vectors(manager, run), _vectors(manager, ev['baseline'])
    t, t0 = np.array(e.get('time', [])), np.array(b.get('time', []))
    out = []
    for net in ev['protected']:
        node = P.node_name(net).lower()
        if node not in e or node not in b:
            continue
        for label, tt, yy in (('%s with the event' % net, t, e[node]), ('%s without it' % net, t0, b[node])):
            stride = max(1, -(-len(tt) // int(max_points)))
            # every solver point within 50 us of the event (a stride alone would step over a sub-microsecond spike), a stride elsewhere
            keep = sorted(set(range(0, len(tt), stride)) | set(int(i) for i in np.where(np.abs(tt - float(ev['t_event'])) <= 50e-6)[0]))
            out += [{'x': float(tt[i]), 'y': float(yy[i]), 'series': label} for i in keep]
    return out, '' if out else 'no protected node vector in run %s' % run
