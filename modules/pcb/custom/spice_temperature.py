"""
@module pcb.custom.spice_temperature

tmp-1 / tmp-2 (AI-Notes/plans/TEMPERATURE_PLAN.md; the user's words 2026-10-31: "A number of parts have temperature tolerances and their drive and
signal data may vary with temperature" ... "Build it starting with whole temperagure, since a background temperature being the basis is the norm
anyways, then part level, and so on"): A PCB'S CIRCUIT SIMULATED AT A TEMPERATURE. Nothing new is modelled here: ngspice's own device models carry
their temperature terms (a diode's saturation current and gap, a transistor's gain, a MOSFET's mobility and threshold, a resistor's tc1 / tc2) and
this module only says WHICH temperature - the deck is pcb.custom.kicad_spice.build_deck's, the runs are kept as every run is (spice_runs).

  tmp-1, the board's (background) temperature
  grades(board)                       the usual rated ranges, each a sweep: low end, 25 C, high end (GRADES, each with its basis)
  reach(manager, board, rows=None)    one row per deck element: does temperature act on it, through what, can it have its own temperature
  run_at(manager, board, temp_c, part_temps=None, sweep='', runner=None, rows=None) -> result   one run, kept (SpiceRun.temp_c ...)
  sweep(manager, board, temps, runner=None, rows=None) -> (sweep name, results)                  one run per temperature, one sweep name
  compare(manager, board, sweep=None) -> (rows, why)   long form: each net at each temperature - min / max / final, the change from 25 C
  overlay(manager, board, sweep=None, max_rows=400)    long form chart rows: every node vector at every temperature, against the run's scale
  trend(manager, board, sweep=None)                    long form chart rows: each net's peak against temperature
  ratings(manager, board, temps, part_temps=None, rows=None)   each part with a rated range: inside it at every simulated temperature, or not

  tmp-2, each part at its own temperature on top of the background
  part_temperatures(manager, board, ambient_c, mode='final', rows=None, h=None) -> (rows, why)
      each part's temperature from the board over time (pcb.custom.thermal_transient, every placed part probed): its junction when its datasheet
      thermal model is given, else the board under its pads; mode 'final' = the end of the run (settled unless a pulse is still cooling), 'peak' =
      each part's own hottest moment (not one instant: different parts peak at different times - said)
  run_parts(manager, board, ambient_c, mode='final', runner=None, rows=None, h=None) -> result
      the board at ambient_c (.temp) and every part ngspice allows at its own temperature (instance temp=); one way - the run's powers do not
      feed back into the temperatures (that needs the thermal model in Cauer form: tmp-3)
With no manager (selftests) the rows live in this process only.
"""
import datetime
import json

ROOM_C = 25.0
#: the usual operating-temperature grades. 'commercial' and 'industrial' are vendors' conventions (no standard body sets them); the automotive
#: grades are the Automotive Electronics Council's AEC-Q100 operating-temperature grades (grade 3 = the industrial range)
GRADES = (
    ('commercial', 0.0, 70.0, 'commercial range, 0 .. 70 C: a vendors\' convention (no standard body sets it)'),
    ('industrial', -40.0, 85.0, 'industrial range, -40 .. 85 C: a vendors\' convention (= AEC-Q100 grade 3)'),
    ('automotive-grade-2', -40.0, 105.0, 'AEC-Q100 operating-temperature grade 2, -40 .. 105 C'),
    ('automotive-grade-1', -40.0, 125.0, 'AEC-Q100 operating-temperature grade 1, -40 .. 125 C'),
    ('automotive-grade-0', -40.0, 150.0, 'AEC-Q100 operating-temperature grade 0, -40 .. 150 C'),
)
#: the temperature terms of ngspice's models (the ngspice manual's model parameter tables) and the defaults that act when a model leaves them out
TEMP_TERMS = {'D': (('xti', 'eg', 'tnom', 'tt1', 'tbv1', 'trs', 'tcv'), 'ngspice\'s defaults: EG 1.11 eV, XTI 3 (silicon)'),
              'Q': (('xtb', 'xti', 'eg', 'tnom', 'trb1', 'trc1', 'tre1'), 'ngspice\'s defaults: XTB 0 (the gain does NOT change), XTI 3, EG 1.11 eV'),
              'M': (('tnom', 'kt1', 'kt2', 'ute', 'ua1', 'ub1', 'uc1', 'at', 'prt', 'tcv', 'bex'), 'the temperature dependence built into its level\'s '
                                                                                                 'equations (mobility, threshold, junctions)'),
              'J': (('xti', 'eg', 'tnom', 'vtotc', 'betatce'), 'ngspice\'s defaults: XTI 3, EG 1.11 eV')}


