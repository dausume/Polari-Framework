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

The plain IEC 61000-4-2 network reproduces the standard's main discharge, NOT its sub-nanosecond first current peak (the gun's own waveform). Checked
2026-10-31 on econ-core's libngspice: the deck's own time step resolves the HBM event (the rectifier's anode peak 3.43 V and 1.332 A equal a forced
2 ns step's, 1.332 A = 2000 V / 1500 Ohm).

esd-4: `iec-contact-waveform` = the standard's OWN equation for the ideal contact discharge current (IEC 61000-4-2:2008 §6.2, the equation under
Figure 2: two Heidler terms, tau1 1.1 ns, tau2 2 ns, tau3 12 ns, tau4 37 ns, I1 16.6 A, I2 9.3 A at 4 kV, n 1.8), scaled linearly with the level (Table 3
scales linearly: 7.5 / 15 / 22.5 / 30 A first peak at 2 / 4 / 6 / 8 kV) and injected as an ngspice PWL current source sampled from it (every sample is
a solver breakpoint, so the sub-nanosecond peak is resolved). It reproduces Table 3 at 4 kV (iec_check). It is the current the standard calibrates
into its 2 Ohm target: forced into a high-impedance net it overstates the voltage there (a real generator's 150 pF / 330 Ohm would limit it) - said.

esd-3: an area's `protection_parts` (board.custom.protection_parts, each with a derived model) are placed from the injected net to ground for both
runs, each through its own 0 V meter, and each one's peak current is checked against its cited I_PP.
"""
import json

MODELS = {
    'hbm': {'kind': 'network', 'c_f': 100e-12, 'r_ohm': 1500.0, 'levels': [500.0, 1000.0, 2000.0, 4000.0],
            'standard': 'human body model, ANSI/ESDA/JEDEC JS-001: 100 pF discharged through 1.5 kOhm (tau 150 ns)', 'caveat': ''},
    'iec-contact': {'kind': 'network', 'c_f': 150e-12, 'r_ohm': 330.0, 'levels': [2000.0, 4000.0, 6000.0, 8000.0],
                    'standard': 'IEC 61000-4-2 contact discharge: 150 pF through 330 Ohm, levels 1-4 = 2 / 4 / 6 / 8 kV',
                    'caveat': 'the plain 150 pF / 330 Ohm network gives the main discharge, not the standard\'s sub-nanosecond first current peak '
                              '(iec-contact-waveform has it)'},
    'iec-contact-waveform': {'kind': 'current', 'c_f': 150e-12, 'r_ohm': -1.0, 'levels': [2000.0, 4000.0, 6000.0, 8000.0],
                             'standard': ('IEC 61000-4-2:2008 §6.2 ideal contact discharge current (the equation under Figure 2, scaled linearly from '
                                          '4 kV): first peak 3.75 A per kV at 0.8 ns, 2 A per kV at 30 ns, 1 A per kV at 60 ns (Table 3)'),
                             'caveat': ('the standard\'s calibration current, forced into the net: right for a low-impedance (clamped or capacitive) net, '
                                        'an overstatement at a high-impedance one, where a real generator\'s 150 pF / 330 Ohm limits the voltage')},
}
SW_MODEL = '.model esdsw sw vt=0.5 vh=0 ron=0.01 roff=1e12'
from pcb.custom.esd_iec import IEC, iec_check, iec_current, iec_samples, _pwl  # noqa: E402,F401 - esd-4's equation, its own file


def protection_lines(node, parts):
    """esd-3: each protection part from the net to ground through its own 0 V meter (vector vprotmK#branch); parts = [(name, model_name, .model line)]."""
    out = []
    for k, (name, mname, mline) in enumerate(parts, 1):
        out += ['* esd-3: protection part %s (board.custom.protection_parts)' % name, 'Vprotm%d %s esd_p%d DC 0' % (k, node, k),
                'Dprot%d 0 esd_p%d %s' % (k, k, mname)]
    # Gear integration when a clamp is in: the trapezoidal rule rings step to step at a breakdown knee (seen on econ-core: +-0.2 A around the
    # 1.33 A HBM current through the SMBJ5.0A, step after step), Gear damps it - an established ngspice method. One step at the edge can still
    # overstate the clamp's current (1.50 A against the source's 1.33 A) - on the safe side for the I_PP check, and the rows show the source beside it
    return out + sorted({p[2] for p in parts}) + (['.options method=gear'] if parts else [])


def event_lines(node, model, level_v, t_event):
    m = MODELS[model]
    if m['kind'] == 'current':
        return (['* esd-4: %s at %g V into %s at %g s (pcb.custom.esd_events)' % (model, level_v, node, t_event)] + _pwl(t_event, level_v)
                + ['Vesdmeas esd_m %s DC 0' % node])
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


def protection_of(manager, a):
    """([(name, model_name, .model line)], why): the area's protection parts, each with its derived model - a part that cannot be modelled is refused."""
    from board.custom import protection_parts as PP
    out = []
    for name in [x.strip() for x in str(a.get('protection_parts') or '').split(',') if x.strip()]:
        r = PP.part(name, manager)
        if r is None:
            return [], 'no protection part %r in the catalogue (%s)' % (name, ', '.join(x['name'] for x in PP.catalogue(manager)))
        mname, line, _, why = PP.spice_model(r)
        if why:
            return [], '%s cannot be simulated: %s' % (name, why)
        out.append((name, mname, line))
    return out, ''


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
    parts, why = protection_of(manager, a)
    if why:
        return {'ok': False, 'status': 422, 'error': why}
    files = {x['path']: x['content'] for x in rows.get('KiCadArtifact') or [] if x['path'] in d['includes']}
    host = socket.gethostname()
    out = {}
    for which, v in (('baseline', 0.0), ('event', level)):
        extra = event_lines(node, model, v, te) + protection_lines(node, parts)
        deck = d['deck'].replace('\n.end\n', '\n' + '\n'.join(extra) + '\n.end\n')
        res = (runner or NS.run)(deck, files)
        ev = {'area': area, 'model': model, 'level_v': v, 'net': inject, 'node': node, 't_event': te, 'protected': protected, 'role': which,
              'baseline': out.get('baseline', {}).get('run', '')}
        if parts:
            ev['protection'] = [p[0] for p in parts]
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
    if abs_max < 0 and float(ev.get('foothold_max_v', -1.0)) >= 0:   # esd-5: the foothold's own cited maximum
        abs_max = float(ev['foothold_max_v'])
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
    parts = protection_rows(manager, ev, e, after, run)
    level = float(ev['level_v'])
    summary = {'run': run, 'baseline': ev['baseline'], 'area': ev['area'], 'model': ev['model'], 'level_v': level, 'net': ev['net'],
               't_event_s': te, 'peak_current_a': i_pk,
               'expected_current_a': level / m['r_ohm'] if m['kind'] == 'network' else iec_current_peak(level),
               'energy_j': 0.5 * m['c_f'] * level ** 2, 'protection_parts': ', '.join(p['part'] for p in parts) or 'none',
               'verdict': ('BREAKS' if any(x['breaks'].startswith('BREAKS') for x in prot) or any(p['breaks'].startswith('BREAKS') for p in parts) else
                           'does not recover in time' if any(x['recovered'].startswith('NO') for x in prot) else
                           'survives, recovers in time' + ('' if abs_max >= 0 else ' (break check undetermined: no absolute maximum)')),
               'basis': ('%s; injected at %s at %g s through a 0 V meter (peak current against %s); compared point by point with the same deck '
                         'and source at 0 (run %s); criterion: %s%s%s'
                         % (m['standard'], ev['net'], te, 'level / R' if m['kind'] == 'network' else 'Table 3\'s first peak, 3.75 A per kV',
                            ev['baseline'], _crit(a), ('; protection parts placed from the net to ground in both runs: %s, each against its cited I_PP'
                                                       % ', '.join(p['part'] for p in parts)) if parts else '',
                            ('; ' + m['caveat']) if m['caveat'] else '')
                         + ('; the pin alone - no chip clamp diodes, no circuit around it (knobs pin_cap_pf / hold_ohm on the area); absolute maximum %s'
                            % ('the area\'s' if float(a['abs_max_v']) >= 0 else 'the foothold\'s max_volts' if abs_max >= 0 else 'not given')
                            if ev.get('pin_only') else ''))}
    return summary, rows, ''


def iec_current_peak(level_v):
    """Table 3's first peak: 3.75 A per kV (7.5 / 15 / 22.5 / 30 A at 2 / 4 / 6 / 8 kV)."""
    return 3.75 * level_v / 1000.0


def protection_rows(manager, ev, e, after, run):
    """esd-3: each protection part's peak current (its 0 V meter) against its cited I_PP."""
    import numpy as np
    from board.custom import protection_parts as PP
    out = []
    for k, name in enumerate(ev.get('protection') or [], 1):
        r = PP.part(name, manager) or {}
        i = np.array(e.get('vprotm%d#branch' % k, [0.0]))
        pk = float(np.abs(i[after]).max()) if len(i) == len(after) else -1.0
        ipp = float(r.get('i_pp_a', -1.0))
        src = np.array(e.get('vesdmeas#branch', [0.0]))
        out.append({'part': name, 'part_number': r.get('part_number', ''), 'peak_current_a': pk,
                    'source_peak_a': float(np.abs(src[after]).max()) if len(src) == len(after) else -1.0, 'i_pp_a': ipp, 'pulse': r.get('pulse', ''),
                    'breaks': ('undetermined - no I_PP given' if ipp <= 0 else
                               'BREAKS: %.4g A is above its %g A peak pulse current (%s)' % (pk, ipp, r.get('pulse')) if pk > ipp else
                               'no (%.3g %% of its I_PP)' % (100.0 * pk / ipp)),
                    'source': r.get('document') or r.get('origin', ''), 'run': run})
    return out


def protection_results(manager, run):
    """(rows, why): the page's per-protection-part rows for one kept event run."""
    import numpy as np
    r, ev = _event(manager, run)
    if r is None or ev.get('role') != 'event':
        return [], 'run %r is not a kept ESD event run' % run
    e = _vectors(manager, run)
    if 'time' not in e:
        return [], 'the event run kept no time vector'
    rows = protection_rows(manager, ev, e, np.array(e['time']) >= float(ev['t_event']), run)
    return rows, '' if rows else 'no protection parts in this event (add one to the area: protection_parts)'


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
