"""
@module board.custom.pin_view

pv-0 (PIN_VIEW_PLAN.md 2.5 / 2.9): THE PIN-VIEW DOOR — one composed read for the d3 view and the three data tables:

    GET /api/board/{board}/pin-view?system=&binding=&mission=&stage=&phase=&protocol=&activated_only=      surfaces + pins + connections (+ shapes, vocabulary, the stage echo)
        protocol takes SEVERAL families / sets at once (protocol=i2c,spi); activated_only=1 keeps the pads a claim activated (pv-2)
    GET /api/board/{board}/pin-view/pins          flat rows, the same filters (+ level= surface= kind= and the drive filters rail= drive_status= limit_class=, each a comma list)
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
from board.custom import pin_view_modes as MD
from board.custom import pin_view_phases as PH
from board.custom import pin_view_state as ST
from board.custom import pv_families as F
from board.custom import pv_shapes as S
from board.custom.hwsys_context import Ctx

PARAMS = ('system', 'binding', 'mission', 'stage', 'phase', 'blank', 'protocol', 'activated_only', 'run', 'candidate')
FILTERS = ('level', 'surface', 'kind', 'rail', 'drive_status', 'limit_class')   # the last three are the drive filters (comma lists)
CAND_STAGE = 'candidate'   # pv-5: draws a solution the attempt engine found (board.custom.pin_view_candidate)
TRUE = ('1', 'true', 'yes', 'on')


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


def bench_layout(binding, board, manager=None):
    """pv-6: the layout the bench parts are drawn on -> (the public layout payload or None, why not). The binding's config when the view has one (`<config>@<board>`), else the Layout page's
    default for the board; a placer refusal (a config with no breadboard parts, an unknown config) leaves the parts in the packed bench column and says why."""
    config = binding.partition('@')[0] if binding else M.BENCH_LAYOUT_DEFAULT.get(board, '')
    if not config:
        return None, 'no layout: the view has no binding and no default layout is known for %s' % board
    try:
        from electrodevice.custom import layout_core as C
        from electrodevice.custom.layout_words import LayoutRefused
    except ImportError as e:   # the electrodevice module is not loaded on this node: the bench column stays
        return None, 'no layout: the electrodevice layout engine is not available here (%s)' % e
    try:
        return C.public(C.layout_place(config, None, manager)), ''
    except LayoutRefused as e:
        return None, 'no layout for %s: %s' % (config, e)


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
    if stage not in ST.STAGES + (CAND_STAGE,):
        raise Refused('unknown stage %r (stages: %s)' % (stage, ', '.join(ST.STAGES + (CAND_STAGE,))))
    try:   # pv-4: the phase and the blank baseline; a phase before init shows no claims, init shows the Initialization Purpose's, runtime the requested stage
        phase, blank = PH.check_params(params.get('phase'), params.get('blank'))
    except PH.PhaseError as e:
        raise Refused(str(e))
    requested_stage, stage = stage, PH.effective_stage(phase, stage)
    ctx = _context(tables, manager, board, params.get('system', ''), params.get('binding', ''))
    lay, lay_why = bench_layout(ctx.binding, board, manager)
    model = M.build(tables, board, bench_layout=lay)
    model.bench['why'] = lay_why
    info = ST.apply_stage(model, tables, ctx, 'base' if stage == CAND_STAGE else stage, ctx.binding, board)
    candidate = None
    if stage == CAND_STAGE:   # pv-5: the base picture, then the chosen run's candidate marks its pins proposed
        from board.custom import pin_view_candidate as CAND
        try:
            candidate = CAND.block(model, tables, board, params, manager)
        except CAND.CandidateRefused as e:
            raise Refused(str(e), e.status)
        info['stage'] = CAND_STAGE
        info['notes'] = ['candidate: the assignment of candidate %s (rank %s) of solution search %s, drawn as proposed; the other pins keep their base stage' % (candidate['id'], candidate['rank'], candidate['run'])]
    info['requested'] = requested_stage
    MD.apply_pins(model, tables, ctx, phase)
    phase_info = PH.apply(model, tables, phase, blank, board)
    phase_info.update({'requested_stage': requested_stage, 'effective_stage': stage, 'blank_facts': PH.blank_block(tables, board, blank, phase)})
    proto = None
    if params.get('protocol'):
        try:
            proto = ST.apply_protocol(model, ctx, params['protocol'], params.get('activated_only', '').lower() in TRUE)
        except ST.PinViewError as e:
            raise Refused(str(e))
    ST.summarise(model, ctx, tables, board)
    MD.apply_connections(model)
    ST.rollup(model)
    mission = params.get('mission', '')
    shapes = {n: dict(r, parameters=json.loads(r['parameters_json'])) for n, r in model.shapes.items() if any(s['shape'] == n for s in model.surfaces)}
    for n in shapes:
        shapes[n].pop('parameters_json', None)
    live = bool(manager is not None and (getattr(manager, 'objectTables', None) or {}).get('EnclosureContact'))
    surf_title = {s['id']: s['title'] for s in model.surfaces}
    for p in model.pins.values():
        p['surface_title'] = surf_title.get(p['surface'], '')
    return {'ok': True, 'board': board, 'source': 'live' if live else 'seed (the live server has no enclosure rows yet)', 'system': ctx.system_name, 'binding': ctx.binding, 'phase': phase, 'blank': blank, 'phase_info': phase_info,
            'mission': {'name': mission, 'status': 'undetermined' if mission else 'none', 'why': 'Task definitions on a Mission arrive with fgm-3; `tasks-assigned` reads the binding\'s graph-node claims today' if mission else ''},
            'stage': info, 'candidate': candidate, 'protocol': proto, 'vocabulary': dict(F.vocabulary(), drive=MD.vocabulary()), 'bench': model.bench, 'layout': dict(S.LABEL, note='drawing knobs (mm): part titles and pin labels are drawn in model units at this font size'), 'surfaces': model.surfaces, 'pins': list(model.pins.values()), 'connections': model.connections, 'unresolved': model.unresolved,
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
                     'consumers': cons, 'drive_relevant': 'yes' if p['drive_relevant'] else 'no', 'drive_status': p['drive_status'], 'rail': p['rail'], 'pull': p['pull'], 'limit_class': p['limit_class'],
                     'group_budget': ', '.join(p['group_budget']), 'signal_relevant': 'yes' if p['signal_relevant'] else 'no', 'activated': p['activated']['function'] if p['activated'] else '',
                     'capable': ', '.join(c['function'] for c in p['capable']), 'lifecycle': ', '.join('%s %s' % (x['policy'], x['phase']) for x in p['lifecycle']), 'lit': 'lit' if p['lit'] else ('dimmed' if p['dim'] else ''),
                     'phase_basis': ' | '.join(p.get('phase_basis', [])), 'lit_why': '; '.join('%s: %s' % (c['child'], c['headline']) for c in p['lit']['children']) if p['lit'] else '', 'notes': p['notes']})
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
                     'rail': a['rail'] if a['rail'] != 'undetermined' else b['rail'], 'limit_class': d['limit_verdict'],
                     'use': ('tasks %s; purposes %s' % (', '.join(t['who'] for t in u['tasks']) or 'none', ', '.join(u['purposes']) or 'none')), 'stage': c['stage'], 'lit': ('dimmed' if c.get('dim') else 'lit') if res['protocol'] else ''})
    return _flt(rows, flt)


def surface_rows(res, flt=None):
    rows = [{'id': s['id'], 'surface': s['id'], 'kind': s['kind'], 'level': s['level'], 'title': s['title'], 'parent': s['parent'], 'shape': s['shape'], 'pin_count': s['pin_count'],
             'unassigned': s['stage_counts']['unassigned'], 'available': s['stage_counts']['available'], 'proposed': s['stage_counts']['proposed'], 'committed': s['stage_counts']['committed']}
            for s in res['surfaces']]
    return _flt(rows, flt)


def _flt(rows, flt):
    """level / surface / kind are exact; the drive filters are comma lists (rail=5V,3V3). A filter whose column the row view does not have (surfaces have no rail) is skipped."""
    for k, v in (flt or {}).items():
        if v and k in FILTERS and (not rows or k in rows[0]):
            want = [x for x in v.split(',') if x]
            rows = [r for r in rows if r.get(k) in want]
    return rows


def rows_payload(res, which, flt=None):
    rows = {'pins': pin_rows, 'connections': connection_rows, 'surfaces': surface_rows}[which](res, flt)
    return {'ok': True, 'board': res['board'], 'source': res['source'], 'system': res['system'], 'binding': res['binding'], 'stage': res['stage']['stage'], 'protocol': (res['protocol'] or {}).get('protocol', ''),
            'rows': rows, 'count': len(rows), 'undetermined': res['stage']['undetermined']}


# ---------------------------------------------------------------- the door bodies (board_object_api calls these)
def door(manager, board, params, which=''):
    """(status, payload) for the whole view or one row view."""
    flt = {k: params.get(k, '') for k in FILTERS}
    if str(board).startswith('bench:'):   # bob-4: a whole Bench drawn - its Boards, their footholds, its connections (board.custom.bench_scene)
        from board.custom import bench_scene as BSC
        status, res = BSC.build(board[len('bench:'):], manager)
        return status, (rows_payload(res, which, flt) if which and status == 200 else res)
    if str(board).startswith('pcb:'):   # bob-3f: one PCB drawn - its outline, its pads and where its heat sits (board.custom.pcb_scene)
        from board.custom import pcb_scene as PSC
        status, res = PSC.build(board[len('pcb:'):], manager)
        return status, (rows_payload(res, which, flt) if which and status == 200 else res)
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
