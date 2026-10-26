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
    POST /api/board/benches                              {name, title?, notes?}        -> 201 an empty bench (409 on a duplicate name)
    POST /api/board/benches/{bench}/attempt              {mission}                     -> cmod solve() over the bench's boards (404 + mission names for an unknown one)
    GET  /api/board/benches/{bench}/attempts             {ok, rows}  wb-2: the LAST attempt on that bench as ONE summary row (verdict, mission, boards_used, not_modelled, run sha)
    GET  /api/board/benches/{bench}/attempts/candidates  {ok, rows}  the last attempt's candidates, every column a plain string
    GET  /api/board/benches/{bench}/attempts/pruned      {ok, rows}  the last attempt's gap (unmet purposes) then its pruned branches with reasons
wb-2: the last attempt per bench lives in the module-level dict `_LAST` - PER PROCESS, NOT PERSISTED (a restart or a second worker forgets it; wb-3 / mis-1 persist
MissionRun rows). Bench rows add board_count + breadboard_count; breadboard options add `outline` (width x height mm) and `fits` (one line over the boards on the bench);
board options add `footprint` (a plain sentence from footprint_json).
bench-options/breadboards rows add rail_power + fit_json {board: breadboard_fit}; bench-options/boards rows add arch, riscv, radios, radios_json, levels,
footprint_json and take the knobs arch= (riscv|not-riscv|<family>) radio= (wifi|ble|802.15.4|thread|lora|none|unverified) level= (bare_c|freertos|zephyr; status yes only).
An unknown bench, board or model is 404; a bad body 400.
"""
import json

from board.custom import bench_seed as SEED
from board.custom import chip_ladder as CL

_MEM = {}   # the in-memory benches when no manager is given (selftests)
_LAST = {}  # wb-2: bench name -> the last attempt result; per process, not persisted


def _j(text, default):
    return CL._j(text, default)


# ---------------------------------------------------------------------------------------------------- stores
def _live_rows(manager, cls):
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls, {}) or {}).values()) if manager is not None else []


def bench_dict(row):
    if isinstance(row, dict):
        return dict(row)
    return {k: getattr(row, k, '[]' if k == 'instruments_json' else '') for k in _FIELDS}


#: the Bench row's fields; instruments_json (osc-0) is owned by instruments.custom.catalog - this module only carries it
_FIELDS = ('name', 'title', 'boards_json', 'breadboards_json', 'notes', 'source', 'instruments_json')


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
        row = Bench(manager=manager, **{k: b.get(k, '[]' if k == 'instruments_json' else '') for k in _FIELDS})
    else:
        for k in ('title', 'boards_json', 'breadboards_json', 'notes', 'instruments_json'):
            setattr(row, k, b.get(k, '[]' if k == 'instruments_json' else ''))
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
                        'price_usd': b.get('price_usd', ''), 'note': b.get('note', ''),
                        'footprint_json': b.get('footprint_json') or {}, 'radios_json': b.get('radios_json') or [], 'levels_chip': _j(e.get('levels_json'), {})}
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
        nbb = sum(int(e.get('count') or 1) for e in _j(b.get('breadboards_json'), []))
        nin = sum(int(e.get('count') or 1) for e in _j(b.get('instruments_json'), []))
        out.append({'name': b['name'], 'title': b['title'], 'boards': len(br), 'breadboards': nbb, 'board_count': len(br), 'breadboard_count': nbb,
                    'instruments': nin, 'instrument_count': nin,
                    'simulated_real_pins': len([r for r in br if r['testing_group'] == 'simulated']),
                    'simulated_stub_pins': len([r for r in br if r['testing_group'] == 'simulated-stub']),
                    'hardware_only': len([r for r in br if r['testing_group'] == 'hardware-only']),
                    'hardware_only_boards': ', '.join(r['label'] for r in br if r['testing_group'] == 'hardware-only') or 'none', 'notes': b.get('notes', '')})
    return out


ARCH_KNOBS = ('riscv', 'not-riscv')
RADIO_KNOBS = ('wifi', 'ble', '802.15.4', 'thread', 'lora', 'none', 'unverified')
LEVEL_KNOBS = ('bare_c', 'freertos', 'zephyr')
_RADIO_WORD = {'wifi': 'Wi-Fi', 'ble': 'BLE', '802.15.4': '802.15.4', 'thread': 'Thread', 'lora': 'LoRa', 'none': 'no radio', 'unverified': 'radio unverified'}
_RT_OF = {'bare_c': 'bare-c', 'freertos': 'freertos', 'zephyr': 'zephyr'}


def _runtime_profiles(manager):
    """{(board, runtime): row dict} from live RuntimeProfile rows, else the board object's seed tables."""
    rows = _live_rows(manager, 'RuntimeProfile')
    if rows:
        return {(r.board, r.runtime): {'supported': r.supported, 'refusal': r.refusal} for r in rows}
    try:
        from board.custom import board_object as BO
        return {(p.get('board'), p.get('runtime')): p for p in BO.seed_tables().get('RuntimeProfile', [])}
    except Exception:  # noqa: BLE001 - no board object: the chip's levels alone speak
        return {}


