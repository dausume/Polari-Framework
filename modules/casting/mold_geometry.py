"""
@cross-cutting
@module casting.mold_geometry
@tags @xc:bindings

cast-1: the inversion primitive. A mold body is DERIVED from a part's
math definition — never hand-built:

    body = stock DIFFERENCE part      (field: max(F_stock, −F_part))

The existing mathshapes CSG executor evaluates that with zero new
math, which is the whole point: every casting stage in a nesting
chain is this one operation applied again, and chain parity (cast-3)
is just the count of applications.

Shrink allowance is an EXACT transform, not a mesh hack: scaling
space by s maps a quadric Q → D·Q·D with D = diag(1/s,1/s,1/s,1)
(p inside the scaled shape iff p/s inside the original). Primitives
scale their scalar params; CSG scales by recursively scaling its
children. Scale is about the ORIGIN — seeds keep parts origin-
centered; a non-centered part still scales correctly but its center
translates by s too (reported, not hidden).

Derived rows are not opinions: re-derivation overwrites a hand-edited
derived row and NAMES the drift in the result (`reconverged`) — the
refuse-rather-than-diverge posture from the handoff.

Imported meshes are REFUSED here (cast-1): they have no volumetric
field, and mathshapes.shape_analysis silently evaluates them as
outside-everywhere — a fill sim pointed at one would compute a
confidently EMPTY mold. The cast-2 voxel bridge lifts this refusal.

Duck-typed manager, stdlib. @see /WAX_MOLD_NESTING_PLAN.md (cast-1)
"""

import json

from mathshapes.shape_analysis import (
    _named, _params, _shape_bounds, shape_properties,
)

#: Families with a volumetric field the inversion can act on.
_FIELD_FAMILIES = ('primitive', 'quadric', 'csg')
#: parameters_json knobs that scale linearly with the shrink factor.
_SCALAR_PARAMS = ('radius', 'height', 'base_radius', 'top_radius')
_VECTOR_PARAMS = ('size', 'radii', 'center')
#: CSG recursion cap — matches shape_equations.field_spec's depth 8.
_MAX_DEPTH = 8
#: Grid resolution for the derivation's volume cross-check, and the
#: honesty tolerance that goes with it (a res-32 occupancy grid is a
#: few-percent instrument; the check is a drift alarm, not a proof).
_CHECK_RES = 32
_CHECK_TOL = 0.06


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _mold_named(manager, mold_name):
    for m in _rows(manager, 'MoldDefinition'):
        if getattr(m, 'name', '') == mold_name:
            return m
    return None


# --------------------------------------------------------------------------
# exact shrink scaling — quadric transform / primitive params / CSG recurse
# --------------------------------------------------------------------------
def scale_quadric_flat(q16, s):
    """Q → D·Q·D for D = diag(1/s,1/s,1/s,1), on the flat row-major
    16-list mathshapes stores: spatial×spatial entries divide by s²,
    spatial×affine by s, the affine corner is untouched. Exact — the
    scaled surface is still the same quadric family."""
    out = list(q16)
    for i in range(4):
        for j in range(4):
            spatial = (i < 3) + (j < 3)
            if spatial:
                out[4 * i + j] = q16[4 * i + j] / (s ** spatial)
    return out


def _scale_bounds(bounds, s):
    return [[lo * s, hi * s] for lo, hi in bounds] if bounds else None


