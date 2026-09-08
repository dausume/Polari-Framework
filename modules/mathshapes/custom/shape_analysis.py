"""
@cross-cutting
@module mathshapes.custom.shape_analysis
@tags @xc:bindings, @xc:render-3d

Manager-facing analysis over MathShapeDefinition rows. Duck-typed
manager (stdlib-only selftests). Every output carries HOW it was derived
(labels travel with numbers) and refuses honestly when a shape/bound is
missing.

  evaluate_point       inside/outside + implicit value at (x,y,z);
                       recurses through CSG children.
  quadric_classify     the standard surface type of a quadric Q —
                       stdlib for axis-aligned Q, a numpy eigen path for
                       a general (rotated) Q, honest "diagonal-only"
                       refusal when numpy is absent (capability ladder).
  shape_properties     volume / surface area / bbox / centroid —
                       ANALYTIC for primitives, deterministic grid-sample
                       for quadric + CSG; `method` names which.
  sample_surface       surface points (+ triangles) for RENDERING — the
                       clean-geometry fix; parametric for primitives +
                       ellipsoid quadrics, a marching grid for CSG /
                       general quadrics. Shaped to feed a
                       Mesh3DDefinition.

@consumers
  - mathshapes.shape_api
@see /MATH_SHAPES_PLAN.md
"""

import json
import math

from mathshapes.custom.shape_geometry import (
    axial_mesh, classify_axis_aligned, ellipsoid_mesh, hollow_frustum_shell_mesh,
    primitive_inside, primitive_properties, quadric_as_ellipsoid,
    quadric_is_axis_aligned, quadric_value, tube_mesh,
)

_MAX_RES = 80            # grid-sample resolution cap (keeps N^3 bounded)
_MAX_DEPTH = 12          # CSG recursion guard


