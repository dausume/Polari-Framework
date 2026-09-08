"""
@cross-cutting
@module casting.custom.mold_geometry
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

Imported meshes (cast-2): they have no volumetric field — mathshapes
silently evaluates them as outside-everywhere, so the FIELD path is
never used for them. Instead the mesh voxelizes onto the stock's own
lattice (casting.custom.mesh_voxelize, exact vertex-scale shrink) and the
body is carried as an OccupancyGrid: body cells = stock \ part. The
CSG body row is a NAMED ABSENCE for imported parts, not a silent
stand-in; the grid volume cross-checks against the CAD import
record's own volume.

Duck-typed manager, stdlib. @see /WAX_MOLD_NESTING_PLAN.md (cast-1)
"""

import json

from mathshapes.custom.shape_analysis import (
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
    try:
        shrink_pct = float(getattr(mold, 'shrink_allowance_pct', 0.0)
                           or 0.0)
    except (TypeError, ValueError):
        return {'ok': False,
                'error': 'shrink_allowance_pct is not a number'}
    s = 1.0 + shrink_pct / 100.0
    if s <= 0.0:
        return {'ok': False,
                'error': f'shrink_allowance_pct={shrink_pct} implies a '
                         f'non-positive scale — nonsensical'}
    if getattr(mold, 'part_source', 'mathshape') == 'imported-cad':
        return _derive_imported_mold(manager, mold, mold_name,
                                     part_ref, s, shrink_pct, persist)
    part = _named(manager, part_ref)
    if part is None:
        return {'ok': False,
                'error': f"mold '{mold_name}': no MathShapeDefinition "
                         f"named '{part_ref}'"}
    family = getattr(part, 'family', 'primitive')
    if family == 'imported-mesh':
        return {'ok': False, 'refusal': 'imported-mesh via field path',
                'error': f"part '{part_ref}' is an imported mesh but "
                         f"part_source says 'mathshape' — its field "
                         f'silently reads outside-everywhere, which '
                         f'would derive a confidently EMPTY mold. Set '
                         f"part_source='imported-cad' to use the grid "
                         f'path.',
                'suggestion': {'knob': 'part_source',
                               'action': "set 'imported-cad'"}}
    if family not in _FIELD_FAMILIES:
        return {'ok': False, 'refusal': f"family '{family}'",
                'error': f"part '{part_ref}' is family '{family}' — no "
                         f'volumetric inside/outside field to invert '
                         f'(winding/gear/spool are measured or '
                         f'parametric, not volumetric). Carried as a '
                         f'named absence.'}

    rows = []
    findings = []
    # -- the cavity form: the part itself, or its shrink-scaled copy --
    cavity_name = part_ref
    scaled_name = ''
    if abs(s - 1.0) > 1e-12:
        # gap geo-shrink-scale-origin: the scale is about the ORIGIN;
        # an off-center part translates as it scales — say so.
        pb = _shape_bounds(manager, part)
        if pb:
            extent = max(hi - lo for lo, hi in pb) or 1.0
            off = max(abs(hi + lo) / 2.0 for lo, hi in pb)
            if off > 0.1 * extent:
                findings.append(
                    f'part center is ~{off:.2f}cm off origin '
                    f'(>10% of its {extent:.2f}cm extent) — the '
                    f'uniform shrink scale is about the ORIGIN, so '
                    f'the scaled copy shifts by ~{off * abs(s - 1.0):.3f}cm; '
                    f'recenter the part or account for the shift '
                    f'(gap geo-shrink-scale-origin)')
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
        'findings': findings,
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


# --------------------------------------------------------------------------
# cast-2: imported-mesh parts — the grid path
# --------------------------------------------------------------------------
#: Grid lattice for imported-part derivation; mesh parity at this
#: resolution is a coarser instrument than the field grid, so its
#: cross-check tolerance is wider (and named).
_MESH_GRID_RES = 32
_MESH_CHECK_TOL = 0.08


def _resolve_imported_shape(manager, ref):
    """The imported-mesh MathShapeDefinition for `ref` — accepts the
    shape row's own name or an ImportedCadObject name (resolved via
    its shape_name)."""
    shape = _named(manager, ref)
    if shape is not None:
        return shape, None
    for r in _rows(manager, 'ImportedCadObject'):
        if getattr(r, 'name', '') == ref:
            shape = _named(manager, getattr(r, 'shape_name', ''))
            if shape is not None:
                return shape, r
    return None, None


def _import_record_for(manager, shape_name):
    for r in _rows(manager, 'ImportedCadObject'):
        if getattr(r, 'shape_name', '') == shape_name:
            return r
    return None


def _derive_imported_mold(manager, mold, mold_name, part_ref, s,
                          shrink_pct, persist,
                          grid_resolution=_MESH_GRID_RES):
    """Grid derivation for an imported CAD part: voxelize the mesh
    (vertex-scaled by the shrink factor — exact) onto the stock's own
    lattice; body cells = stock \\ part. The CSG body row is a NAMED
    ABSENCE (no field exists to write); downstream consumers read the
    grid summary from derivation_json and rebuild grids on demand."""
    from casting.custom.mesh_voxelize import mesh_grid

    shape, record = _resolve_imported_shape(manager, part_ref)
    if shape is None:
        return {'ok': False,
                'error': f"mold '{mold_name}': '{part_ref}' names no "
                         f'imported-mesh shape or ImportedCadObject'}
    if getattr(shape, 'family', '') != 'imported-mesh':
        return {'ok': False,
                'error': f"part_source='imported-cad' but "
                         f"'{getattr(shape, 'name', '')}' is family "
                         f"'{getattr(shape, 'family', '')}' — fix "
                         f'part_source or the ref'}
    try:
        b = json.loads(getattr(shape, 'bounds_json', '') or 'null')
    except (TypeError, ValueError):
        b = None
    if not b:
        return {'ok': False,
                'error': f"imported shape "
                         f"'{getattr(shape, 'name', '')}' has no "
                         f'bounds_json — re-import it'}
    b = [[float(lo) * s, float(hi) * s] for lo, hi in b]
    try:
        margin = float(getattr(mold, 'stock_margin_cm', 1.0) or 0.0)
    except (TypeError, ValueError):
        margin = 1.0
    if margin <= 0.0:
        return {'ok': False,
                'error': f'stock_margin_cm={margin} — the stock must '
                         f'clear the part on every side'}
    stock_bounds = [[lo - margin, hi + margin] for lo, hi in b]
    stock_name = f'{mold_name}--stock'
    stock_size = [round(hi - lo, 6) for lo, hi in stock_bounds]
    stock_center = [round((hi + lo) / 2.0, 6) for lo, hi in stock_bounds]

    part_res = mesh_grid(shape, resolution=grid_resolution, scale=s,
                         bounds=stock_bounds)
    if not part_res.get('ok'):
        return part_res
    part_grid = part_res['grid']
    body_grid = part_grid.complement()

    if not persist:
        return {'ok': True, 'mold': mold_name, 'dryRun': True,
                'mode': 'grid', 'rows': [stock_name]}

    converge = _converge_shape_rows(manager, [{
        'name': stock_name,
        'display_name': f'{mold_name} stock block',
        'family': 'primitive', 'primitive_kind': 'box',
        'quadric_matrix_json': '', 'csg_json': '',
        'parameters_json': json.dumps({'size': stock_size,
                                       'center': stock_center}),
        'bounds_json': '', 'provenance_id': 'cast-2',
        'notes': f'derived: AABB of imported '
                 f"{getattr(shape, 'name', '')} ×{s:.4f} + "
                 f'{margin:.2f}cm margin each side'}])
    if not converge.get('ok', True):
        return converge

    v_stock = stock_size[0] * stock_size[1] * stock_size[2]
    v_part = part_grid.volume_cm3()
    v_body = body_grid.volume_cm3()
    # Cross-check: the grid's part volume vs the CAD importer's own
    # measurement, scaled — two independent instruments.
    record = record or _import_record_for(
        manager, getattr(shape, 'name', ''))
    check = {'ok': None,
             'note': 'no ImportedCadObject volume to check against'}
    rec_vol = float(getattr(record, 'volume_cm3', 0.0) or 0.0) \
        if record is not None else 0.0
    if rec_vol > 0.0:
        expected = rec_vol * s ** 3
        dev = abs(v_part - expected) / expected
        check = {'ok': dev <= _MESH_CHECK_TOL,
                 'gridPartCm3': round(v_part, 3),
                 'importerPartCm3': round(expected, 3),
                 'relDeviation': round(dev, 4),
                 'tolerance': _MESH_CHECK_TOL,
                 'note': f'mesh parity grid (N={grid_resolution}) vs '
                         f'the CAD importer volume — independent '
                         f'instruments'}

    gaps = list(part_res.get('gaps', []))
    gaps.append('no CSG body row for an imported part — no analytic '
                'field exists; the body is carried as a grid (named '
                'absence, not a stand-in)')

    mold.stock_shape_name = stock_name
    mold.scaled_part_shape_name = ''
    mold.body_shape_name = ''
    mold.derivation_json = json.dumps({
        'mode': 'grid', 'gridResolution': grid_resolution,
        'scaleFactor': round(s, 6),
        'stockVolumeCm3': round(v_stock, 3),
        'partVolumeCm3': round(v_part, 3),
        'bodyVolumeCm3': round(v_body, 3),
        'volumeCheck': check, 'gaps': gaps,
        'rows': [stock_name]})
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(mold)
        except Exception:
            pass
    return {'ok': True, 'mold': mold_name,
            'part': getattr(shape, 'name', ''), 'mode': 'grid',
            'stockShape': stock_name, 'scaledPartShape': '',
            'bodyShape': '',
            'shrinkAllowancePct': shrink_pct,
            'scaleFactor': round(s, 6),
            'inserted': converge['inserted'],
            'reconverged': converge['reconverged'],
            'stockVolumeCm3': round(v_stock, 3),
            'partVolumeCm3': round(v_part, 3),
            'bodyVolumeCm3': round(v_body, 3),
            'volumeCheck': check, 'gaps': gaps,
            'note': 'imported part derived on the GRID path: mesh '
                    'voxelized (vertex-scaled — exact) onto the '
                    "stock's lattice; body = stock \\ part. No CSG "
                    'body row — a named absence, see gaps.'}
