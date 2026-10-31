"""
@module pcb.custom.thermal_inputs

bob-3g (BENCH_BOARDS_PLAN bob-3; the user's words 2026-10-31: "some components are black boxes and we need the capability to run simulations based on their
data sheets specified thermal behavior over time"): WHAT A PERSON GIVES the thermal views - per placed part of a PCB, its power (PartPowerInput: watts,
and on / pulsed / duty-cycled) and its datasheet thermal behaviour (PartThermalModel: Foster stages junction -> board, Tj max, the datasheet's own
junction-to-ambient Rth for comparison). A given power wins over a run's average for that part; a part with neither is not heated.

  parts(manager, board, rows=None)                  one row per placed part: the run's figure, the given one, which is used, its datasheet model
  quantities(manager, board, ref)                   LONG FORM, one row per number a person can give for that part (the page edits `value`)
  set_quantity(manager, board, ref, quantity, value) -> (status, body)   PUT; clear_quantity(...) -> (status, body)   DELETE (back to 'not given')
  power_plan(manager, board, run=None, rows=None)    -> (plan, source_words, unplaced_words, why)  the powers the solvers use, each with where it came from
  models(manager, board, rows=None)                 {ref: {stages, rth, tj_max_c, rth_ja_k_w, reference, name, words}} - the datasheet models that apply
With no manager (selftests) the rows live in this process only.
"""
import json
import math

STAGES = 6
_MEM = {'PartPowerInput': {}, 'PartThermalModel': {}}

#: quantity -> (class, unit, meaning). The Foster stages are r<i>_k_w / tau<i>_s, i = 1..STAGES.
QUANTITIES = {
    'power_w': ('PartPowerInput', 'W', 'power while on (-1 = not given: the run\'s average is used)'),
    'on_s': ('PartPowerInput', 's', 'on time: 0 = on for the whole run; > 0 = one pulse this long (or per period)'),
    'period_s': ('PartPowerInput', 's', 'repeat period: 0 = no repeat; > 0 = on for on_s at the start of every period'),
    'tj_max_c': ('PartThermalModel', 'C', 'the datasheet\'s maximum junction temperature (0 = not given)'),
    'rth_ja_k_w': ('PartThermalModel', 'K/W', 'the datasheet\'s junction-to-ambient Rth, on ITS test board - shown beside the result, never added (0 = not given)'),
}
for _i in range(1, STAGES + 1):
    QUANTITIES['r%d_k_w' % _i] = ('PartThermalModel', 'K/W', 'Foster stage %d resistance, junction -> board (0 = no stage)' % _i)
    QUANTITIES['tau%d_s' % _i] = ('PartThermalModel', 's', 'Foster stage %d time constant (needed when its R > 0)' % _i)
_NOT_GIVEN = {'power_w': -1.0}


def _objs(manager, cls):
    if manager is None:
        return list(_MEM[cls].values())
    return list(((getattr(manager, 'objectTables', None) or {}).get(cls) or {}).values())


def _get(o, k, default=None):
    return o.get(k, default) if isinstance(o, dict) else getattr(o, k, default)


def _find(manager, cls, name):
    return next((o for o in _objs(manager, cls) if _get(o, 'name') == name), None)


def _save(manager, cls, name, fields):
    """Create the row or change the stored one, then persist it (an in-memory manager has no db)."""
    o = _find(manager, cls, name)
    if manager is None:
        _MEM[cls][name] = dict(o or {}, name=name, **fields)
        return _MEM[cls][name]
    if o is None:
        if cls == 'PartPowerInput':
            from pcb.objects.pcb.PartPowerInput import PartPowerInput as C
        else:
            from pcb.objects.pcb.PartThermalModel import PartThermalModel as C
        o = C(manager=manager, name=name, **fields)
    else:
        for k, v in fields.items():
            setattr(o, k, v)
    try:
        manager.db.saveInstanceInDB(o)
    except Exception:  # noqa: BLE001 - an in-memory manager has no db
        pass
    return o


def _stages_of(model):
    """The model's Foster pairs padded to STAGES slots: [[R, tau], ...]."""
    raw = json.loads(_get(model, 'foster_json', '[]') or '[]') if model is not None else []
    return [[float(p[0]), float(p[1])] for p in raw[:STAGES]] + [[0.0, 0.0] for _ in range(STAGES - len(raw[:STAGES]))]


def _symbols(rows):
    return {s['ref']: s for s in rows.get('SchematicSymbol') or [] if s.get('power') != 'yes'}