# --------------------------------------------------------------------------
# manager + row helpers
# --------------------------------------------------------------------------
def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _named(manager, name):
    for row in _rows(manager, 'MathShapeDefinition'):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _json(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _quadric_matrix(shape):
    """Parse quadric_matrix_json (16 numbers, row-major) into a 4x4."""
    flat = _json(getattr(shape, 'quadric_matrix_json', ''), None)
    if not isinstance(flat, list) or len(flat) != 16:
        return None
    try:
        vals = [float(v) for v in flat]
    except (TypeError, ValueError):
        return None
    return [vals[0:4], vals[4:8], vals[8:12], vals[12:16]]


def _params(shape):
    return _json(getattr(shape, 'parameters_json', '{}'), {}) or {}


# --------------------------------------------------------------------------
# evaluate — inside/outside + implicit value (interior < 0)
# --------------------------------------------------------------------------
def _evaluate_shape(manager, shape, x, y, z, depth=0, seen=None):
    """(inside, value) for a shape row. Primitive/CSG use a signed
    indicator (-1 inside / +1 outside) so min/max compose booleans;
    quadric uses the real matrix form pᵀQp."""
    if depth > _MAX_DEPTH:
        return False, 1.0
    family = getattr(shape, 'family', 'primitive')
    if family == 'quadric':
        Q = _quadric_matrix(shape)
        if Q is None:
            return False, 1.0
        v = quadric_value(Q, x, y, z)
        return v < 0.0, v
    if family == 'primitive':
        kind = getattr(shape, 'primitive_kind', '')
        inside = primitive_inside(kind, _params(shape), x, y, z)
        return inside, (-1.0 if inside else 1.0)
    if family == 'csg':
        return _evaluate_csg(manager, shape, x, y, z, depth, seen)
    return False, 1.0


def _evaluate_csg(manager, shape, x, y, z, depth, seen):
    spec = _json(getattr(shape, 'csg_json', ''), {}) or {}
    op = spec.get('op', 'union')
    names = spec.get('shapes', []) or []
    seen = set(seen or ())
    seen.add(getattr(shape, 'name', ''))
    child_vals = []
    for nm in names:
        if nm in seen:                        # cycle guard
            continue
        child = _named(manager, nm)
        if child is None:
            continue
        _, v = _evaluate_shape(manager, child, x, y, z, depth + 1, seen)
        child_vals.append(v)
    if not child_vals:
        return False, 1.0
    if op == 'union':
        v = min(child_vals)
    elif op == 'intersection':
        v = max(child_vals)
    elif op == 'difference':
        base = child_vals[0]
        v = max([base] + [-c for c in child_vals[1:]])
    else:
        v = min(child_vals)
    return v < 0.0, v


def evaluate_point(manager, shape_name, x, y, z):
    """Public: {inside, value, family} at a point."""
    shape = _named(manager, shape_name)
    if shape is None:
        return {'ok': False, 'error': f"no MathShapeDefinition named "
                f"'{shape_name}'"}
    inside, value = _evaluate_shape(manager, shape,
                                    float(x), float(y), float(z))
    return {'ok': True, 'shape': shape_name,
            'family': getattr(shape, 'family', ''),
            'point': [float(x), float(y), float(z)],
            'inside': bool(inside), 'value': round(value, 6)}


# --------------------------------------------------------------------------
# quadric classification
# --------------------------------------------------------------------------
def _numpy():
    try:
        import numpy
        return numpy
    except ImportError:
        return None


def quadric_classify(manager, shape_name):
    """The standard surface type of a quadric shape's Q."""
    shape = _named(manager, shape_name)
    if shape is None:
        return {'ok': False, 'error': f"no MathShapeDefinition named "
                f"'{shape_name}'"}
    if getattr(shape, 'family', '') != 'quadric':
        return {'ok': False, 'error': 'shape family is not quadric',
                'family': getattr(shape, 'family', '')}
    Q = _quadric_matrix(shape)
    if Q is None:
        return {'ok': False,
                'error': 'quadric_matrix_json must hold 16 numbers'}
    return classify_quadric_matrix(Q)


def classify_quadric_matrix(Q):
    """Classify a raw 4x4 Q (used by the API + selftest directly)."""
    if quadric_is_axis_aligned(Q):
        return {'ok': True, 'type': classify_axis_aligned(Q),
                'method': 'axis-aligned sign pattern (stdlib)'}
    np = _numpy()
    if np is None:
        return {'ok': False, 'method': 'diagonal-only',
                'error': 'Q has cross terms (rotated quadric); general '
                         'classification needs numpy eigenvalues, which '
                         'is not available in this backend. Provide an '
                         'axis-aligned Q or run on a numpy-capable node.',
                'capability': 'numpy-absent'}
    # general path: eigen-decompose the top-left 3x3 quadratic block,
    # rebuild an axis-aligned Q in principal axes, classify that.
    A = np.array([[Q[i][j] for j in range(3)] for i in range(3)],
                 dtype=float)
    evals, evecs = np.linalg.eigh(A)
    b = np.array([Q[0][3], Q[1][3], Q[2][3]], dtype=float)
    b_rot = evecs.T.dot(b)
    Qr = [[0.0] * 4 for _ in range(4)]
    for i in range(3):
        Qr[i][i] = float(evals[i])
        Qr[i][3] = Qr[3][i] = float(b_rot[i])
    Qr[3][3] = Q[3][3]
    inner = classify_axis_aligned(Qr)
    return {'ok': True, 'type': inner,
            'method': 'numpy eigenvalue decomposition (general Q)',
            'principalCurvatures': [round(float(v), 6) for v in evals]}


# --------------------------------------------------------------------------
# bounds (AABB) resolution
# --------------------------------------------------------------------------
def _shape_bounds(manager, shape, depth=0, seen=None):
    if depth > _MAX_DEPTH:
        return None
    family = getattr(shape, 'family', 'primitive')
    if family == 'primitive':
        _, _, bounds, _ = primitive_properties(
            getattr(shape, 'primitive_kind', ''), _params(shape))
        return bounds
    if family == 'quadric':
        explicit = _json(getattr(shape, 'bounds_json', ''), None)
        if isinstance(explicit, list) and len(explicit) == 3:
            return [[float(explicit[i][0]), float(explicit[i][1])]
                    for i in range(3)]
        ell = quadric_as_ellipsoid(_quadric_matrix(shape) or [])
        if ell:
            c, r = ell['center'], ell['radii']
            return [[c[i] - r[i], c[i] + r[i]] for i in range(3)]
        return None
    if family == 'csg':
        spec = _json(getattr(shape, 'csg_json', ''), {}) or {}
        seen = set(seen or ())
        seen.add(getattr(shape, 'name', ''))
        boxes = []
        for nm in (spec.get('shapes', []) or []):
            if nm in seen:
                continue
            child = _named(manager, nm)
            if child is None:
                continue
            cb = _shape_bounds(manager, child, depth + 1, seen)
            if cb:
                boxes.append(cb)
        if not boxes:
            return None
        # a difference/intersection is bounded by the base (first child)
        op = spec.get('op', 'union')
        if op in ('difference', 'intersection'):
            return boxes[0]
        return [[min(b[i][0] for b in boxes), max(b[i][1] for b in boxes)]
                for i in range(3)]
    return None


# --------------------------------------------------------------------------
# properties — analytic for primitives, grid-sampled for quadric/CSG
# --------------------------------------------------------------------------
def shape_properties(manager, shape_name, resolution=32):
    shape = _named(manager, shape_name)
    if shape is None:
        return {'ok': False, 'error': f"no MathShapeDefinition named "
                f"'{shape_name}'"}
    family = getattr(shape, 'family', 'primitive')
    if family == 'primitive':
        vol, area, bounds, centroid = primitive_properties(
            getattr(shape, 'primitive_kind', ''), _params(shape))
        return {'ok': True, 'shape': shape_name, 'family': family,
                'volumeCm3': round(vol, 4),
                'surfaceAreaCm2': round(area, 4),
                'boundingBox': [[round(v, 4) for v in ax] for ax in bounds],
                'centroid': [round(v, 4) for v in centroid],
                'method': 'analytic'}
    if family == 'spool':
        from mathshapes.custom.spool_geometry import spool_from_winding
        params = _params(shape)
        wref = _named(manager, params.get('winding_ref', ''))
        if wref is None:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': f'winding_ref '
                             f'"{params.get("winding_ref")}" not '
                             f'found'}
        spool = spool_from_winding(_params(wref), params)
        if not spool['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(spool['refusals'])}
        o = spool['object']
        fr = spool['derived']['flangeRadius']
        return {'ok': True, 'shape': shape_name, 'family': family,
                'derived': spool['derived'],
                'centroid': [round(v, 4) for v in o['C']],
                'boundingBox': [[round(o['C'][i] - fr, 4),
                                 round(o['C'][i] + fr, 4)]
                                for i in range(3)],
                'method': spool['note']}
    if family == 'gear':
        from mathshapes.custom.gear_geometry import gear_coherence
        params = _params(shape)

        def _resolve(ref, key):
            props = shape_properties(manager, ref)
            drv = props.get('derived') or {}
            v = drv.get(key)
            return v if isinstance(v, (int, float)) else None

        coherent = gear_coherence(params, resolve_ref=_resolve)
        if not coherent['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(coherent['refusals'])}
        from mathshapes.custom.gear_geometry import gear_volume
        o = coherent['object']
        ra = coherent['derived']['tipRadius']
        return {'ok': True, 'shape': shape_name, 'family': family,
                'volumeCm3': round(gear_volume(
                    o, flank_samples=int(
                        params.get('flank_samples') or 8)), 6),
                'derived': coherent['derived'],
                'centroid': [round(float(v), 4)
                             for v in o['center']],
                'boundingBox': [[round(o['center'][i] - ra, 4),
                                 round(o['center'][i] + ra, 4)]
                                for i in range(3)],
                'method': coherent['note'] + ' — volume is the '
                          'exact profile-polygon extrusion (units '
                          'follow the consuming part)'}
    if family == 'derived-cylinder':
        from mathshapes.custom.spool_geometry import derived_cylinder
        follower = derived_cylinder(manager, _params(shape),
                                    shape_properties)
        if not follower['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(follower['refusals'])}
        o = follower['object']
        vol = 3.141592653589793 * o['radius'] ** 2 * o['height']
        return {'ok': True, 'shape': shape_name, 'family': family,
                'volumeCm3': round(vol, 4),
                'derived': follower['derived'],
                'centroid': [round(float(v), 4)
                             for v in o['center']],
                'method': follower['note']}
    if family == 'winding':
        # ws-1: analytic from the math object — the wire's own
        # volume (length x cross-section), not the bobbin envelope.
        from mathshapes.custom.winding_geometry import winding_coherence
        coherent = winding_coherence(_params(shape))
        if not coherent['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(coherent['refusals'])}
        drv = coherent['derived']
        obj = coherent['object']
        outer = drv['outerRadius']
        c = obj['C']
        return {'ok': True, 'shape': shape_name, 'family': family,
                'volumeCm3': drv['wireVolume'],
                'wireLength': drv['wireLength'],
                'boundingBox': [[round(c[i] - outer, 4),
                                 round(c[i] + outer, 4)]
                                for i in range(3)],
                'centroid': [round(v, 4) for v in c],
                'derived': drv,
                'method': 'analytic winding (wire volume = length '
                          'x cross-section; units follow the '
                          'shape_units of the consuming part)'}
    bounds = _shape_bounds(manager, shape)
    if bounds is None:
        return {'ok': False,
                'error': 'quadric/CSG needs a bounding box to grid-sample; '
                         'set bounds_json ([[xmin,xmax],...]) on the '
                         'quadric or its base shape',
                'suggestion': {'knob': 'MathShapeDefinition.bounds_json',
                               'action': 'set an AABB enclosing the solid'}}
    return _grid_properties(manager, shape, bounds, resolution)


def _grid_properties(manager, shape, bounds, resolution):
    n = max(4, min(int(resolution), _MAX_RES))
    (x0, x1), (y0, y1), (z0, z1) = bounds
    dx, dy, dz = (x1 - x0) / n, (y1 - y0) / n, (z1 - z0) / n
    cell = dx * dy * dz
    inside_count = 0
    sx = sy = sz = 0.0
    # store inside flags to estimate a boundary-cell surface area
    grid = {}
    for i in range(n):
        cx = x0 + (i + 0.5) * dx
        for j in range(n):
            cy = y0 + (j + 0.5) * dy
            for k in range(n):
                cz = z0 + (k + 0.5) * dz
                inside, _ = _evaluate_shape(manager, shape, cx, cy, cz)
                if inside:
                    inside_count += 1
                    sx += cx
                    sy += cy
                    sz += cz
                    grid[(i, j, k)] = True
    volume = inside_count * cell
    if inside_count == 0:
        return {'ok': True, 'shape': getattr(shape, 'name', ''),
                'family': getattr(shape, 'family', ''), 'volumeCm3': 0.0,
                'surfaceAreaCm2': 0.0,
                'boundingBox': [[round(v, 4) for v in ax] for ax in bounds],
                'centroid': None,
                'method': f'grid-sample (N={n}); no interior cells found'}
    # boundary faces: a cell face exposed to a non-inside neighbour
    face_x, face_y, face_z = dy * dz, dx * dz, dx * dy
    area = 0.0
    for (i, j, k) in grid:
        for di, dj, dk, fa in ((1, 0, 0, face_x), (-1, 0, 0, face_x),
                               (0, 1, 0, face_y), (0, -1, 0, face_y),
                               (0, 0, 1, face_z), (0, 0, -1, face_z)):
            if (i + di, j + dj, k + dk) not in grid:
                area += fa
    return {'ok': True, 'shape': getattr(shape, 'name', ''),
            'family': getattr(shape, 'family', ''),
            'volumeCm3': round(volume, 4),
            'surfaceAreaCm2': round(area, 4),
            'boundingBox': [[round(v, 4) for v in ax] for ax in bounds],
            'centroid': [round(sx / inside_count, 4),
                         round(sy / inside_count, 4),
                         round(sz / inside_count, 4)],
            'method': f'grid-sample (N={n}); volume = inside-cells × cell '
                      f'volume, area = boundary faces (approx)'}


# --------------------------------------------------------------------------
# surface sampling — the clean-render fix
# --------------------------------------------------------------------------
def _box_mesh(params):
    from mathshapes.custom.shape_geometry import _center, _num
    c = _center(params)
    size = params.get('size', [1.0, 1.0, 1.0])
    hx, hy, hz = (float(size[0]) / 2, float(size[1]) / 2, float(size[2]) / 2)
    corners = [[c[0] + sx * hx, c[1] + sy * hy, c[2] + sz * hz]
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    # 12 triangles over the 8 corners (indices into `corners`)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 2, 6, 4),
             (1, 5, 7, 3), (0, 4, 5, 1), (2, 3, 7, 6)]
    tris = []
    for a, b, d, e in faces:
        tris.append([a, b, d])
        tris.append([a, d, e])
    return corners, tris


def sample_surface(manager, shape_name, n=24):
    """Surface points (+ triangles) shaped to feed a Mesh3DDefinition."""
    shape = _named(manager, shape_name)
    if shape is None:
        return {'ok': False, 'error': f"no MathShapeDefinition named "
                f"'{shape_name}'"}
    family = getattr(shape, 'family', 'primitive')
    n = max(6, min(int(n), 64))
    # ws-1: the wire winding — a swept tube along the matrix-equation
    # curve. Coherence refusals surface here verbatim: an incoherent
    # tuning cannot be drawn because it is not a math object.
    if family == 'winding':
        from mathshapes.custom.winding_geometry import (
            winding_coherence, winding_display_mesh,
        )
        params = _params(shape)
        coherent = winding_coherence(params)
        if not coherent['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(coherent['refusals'])}
        mesh = winding_display_mesh(coherent['object'], params)
        return {'ok': True, 'shape': shape_name, 'family': family,
                'points': mesh['points'],
                'triangles': mesh['triangles'],
                'count': len(mesh['points']),
                'method': mesh['method'],
                'renderMode': mesh.get('renderMode'),
                'textureHint': mesh.get('textureHint'),
                'derived': coherent['derived'],
                'latex': coherent['latex']}
    # ws-4: the coupled family — spool derives from its winding,
    # followers derive from what they follow. Refusals verbatim.
    if family == 'spool':
        from mathshapes.custom.spool_geometry import (
            spool_from_winding, spool_mesh,
        )
        params = _params(shape)
        wref = _named(manager, params.get('winding_ref', ''))
        if wref is None:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': f'winding_ref '
                             f'"{params.get("winding_ref")}" not '
                             f'found'}
        spool = spool_from_winding(_params(wref), params)
        if not spool['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(spool['refusals'])}
        pts, tris = spool_mesh(spool, n_lon=max(n, 24))
        return {'ok': True, 'shape': shape_name, 'family': family,
                'points': [[round(v, 4) for v in p] for p in pts],
                'triangles': tris, 'count': len(pts),
                'derived': spool['derived'],
                'method': 'parametric spool (barrel + flanges) — '
                          'every size derived live from '
                          + params.get('winding_ref', '')}
    if family == 'gear':
        from mathshapes.custom.gear_geometry import (
            gear_coherence, gear_mesh,
        )
        params = _params(shape)

        def _resolve(ref, key):
            props = shape_properties(manager, ref)
            drv = props.get('derived') or {}
            v = drv.get(key)
            return v if isinstance(v, (int, float)) else None

        coherent = gear_coherence(params, resolve_ref=_resolve)
        if not coherent['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(coherent['refusals'])}
        pts, tris = gear_mesh(
            coherent['object'],
            flank_samples=int(params.get('flank_samples')
                              or max(4, n // 4)))
        return {'ok': True, 'shape': shape_name, 'family': family,
                'points': [[round(v, 4) for v in p] for p in pts],
                'triangles': tris, 'count': len(pts),
                'derived': coherent['derived'],
                'latex': coherent['latex'],
                'method': 'parametric involute spur gear ('
                          + coherent['note'] + ')'}
    if family == 'derived-cylinder':
        # NOTE: axial_mesh is the MODULE-LEVEL import — a local
        # re-import here shadowed it for the whole function and
        # crashed every cylinder/cone/frustum sample below
        # (UnboundLocalError, caught by the mq-1 parity work).
        from mathshapes.custom.spool_geometry import derived_cylinder
        follower = derived_cylinder(manager, _params(shape),
                                    shape_properties)
        if not follower['ok']:
            return {'ok': False, 'shape': shape_name,
                    'family': family,
                    'error': '; '.join(follower['refusals'])}
        o = follower['object']
        pts, tris = axial_mesh(
            'cylinder',
            {'radius': o['radius'], 'height': o['height'],
             'axis': o['axis'], 'center': o['center'],
             'cap_base': True, 'cap_top': True},
            n_lon=n, cap_base=True, cap_top=True)
        return {'ok': True, 'shape': shape_name, 'family': family,
                'points': [[round(v, 4) for v in p] for p in pts],
                'triangles': tris, 'count': len(pts),
                'derived': follower['derived'],
                'method': follower['note']}
    if family == 'primitive':
        kind = getattr(shape, 'primitive_kind', '')
        params = _params(shape)
        if kind == 'box':
            pts, tris = _box_mesh(params)
        elif kind == 'sphere':
            from mathshapes.custom.shape_geometry import _center, _num
            r = _num(params, 'radius', 1.0)
            pts, tris = ellipsoid_mesh(_center(params), [r, r, r],
                                       n_lat=n // 2 or 8, n_lon=n)
        elif kind == 'ellipsoid':
            from mathshapes.custom.shape_geometry import _center
            radii = params.get('radii', [1.0, 1.0, 1.0])
            pts, tris = ellipsoid_mesh(
                _center(params),
                [float(radii[0]), float(radii[1]), float(radii[2])],
                n_lat=n // 2 or 8, n_lon=n)
        elif kind == 'hollow_frustum':
            pts, tris = hollow_frustum_shell_mesh(
                params, n_lon=n, n_stack=max(6, n // 2))
        elif kind == 'annular_sector':
            from mathshapes.custom.shape_geometry import (
                _center as _ctr, annular_sector_mesh,
            )
            pts, tris = annular_sector_mesh(
                params, _ctr(params), params.get('axis', 'z'),
                n_arc=n)
        elif kind == 'arc_faced_bar':
            from mathshapes.custom.shape_geometry import (
                _center as _ctr2, arc_faced_bar_mesh,
            )
            pts, tris = arc_faced_bar_mesh(
                params, _ctr2(params), params.get('axis', 'z'),
                n_arc=n)
        else:                                 # cylinder / cone / frustum
            pts, tris = axial_mesh(
                kind, params, n_lon=n,
                cap_base=bool(params.get('cap_base', False)),
                cap_top=bool(params.get('cap_top', False)),
                inward=bool(params.get('inward', False)))
        return {'ok': True, 'shape': shape_name, 'family': family,
                'points': [[round(v, 4) for v in p] for p in pts],
                'triangles': tris, 'count': len(pts),
                'method': f'parametric {kind} mesh'}
    if family == 'quadric':
        ell = quadric_as_ellipsoid(_quadric_matrix(shape) or [])
        if ell:
            pts, tris = ellipsoid_mesh(ell['center'], ell['radii'],
                                       n_lat=n // 2 or 8, n_lon=n)
            return {'ok': True, 'shape': shape_name, 'family': family,
                    'points': [[round(v, 4) for v in p] for p in pts],
                    'triangles': tris, 'count': len(pts),
                    'method': 'parametric ellipsoid from quadric Q'}
    # CSG special case: a difference of two COAXIAL cylinders is an
    # annular tube with an exact parametric mesh — no marching needed.
    if family == 'csg':
        tube = _csg_tube_params(manager, shape)
        if tube is not None:
            pts, tris = tube_mesh(**tube, n_lon=max(n, 24))
            return {'ok': True, 'shape': shape_name, 'family': family,
                    'points': [[round(v, 4) for v in p] for p in pts],
                    'triangles': tris, 'count': len(pts),
                    'method': 'parametric tube (difference of coaxial '
                              'cylinders)'}
    # quadric (general) + CSG: march the grid, triangulate voxel faces
    bounds = _shape_bounds(manager, shape)
    if bounds is None:
        return {'ok': False,
                'error': 'need bounds_json to march a general quadric/CSG '
                         'surface'}
    return _march_voxel_mesh(manager, shape, bounds, n)


def _csg_tube_params(manager, shape):
    """If this CSG row is `difference` of exactly two coaxial cylinder
    primitives (same axis, same center in the perpendicular plane,
    bore radius < outer radius, bore at least as tall as the outer),
    return tube_mesh kwargs; else None (the marching fallback runs)."""
    from mathshapes.custom.shape_geometry import _axis_index, _center, _num
    blob = _json(getattr(shape, 'csg_json', ''), {})
    if (blob.get('op') != 'difference'
            or len(blob.get('shapes') or []) != 2):
        return None
    outer, bore = (_named(manager, s) for s in blob['shapes'])
    for part in (outer, bore):
        if (part is None
                or getattr(part, 'family', '') != 'primitive'
                or getattr(part, 'primitive_kind', '') != 'cylinder'):
            return None
    po, pb = _params(outer), _params(bore)
    axis = po.get('axis', 'z')
    if pb.get('axis', 'z') != axis:
        return None
    ai = _axis_index(axis)
    co, cb = _center(po), _center(pb)
    perp = [d for d in range(3) if d != ai]
    if any(abs(co[d] - cb[d]) > 1e-9 for d in perp + [ai]):
        return None                      # off-axis or axially shifted
    r_outer = _num(po, 'radius', 1.0)
    r_inner = _num(pb, 'radius', 1.0)
    if not (0 < r_inner < r_outer):
        return None
    h_outer = _num(po, 'height', 1.0)
    if _num(pb, 'height', 1.0) < h_outer - 1e-9:
        return None                      # bore doesn't pierce through
    return {'center': co, 'axis': axis, 'r_outer': r_outer,
            'r_inner': r_inner, 'height': h_outer}


def _march_voxel_mesh(manager, shape, bounds, n):
    """Marching-grid mesh for general quadric/CSG shapes: every
    boundary face between an inside cell and an outside neighbor
    becomes a quad (2 triangles) on the cell lattice. Blocky — exact
    only in the N→∞ limit, and the method string says so — but a
    closed, orientable, RENDERABLE surface (mag-7: the old point
    cloud drew nothing in the 3D viewer)."""
    (x0, x1), (y0, y1), (z0, z1) = bounds
    dx, dy, dz = (x1 - x0) / n, (y1 - y0) / n, (z1 - z0) / n
    inside_flags = set()
    for i in range(n):
        cx = x0 + (i + 0.5) * dx
        for j in range(n):
            cy = y0 + (j + 0.5) * dy
            for k in range(n):
                cz = z0 + (k + 0.5) * dz
                inside, _ = _evaluate_shape(manager, shape, cx, cy, cz)
                if inside:
                    inside_flags.add((i, j, k))
    # Corner-lattice vertices, deduplicated across faces.
    vert_index = {}
    pts, tris = [], []

    def vert(i, j, k):
        key = (i, j, k)
        if key not in vert_index:
            vert_index[key] = len(pts)
            pts.append([round(x0 + i * dx, 4), round(y0 + j * dy, 4),
                        round(z0 + k * dz, 4)])
        return vert_index[key]

    # For each axis direction: the face's 4 corners, ordered so the
    # outward normal points toward the OUTSIDE neighbor.
    face_corners = {
        (1, 0, 0): ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
        (-1, 0, 0): ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
        (0, 1, 0): ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
        (0, -1, 0): ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
        (0, 0, 1): ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
        (0, 0, -1): ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
    }
    for (i, j, k) in inside_flags:
        for (di, dj, dk), corners in face_corners.items():
            if (i + di, j + dj, k + dk) in inside_flags:
                continue
            a, b, c, d = (vert(i + ci, j + cj, k + ck)
                          for ci, cj, ck in corners)
            tris.append([a, b, c])
            tris.append([a, c, d])
    return {'ok': True, 'shape': getattr(shape, 'name', ''),
            'family': getattr(shape, 'family', ''),
            'points': pts, 'triangles': tris, 'count': len(pts),
            'method': f'voxel-face mesh from marching grid (N={n}); '
                      f'blocky — exact only as N grows'}
