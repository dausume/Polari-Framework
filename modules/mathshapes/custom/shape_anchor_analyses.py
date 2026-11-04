"""
@module mathshapes.custom.shape_anchor_analyses

The ms-anchor engine (custom/shape_anchor.py) as Polari ANALYSES —
`fn(manager, **params) -> dict`, the contract of
polariNoCode.analysis_calls: an AnalysisDefinition row names each one
by `callable_ref` (shape_anchor_seed.SEED_SHAPE_ANCHOR_ANALYSES), an
AnalysisCall node in any no-code solution runs it, and one seeded
DirectInvocation → AnalysisCall → ReturnValue solution per analysis
makes it runnable through the generic solution-execution routes. No
custom API (Dustin 2026-11-03: "polari fully automates away api
creation so long as functionality and engines are wrapped by polari
properly") — the routes this replaces were removed from shape_api.py.

The engine stays pure in shape_anchor.py; this file adapts names →
rows, trims what JSON cannot carry (the callables), and refuses by
name with {'ok': False, 'error', 'suggestion'} for a missing row
(knobs-and-suggestions), never raising for a bad name.

Persistence: the two writing analyses (pick_anchor persist=True,
offset_result persist=True) land rows on the manager's objectTables
(a real ShapeAnchor row when the manager can mint ids, else a plain
attribute bundle the CRUDE layer can adopt) and save through
manager.db when present.

@consumers mathshapes.shape_anchor_seed (SEED_SHAPE_ANCHOR_ANALYSES),
SolutionExecutionEngine (AnalysisCall / SolutionInvocation),
mathshapes.shape_anchor_selftest
"""
import json

from mathshapes.custom import shape_anchor as engine
from mathshapes.objects.shape._shared import REFERENCE_MODES


def _rows(manager, cls):
    t = (getattr(manager, 'objectTables', {}) or {}).get(cls) or {}
    return list(t.values()) if isinstance(t, dict) else list(t)


def _names(manager, cls):
    return sorted(str(getattr(r, 'name', '')) for r in _rows(manager, cls))


def _missing(cls, name, known):
    return {'ok': False, 'error': f'no {cls} named {name!r}',
            'suggestion': {'knob': f'{cls}.name', 'evidence': known[:20]}}


def _public(row):
    """A row as JSON: no manager/tree internals, *_json fields parsed."""
    src = row if isinstance(row, dict) else vars(row)
    out = {}
    for k, v in src.items():
        if k.startswith('_') or k in ('manager', 'polServer', 'branch',
                                      'inTree'):
            continue
        if k.endswith('_json') and isinstance(v, str) and v:
            try:
                v = json.loads(v)
            except ValueError:
                pass
        out[k] = v
    return out


def _jsonable(value):
    if callable(value):
        return '<fn>'
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _save(manager, row):
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception:
            pass


def _upsert(manager, cls, payload, make_row):
    """Insert-or-update by name on objectTables[cls]; a real treeObject
    row only when the manager can mint ids (idList), else a bundle."""
    tables = getattr(manager, 'objectTables', None)
    if tables is None:
        return None, False
    table = tables.setdefault(cls, {})
    row = table.get(payload['name']) if isinstance(table, dict) else None
    if row is None and isinstance(table, dict):
        row = next((r for r in table.values()
                    if getattr(r, 'name', '') == payload['name']), None)
    created = row is None
    if created:
        if hasattr(manager, 'idList'):
            try:
                row = make_row(manager, payload)
            except Exception:
                row = engine._ShapeRow(**payload)
        else:
            row = engine._ShapeRow(**payload)
        if isinstance(table, dict):
            table[payload['name']] = row
    else:
        for k, v in payload.items():
            setattr(row, k, v)
    _save(manager, row)
    return row, created


# ---- step 1 + 2: anchors -----------------------------------------------