def _rows(manager, board, rows):
    from pcb.custom.thermal import _rows_of
    return rows if rows is not None else _rows_of(manager, board, ('SchematicSymbol', 'NetEndpoint', 'KiCadArtifact', 'PcbBoard', 'PcbPad'))


def grades(board):
    return [{'board': board, 'grade': g, 't_min_c': lo, 't_max_c': hi, 'temperatures': '%g, %g, %g C' % (lo, ROOM_C, hi), 'basis': basis}
            for g, lo, hi, basis in GRADES]


def grade_temps(grade):
    g = next((x for x in GRADES if x[0] == grade), None)
    return [g[1], ROOM_C, g[2]] if g else None


def reach(manager, board, rows=None):
    from pcb.custom import kicad_spice as P
    from pcb.custom.temperature_inputs import coefficients
    rows = _rows(manager, board, rows)
    d = P.build_deck(rows, coefficients=coefficients(manager, board, rows))
    arts = {a['path']: a['content'] for a in rows.get('KiCadArtifact') or []}
    out = []
    for name, e in sorted(d['elements'].items()):
        kind, ref = e['kind'], e.get('ref', name)
        lib = arts.get(e.get('library', ''), '')
        refusal = P.instance_temp_refusal(kind, lib, e.get('model', ''))
        row = {'board': board, 'ref': ref, 'element': name, 'kind': kind, 'model': e.get('model', ''), 'acts': 'no', 'through': '',
               'own_temperature': 'yes' if not refusal else 'no - %s' % refusal}
        if kind in ('R', 'C', 'L'):
            tc = d['temperature']['coefficients'].get(ref)
            if tc:
                row.update(acts='yes', through='tc1 %g /K, tc2 %g /K2 (%s)' % (tc[0], tc[1], tc[2]))
            else:
                row['through'] = ('an ideal %s with no temperature coefficient: unchanged by temperature (give its datasheet tc1 / tc2 on this tab)'
                                  % {'R': 'resistor', 'C': 'capacitor', 'L': 'inductor'}[kind])
        elif kind in TEMP_TERMS:
            mtype, params = P.model_card(lib, e.get('model', ''))
            terms, defaults = TEMP_TERMS[kind]
            have = ['%s=%s' % (t.upper(), params[t]) for t in terms if t in params]
            row.update(acts='yes', through=('model %s%s: %s' % (e.get('model', ''), ' (%s)' % mtype if mtype else '',
                                                               ('its own temperature terms ' + ', '.join(have)) if have else defaults)))
        elif kind == 'X':
            row.update(acts='inside its model', through='subcircuit %s: the devices inside respond to the board\'s temperature as their own models allow'
                                                        % e.get('model', ''))
        else:
            row['through'] = 'an ideal source: unchanged by temperature'
        out.append(row)
    return out


def _files(rows, includes):
    return {a['path']: a['content'] for a in rows.get('KiCadArtifact') or [] if a['path'] in includes}