def board_levels(info, profiles):
    """{bare_c|freertos|zephyr: {status, basis}}: the chip's levels_json, overridden by the board's RuntimeProfile when one exists (the stronger, board-specific basis)."""
    out = {}
    for lv in LEVEL_KNOBS:
        c = (info.get('levels_chip') or {}).get(lv) or {'status': 'unverified', 'basis': 'no ladder claim'}
        st, basis = c.get('status', 'unverified'), 'chip ladder: ' + str(c.get('basis', ''))
        alts = ['esp-idf'] if lv == 'freertos' else []
        for rt in [_RT_OF[lv]] + alts:
            p = profiles.get((info['board'], rt))
            if p:
                st = 'yes' if p.get('supported') else 'no'
                basis = 'RuntimeProfile %s:%s%s' % (info['board'], rt, '' if p.get('supported') else ' refuses: ' + str(p.get('refusal', ''))[:120])
                break
        out[lv] = {'status': st, 'basis': basis}
    return out


def _radios_text(rs):
    parts, mods, certs = [], [], []
    for r in rs:
        parts.append(_RADIO_WORD.get(r.get('kind'), r.get('kind', '?')))
        mods.append(str(r.get('module') or ''))
        pc = r.get('precertified') or {}
        certs.append('FCC %s / IC %s / CE %s' % (pc.get('fcc_id') or '-', pc.get('ic') or '-', 'unverified' if pc.get('ce') is None else ('yes' if pc['ce'] else 'no')))
    if not rs:
        return 'unverified'
    if all(r.get('kind') == 'none' for r in rs):
        return 'no radio'
    m = next((x for x in mods if x), 'unverified')
    c = certs[0]
    unv = all('unverified' in c or 'FCC - ' in c for c in certs[:1])
    return '%s (module %s, %s)' % (' + '.join(parts), m.split(' (')[0] if m != 'unverified' else 'unverified', 'uncertified/unverified' if unv else c)


def footprint_text(fp):
    """A footprint_json as one plain sentence: '2 rows, 7 pitches apart, 16 pins/row - straddles', or 'unverified' when the numbers are -1."""
    fp = fp or {}
    rows, s, n = fp.get('rows', -1), fp.get('row_spacing_pitches', -1), fp.get('pins_per_row', -1)
    if fp.get('straddles') is False:
        return '%s, %s - beside the breadboard (not on a continuous 0.1 in grid)' % ('rows unverified' if rows in (-1, None) else '%s rows' % rows, 'pins/row unverified' if n in (-1, None) else '%s pins/row' % n)
    if -1 in (rows, s, n) or None in (rows, s, n):
        return 'unverified'
    return '%s rows, %s pitches apart, %s pins/row - straddles' % (rows, s, n)


def board_options(manager=None, bench_name='', arch='', radio='', level=''):
    b = bench(bench_name, manager) if bench_name else None
    on = {}
    for e in _j((b or {}).get('boards_json'), []):
        on[e.get('board', '')] = on.get(e.get('board', ''), 0) + 1
    profiles = _runtime_profiles(manager)
    rows = []
    for key, info in sorted(ladder_boards(manager).items(), key=lambda kv: (kv[1]['section'] != 'RISC-V', kv[1]['testing_group'] != 'simulated', kv[0])):
        lv = board_levels(info, profiles)
        rs = info['radios_json']
        if arch and not ((arch == 'riscv' and info['family'] == 'RISC-V') or (arch == 'not-riscv' and info['family'] != 'RISC-V') or arch == info['family']):
            continue
        if radio and radio not in [r.get('kind') for r in rs]:
            continue
        if level and lv[level]['status'] != 'yes':
            continue
        words = ' \u00b7 '.join('%s %s' % (l.replace('_', '-'), lv[l]['status']) for l in LEVEL_KNOBS)
        src = ', '.join(sorted({'RuntimeProfile' if v['basis'].startswith('RuntimeProfile') else 'chip ladder' for v in lv.values()}))
        rows.append(dict({k: v for k, v in info.items() if k != 'levels_chip'}, on_bench=on.get(key, 0), can_add=True, bench=bench_name, arch=info['family'],
                         riscv=info['family'] == 'RISC-V', radios=_radios_text(rs), footprint=footprint_text(info['footprint_json']), levels='%s (basis: %s)' % (words, src), levels_json=lv))
    return rows


