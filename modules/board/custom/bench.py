"""
@module board.custom.bench

bench-0: the Bench doors' bodies (MISSION_GENERIC_PLAN.md section 13.1). A Bench holds the dev / eval boards and the breadboards on one table;
two SELECTION lists feed it (configured tables with an "Add to bench" row action - no new component). Every board row carries its TESTING word
from the chips-and-levels ladder (`chip_ladder.testing_of`): simulated with real pins, simulated with STUB pins, or HARDWARE ONLY - said in
capitals, never left blank (his rule 2026-10-24).

    GET  /api/board/benches                              {ok, rows}  one row per bench: counts, how many boards are hardware-only
    GET  /api/board/benches/{bench}/boards               {ok, rows}  the boards on it, each with its testing word, software and how
    GET  /api/board/benches/{bench}/breadboards          {ok, rows}  the breadboards on it, each with its model's geometry state
    GET  /api/board/bench-options/boards?bench=          {ok, rows}  every dev / eval board the ladder knows, with testing + on_bench + can_add
    GET  /api/board/bench-options/breadboards?bench=     {ok, rows}  every BreadboardModel, with on_bench count
    POST /api/board/benches/{bench}/boards               {board, label?, note?}        -> 201 + the bench's boards
    POST /api/board/benches/{bench}/breadboards          {model, count?, note?}        -> 201 + the bench's breadboards
    POST /api/board/benches/{bench}/remove               {kind: board|breadboard, key}  -> 200 + the rows left
An unknown bench, board or model is 404; a bad body 400.
"""
import json

from board.custom import bench_seed as SEED
from board.custom import chip_ladder as CL

_MEM = {}   # the in-memory benches when no manager is given (selftests)


def _j(text, default):
    return CL._j(text, default)


# ---------------------------------------------------------------------------------------------------- stores
def _live_rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls, {}) or {}).values()) if manager is not None else []


def bench_dict(row):
    if isinstance(row, dict):
        return dict(row)
    return {k: getattr(row, k, '') for k in ('name', 'title', 'boards_json', 'breadboards_json', 'notes', 'source')}


def benches(manager=None):
    live = [bench_dict(r) for r in _live_rows(manager, 'Bench')]
    if live:
        return live
    if manager is None:
        if not _MEM:
            for b in SEED.SEED_BENCHES:
                _MEM[b['name']] = dict(b)
        return [dict(b) for b in _MEM.values()]
    return [dict(b) for b in SEED.SEED_BENCHES]


def bench(name, manager=None):
    return next((b for b in benches(manager) if b['name'] == name), None)


def _save(manager, b):
    """Write the bench back: the live row when the manager holds one (or can make one), else the in-memory store."""
    if manager is None:
        _MEM[b['name']] = dict(b)
        return
    row = next((r for r in _live_rows(manager, 'Bench') if getattr(r, 'name', '') == b['name']), None)
    if row is None:
        from board.objects.board.Bench import Bench
        row = Bench(manager=manager, **{k: b.get(k, '') for k in ('name', 'title', 'boards_json', 'breadboards_json', 'notes', 'source')})
    else:
        for k in ('title', 'boards_json', 'breadboards_json', 'notes'):
            setattr(row, k, b.get(k, ''))
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass


def models(manager=None):
    live = _live_rows(manager, 'BreadboardModel')
    if live:
        return [{k: getattr(r, k, '') for k in SEED.SEED_BREADBOARD_MODELS[0].keys()} for r in live]
    return [dict(m) for m in SEED.SEED_BREADBOARD_MODELS]


# ---------------------------------------------------------------------------------------------------- the ladder's boards
def ladder_boards(manager=None):
    """One dict per dev / eval board the chips-and-levels ladder knows: {board, title, chip, family, section, slot, testing, software, how,
    inputs_driven_by, on_hand, price_usd}."""
    out = {}
    for e in CL.entries(manager):
        em = _j(e.get('emulator_json'), {})
        t = CL.testing_of(em)
        for b in _j(e.get('boards_json'), []):
            key = b.get('board', '')
            if not key or key in out:
                continue
            out[key] = {'board': key, 'title': b.get('title') or key, 'chip': e.get('chip', ''), 'family': e.get('family', ''),
                        'section': 'RISC-V' if e.get('section') == 'riscv' else 'convenience', 'slot': e.get('slot', ''),
                        'testing_group': t['group'], 'testing': t['word'], 'software': t['software'], 'how': t['how'],
                        'inputs_driven_by': t['inputs_driven_by'], 'on_hand': 'yes' if b.get('on_hand') else 'no',
                        'price_usd': b.get('price_usd', ''), 'note': b.get('note', '')}
    return out