def model_for(manager, board, ref, symbol=None):
    """The datasheet model that applies to one placed part: '<board>:<ref>' first, else a board-free row whose part_key is the symbol's value or lib_id."""
    own = _find(manager, 'PartThermalModel', '%s:%s' % (board, ref))
    if own is not None:
        return own
    keys = {k for k in ((symbol or {}).get('value'), (symbol or {}).get('lib_id')) if k}
    return next((m for m in _objs(manager, 'PartThermalModel') if not _get(m, 'board') and _get(m, 'part_key') in keys), None)


def models(manager, board, rows=None):
    from pcb.custom.thermal import _rows_of
    from materialsScience.engines.thermal_rc import check_stages, rth
    rows = rows if rows is not None else _rows_of(manager, board, ('SchematicSymbol', 'PcbPad'))
    syms = _symbols(rows)
    out = {}
    for ref in sorted({p['ref'] for p in rows.get('PcbPad') or []} | set(syms)):
        m = model_for(manager, board, ref, syms.get(ref))
        if m is None:
            continue
        pairs = [p for p in _stages_of(m) if p[0] > 0]
        bad = check_stages(pairs)
        cite = (', '.join(x for x in (_get(m, 'document'), _get(m, 'revision'), _get(m, 'page_table')) if x)
                or 'no document named: %s' % (_get(m, 'origin', '') or 'given by a person'))
        out[ref] = {'name': _get(m, 'name'), 'stages': [] if bad else pairs, 'bad': bad, 'rth': rth(pairs) if not bad else -1.0,
                    'tj_max_c': float(_get(m, 'tj_max_c', 0) or 0), 'rth_ja_k_w': float(_get(m, 'rth_ja_k_w', 0) or 0),
                    'reference': _get(m, 'reference', 'board'), 'words': cite}
    return out


def power_plan(manager, board, run=None, rows=None):
    """The power each part gets in the thermal solvers: a given figure (PartPowerInput) wins; otherwise the run's average (pcb.custom.thermal)."""
    from pcb.custom.thermal import dissipation
    given = {_get(o, 'ref'): o for o in _objs(manager, 'PartPowerInput') if _get(o, 'board') == board and float(_get(o, 'power_w', -1)) >= 0}
    parts, why = dissipation(manager, board, run, rows)
    if why and not given:
        return [], '', '', why
    plan, undetermined = [], []
    run_name = parts[0]['run'] if parts else ''
    for p in parts:
        if p['ref'] in given:
            continue
        if p['kind'] != 'V' and p['avg_w'] > 0:
            plan.append({'ref': p['ref'], 'avg_w': p['avg_w'], 'on_s': 0.0, 'period_s': 0.0, 'from': 'run %s' % run_name})
        elif p['avg_w'] == -1.0:
            undetermined.append(p['ref'])
    for ref, o in sorted(given.items()):
        plan.append({'ref': ref, 'avg_w': float(_get(o, 'power_w')), 'on_s': float(_get(o, 'on_s', 0) or 0), 'period_s': float(_get(o, 'period_s', 0) or 0),
                     'from': 'given (%s)' % (_get(o, 'origin') or 'a person')})
    words = ' + '.join(x for x in (('run %s' % run_name) if run_name and any(p['from'].startswith('run') for p in plan) else '',
                                   ('%d given by a person' % len(given)) if given else '') if x) or 'nothing'
    unplaced = ('; power NOT placed (its parts\' current is not in the run): %s' % ', '.join(undetermined)) if undetermined else ''
    return plan, words, unplaced, ''


def parts(manager, board, rows=None):
    from pcb.custom.thermal import _rows_of
    rows = rows if rows is not None else _rows_of(manager, board, ('SchematicSymbol', 'NetEndpoint', 'KiCadArtifact', 'PcbBoard', 'PcbPad'))
    syms = _symbols(rows)
    placed = sorted({p['ref'] for p in rows.get('PcbPad') or []})
    plan, _, _, why = power_plan(manager, board, None, rows)
    used = {p['ref']: p for p in plan}
    from pcb.custom.thermal import dissipation
    run_w = {p['ref']: p['avg_w'] for p in dissipation(manager, board, None, rows)[0]}
    mods = models(manager, board, rows)
    out = []
    for ref in placed:
        given = _find(manager, 'PartPowerInput', '%s:%s' % (board, ref))
        u, m = used.get(ref), mods.get(ref)
        out.append({'board': board, 'ref': ref, 'value': (syms.get(ref) or {}).get('value', ''), 'run_w': run_w.get(ref, -1.0),
                    'given_w': float(_get(given, 'power_w', -1)) if given is not None else -1.0,
                    'on_s': float(_get(given, 'on_s', 0) or 0) if given is not None else 0.0,
                    'period_s': float(_get(given, 'period_s', 0) or 0) if given is not None else 0.0,
                    'used_w': u['avg_w'] if u else 0.0, 'used_from': u['from'] if u else ('not heated' + (' (%s)' % why if why else '')),
                    'datasheet_model': (m['name'] + (' - ' + m['bad'] if m['bad'] else '')) if m else '',
                    'rth_j_board_k_w': m['rth'] if m else -1.0, 'tj_max_c': m['tj_max_c'] if m and m['tj_max_c'] else -1.0})
    return out


