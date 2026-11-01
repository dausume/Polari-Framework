"""
@module board.custom.board_esd

esd-0 / esd-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): the Board Details page's ESD parts - thin row shapes over board.custom.esd_areas and
pcb.custom.esd_events (board.custom.board_details dispatches here).

  esd(kind, definition, which, manager, params) -> (rows, why)
      esd-candidates   the pieces that can be flagged - a PCB's nets (any other board: its footholds) - each with flagged yes / no
      esd-areas        the flagged areas with their test and criterion (click one; its row button runs the event on a PCB)
      esd-quantities   ?area= the area's numbers, long form (the page edits value)
      esd-models       the discharge networks and their standards
      esd-runs         the board's kept ESD event runs, newest first (click one) - a PCB's on its circuit, any other board's on a foothold's pin (esd-5)
      esd-summary / esd-results / esd-chart   ?run= the event's verdict, each node's peak / break / recovery, the waveforms with and without it
      esd-protection   ?area= esd-3: the protection catalogue, each with its derived model or why not, and whether it is on the area (row button toggles)
      esd-protection-results   ?run= each protection part's peak current against its cited I_PP
"""
PARTS = ('esd-candidates', 'esd-areas', 'esd-quantities', 'esd-models', 'esd-runs', 'esd-summary', 'esd-results', 'esd-chart', 'esd-protection',
         'esd-protection-results')


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
        return [{'model': k, 'source': ('series LCR loop' if m.get('l_h') else 'network') if m['kind'] == 'network' else 'the standard\'s current equation',
                 'capacitance_pf': m['c_f'] * 1e12, 'resistance_ohm': m['r_ohm'], 'inductance_nh': m.get('l_h', 0.0) * 1e9, 'levels': ', '.join('%g V' % v for v in m['levels']),
                 'standard': m['standard'], 'caveat': m['caveat']} for k, m in MODELS.items()], ''
    if which == 'esd-protection':
        from board.custom import protection_parts as PP
        area = params.get('area') or ''
        on = set()
        if area:
            o = EA._find(manager, area)
            on = {x.strip() for x in str(EA._get(o, 'protection_parts', '') or '').split(',') if x.strip()} if o is not None else set()
        return [dict(r, area=area, on_area='yes' if r['name'] in on else 'no') for r in PP.catalogue(manager)], ''
    from board.custom.esd_footholds import board_key
    from pcb.custom import esd_events as E
    from pcb.custom import spice_runs as SR
    if which == 'esd-runs':
        return [r for r in SR.runs(manager, board_key(kind, definition)) if r.get('event', '').startswith('ESD')], ''
    run = params.get('run') or ''
    if not run:
        return [], 'pick an event run first'
    if which == 'esd-chart':
        return E.chart(manager, run)
    if which == 'esd-protection-results':
        return E.protection_results(manager, run)
    summary, rows, why = E.results(manager, run)
    return ([summary] if which == 'esd-summary' and summary else rows if which == 'esd-results' else []), why
