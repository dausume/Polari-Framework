"""
@module board.custom.bench_boards

bob-1 (AI-Notes/plans/BENCH_BOARDS_PLAN.md): ONE LIST OF BOARDS ON A BENCH. His ruling 2026-10-30: dev boards, breadboards and PCBs are equally Boards on the
Bench; how each is defined is its own level. The Bench row still keeps its two older lists (the /display/bench panels read them); this module reads
them together with the BenchBoard rows that name the bench (how a PCB joins) into one shape:

  boards_on_bench(bench, manager)  [{n, board, board_kind, label, definition_kind, definition, source, testing, footholds, nodes, footholds_note, details}]
  add_pcb(manager, bench, body)    a PcbBoard (an ingested KiCad project) onto a bench: a BenchBoard row (model pcb, definition_kind layers)

`details` = the Board Details route for the board's definition (bob-3); `footholds` = how many (-1 with the reason when the definition yields none).
"""
from board.custom import bench as B
from board.custom import footholds as FH

KIND_OF = {'datasheet': 'dev-board', 'geometry': 'breadboard', 'layers': 'pcb'}


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values()) if manager is not None else []


def details_route(kind, definition):
    return '/display/board-details?board=%s/%s' % (kind, definition)


def _summary(kind, definition, manager, tables, cache):
    key = (kind, definition)
    if key not in cache:
        rows, why = FH.for_definition(kind, definition, tables=tables, manager=manager)
        cache[key] = (len(rows), len({r['node'] for r in rows}), why) if rows else (-1, -1, why)
    return cache[key]


def boards_on_bench(bench_name, manager=None):
    b = B.bench(bench_name, manager)
    if b is None:
        return None
    from board.custom import hardware_system as HS
    tables = HS.default_tables(manager)
    cache, out = {}, []

    def add(kind, definition, label, source, testing, extra=None):
        n, nodes, why = _summary(kind, definition, manager, tables, cache)
        out.append(dict({'n': len(out) + 1, 'board': '%s/%s' % (kind, definition), 'board_kind': KIND_OF[kind], 'label': label, 'definition_kind': kind, 'definition': definition, 'source': source,
                         'testing': testing, 'footholds': n, 'nodes': nodes, 'footholds_note': why, 'details': details_route(kind, definition)}, **(extra or {})))

    for r in B.board_rows(b, manager):
        add('datasheet', r['board'], r['label'], 'Bench.boards_json', r['testing'])
    for r in B.breadboard_rows(b, manager):
        for i in range(1, r['count'] + 1):
            add('geometry', r['model'], '%s #%d' % (r['title'], i), 'Bench.breadboards_json', r['geometry'])
    for bb in sorted(_rows(manager, 'BenchBoard'), key=lambda o: getattr(o, 'name', '')):
        if getattr(bb, 'bench', '') == bench_name and getattr(bb, 'definition_kind', '') in KIND_OF:
            add(bb.definition_kind, bb.definition, bb.label or bb.definition, 'BenchBoard:%s' % bb.name,
                'simulated from its design (no hardware attached)' if bb.definition_kind == 'layers' else '')
    return out


def add_pcb(manager, bench_name, body):
    """(status, body): put an ingested PCB (a PcbBoard row) on a bench as a BenchBoard of kind layers."""
    if B.bench(bench_name, manager) is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    pcb = str((body or {}).get('pcb', '')).strip()
    known = sorted(getattr(o, 'name', '') for o in _rows(manager, 'PcbBoard'))
    if pcb not in known:
        return 404, {'ok': False, 'error': 'no ingested PCB named %r - ingest it first (POST /api/pcb/ingest)' % pcb, 'known': known}
    if manager is None:
        return 503, {'ok': False, 'error': 'no object manager: a Board on the Bench is a stored row'}
    from electrodevice.objects.layout.BenchBoard import BenchBoard
    mine = [o for o in _rows(manager, 'BenchBoard') if getattr(o, 'bench', '') == bench_name and getattr(o, 'definition', '') == pcb]
    name = '%s:pcb:%s#%d' % (bench_name, pcb, len(mine) + 1)
    BenchBoard(manager=manager, name=name, model_name='pcb', label=str(body.get('label') or '%s #%d' % (pcb, len(mine) + 1)), owner='',
               notes=str(body.get('note') or ''), bench=bench_name, definition_kind='layers', definition=pcb)
    return 201, {'ok': True, 'bench': bench_name, 'added': name, 'rows': boards_on_bench(bench_name, manager)}
