"""
@module board.custom.board_temperature

tmp-1 / tmp-2 (AI-Notes/plans/TEMPERATURE_PLAN.md): the Board Details page's TEMPERATURE parts of a PCB - thin row shapes over
pcb.custom.spice_temperature and pcb.custom.temperature_inputs (board.custom.board_details dispatches here).

  temperature(definition, which, manager, params) -> (rows, why)
      temperature-at        one row: run the circuit with the whole board at a typed temperature (the page edits temp_c)
      temperature-grades    the usual rated ranges, each a sweep (the page's row button runs it)
      temperature-reach     each deck element: does temperature act on it, through what, can it have its own
      temperature-sweep     each net at each temperature of the newest sweep, and the change from 25 C
      temperature-trend     chart rows: each net's peak against temperature
      temperature-overlay   chart rows: every node vector at every temperature
      temperature-parts     each part's rated range and coefficients (click one to give them)
      temperature-inputs    ?ref= the four numbers a person can give that part (signed)
      temperature-ratings   each part with a rated range against the sweep's temperatures
      part-run              tmp-2: two rows (end of run / each part's peak): run with every part at its own temperature (the page edits ambient_c)
      part-temperatures     tmp-2: each part's own temperature at the newest part-level run's background (25 C before one)
      self-heat-run         tmp-3: one row - run the loop at a typed background (the page edits ambient_c); the newest loop's verdict beside it
      self-heating          tmp-3: the newest loop's passes - each part's power, the temperature it ran at, the one it heats to, the change
      curve-catalogue       tmp-5: the cited curves (click one, then a part, to give that part the curve)
      temperature-curves    tmp-5: each part's curves at the newest sweep's temperatures (else -40 / 25 / 85 / 125 C), and what the deck does
      curve-run             tmp-5: three rows (nominal / low / high corner): run at a typed temperature with the curves in the deck
"""
PARTS = ('temperature-at', 'temperature-grades', 'temperature-reach', 'temperature-sweep', 'temperature-trend', 'temperature-overlay',
         'temperature-parts', 'temperature-inputs', 'temperature-ratings', 'part-run', 'part-temperatures', 'self-heat-run', 'self-heating',
         'curve-catalogue', 'temperature-curves', 'curve-run')
CURVE_TEMPS = (-40.0, 25.0, 85.0, 125.0)


def _latest(manager, board, mode):
    from pcb.custom import spice_runs as SR
    return next((r for r in SR.runs(manager, board) if r.get('temp_mode') in mode), None)


def temperature(definition, which, manager, params):
    from pcb.custom import spice_temperature as ST
    from pcb.custom import temperature_inputs as TI
    params = params or {}
    if which == 'temperature-at':
        last = _latest(manager, definition, ('board', 'parts'))
        return [{'board': definition, 'temp_c': float(last['temp_c']) if last else ST.ROOM_C, 'signed': True,
                 'last_run': ('%s - %s' % (last['temperature'], last['status'])) if last else 'none yet',
                 'how': 'type a temperature (C) and press Enter: the circuit runs once with the whole board at it'}], ''
    if which == 'temperature-grades':
        return ST.grades(definition), ''
    if which == 'temperature-reach':
        rows = ST.reach(manager, definition)
        return rows, '' if rows else 'no simulation deck for %s (no ingested schematic)' % definition
    if which == 'temperature-sweep':
        return ST.compare(manager, definition, params.get('sweep') or None)
    if which == 'temperature-trend':
        return ST.trend(manager, definition, params.get('sweep') or None)
    if which == 'temperature-overlay':
        return ST.overlay(manager, definition, params.get('sweep') or None)
    if which == 'temperature-parts':
        return TI.parts(manager, definition), ''
    if which == 'temperature-inputs':
        ref = params.get('ref') or ''
        return (TI.quantities(manager, definition, ref), '') if ref else ([], 'pick a part (its ref) first')
    if which == 'temperature-ratings':
        rows, why = ST.compare(manager, definition, params.get('sweep') or None)
        temps = sorted({r['temp_c'] for r in rows})
        return (ST.ratings(manager, definition, temps), '') if temps else ([], why)
    if which == 'part-run':
        last = _latest(manager, definition, ('parts',))
        t = float(last['temp_c']) if last else ST.ROOM_C
        return [{'board': definition, 'mode': m, 'ambient_c': t, 'signed': True, 'meaning': words,
                 'last_run': ('%s - %s' % (last['temperature'], last['status'])) if last else 'none yet'}
                for m, words in (('final', 'each part at its temperature at the end of the board-over-time run (settled)'),
                                 ('peak', 'each part at its own hottest moment (worst case; not one instant)'))], ''
    if which == 'part-temperatures':
        last = _latest(manager, definition, ('parts',))
        return ST.part_temperatures(manager, definition, float(last['temp_c']) if last else ST.ROOM_C)
    if which in ('curve-catalogue', 'temperature-curves', 'curve-run'):
        from pcb.custom import temperature_curves as TC
        if which == 'curve-catalogue':
            return [{'curve': TC._get(c, 'name'), 'part_key': TC._get(c, 'part_key'), 'quantity': TC._get(c, 'quantity'), 'unit': TC._get(c, 'unit'),
                     'kind': TC._get(c, 'kind'), 'range': '%g .. %g C' % (TC._get(c, 't_min_c'), TC._get(c, 't_max_c')),
                     'conditions': TC._get(c, 'conditions'), 'source': TC._cite(c)} for c in TC.catalogue(manager)], ''
        if which == 'temperature-curves':
            rows, _why = ST.compare(manager, definition, params.get('sweep') or None)
            temps = sorted({r['temp_c'] for r in rows}) or list(CURVE_TEMPS)
            out = TC.at_temperatures(manager, definition, temps)
            return out, '' if out else 'no part of %s has a curve - give one from the catalogue' % definition
        last = _latest(manager, definition, ('board',))
        return [{'board': definition, 'corner': c, 'temp_c': float(last['temp_c']) if last else ST.ROOM_C, 'signed': True, 'meaning': words}
                for c, words in (('nominal', 'each curve\'s value at the temperature (a band stays at nominal)'),
                                 ('low', 'a band\'s low corner (e.g. an X7R capacitor 15 % under nominal)'),
                                 ('high', 'a band\'s high corner'))], ''
    if which in ('self-heat-run', 'self-heating'):
        from pcb.custom import electrothermal as ET
        last = ET.last(definition)
        if which == 'self-heating':
            return (last['rows'], '') if last and last.get('ok') else ([], 'no self-heating loop run yet - run one above')
        return [{'board': definition, 'ambient_c': last['ambient_c'] if last else ST.ROOM_C, 'signed': True,
                 'verdict': last['verdict'] if last else 'not run', 'why': last['why'] if last else '', 'passes': last['passes'] if last else 0,
                 'loop_gain': last['loop_gain'] if last else -1.0, 'over_tj_max': '; '.join(last['over_tj_max']) if last else '',
                 'basis': last['basis'] if last else 'type the background temperature (C) and press Enter'}], ''
    return [], 'no temperature part %r' % which