# ---------------------------------------------------------------------------------------------------- rows
def board_rows(b, manager=None):
    lb = ladder_boards(manager)
    rows = []
    for i, e in enumerate(_j(b.get('boards_json'), []), 1):
        info = lb.get(e.get('board', '')) or {'title': e.get('board', ''), 'chip': '', 'family': '', 'section': '', 'testing_group': 'unknown',
                                               'testing': 'UNKNOWN BOARD - not in the chips-and-levels ladder', 'software': '', 'how': '', 'inputs_driven_by': ''}
        rows.append({'n': i, 'board': e.get('board', ''), 'label': e.get('label') or '%s #%d' % (info['title'], i), 'title': info['title'], 'chip': info['chip'],
                     'family': info['family'], 'section': info['section'], 'testing_group': info['testing_group'], 'testing': info['testing'],
                     'software': info['software'], 'how': info['how'], 'inputs_driven_by': info['inputs_driven_by'], 'added': e.get('added', ''),
                     'note': e.get('note', ''), 'bench': b['name']})
    return rows


def breadboard_rows(b, manager=None):
    ms = {m['name']: m for m in models(manager)}
    rows = []
    for e in _j(b.get('breadboards_json'), []):
        m = ms.get(e.get('model', '')) or {'title': e.get('model', ''), 'kind': 'unverified', 'tie_points': -1, 'rows': -1, 'geometry_known': False, 'basis': 'unknown model'}
        rows.append({'model': e.get('model', ''), 'title': m['title'], 'kind': m['kind'], 'count': int(e.get('count') or 1), 'tie_points': m['tie_points'],
                     'rows': m['rows'], 'geometry': 'known (%.1f x %.1f mm)' % (m['width_mm'], m['height_mm']) if m.get('geometry_known') else 'UNVERIFIED - cannot be drawn or placed on yet',
                     'basis': m['basis'], 'note': e.get('note', ''), 'bench': b['name']})
    return rows


def bench_rows(manager=None):
    out = []
    for b in benches(manager):
        br = board_rows(b, manager)
        out.append({'name': b['name'], 'title': b['title'], 'boards': len(br), 'breadboards': sum(int(e.get('count') or 1) for e in _j(b.get('breadboards_json'), [])),
                    'simulated_real_pins': len([r for r in br if r['testing_group'] == 'simulated']),
                    'simulated_stub_pins': len([r for r in br if r['testing_group'] == 'simulated-stub']),
                    'hardware_only': len([r for r in br if r['testing_group'] == 'hardware-only']),
                    'hardware_only_boards': ', '.join(r['label'] for r in br if r['testing_group'] == 'hardware-only') or 'none', 'notes': b.get('notes', '')})
    return out


def board_options(manager=None, bench_name=''):
    b = bench(bench_name, manager) if bench_name else None
    on = {}
    for e in _j((b or {}).get('boards_json'), []):
        on[e.get('board', '')] = on.get(e.get('board', ''), 0) + 1
    rows = []
    for key, info in sorted(ladder_boards(manager).items(), key=lambda kv: (kv[1]['section'] != 'RISC-V', kv[1]['testing_group'] != 'simulated', kv[0])):
        rows.append(dict(info, on_bench=on.get(key, 0), can_add=True, bench=bench_name))
    return rows


def breadboard_options(manager=None, bench_name=''):
    b = bench(bench_name, manager) if bench_name else None
    on = {e.get('model', ''): int(e.get('count') or 1) for e in _j((b or {}).get('breadboards_json'), [])}
    rows = []
    for m in models(manager):
        rows.append(dict(m, geometry='known (%.1f x %.1f mm)' % (m['width_mm'], m['height_mm']) if m.get('geometry_known') else 'UNVERIFIED - cannot be drawn or placed on yet',
                         on_bench=on.get(m['name'], 0), can_add=True, bench=bench_name))
    return rows