def run_at(manager, board, temp_c, part_temps=None, sweep='', runner=None, rows=None, extra=None):
    """One run of the board's deck with the board at temp_c (and parts at their own, where ngspice allows), kept as a SpiceRun."""
    import socket
    from electrodevice.custom import ngspice_shared as NS
    from pcb.custom import kicad_spice as P
    from pcb.custom import spice_runs as SR
    from pcb.custom.temperature_inputs import coefficients
    rows = _rows(manager, board, rows)
    if not rows.get('SchematicSymbol'):
        return {'ok': False, 'error': 'no ingested schematic for %r' % board, 'status': 404}
    d = P.build_deck(rows, temp_c=temp_c, part_temps=part_temps, coefficients=coefficients(manager, board, rows))
    res = (runner or NS.run)(d['deck'], _files(rows, d['includes']))
    t = d['temperature']
    temperature = {'temp_c': temp_c, 'mode': 'parts' if t['part_temps'] else 'board', 'part_temps': t['part_temps'], 'sweep': sweep}
    name = SR.store(manager, board, d['deck'], res, 'local', socket.gethostname(), temperature=temperature)
    return dict(res, run=name, board=board, temperature=t, deck=d['deck'], problems=d['problems'], skipped=d['skipped'], **(extra or {}))


def sweep(manager, board, temps, runner=None, rows=None):
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='microseconds')   # two sweeps in one second stay apart
    name = '%s:sweep:%s' % (board, stamp)
    results = [run_at(manager, board, float(t), sweep=name, runner=runner, rows=rows) for t in temps]
    return name, results


def _sweep_runs(manager, board, sweep_name):
    from pcb.custom import spice_runs as SR
    runs = [r for r in SR.runs(manager, board) if r.get('sweep')]
    if not runs:
        return [], '', 'no temperature sweep kept for %s - run one (a grade on the Temperature tab)' % board
    name = sweep_name or max(r['sweep'] for r in runs)   # the newest: sweep names end in their UTC start time
    mine = sorted((r for r in runs if r['sweep'] == name), key=lambda r: float(r['temp_c']))
    if not mine:
        return [], name, 'no sweep %r for %s' % (name, board)
    return mine, name, ''


def compare(manager, board, sweep=None):
    from pcb.custom import spice_runs as SR
    runs, name, why = _sweep_runs(manager, board, sweep)
    if why:
        return [], why
    done = [r for r in runs if r['ok']]
    if not done:
        return [], 'sweep %s: no temperature ran (%s)' % (name, '; '.join('%g C: %s' % (float(r['temp_c']), r['status']) for r in runs))
    room = min(done, key=lambda r: abs(float(r['temp_c']) - ROOM_C))
    by_run = {r['name']: {p['net']: p for p in SR.projection(manager, board, r['name'])[0]} for r in done}
    out = []
    for r in done:
        t = float(r['temp_c'])
        for net, p in sorted(by_run[r['name']].items()):
            if p['basis'].startswith('no vector'):
                continue
            ref = by_run[room['name']].get(net)
            change = p['max'] - ref['max'] if ref else 0.0
            dt = t - float(room['temp_c'])
            out.append({'net': net, 'temp_c': t, 'unit': p['unit'], 'min': p['min'], 'max': p['max'], 'final': p['final'], 'at': p['at'],
                        'peak_change': change, 'peak_change_per_k': change / dt if dt else 0.0, 'run': r['name'], 'sweep': name,
                        'basis': 'peak = %s; the change is from the run at %g C' % ('the largest |V| of the AC sweep' if p['unit'] == '|V|' else
                                                                                   'the highest value of the transient', float(room['temp_c']))})
    skipped = [r for r in runs if not r['ok']]
    for r in skipped:
        out.append({'net': '', 'temp_c': float(r['temp_c']), 'unit': '', 'min': -1.0, 'max': -1.0, 'final': -1.0, 'at': '', 'peak_change': 0.0,
                    'peak_change_per_k': 0.0, 'run': r['name'], 'sweep': name, 'basis': 'this temperature did not run: %s' % r['status']})
    return out, ''


def trend(manager, board, sweep=None):
    rows, why = compare(manager, board, sweep)
    return [{'x': r['temp_c'], 'y': r['max'], 'series': '%s peak (%s)' % (r['net'], r['unit'])} for r in rows if r['net']], why


def overlay(manager, board, sweep=None, max_rows=400):
    from pcb.custom import spice_runs as SR
    runs, name, why = _sweep_runs(manager, board, sweep)
    if why:
        return [], why
    out = []
    for r in runs:
        if not r['ok']:
            continue
        status, c = SR.chart(manager, r['name'], max_rows)
        if status == 200:
            out += [dict(p, series='%s at %g C' % (p['series'], float(r['temp_c']))) for p in c['rows'] if '#branch' not in p['series']]
    return out, ''


