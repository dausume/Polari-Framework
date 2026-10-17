"""
@module board.custom.pin_view

pv-0 (PIN_VIEW_PLAN.md 2.5 / 2.9): THE PIN-VIEW DOOR — one composed read for the d3 view and the three data tables:

    GET /api/board/{board}/pin-view?system=&binding=&mission=&stage=&phase=&protocol=      surfaces + pins + connections (+ shapes, vocabulary, the stage echo)
    GET /api/board/{board}/pin-view/pins          flat rows, the same filters (+ level= surface= kind=)
    GET /api/board/{board}/pin-view/connections   flat rows (both ends, kind, via, the three summaries)
    GET /api/board/{board}/pin-view/surfaces      flat rows (pin counts by stage)

Structure: board.custom.pin_view_model (derived from the hsp-0/1 rows); state: board.custom.pin_view_state (stage, protocol filter, drive / signal / use); shapes: board.custom.pv_shapes
(MathShapeDefinition rows); vocabulary: board.custom.pv_families. Everything is recomputed on every read from the rows in hand; nothing is stored and nothing blocks.

    python3 -m board.custom.pin_view surfaces|pins|connections|view <board> [--system S] [--binding B] [--stage ST] [--protocol P] [--phase PH] [--mission M] [--json]
"""
import json
import sys

from board.custom import board_object as BO
from board.custom import hardware_system as HS
from board.custom import hwsys_system as SYS
from board.custom import pin_view_model as M
from board.custom import pin_view_state as ST
from board.custom import pv_families as F
from board.custom import pv_shapes as S
from board.custom.hwsys_context import Ctx

PARAMS = ('system', 'binding', 'mission', 'stage', 'phase', 'protocol')
FILTERS = ('level', 'surface', 'kind')


class Refused(ValueError):
    def __init__(self, msg, status=400):
        super().__init__(msg)
        self.status = status


def _context(tables, manager, board, system, binding):
    rows = SYS.rows(tables)
    if system:
        row = next((r for r in rows if r['name'] == system), None)
        if row is None:
            raise Refused('no hardware system %r (GET /api/hardware-systems lists them: %s)' % (system, ', '.join(r['name'] for r in rows)), 404)
    else:
        bd = next((b for b in tables.get('BoardDefinition', []) if b['name'] == board), {})
        row = {'name': '', 'participants_json': json.dumps([{'role': 'board', 'kind': 'hardware', 'ref': 'BoardDefinition:%s' % board, 'variant': 'pending' if bd.get('variant_status') == 'pending' else ''}]),
               'solution': ''}
    ctx = Ctx(tables, manager, row)
    if binding:
        ctx.binding = binding
    return ctx