# ---------------------------------------------------------------------------------------------------- writes
def add_board(manager, bench_name, body):
    b = bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    key = str((body or {}).get('board', '')).strip()
    lb = ladder_boards(manager)
    if key not in lb:
        return 404, {'ok': False, 'error': 'no dev / eval board named %r in the chips-and-levels ladder' % key, 'known': sorted(lb)}
    entries = _j(b.get('boards_json'), [])
    n = len([e for e in entries if e.get('board') == key]) + 1
    entries.append({'board': key, 'label': str(body.get('label') or '%s #%d' % (lb[key]['title'], n)), 'added': str(body.get('added') or ''),
                    'note': str(body.get('note') or ''), 'testing': lb[key]['testing']})
    b['boards_json'] = json.dumps(entries)
    _save(manager, b)
    return 201, {'ok': True, 'bench': bench_name, 'added': key, 'testing': lb[key]['testing'], 'rows': board_rows(b, manager)}


def add_breadboard(manager, bench_name, body):
    b = bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    key = str((body or {}).get('model', '')).strip()
    ms = {m['name'] for m in models(manager)}
    if key not in ms:
        return 404, {'ok': False, 'error': 'no breadboard model named %r' % key, 'known': sorted(ms)}
    try:
        raw = body.get('count', 1)
        count = 1 if raw in (None, '') else int(raw)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': 'count must be a whole number'}
    if count < 1:
        return 400, {'ok': False, 'error': 'count must be 1 or more'}
    entries = _j(b.get('breadboards_json'), [])
    hit = next((e for e in entries if e.get('model') == key), None)
    if hit:
        hit['count'] = int(hit.get('count') or 1) + count
    else:
        entries.append({'model': key, 'count': count, 'note': str(body.get('note') or '')})
    b['breadboards_json'] = json.dumps(entries)
    _save(manager, b)
    return 201, {'ok': True, 'bench': bench_name, 'added': key, 'count': count, 'rows': breadboard_rows(b, manager)}


def remove(manager, bench_name, body):
    b = bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    kind, key = str((body or {}).get('kind', '')), str((body or {}).get('key', '')).strip()
    if kind == 'board':
        entries = _j(b.get('boards_json'), [])
        hit = next((e for e in entries if e.get('board') == key or e.get('label') == key), None)
        if hit is None:
            return 404, {'ok': False, 'error': 'no board %r on bench %s' % (key, bench_name)}
        entries.remove(hit)
        b['boards_json'] = json.dumps(entries)
        _save(manager, b)
        return 200, {'ok': True, 'bench': bench_name, 'removed': key, 'rows': board_rows(b, manager)}
    if kind == 'breadboard':
        entries = _j(b.get('breadboards_json'), [])
        hit = next((e for e in entries if e.get('model') == key), None)
        if hit is None:
            return 404, {'ok': False, 'error': 'no breadboard %r on bench %s' % (key, bench_name)}
        if int(hit.get('count') or 1) > 1:
            hit['count'] = int(hit['count']) - 1
        else:
            entries.remove(hit)
        b['breadboards_json'] = json.dumps(entries)
        _save(manager, b)
        return 200, {'ok': True, 'bench': bench_name, 'removed': key, 'rows': breadboard_rows(b, manager)}
    return 400, {'ok': False, 'error': 'kind must be board or breadboard'}


# ---------------------------------------------------------------------------------------------------- doors
def get_door(manager, params, which, bench_name=''):
    if which == 'benches':
        return 200, {'ok': True, 'rows': bench_rows(manager)}
    if which == 'options-boards':
        return 200, {'ok': True, 'rows': board_options(manager, (params.get('bench') or SEED.HOME_BENCH).strip())}
    if which == 'options-breadboards':
        return 200, {'ok': True, 'rows': breadboard_options(manager, (params.get('bench') or SEED.HOME_BENCH).strip())}
    b = bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name, 'known': [x['name'] for x in benches(manager)]}
    if which == 'boards':
        return 200, {'ok': True, 'bench': bench_name, 'rows': board_rows(b, manager)}
    if which == 'breadboards':
        return 200, {'ok': True, 'bench': bench_name, 'rows': breadboard_rows(b, manager)}
    return 404, {'ok': False, 'error': 'unknown door'}


def post_door(manager, bench_name, which, body):
    if not isinstance(body, dict):
        return 400, {'ok': False, 'error': 'the body must be a JSON object'}
    if which == 'boards':
        return add_board(manager, bench_name, body)
    if which == 'breadboards':
        return add_breadboard(manager, bench_name, body)
    if which == 'remove':
        return remove(manager, bench_name, body)
    return 404, {'ok': False, 'error': 'unknown door'}