def rail_power_text(m):
    v, a = m.get('rail_voltage_max_v', -1), m.get('rail_current_max_a', -1)
    if v == -1 and a == -1:
        return 'unverified'
    return '%s V / %s A (%s)' % ('?' if v == -1 else '%g' % v, '?' if a == -1 else '%g' % a, m.get('power_basis', ''))


def _fit_words(f):
    v = f.get('verdict')
    if v == 'straddles':
        return 'straddles, %s free holes/side' % f.get('free_holes_per_side')
    return {'beside': 'beside', 'too-wide': 'too wide', 'too-long': 'too long (not enough rows)'}.get(v, 'unverified')


def breadboard_options(manager=None, bench_name=''):
    from board.custom.bench_fit import breadboard_fit
    b = bench(bench_name, manager) if bench_name else None
    on = {e.get('model', ''): int(e.get('count') or 1) for e in _j((b or {}).get('breadboards_json'), [])}
    lb = ladder_boards(manager)
    keys = [e.get('board', '') for e in _j((b or {}).get('boards_json'), [])]
    rows = []
    for m in models(manager):
        fit = {k: breadboard_fit((lb.get(k) or {}).get('footprint_json'), m) for k in dict.fromkeys(keys) if k}
        fits = ' \u00b7 '.join('%s: %s' % (lb[k]['title'] if k in lb else k, _fit_words(v)) for k, v in fit.items()) or 'no boards on the bench yet'
        outline = '%g x %g mm' % (m['width_mm'], m['height_mm']) if m.get('width_mm', -1) > 0 and m.get('height_mm', -1) > 0 else 'unverified'
        rows.append(dict(m, outline=outline, fits=fits, geometry='known (%.1f x %.1f mm)' % (m['width_mm'], m['height_mm']) if m.get('geometry_known') else 'UNVERIFIED - cannot be drawn or placed on yet',
                         on_bench=on.get(m['name'], 0), can_add=True, bench=bench_name, rail_power=rail_power_text(m), fit_json=fit))
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
        knobs = {'arch': (params.get('arch') or '').strip(), 'radio': (params.get('radio') or '').strip(), 'level': (params.get('level') or '').strip()}
        for k, allowed in (('arch', ARCH_KNOBS), ('radio', RADIO_KNOBS), ('level', LEVEL_KNOBS)):
            v = knobs[k]
            fams = sorted({r['family'] for r in ladder_boards(manager).values()}) if k == 'arch' else []
            if v and v not in allowed and v not in fams:
                return 400, {'ok': False, 'error': 'unknown %s %r' % (k, v), 'allowed': list(allowed) + fams}
        return 200, {'ok': True, 'rows': board_options(manager, (params.get('bench') or SEED.HOME_BENCH).strip(), **knobs)}
    if which in ('attempts', 'attempts-candidates', 'attempts-pruned'):
        if bench(bench_name, manager) is None:
            return 404, {'ok': False, 'error': 'no bench named %r' % bench_name, 'known': [x['name'] for x in benches(manager)]}
        return 200, {'ok': True, 'bench': bench_name, 'rows': attempt_rows(bench_name, which)}
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


def create_bench(manager, body):
    name = str((body or {}).get('name', '')).strip()
    if not name:
        return 400, {'ok': False, 'error': 'name is required'}
    if bench(name, manager) is not None:
        return 409, {'ok': False, 'error': 'a bench named %r already exists' % name}
    b = {'name': name, 'title': str(body.get('title') or name), 'boards_json': '[]', 'breadboards_json': '[]', 'instruments_json': '[]',
         'notes': str(body.get('notes') or ''), 'source': 'wb-0 create door'}
    _save(manager, b)
    return 201, {'ok': True, 'bench': name, 'rows': bench_rows(manager)}


def mission_names(manager=None):
    from cmod.custom import mission_seeds as MS
    names = [m['name'] for m in MS.MISSION_SEEDS]
    names += [getattr(r, 'name', '') for r in _live_rows(manager, 'HardwareMission')]
    return sorted({n for n in names if n})