def build(board, params=None, manager=None, tables=None):
    """-> the composed payload (a dict with ok True). Raises Refused (status 400 / 404) on a bad parameter or board."""
    params = {k: (v or '') for k, v in (params or {}).items()}
    board = BO.board_name(board)
    try:
        tables = tables if tables is not None else HS.default_tables(manager)
        BO.rows_for(board, tables)   # refuses an unknown board (BoardObjectRefused)
    except BO.BoardObjectRefused as e:
        raise Refused(str(e), 404)
    stage = params.get('stage') or 'base'
    if stage not in ST.STAGES:
        raise Refused('unknown stage %r (stages: %s)' % (stage, ', '.join(ST.STAGES)))
    ctx = _context(tables, manager, board, params.get('system', ''), params.get('binding', ''))
    model = M.build(tables, board)
    info = ST.apply_stage(model, tables, ctx, stage, ctx.binding, board)
    proto = None
    if params.get('protocol'):
        try:
            proto = ST.apply_protocol(model, ctx, params['protocol'])
        except ST.PinViewError as e:
            raise Refused(str(e))
    ST.summarise(model, ctx, tables, board)
    ST.rollup(model)
    mission = params.get('mission', '')
    shapes = {n: dict(r, parameters=json.loads(r['parameters_json'])) for n, r in model.shapes.items() if any(s['shape'] == n for s in model.surfaces)}
    for n in shapes:
        shapes[n].pop('parameters_json', None)
    live = bool(manager is not None and (getattr(manager, 'objectTables', None) or {}).get('EnclosureContact'))
    surf_title = {s['id']: s['title'] for s in model.surfaces}
    for p in model.pins.values():
        p['surface_title'] = surf_title.get(p['surface'], '')
    return {'ok': True, 'board': board, 'source': 'live' if live else 'seed (the live server has no enclosure rows yet)', 'system': ctx.system_name, 'binding': ctx.binding, 'phase': params.get('phase') or 'runtime',
            'mission': {'name': mission, 'status': 'undetermined' if mission else 'none', 'why': 'Task definitions on a Mission arrive with fgm-3; `tasks-assigned` reads the binding\'s graph-node claims today' if mission else ''},
            'stage': info, 'protocol': proto, 'vocabulary': F.vocabulary(), 'surfaces': model.surfaces, 'pins': list(model.pins.values()), 'connections': model.connections, 'unresolved': model.unresolved,
            'shapes': shapes, 'counts': {'surfaces': len(model.surfaces), 'pins': len(model.pins), 'connections': len(model.connections), 'unresolved': len(model.unresolved),
                                         'by_level': {lv: sum(1 for p in model.pins.values() if p['level'] == lv) for lv in M.LEVELS},
                                         'by_kind': {k: sum(1 for c in model.connections if c['kind'] == k) for k in sorted({c['kind'] for c in model.connections})}},
            'echo': {k: params.get(k, '') for k in PARAMS}}


# ---------------------------------------------------------------- the flat row views (configured tables read these)
def _label(res, pid):
    p = next((x for x in res['pins'] if x['id'] == pid), None)
    return p['label'] if p else ''


def _text(d, keys):
    return '; '.join('%s %s' % (k, d[k]) for k in keys if d.get(k))


def pin_rows(res, flt=None):
    rows = []
    for p in res['pins']:
        cons = ', '.join('%s %s' % (c['kind'], c['who']) for c in p['consumers'])
        rows.append({'id': p['id'], 'level': p['level'], 'surface': p['surface'], 'owner': p.get('surface_title', ''), 'label': p['label'], 'number': p['number'] if p['number'] is not None else '', 'kind': p['kind'],
                     'canonical': p['canonical'], 'families': ', '.join(p['families']), 'drive_class': p['drive_class'], 'stage': p['stage'], 'stage_why': p['stage_why'], 'bonded': 'yes' if p['bonded'] else 'no',
                     'consumers': cons, 'lit': 'lit' if p['lit'] else ('dimmed' if p['dim'] else ''),
                     'lit_why': '; '.join('%s: %s' % (c['child'], c['headline']) for c in p['lit']['children']) if p['lit'] else '', 'notes': p['notes']})
    return _flt(rows, flt)


def connection_rows(res, flt=None):
    rows = []
    for c in res['connections']:
        a = next(p for p in res['pins'] if p['id'] == c['a'])
        b = next(p for p in res['pins'] if p['id'] == c['b'])
        d, s, u = c['drive'], c['signal'], c['use']
        rows.append({'id': c['id'], 'a': c['a'], 'a_label': a['label'], 'a_owner': a.get('surface_title', ''), 'a_level': a['level'], 'b': c['b'], 'b_label': b['label'], 'b_owner': b.get('surface_title', ''), 'b_level': b['level'],
                     'level': a['level'], 'surface': a['surface'], 'kind': c['kind'], 'via': (c['via'] + (' ' + c['via_part'] if c['via_part'] else '')).strip(),
                     'drive': 'ends %s / %s; rail %s; domain %s; pull %s; limit %s' % (d['a'], d['b'], d['rail'] or '-', d['domain'] or '-', d['pull'], d['limit_verdict']),
                     'signal': '%s / %s; %s%s' % (s['a'], s['b'], s['family'] or 'no family', ('; ' + s['protocol_signal']) if s['protocol_signal'] else ''),
                     'use': ('tasks %s; purposes %s' % (', '.join(t['who'] for t in u['tasks']) or 'none', ', '.join(u['purposes']) or 'none')), 'stage': c['stage'], 'lit': ('dimmed' if c.get('dim') else 'lit') if res['protocol'] else ''})
    return _flt(rows, flt)