def quantities(manager, board, ref):
    p = _find(manager, 'PartPowerInput', '%s:%s' % (board, ref))
    m = _find(manager, 'PartThermalModel', '%s:%s' % (board, ref))
    stages = _stages_of(m)
    out = []
    for q, (cls, unit, meaning) in QUANTITIES.items():
        o = p if cls == 'PartPowerInput' else m
        if q.startswith('r') and q.endswith('_k_w') and q[1:-4].isdigit():
            v = stages[int(q[1:-4]) - 1][0]
        elif q.startswith('tau'):
            v = stages[int(q[3:-2]) - 1][1]
        else:
            v = float(_get(o, q, _NOT_GIVEN.get(q, 0.0))) if o is not None else _NOT_GIVEN.get(q, 0.0)
        stored = o is not None and v != _NOT_GIVEN.get(q, 0.0)
        out.append({'board': board, 'ref': ref, 'quantity': q, 'value': v, 'unit': unit, 'meaning': meaning, 'given': stored,
                    'kept_in': cls, 'origin': _get(o, 'origin', '') if stored else ''})
    return out


def set_quantity(manager, board, ref, quantity, value):
    if quantity not in QUANTITIES:
        return 400, {'ok': False, 'error': 'no quantity %r - %s' % (quantity, ', '.join(QUANTITIES))}
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 400, {'ok': False, 'error': '%s needs a number, got %r' % (quantity, value)}
    if not math.isfinite(v) or v < 0:
        return 400, {'ok': False, 'error': '%s needs a number >= 0, got %r' % (quantity, value)}
    cls = QUANTITIES[quantity][0]
    name = '%s:%s' % (board, ref)
    if cls == 'PartPowerInput':
        cur = _find(manager, cls, name)
        fields = {'board': board, 'ref': ref, quantity: v}
        if cur is None and quantity != 'power_w':
            fields['power_w'] = -1.0
        _save(manager, cls, name, fields)
    elif quantity in ('tj_max_c', 'rth_ja_k_w'):
        _save(manager, cls, name, {'board': board, 'ref': ref, quantity: v})
    else:
        stages = _stages_of(_find(manager, cls, name))
        i = int(quantity[1:-4] if quantity.startswith('r') else quantity[3:-2]) - 1
        stages[i][0 if quantity.startswith('r') else 1] = v
        while stages and stages[-1] == [0.0, 0.0]:
            stages.pop()
        _save(manager, cls, name, {'board': board, 'ref': ref, 'foster_json': json.dumps(stages)})
    return 200, {'ok': True, 'board': board, 'ref': ref, 'quantity': quantity, 'value': v, 'rows': quantities(manager, board, ref)}


def clear_quantity(manager, board, ref, quantity):
    """Back to 'not given': power_w -> -1 (the run's figure is used again), everything else -> 0."""
    if quantity not in QUANTITIES:
        return 400, {'ok': False, 'error': 'no quantity %r - %s' % (quantity, ', '.join(QUANTITIES))}
    if _find(manager, QUANTITIES[quantity][0], '%s:%s' % (board, ref)) is None:
        return 200, {'ok': True, 'board': board, 'ref': ref, 'quantity': quantity, 'cleared': False, 'rows': quantities(manager, board, ref)}
    if quantity == 'power_w':
        _save(manager, 'PartPowerInput', '%s:%s' % (board, ref), {'power_w': -1.0})
        return 200, {'ok': True, 'board': board, 'ref': ref, 'quantity': quantity, 'cleared': True, 'rows': quantities(manager, board, ref)}
    status, body = set_quantity(manager, board, ref, quantity, 0.0)
    return status, dict(body, cleared=True)
