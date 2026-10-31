"""
@module board.custom.board_esd

esd-0 / esd-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): the Board Details page's ESD parts - thin row shapes over board.custom.esd_areas and
pcb.custom.esd_events (board.custom.board_details dispatches here).

  esd(kind, definition, which, manager, params) -> (rows, why)
      esd-candidates   the pieces that can be flagged - a PCB's nets (any other board: its footholds) - each with flagged yes / no
      esd-areas        the flagged areas with their test and criterion (click one; its row button runs the event on a PCB)
      esd-quantities   ?area= the area's numbers, long form (the page edits value)
      esd-models       the discharge networks and their standards
      esd-runs         a PCB's kept ESD event runs, newest first (click one)
      esd-summary / esd-results / esd-chart   ?run= the event's verdict, each node's peak / break / recovery, the waveforms with and without it
"""
PARTS = ('esd-candidates', 'esd-areas', 'esd-quantities', 'esd-models', 'esd-runs', 'esd-summary', 'esd-results', 'esd-chart')


def _nets(manager, definition):
    t = (getattr(manager, 'objectTables', None) or {}).get('SchematicNet') or {}
    return sorted({getattr(n, 'net', '') for n in t.values() if getattr(n, 'board', '') == definition} - {''})


def esd(kind, definition, which, manager, params):
    from board.custom import esd_areas as EA
    params = params or {}
    if which == 'esd-candidates':
        flagged = {(a['scope'], a['target']) for a in EA.areas(manager, kind, definition)}
        if kind == 'layers':
            pieces = [('net', n) for n in _nets(manager, definition) if n not in ('GND', '0')]
        else:
            from board.custom import footholds as FH
            pieces = [('foothold', f['foothold']) for f in FH.for_definition(kind, definition, manager=manager)[0]]
        return [{'board': definition, 'definition_kind': kind, 'scope': s, 'target': t, 'flagged': (s, t) in flagged,
                 'action': 'unflag' if (s, t) in flagged else 'flag'} for s, t in pieces], '' if pieces else 'no nets or footholds known for %s/%s' % (kind, definition)
    if which == 'esd-areas':
        return EA.areas(manager, kind, definition), ''
    if which == 'esd-quantities':
        area = params.get('area') or ''
        return (EA.quantities(manager, area), '') if area else ([], 'pick an area first')
    if which == 'esd-models':
        from pcb.custom.esd_events import MODELS
        return [{'model': k, 'capacitance_pf': m['c_f'] * 1e12, 'resistance_ohm': m['r_ohm'], 'levels': ', '.join('%g V' % v for v in m['levels']),
                 'standard': m['standard'], 'caveat': m['caveat']} for k, m in MODELS.items()], ''
    if kind != 'layers':
        return [], 'an ESD event runs on a PCB\'s circuit (a layers board); %s/%s has none' % (kind, definition)
    from pcb.custom import esd_events as E
    from pcb.custom import spice_runs as SR
    if which == 'esd-runs':
        return [r for r in SR.runs(manager, definition) if r.get('event', '').startswith('ESD')], ''
    run = params.get('run') or ''
    if not run:
        return [], 'pick an event run first'
    if which == 'esd-chart':
        return E.chart(manager, run)
    summary, rows, why = E.results(manager, run)
    return ([summary] if which == 'esd-summary' and summary else rows if which == 'esd-results' else []), why