def _scaled_shape_rows(manager, shape, s, mold_name, depth=0, seen=None):
    """Build the scaled-copy row dict(s) for `shape` (recursing into
    CSG children). Returns (top_name, [row_dicts]) or a refusal dict."""
    if depth > _MAX_DEPTH:
        return None, {'ok': False,
                      'error': f'CSG nesting deeper than {_MAX_DEPTH} '
                               f'while scaling — cycle or runaway'}
    seen = set(seen or ())
    src = getattr(shape, 'name', '')
    if src in seen:
        return None, {'ok': False,
                      'error': f"CSG cycle at '{src}' while scaling"}
    seen.add(src)
    family = getattr(shape, 'family', 'primitive')
    top = f'{mold_name}--scaled--{src}'
    base = {'name': top,
            'display_name': f'{src} ×{s:.4f} (shrink allowance)',
            'family': family, 'primitive_kind': '',
            'quadric_matrix_json': '', 'csg_json': '',
            'parameters_json': '{}', 'bounds_json': '',
            'provenance_id': 'cast-1',
            'notes': f'derived: {src} uniformly scaled ×{s:.4f} about '
                     f'the origin for mold {mold_name} — edit the part '
                     f'or shrink_allowance_pct, not this row'}
    if family == 'primitive':
        params = _params(shape)
        scaled = dict(params)
        for k in _SCALAR_PARAMS:
            if k in scaled:
                scaled[k] = float(scaled[k]) * s
        for k in _VECTOR_PARAMS:
            if k in scaled and isinstance(scaled[k], (list, tuple)):
                scaled[k] = [float(v) * s for v in scaled[k]]
        base['primitive_kind'] = getattr(shape, 'primitive_kind', '')
        base['parameters_json'] = json.dumps(scaled)
        return top, [base]
    if family == 'quadric':
        try:
            q16 = json.loads(getattr(shape, 'quadric_matrix_json', '')
                             or '[]')
        except (TypeError, ValueError):
            q16 = []
        if len(q16) != 16:
            return None, {'ok': False,
                          'error': f"quadric '{src}' has no valid 16-"
                                   f'number matrix to scale'}
        base['quadric_matrix_json'] = json.dumps(
            scale_quadric_flat(q16, s))
        try:
            b = json.loads(getattr(shape, 'bounds_json', '') or 'null')
        except (TypeError, ValueError):
            b = None
        if b:
            base['bounds_json'] = json.dumps(_scale_bounds(b, s))
        return top, [base]
    if family == 'csg':
        try:
            spec = json.loads(getattr(shape, 'csg_json', '') or '{}')
        except (TypeError, ValueError):
            spec = {}
        child_names, rows = [], []
        for nm in (spec.get('shapes', []) or []):
            child = _named(manager, nm)
            if child is None:
                return None, {'ok': False,
                              'error': f"CSG '{src}' references missing "
                                       f"shape '{nm}'"}
            cn, crows = _scaled_shape_rows(manager, child, s, mold_name,
                                           depth + 1, seen)
            if cn is None:
                return None, crows
            child_names.append(cn)
            rows.extend(crows)
        base['csg_json'] = json.dumps({'op': spec.get('op', 'union'),
                                       'shapes': child_names})
        return top, rows + [base]
    return None, {'ok': False,
                  'error': f"family '{family}' has no volumetric field "
                           f'to scale'}


# --------------------------------------------------------------------------
# derived-row convergence — derived rows always converge, drift is named
# --------------------------------------------------------------------------
_ROW_FIELDS = ('display_name', 'family', 'primitive_kind',
               'quadric_matrix_json', 'csg_json', 'parameters_json',
               'bounds_json', 'notes', 'provenance_id')


def _converge_shape_rows(manager, row_dicts):
    """Insert-or-overwrite derived MathShapeDefinition rows. Unlike
    seed_upsert (where is_prior=False protects human edits), a DERIVED
    row is never a human's to keep: drift is overwritten and NAMED.
    Real rows via the class when the manager can host them (persists
    through treeObject/CRUDE); attribute-bundle fallback otherwise
    (selftests' duck manager, matching shape_modify._ShapeRow)."""
    tables = getattr(manager, 'objectTables', None)
    if tables is None:
        return {'ok': False, 'error': 'manager has no objectTables'}
    table = tables.get('MathShapeDefinition')
    if table is None:
        table = tables['MathShapeDefinition'] = {}
    by_name = {getattr(o, 'name', None): o for o in table.values()}
    report = {'inserted': [], 'reconverged': []}
    for rd in row_dicts:
        name = rd['name']
        row = by_name.get(name)
        if row is None:
            made = None
            try:
                from mathshapes.shape_basis import MathShapeDefinition
                made = MathShapeDefinition(**rd, manager=manager)
            except Exception:
                made = None
            if made is None or name not in {
                    getattr(o, 'name', None) for o in table.values()}:
                class _Row:  # shape_modify._ShapeRow idiom
                    pass
                r = _Row()
                for k, v in rd.items():
                    setattr(r, k, v)
                table[name] = r
            report['inserted'].append(name)
            continue
        drift = [f for f in _ROW_FIELDS
                 if getattr(row, f, None) != rd.get(f, None)]
        if drift:
            for f in drift:
                setattr(row, f, rd.get(f))
            db = getattr(manager, 'db', None)
            if db is not None:
                try:
                    db.saveInstanceInDB(row)
                except Exception:
                    pass
            report['reconverged'].append({'name': name, 'fields': drift})
    return report