def pick_anchor(manager, shape='', ray_origin=None, ray_dir=None,
                reference='toward', name='', persist=False,
                max_dist=None, step=None):
    """Ray-pick an anchor on a MathShapeDefinition: the hit, the normal
    (∇F/|∇F|), the tangent basis and the frame for `reference`; with
    persist=True the ShapeAnchor row is upserted by name."""
    if engine._shape_named(manager, shape) is None:
        return _missing('MathShapeDefinition', shape,
                        _names(manager, 'MathShapeDefinition'))
    reference = reference or 'toward'
    if reference not in REFERENCE_MODES:
        return {'ok': False,
                'error': f'reference {reference!r} is not one of '
                         f'{list(REFERENCE_MODES)}',
                'suggestion': {'knob': 'reference',
                               'evidence': list(REFERENCE_MODES)}}
    pick = engine.pick_anchor(manager, shape, ray_origin or [0, 0, 0],
                              ray_dir or [0, 0, -1], max_dist=max_dist,
                              step=step)
    if not pick.get('ok'):
        return {'ok': False, 'error': pick.get('refusal'),
                'suggestion': {'knob': 'ray_origin / ray_dir',
                               'evidence': {k: pick.get(k) for k in
                                            ('step', 'maxDist')}}}
    name = name or f'{shape}-anchor'
    payload = engine.anchor_payload(pick, name, shape, reference)
    frame = engine.anchor_frame(pick, reference)
    out = {'ok': True, 'shape': shape, 'name': name, 'pick': pick,
           'frame': frame, 'row': _public(payload), 'saved': False}
    if persist:
        from mathshapes.shape_basis import ShapeAnchor
        _, created = _upsert(
            manager, 'ShapeAnchor', payload,
            lambda m, p: ShapeAnchor(manager=m, **p))
        out.update(saved=True, created=created)
    return out


def anchor_frame(manager, anchor='', mode=''):
    """The frame (a, b, c, origin, world→local 4x4) of a ShapeAnchor
    for any of the four references ('' = the anchor's own)."""
    row = engine.anchor_named(manager, anchor)
    if row is None:
        return _missing('ShapeAnchor', anchor, _names(manager, 'ShapeAnchor'))
    out = engine.anchor_frame(row, mode or None)
    if not out.get('ok'):
        return {'ok': False, 'error': out.get('refusal'),
                'suggestion': {'knob': 'mode',
                               'evidence': list(REFERENCE_MODES)}}
    out['anchor'] = anchor
    return out


# ---- step 3 + 4: offsets -----------------------------------------------

def _offset_row(manager, offset):
    row = engine.offset_named(manager, offset)
    if row is None:
        return None, _missing('AnchoredOffset', offset,
                              _names(manager, 'AnchoredOffset'))
    return row, None


def _refused(out):
    return {'ok': False, 'error': out.get('refusal'),
            'suggestion': {'knob': 'AnchoredOffset', 'evidence': out.get('kind', '')}}


def evaluate_offset(manager, offset='', points=None):
    """G / F / the composed result at one or more world points
    (points = [x, y, z] or [[x, y, z], ...]), each with its local
    (u, v, w) in the anchor frame."""
    _, miss = _offset_row(manager, offset)
    if miss:
        return miss
    pts = points if points is not None else [[0.0, 0.0, 0.0]]
    if pts and not isinstance(pts[0], (list, tuple)):
        pts = [pts]
    results = []
    for p in pts:
        try:
            x, y, z = (float(p[0]), float(p[1]), float(p[2]))
        except (TypeError, ValueError, IndexError):
            return {'ok': False, 'error': f'point {p!r} is not [x, y, z]',
                    'suggestion': {'knob': 'points', 'evidence': pts[:5]}}
        out = engine.evaluate_offset(manager, offset, x, y, z)
        if not out.get('ok'):
            return _refused(out)
        results.append(out)
    first = results[0] if results else {}
    return {'ok': True, 'offset': offset, 'count': len(results),
            'mode': first.get('mode'), 'op': first.get('op'),
            'approxReason': first.get('approxReason', ''),
            'points': results}


def sample_offset(manager, offset='', grid=24):
    """Grid-sampled volumes of parent / offset solid / result over the
    offset's bounds (a discretisation, said as such)."""
    _, miss = _offset_row(manager, offset)
    if miss:
        return miss
    try:
        grid = int(grid)
    except (TypeError, ValueError):
        grid = 24
    out = engine.sample_offset(manager, offset, resolution=grid)
    return out if out.get('ok') else _refused(out)


def offset_equations(manager, offset=''):
    """The no-code rows of an offset (frame matrix, local q = M p, G in
    q, the composed field) plus the parent's rows; conform refuses by
    name (no row form yet)."""
    _, miss = _offset_row(manager, offset)
    if miss:
        return miss
    out = engine.offset_equation_rows(manager, offset)
    return out if out.get('ok') else _refused(out)


def offset_result(manager, offset='', persist=False):
    """The result as ordinary MathShapeDefinition rows (planar modes with
    a constant t): world-frame quadrics + `--solid` + `--result` csg;
    persist=True lands them and sets result_shape_ref."""
    row, miss = _offset_row(manager, offset)
    if miss:
        return miss
    out = engine.result_shape_rows(manager, offset, persist=bool(persist))
    if not out.get('ok'):
        return _refused(out)
    rows = out.pop('rows')
    if persist:
        for r in rows:
            _save(manager, r)
        _save(manager, row)
    out['rows'] = [_public(r) for r in rows]
    out['rowNames'] = [r.name for r in rows]
    return _jsonable(out)