def attempt(manager, bench_name, body):
    """Wrap cmod solve() over the bench's boards the engine models. The engine honours none of allowed_boards / max_dev_boards / max_breadboards / on_hand_only
    (normalise_limits raises on an unknown key), so only `boards` and max_candidates are passed; boards without a SoC row are named in `not_modelled`."""
    b = bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    mission = str((body or {}).get('mission', '')).strip()
    names = mission_names(manager)
    if mission not in names:
        return 404, {'ok': False, 'error': 'no mission named %r' % mission, 'known': names}
    from cmod.custom import isotope_variants_eligibility as E
    from cmod.custom import solve as SOLVE
    from cmod.custom import solve_record as SR
    keys = list(dict.fromkeys(e.get('board', '') for e in _j(b.get('boards_json'), []) if e.get('board')))
    known = set(E.boards())
    use = [k for k in keys if k in known]
    gone = [k for k in keys if k not in known]
    if not use:
        out = {'ok': True, 'verdict': 'none', 'mission': mission, 'bench': bench_name, 'candidates': [], 'gap': [], 'pruned': [], 'run': {}, 'boards_used': [],
               'not_modelled': gone, 'why': 'no board on this bench has a SoC row the attempt engine models'}
        _LAST[bench_name] = out
        return 200, out
    res = SOLVE.solve(mission, boards=use, limits={'max_candidates': 10}, manager=manager)
    w = res['chosen_candidate']
    if w and w['complete'] and w['meets_criteria'] and w.get('buildable_on_bench', True):
        verdict = 'meets'
    elif res['candidates']:
        verdict = 'closest'
    else:
        verdict = 'none'
    cand = [{k: c.get(k) for k in ('id', 'rank', 'routes_text', 'tier', 'complete', 'meets_criteria', 'lost', 'buildable_on_bench', 'parts_missing', 'pins_used')} | {'board': c['hardware']['board']}
            for c in res['candidates']]
    run = {'result_sha256': res['result_sha256'], 'inputs_sha256': SR.SI.sha(res['inputs'])}
    if manager is not None:
        row = SR.store(manager, res, who='bench attempt')
        run['name'] = row.name
    out = {'ok': True, 'verdict': verdict, 'mission': mission, 'bench': bench_name, 'boards_used': use, 'not_modelled': gone, 'candidates': cand,
           'gap': list(w['lost']) if (w and verdict != 'meets') else [], 'pruned': res['pruned_rows'], 'run': run}
    _LAST[bench_name] = out
    return 200, out


def _s(v):
    return ', '.join(str(x) for x in v) if isinstance(v, (list, tuple)) else ('' if v is None else str(v))


def attempt_rows(bench_name, which):
    """wb-2: the last stored attempt on `bench_name` as scalar-only rows (no stored attempt -> [])."""
    a = _LAST.get(bench_name)
    if not a:
        return []
    if which == 'attempts':
        return [{'bench': bench_name, 'verdict': a['verdict'], 'mission': a['mission'], 'boards_used': _s(a['boards_used']) or 'none', 'not_modelled': _s(a['not_modelled']) or 'none',
                 'candidates': len(a['candidates']), 'run_sha': (a.get('run') or {}).get('result_sha256', ''), 'why': a.get('why', '')}]
    if which == 'attempts-candidates':
        return [{'rank': c.get('rank'), 'board': c.get('board', ''), 'tier': _s(c.get('tier')), 'complete': 'yes' if c.get('complete') else 'no',
                 'meets_criteria': 'yes' if c.get('meets_criteria') else 'no', 'buildable_on_bench': 'yes' if c.get('buildable_on_bench') else 'no',
                 'routes': _s(c.get('routes_text')), 'pins_used': _s(c.get('pins_used')), 'unmet': _s(c.get('lost')) or 'none', 'parts_missing': _s(c.get('parts_missing')) or 'none'}
                for c in a['candidates']]
    rows = [{'what': 'gap', 'count': 1, 'where': a['mission'], 'reason': _s(g)} for g in a['gap']]
    rows += [{'what': 'pruned: %s' % p.get('kind', ''), 'count': p.get('count', 1), 'where': _s(p.get('where')), 'reason': _s(p.get('reason'))} for p in a['pruned']]
    return rows


def post_door(manager, bench_name, which, body):
    if not isinstance(body, dict):
        return 400, {'ok': False, 'error': 'the body must be a JSON object'}
    if which == 'boards':
        return add_board(manager, bench_name, body)
    if which == 'breadboards':
        return add_breadboard(manager, bench_name, body)
    if which == 'remove':
        return remove(manager, bench_name, body)
    if which == 'create':
        return create_bench(manager, body)
    if which == 'attempt':
        return attempt(manager, bench_name, body)
    return 404, {'ok': False, 'error': 'unknown door'}