# --------------------------------------------------------------------------
# the inversion
# --------------------------------------------------------------------------
def derive_mold(manager, mold_name, persist=True):
    """Derive a MoldDefinition's geometry: stock (auto box unless an
    explicit stock_shape_ref), shrink-scaled part copy (when allowance
    ≠ 0), and the mold body = stock DIFFERENCE part. Cross-checks the
    body's grid volume against stock − part and reports the deviation
    (a drift alarm at grid honesty, not a proof)."""
    mold = _mold_named(manager, mold_name)
    if mold is None:
        return {'ok': False,
                'error': f"no MoldDefinition named '{mold_name}'"}
    part_ref = getattr(mold, 'part_shape_ref', '')
    if getattr(mold, 'part_source', 'mathshape') == 'imported-cad':
        return {'ok': False, 'refusal': 'imported-mesh part',
                'error': f"mold '{mold_name}': part '{part_ref}' is an "
                         f'imported CAD mesh. An imported mesh has no '
                         f'volumetric field — shape_analysis silently '
                         f'evaluates it as outside-everywhere, so the '
                         f'derived mold would be confidently EMPTY. '
                         f'Refused until the cast-2 voxel bridge '
                         f'(mesh → occupancy grid) lands.',
                'suggestion': {'knob': 'part_source',
                               'action': 'use a mathshapes part, or '
                                         'wait for cast-2 to voxelize '
                                         'imported meshes'}}
    part = _named(manager, part_ref)
    if part is None:
        return {'ok': False,
                'error': f"mold '{mold_name}': no MathShapeDefinition "
                         f"named '{part_ref}'"}
    family = getattr(part, 'family', 'primitive')
    if family not in _FIELD_FAMILIES:
        return {'ok': False, 'refusal': f"family '{family}'",
                'error': f"part '{part_ref}' is family '{family}' — no "
                         f'volumetric inside/outside field to invert '
                         f'(imported-mesh/winding/gear/spool are '
                         f'measured or parametric, not volumetric). '
                         f'Carried as a named absence.'}

    try:
        shrink_pct = float(getattr(mold, 'shrink_allowance_pct', 0.0)
                           or 0.0)
    except (TypeError, ValueError):
        return {'ok': False,
                'error': f'shrink_allowance_pct is not a number'}
    s = 1.0 + shrink_pct / 100.0
    if s <= 0.0:
        return {'ok': False,
                'error': f'shrink_allowance_pct={shrink_pct} implies a '
                         f'non-positive scale — nonsensical'}

    rows = []
    # -- the cavity form: the part itself, or its shrink-scaled copy --
    cavity_name = part_ref
    scaled_name = ''
    if abs(s - 1.0) > 1e-12:
        scaled_name, scaled_rows = _scaled_shape_rows(
            manager, part, s, mold_name)
        if scaled_name is None:
            return scaled_rows      # the refusal dict
        rows.extend(scaled_rows)
        cavity_name = scaled_name

    # -- stock: explicit ref, or an auto box around the cavity form --
    explicit_stock = getattr(mold, 'stock_shape_ref', '') or ''
    if explicit_stock:
        stock_name = explicit_stock
        if _named(manager, stock_name) is None:
            return {'ok': False,
                    'error': f"stock_shape_ref '{stock_name}' names no "
                             f'MathShapeDefinition'}
        stock_size = None
    else:
        # Bounds of the UNSCALED part, scaled exactly (the scaled copy
        # is not in the table yet during a dry run).
        b = _shape_bounds(manager, part)
        if b is None:
            return {'ok': False,
                    'error': f"part '{part_ref}' has no derivable "
                             f'bounds (unbounded quadric without '
                             f'bounds_json?) — cannot size stock'}
        b = _scale_bounds(b, s)
        try:
            margin = float(getattr(mold, 'stock_margin_cm', 1.0) or 0.0)
        except (TypeError, ValueError):
            margin = 1.0
        if margin <= 0.0:
            return {'ok': False,
                    'error': f'stock_margin_cm={margin} — the stock '
                             f'must clear the part on every side'}
        stock_name = f'{mold_name}--stock'
        stock_size = [round((hi - lo) + 2.0 * margin, 6)
                      for lo, hi in b]
        stock_center = [round((hi + lo) / 2.0, 6) for lo, hi in b]
        rows.append({
            'name': stock_name,
            'display_name': f'{mold_name} stock block',
            'family': 'primitive', 'primitive_kind': 'box',
            'quadric_matrix_json': '', 'csg_json': '',
            'parameters_json': json.dumps({'size': stock_size,
                                           'center': stock_center}),
            'bounds_json': '', 'provenance_id': 'cast-1',
            'notes': f'derived: AABB of {cavity_name} + '
                     f'{margin:.2f}cm margin each side — edit '
                     f'stock_margin_cm or stock_shape_ref, not this '
                     f'row'})

    # -- the inversion itself: body = stock DIFFERENCE cavity form --
    body_name = f'{mold_name}--body'
    rows.append({
        'name': body_name,
        'display_name': f'{mold_name} mold body (negative)',
        'family': 'csg', 'primitive_kind': '',
        'quadric_matrix_json': '',
        'csg_json': json.dumps({'op': 'difference',
                                'shapes': [stock_name, cavity_name]}),
        'parameters_json': '{}', 'bounds_json': '',
        'provenance_id': 'cast-1',
        'notes': f'DERIVED negative: field = max(F_stock, −F_part). '
                 f'One casting stage inverts once — chain parity is '
                 f'the count of these (cast-3). Edit the part or the '
                 f'mold knobs; re-derivation overwrites this row.'})

    if not persist:
        return {'ok': True, 'mold': mold_name, 'dryRun': True,
                'rows': [r['name'] for r in rows]}

    converge = _converge_shape_rows(manager, rows)
    if not converge.get('ok', True):
        return converge

    # -- volume cross-check: grid body vs (stock − cavity form) --
    stock_props = shape_properties(manager, stock_name,
                                   resolution=_CHECK_RES)
    cavity_props = shape_properties(manager, cavity_name,
                                    resolution=_CHECK_RES)
    body_props = shape_properties(manager, body_name,
                                  resolution=_CHECK_RES)
    check = {'ok': False, 'note': 'volume check unavailable'}
    if (stock_props.get('ok') and cavity_props.get('ok')
            and body_props.get('ok')):
        v_stock = stock_props.get('volumeCm3') or 0.0
        v_cav = cavity_props.get('volumeCm3') or 0.0
        v_body = body_props.get('volumeCm3') or 0.0
        expected = v_stock - v_cav
        dev = (abs(v_body - expected) / v_stock) if v_stock else 1.0
        check = {'ok': dev <= _CHECK_TOL,
                 'stockCm3': round(v_stock, 2),
                 'cavityFormCm3': round(v_cav, 2),
                 'bodyCm3': round(v_body, 2),
                 'expectedBodyCm3': round(expected, 2),
                 'relDeviation': round(dev, 4),
                 'tolerance': _CHECK_TOL,
                 'note': f'grid instrument at resolution {_CHECK_RES} '
                         f'— a drift alarm, not a proof'}

    result = {
        'ok': True, 'mold': mold_name, 'part': part_ref,
        'stockShape': stock_name, 'scaledPartShape': scaled_name,
        'bodyShape': body_name,
        'shrinkAllowancePct': shrink_pct, 'scaleFactor': round(s, 6),
        'inserted': converge['inserted'],
        'reconverged': converge['reconverged'],
        'volumeCheck': check,
        'note': 'mold body DERIVED as stock DIFFERENCE part '
                '(max(F_stock, −F_part)); shrink applied as the exact '
                'quadric/param scale about the origin. Derived rows '
                'always reconverge — hand-edits are overwritten and '
                'named in `reconverged`.'}
    if converge['reconverged']:
        result['handEditNote'] = (
            'derived rows had drifted (hand-edit or stale derivation) '
            'and were overwritten: '
            + ', '.join(r['name'] for r in converge['reconverged']))

    # Write the derived names back onto the mold row (CRUDE persists).
    mold.stock_shape_name = stock_name
    mold.scaled_part_shape_name = scaled_name
    mold.body_shape_name = body_name
    mold.derivation_json = json.dumps(
        {'volumeCheck': check, 'scaleFactor': round(s, 6),
         'rows': [r['name'] for r in rows]})
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(mold)
        except Exception:
            pass
    return result