def surface_rows(res, flt=None):
    rows = [{'id': s['id'], 'surface': s['id'], 'kind': s['kind'], 'level': s['level'], 'title': s['title'], 'parent': s['parent'], 'shape': s['shape'], 'pin_count': s['pin_count'],
             'unassigned': s['stage_counts']['unassigned'], 'available': s['stage_counts']['available'], 'proposed': s['stage_counts']['proposed'], 'committed': s['stage_counts']['committed']}
            for s in res['surfaces']]
    return _flt(rows, flt)


def _flt(rows, flt):
    for k, v in (flt or {}).items():
        if v and k in FILTERS:
            rows = [r for r in rows if r.get(k) == v]
    return rows


def rows_payload(res, which, flt=None):
    rows = {'pins': pin_rows, 'connections': connection_rows, 'surfaces': surface_rows}[which](res, flt)
    return {'ok': True, 'board': res['board'], 'source': res['source'], 'system': res['system'], 'binding': res['binding'], 'stage': res['stage']['stage'], 'protocol': (res['protocol'] or {}).get('protocol', ''),
            'rows': rows, 'count': len(rows), 'undetermined': res['stage']['undetermined']}


# ---------------------------------------------------------------- the door bodies (board_object_api calls these)
def door(manager, board, params, which=''):
    """(status, payload) for the whole view or one row view."""
    flt = {k: params.get(k, '') for k in FILTERS}
    try:
        res = build(board, {k: params.get(k, '') for k in PARAMS}, manager)
    except Refused as e:
        return e.status, {'ok': False, 'error': str(e)}
    return 200, (rows_payload(res, which, flt) if which else res)


# ---------------------------------------------------------------- CLI
def render(res, which):
    if which == 'view':
        c = res['counts']
        out = ['%s — stage %s%s%s: %d surfaces, %d pins, %d connections (%s), %d unresolved' % (res['board'], res['stage']['stage'], (', system ' + res['system']) if res['system'] else '',
               (', protocol ' + res['protocol']['protocol']) if res['protocol'] else '', c['surfaces'], c['pins'], c['connections'], ', '.join('%d %s' % (v, k) for k, v in c['by_kind'].items()), c['unresolved'])]
        out += ['  ' + n for n in res['stage']['notes']] + ['  UNDETERMINED: ' + u for u in res['stage']['undetermined']]
        return '\n'.join(out)
    rows = rows_payload(res, which)['rows']
    if not rows:
        return '(no rows)'
    cols = {'pins': ('id', 'level', 'label', 'families', 'stage', 'consumers'), 'connections': ('a_label', 'b_label', 'kind', 'via', 'stage', 'signal'),
            'surfaces': ('id', 'kind', 'pin_count', 'unassigned', 'available', 'proposed', 'committed')}[which]
    return '\n'.join('  '.join(str(r[c])[:46].ljust(14) for c in cols) for r in rows)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in ('surfaces', 'pins', 'connections', 'view'):
        print(__doc__)
        return 2
    which, board, params, as_json = argv[0], argv[1], {}, False
    i = 2
    while i < len(argv):
        a = argv[i]
        if a == '--json':
            as_json = True
        elif a.startswith('--') and a[2:] in PARAMS + FILTERS and i + 1 < len(argv):
            params[a[2:]] = argv[i + 1]
            i += 1
        else:
            print('unknown option %s' % a)
            return 2
        i += 1
    try:
        res = build(board, {k: params.get(k, '') for k in PARAMS})
    except Refused as e:
        print('refused: %s' % e)
        return 1
    if as_json:
        print(json.dumps(res if which == 'view' else rows_payload(res, which, params), indent=2))
    else:
        print(render(res, which))
    return 0


if __name__ == '__main__':
    sys.exit(main())