def ratings(manager, board, temps, part_temps=None, rows=None):
    """Each part with a rated range given: its lowest and highest simulated temperature against the range (its own, when it had one)."""
    from pcb.custom.temperature_inputs import behaviour
    rows = _rows(manager, board, rows)
    part_temps = part_temps or {}
    out = []
    for s in sorted((s for s in rows.get('SchematicSymbol') or [] if s.get('power') != 'yes'), key=lambda s: s['ref']):
        b = behaviour(manager, board, s['ref'], s)
        if not b or not b['given'] & {'t_min_c', 't_max_c'}:
            continue
        seen = [part_temps[s['ref']]] if s['ref'] in part_temps else list(temps)
        lo, hi = min(seen), max(seen)
        low_margin = lo - b['t_min_c'] if 't_min_c' in b['given'] else ''
        high_margin = b['t_max_c'] - hi if 't_max_c' in b['given'] else ''
        bad = [w for w, m in (('BELOW its rated minimum', low_margin), ('ABOVE its rated maximum', high_margin)) if m != '' and m < 0]
        out.append({'board': board, 'ref': s['ref'], 'value': s.get('value', ''), 'rated_min_c': b['t_min_c'] if 't_min_c' in b['given'] else '',
                    'rated_max_c': b['t_max_c'] if 't_max_c' in b['given'] else '', 'simulated_c': ', '.join('%g' % t for t in seen),
                    'low_margin_c': low_margin, 'high_margin_c': high_margin, 'verdict': ' and '.join(bad) if bad else 'inside its rated range',
                    'basis': '%s; simulated at %s' % (b['words'], 'its own temperature' if s['ref'] in part_temps else 'the board\'s temperatures')})
    return out


def part_temperatures(manager, board, ambient_c, mode='final', rows=None, h=None):
    from pcb.custom import thermal_transient as TT
    from pcb.custom.thermal import H_FREE_AIR
    if mode not in ('final', 'peak'):
        return [], 'mode must be final or peak, got %r' % mode
    rows = _rows(manager, board, rows)
    summary, junctions, _chart, why = TT.transient(manager, board, rows=rows, h=h or H_FREE_AIR, ambient_c=ambient_c, probe_all=True)
    if why:
        return [], 'no board temperatures: %s - every part stays at the background %g C' % (why, ambient_c)
    out = []
    for j in junctions:
        modelled = j['junction_peak_rise_c'] != -1.0
        rise = (j['junction_%s_rise_c' % mode] if modelled else j['board_%s_rise_c' % mode])
        out.append({'board': board, 'ref': j['ref'], 'power_w': j['power_w'], 'temp_c': ambient_c + rise, 'rise_c': rise, 'mode': mode,
                    'from': ('its junction: the board under it + its datasheet Zth (%s)' % j['model']) if modelled else
                            ('the board under its pads' + ('' if j['power_w'] else ' (it takes no power itself: the heat is its neighbours\')')),
                    'basis': 'background %g C + the %s rise from the board over time (t_end %g s; %s)%s'
                             % (ambient_c, 'end-of-run' if mode == 'final' else 'own peak', summary['t_end_s'], summary['source'],
                                '' if mode == 'final' else ' - each part at its own hottest moment, not one instant')})
    return sorted(out, key=lambda r: -r['temp_c']), ''


def run_parts(manager, board, ambient_c, mode='final', runner=None, rows=None, h=None):
    rows = _rows(manager, board, rows)
    temps, why = part_temperatures(manager, board, ambient_c, mode, rows, h)
    if why and not temps:
        return dict(run_at(manager, board, ambient_c, runner=runner, rows=rows), parts_note=why)
    return run_at(manager, board, ambient_c, part_temps={r['ref']: r['temp_c'] for r in temps}, runner=runner, rows=rows,
                  extra={'part_temperatures': temps})

