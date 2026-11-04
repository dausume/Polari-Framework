"""
@module mathshapes.custom.shape_anchor

ms-anchor (MECH_FREECAD_INTERCHANGE_PLAN §8.5; Dustin 2026-11-03:
"that should be its own unique tool inside math shapes"): the
ANCHORED OFFSET tool. Not a sub-feature of the FreeCAD bridge or of
the mech catalogue — those are its consumers (a thread on a screw, a
magnet pocket in a bin).

Four steps, each a function here, each honest about its method:

  pick_anchor      a ray r(s) = o + s·d MARCHED along the shape's
                   implicit field F (shape_equations.field_spec — the
                   same exact quadric field the no-code rows carry)
                   to the first sign change, then BISECTED to 1e-12.
                   The march step is finite: a feature thinner than
                   one step can be skipped (reported as `step`). The
                   normal is n = ∇F/|∇F| from the exact 2Qp of the
                   active surface (gradient_value); central finite
                   differences are the fallback where that gradient
                   vanishes (an apex) and the anchor then says
                   basis='sampled'.
  anchor_frame     the FOUR-WAY reference toggle -> the frame (a, b,
                   c) and its world->local 4x4. See the ASSUMPTION in
                   ShapeAnchor's docstring: 'tangent_toward' is the
                   viewer direction projected onto the tangent plane.
  offset_field     the offset SOLID G < 0 in that frame — planar
                   square / disk (exact degenerate quadrics), conform
                   (F(p − t·n(p)), exact on a sphere or a plane-like
                   reference, first-order `approx` elsewhere), or a
                   custom expression (the thread) — plus the
                   composition with the parent by the CSG algebra
                   (add→min, subtract→max(F, −G), intersect→max).
  offset_equation_rows / result_shape_rows
                   the no-code form: a `<offset>--frame` matrix, a
                   `<offset>--local` row q = M p, a `<offset>--G` row
                   in q, and `<offset>--field` composed with the
                   parent's `<shape>--field` — evaluable by the real
                   matrix executor; and, for the planar modes with a
                   constant t, ordinary MathShapeDefinition rows
                   (world-frame quadrics + csg) so the result rides
                   the existing shape_properties / render path.

NAMED ABSENCE: `conform` has no row form yet — it needs the executor
to evaluate a referenced equation at a TRANSLATED point (rebind p),
which the 'expr' kind cannot do; offset_equation_rows refuses by
name and the python leg still evaluates it.

Units follow the shape (cm). Duck-typed manager, stdlib only (the
selftest runs without numpy; the executor parity check needs it).

@consumers mathshapes.shape_api (/api/shapes/anchor, /api/shapes/offset),
mathshapes.shape_anchor_selftest, mech catalogue + FreeCAD export (8.1)
"""

import json
import math
import re

from mathshapes.custom.shape_analysis import _shape_bounds
from mathshapes.custom.shape_analysis import _named as _shape_named
from mathshapes.custom.shape_equations import (
    _eval_spec, _eval_spec_grad, eval_field_expr, executor_operand,
    field_spec, finite_difference_gradient, gradient_rows,
    resolve_field_operand, rewrite_field_functions,
)
from mathshapes.custom.shape_geometry import plane_quadric_matrix
from mathshapes.objects.shape._shared import (
    OFFSET_MODES, OFFSET_OPS, REFERENCE_MODES,
)

PROV = 'ms-anchor'

#: bisection stops when |F| < this or the bracket is narrower.
_BISECT_TOL = 1e-12
_BISECT_MAX = 200
#: default march step as a fraction of the shape's bounding diagonal.
_STEP_FRACTION = 1.0 / 256.0


# ------------------------------------------------------------------
# small vector helpers (3-lists; no numpy)
# ------------------------------------------------------------------
def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    n = _norm(a)
    return [v / n for v in a] if n > 0 else [0.0, 0.0, 0.0]


def _scale(a, k):
    return [v * k for v in a]


def _add(a, b):
    return [a[i] + b[i] for i in range(3)]


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _vec(v, default):
    try:
        out = [float(c) for c in v]
        return out if len(out) == 3 else list(default)
    except (TypeError, ValueError):
        return list(default)


def _json_attr(row, attr, default):
    raw = getattr(row, attr, '') if not isinstance(row, dict) \
        else row.get(attr, '')
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw) if raw else default
    except (TypeError, ValueError):
        return default


def _attr(row, name, default=''):
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def anchor_named(manager, name):
    for r in _rows(manager, 'ShapeAnchor'):
        if getattr(r, 'name', '') == name:
            return r
    return None


def offset_named(manager, name):
    for r in _rows(manager, 'AnchoredOffset'):
        if getattr(r, 'name', '') == name:
            return r
    return None


# ------------------------------------------------------------------
# step 1 — pick the anchor by a ray
# ------------------------------------------------------------------
def _field_of(manager, shape_name):
    spec = field_spec(manager, shape_name)
    if not spec.get('ok'):
        return None, spec
    return (lambda x, y, z: _eval_spec(spec, x, y, z)), spec


def pick_anchor(manager, shape_name, ray_origin, ray_dir,
                max_dist=None, step=None):
    """March F along o + s·d to its first sign change, bisect, and
    read the normal there. Refuses when the shape has no field, the
    direction is zero, or the ray misses within max_dist."""
    F, spec = _field_of(manager, shape_name)
    if F is None:
        return {'ok': False,
                'refusal': f'anchor needs an implicit field: '
                           f'{spec.get("refusal")}'}
    o = _vec(ray_origin, [0.0, 0.0, 0.0])
    d = _vec(ray_dir, [0.0, 0.0, 0.0])
    if _norm(d) < 1e-15:
        return {'ok': False, 'refusal': 'ray direction is zero'}
    d = _unit(d)
    shape = _shape_named(manager, shape_name)
    bounds = _shape_bounds(manager, shape) if shape is not None else None
    if bounds:
        lo = [b[0] for b in bounds]
        hi = [b[1] for b in bounds]
        diag = _norm(_sub(hi, lo)) or 1.0
        centre = _scale(_add(lo, hi), 0.5)
        if max_dist is None:
            max_dist = _norm(_sub(centre, o)) + 1.5 * diag
        if step is None:
            step = diag * _STEP_FRACTION
    else:
        max_dist = 100.0 if max_dist is None else float(max_dist)
        step = 0.05 if step is None else float(step)
    step = float(step)
    max_dist = float(max_dist)

    def at(s):
        return _add(o, _scale(d, s))

    s0, f0 = 0.0, F(*o)
    started_inside = f0 < 0.0
    hit_s = None
    if f0 == 0.0:
        hit_s = 0.0
    else:
        s = 0.0
        while s < max_dist:
            s1 = min(s + step, max_dist)
            f1 = F(*at(s1))
            if f1 == 0.0:
                hit_s = s1
                break
            if (f1 < 0.0) != (f0 < 0.0):
                lo_s, hi_s, lo_f = s, s1, f0
                for _ in range(_BISECT_MAX):
                    mid = 0.5 * (lo_s + hi_s)
                    fm = F(*at(mid))
                    if abs(fm) < _BISECT_TOL or (hi_s - lo_s) < _BISECT_TOL:
                        break
                    if (fm < 0.0) == (lo_f < 0.0):
                        lo_s, lo_f = mid, fm
                    else:
                        hi_s = mid
                hit_s = 0.5 * (lo_s + hi_s)
                break
            s, f0 = s1, f1
            if s1 >= max_dist:
                break
    if hit_s is None:
        return {'ok': False,
                'refusal': f'ray from {o} along {d} misses '
                           f'"{shape_name}" within {max_dist:.4g} '
                           f'(march step {step:.4g})',
                'step': step, 'maxDist': max_dist}
    p0 = at(hit_s)
    _, g = _eval_spec_grad(spec, *p0)
    basis, method = 'exact', ('normal = 2Qp of the active surface, '
                              'normalised (exact)')
    if _norm(g) < 1e-9:
        g = finite_difference_gradient(F, *p0)
        basis, method = 'sampled', ('normal by central finite '
                                    'differences (h=1e-5) — the exact '
                                    'gradient vanishes here (apex / '
                                    'degenerate point)')
        if _norm(g) < 1e-9:
            return {'ok': False,
                    'refusal': f'no normal at {p0}: both the exact '
                               f'and the finite-difference gradient '
                               f'vanish (a degenerate point of '
                               f'"{shape_name}")'}
    n = _unit(g)
    t1, t2, degenerate = _tangent_basis(n, d)
    return {
        'ok': True, 'shape': shape_name,
        'rayOrigin': o, 'rayDir': d, 'rayParam': hit_s,
        'hit': p0, 'normal': n,
        'normalEqRef': f'{shape_name}--grad',
        'tangentToward': t1, 'tangent2': t2,
        'tangentDegenerate': degenerate,
        'startedInside': started_inside,
        'basis': basis, 'step': step,
        'method': f'ray march (step {step:.4g}, a feature thinner '
                  f'than one step can be skipped) + bisection to '
                  f'|F| < {_BISECT_TOL:g}; {method}',
    }


def _tangent_basis(n, d):
    """t₁ = normalise(−d − (−d·n)n) — the in-plane direction leaning
    at the viewer (the ASSUMPTION recorded on ShapeAnchor); t₂ = n ×
    t₁. When d is along n there is no 'most toward' tangent: an
    arbitrary perpendicular is chosen and flagged."""
    minus_d = _scale(d, -1.0)
    proj = _sub(minus_d, _scale(n, _dot(minus_d, n)))
    if _norm(proj) < 1e-9:
        helper = [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]
        proj = _sub(helper, _scale(n, _dot(helper, n)))
        degenerate = True
    else:
        degenerate = False
    t1 = _unit(proj)
    t2 = _unit(_cross(n, t1))
    return t1, t2, degenerate


# ------------------------------------------------------------------
# step 2 — the reference toggle -> the frame
# ------------------------------------------------------------------
def anchor_frame(anchor, mode=None):
    """The frame (a, b, c) + origin p₀ + world->local 4x4 for one of
    the four reference modes (default: the anchor's own). `anchor` is
    a ShapeAnchor row or a pick_anchor result."""
    mode = mode or _attr(anchor, 'reference', 'toward') or 'toward'
    if mode not in REFERENCE_MODES:
        return {'ok': False,
                'refusal': f'reference "{mode}" is not one of '
                           f'{list(REFERENCE_MODES)}'}
    if isinstance(anchor, dict) and 'hit' in anchor:
        p0, n, d = anchor['hit'], anchor['normal'], anchor['rayDir']
    else:
        p0 = _json_attr(anchor, 'hit_json', None)
        n = _json_attr(anchor, 'normal_json', None)
        d = _json_attr(anchor, 'ray_dir_json', None)
        if not (p0 and n and d):
            return {'ok': False,
                    'refusal': 'anchor is undetermined — hit_json / '
                               'normal_json / ray_dir_json are empty; '
                               'pick it first'}
    p0, n, d = _vec(p0, [0, 0, 0]), _unit(_vec(n, [0, 0, 1])), \
        _unit(_vec(d, [0, 0, -1]))
    # the face LOOKING AT the viewer: n flipped so that n·d < 0.
    n_toward = n if _dot(n, d) <= 0.0 else _scale(n, -1.0)
    t1, t2, degenerate = _tangent_basis(n, d)
    if mode == 'toward':
        a = n_toward
    elif mode == 'away':
        a = _scale(n_toward, -1.0)
    elif mode == 'tangent_toward':
        a = t1
    else:
        a = _scale(t1, -1.0)
    b = _cross(n, a)
    note = ''
    if _norm(b) < 1e-9:                     # a is along n
        b = t1
        if degenerate:
            note = ('ray is along the normal: no "most toward" '
                    'tangent exists; b is an arbitrary in-plane '
                    'direction')
    b = _unit(b)
    c = _unit(_cross(a, b))
    # q = M p = [u, v, w, 1]: w ALONG the reference axis a, (u, v)
    # along (b, c). §8.5 writes (u, v, w) = (·a, ·b, ·c) in one line
    # and then uses w as the distance along the reference everywhere
    # (the offset plane w − t = 0, the thread along w) — the usage is
    # what the examples need, so it is what is implemented; a
    # deviation recorded for Dustin.
    M = [b[0], b[1], b[2], -_dot(b, p0),
         c[0], c[1], c[2], -_dot(c, p0),
         a[0], a[1], a[2], -_dot(a, p0),
         0.0, 0.0, 0.0, 1.0]
    return {'ok': True, 'mode': mode, 'a': a, 'b': b, 'c': c,
            'origin': p0, 'normal': n, 'viewer': d,
            'tangentToward': t1, 'matrix': M, 'note': note,
            'assumption': 'tangent_toward = the viewer direction '
                          'projected onto the tangent plane (−d minus '
                          'its normal part), tangent_away its '
                          'negative — awaiting confirmation'}


def local_coords(frame, x, y, z):
    """(u, v, w) = ((p − p₀)·b, ·c, ·a) — w along the reference."""
    r = [x - frame['origin'][0], y - frame['origin'][1],
         z - frame['origin'][2]]
    return _dot(r, frame['b']), _dot(r, frame['c']), _dot(r, frame['a'])


def world_coords(frame, u, v, w):
    p = list(frame['origin'])
    for k, e in ((u, frame['b']), (v, frame['c']), (w, frame['a'])):
        p = _add(p, _scale(e, k))
    return p


# ------------------------------------------------------------------
# step 3 + 4 — the offset solid in the frame, varying with position
# ------------------------------------------------------------------
_SYM = {'u': 'q[0]', 'v': 'q[1]', 'w': 'q[2]'}


def _in_q(expr):
    """u/v/w -> q[0]/q[1]/q[2] for the row form (whole words only,
    not attributes, not parts of longer names)."""
    return re.sub(r'(?<![A-Za-z0-9_.])([uvw])(?![A-Za-z0-9_])',
                  lambda m: _SYM[m.group(1)], expr)


def _knobs(offset):
    raw = _json_attr(offset, 'parameters_json', {}) or {}
    out = {}
    for k, v in raw.items():
        try:
            out[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return out


def _extent_clips(extent):
    """Half-space clips from {"u":[lo,hi],...} as (axis, lo, hi)."""
    clips = []
    for ax in ('u', 'v', 'w'):
        rng = extent.get(ax)
        if isinstance(rng, (list, tuple)) and len(rng) == 2:
            clips.append((ax, float(rng[0]), float(rng[1])))
    return clips


def _custom_source(manager, offset):
    """(expr, operands) of a custom offset: the referenced
    MatrixEquationDefinition's operation/operands, else the inline
    surface_eq_json."""
    ref = _attr(offset, 'surface_eq_ref', '')
    if ref:
        for r in _rows(manager, 'MatrixEquationDefinition'):
            if getattr(r, 'name', '') == ref:
                op = _json_attr(r, 'operation_json', {}) or {}
                return (op.get('expr', ''),
                        _json_attr(r, 'operands_json', {}) or {})
        return None, {'refusal': f'surface_eq_ref "{ref}" names no '
                                 f'MatrixEquationDefinition'}
    inline = _json_attr(offset, 'surface_eq_json', {}) or {}
    return inline.get('expr', ''), inline.get('operands', {}) or {}


def _is_sphere(spec):
    if 'surfaces' not in spec or len(spec['surfaces']) != 1:
        return False
    Q = spec['surfaces'][0][1]
    diag = [Q[0][0], Q[1][1], Q[2][2]]
    off = [Q[0][1], Q[0][2], Q[1][2]]
    return (all(abs(v) < 1e-12 for v in off) and diag[0] > 0
            and all(abs(diag[i] - diag[0]) < 1e-12 for i in (1, 2)))


def _active_is_plane(spec, p):
    """True when the surface that wins at p has no quadratic part —
    the reference is plane-like and F(p − t·a) is exact."""
    if 'surfaces' in spec:
        best = max(spec['surfaces'],
                   key=lambda s: _eval_spec({'surfaces': [s]}, *p))
        Q = best[1]
        return all(abs(Q[i][j]) < 1e-12 for i in range(3)
                   for j in range(3))
    # csg: descend into the active child
    vals = [(_eval_spec(c, *p), c) for c in spec['children']]
    if spec['op'] == 'union':
        child = min(vals, key=lambda v: v[0])[1]
    elif spec['op'] == 'intersection':
        child = max(vals, key=lambda v: v[0])[1]
    else:
        cands = [vals[0]] + [(-v, c) for v, c in vals[1:]]
        child = max(cands, key=lambda v: v[0])[1]
    return _active_is_plane(child, p)


def offset_field(manager, offset):
    """Build the callable fields of an AnchoredOffset (row or name):
    G (world), G_local, the parent F, and `composed` by the op.
    Reports approxReason ('' when exact) and, for the planar modes
    with a constant t, the world-frame quadrics of the solid."""
    if isinstance(offset, str):
        row = offset_named(manager, offset)
        if row is None:
            return {'ok': False,
                    'refusal': f'no AnchoredOffset named "{offset}"'}
        offset = row
    name = _attr(offset, 'name', '')
    mode = _attr(offset, 'mode', 'planar_square') or 'planar_square'
    op = _attr(offset, 'op', 'add') or 'add'
    if mode not in OFFSET_MODES:
        return {'ok': False, 'refusal': f'mode "{mode}" is not one of '
                                        f'{list(OFFSET_MODES)}'}
    if op not in OFFSET_OPS:
        return {'ok': False, 'refusal': f'op "{op}" is not one of '
                                        f'{list(OFFSET_OPS)}'}
    anchor = anchor_named(manager, _attr(offset, 'anchor_ref', ''))
    if anchor is None:
        return {'ok': False,
                'refusal': f'offset "{name}" references no ShapeAnchor '
                           f'("{_attr(offset, "anchor_ref", "")}")'}
    shape_name = getattr(anchor, 'shape_ref', '')
    F, spec = _field_of(manager, shape_name)
    if F is None:
        return {'ok': False, 'refusal': spec.get('refusal')}
    frame = anchor_frame(anchor)
    if not frame.get('ok'):
        return frame
    knobs = _knobs(offset)
    try:
        t = float(_attr(offset, 't', 0.0) or 0.0)
    except (TypeError, ValueError):
        t = 0.0
    extent = _json_attr(offset, 'extent_json', {}) or {}
    clips = _extent_clips(extent)
    offset_eq = (_attr(offset, 'offset_eq', '') or '').strip()
    t_expr = rewrite_field_functions(offset_eq) if offset_eq else ''

    def t_at(u, v, w):
        if not t_expr:
            return t
        return eval_field_expr(t_expr, dict(knobs, u=u, v=v, w=w, t=t))

    def clipped(g, u, v, w):
        for ax, lo, hi in clips:
            val = {'u': u, 'v': v, 'w': w}[ax]
            g = max(g, lo - val, val - hi)
        return g

    approx = ''
    surfaces = None
    sign = -1.0 if t < 0.0 else 1.0

    def slab(u, v, w):
        # 0 <= sign·w <= |t(u,v,w)|: between the anchor plane and the
        # offset plane, on the side the sign of t names.
        return max(-sign * w, sign * w - abs(t_at(u, v, w)))

    if mode in ('planar_square', 'planar_disk'):
        if mode == 'planar_square':
            side = float(extent.get('side', 1.0))
            half = side / 2.0

            def G_local(u, v, w, _p=None):
                return clipped(max(slab(u, v, w), abs(u) - half,
                                   abs(v) - half), u, v, w)
        else:
            R = float(extent.get('radius', 0.5))

            def G_local(u, v, w, _p=None):
                return clipped(max(slab(u, v, w), u * u + v * v - R * R),
                               u, v, w)
        if not t_expr:
            surfaces = _planar_surfaces(frame, mode, t, extent)
    elif mode == 'conform':
        a = frame['a']
        plane_like = _active_is_plane(spec, frame['origin'])
        sphere = _is_sphere(spec)
        if not (plane_like or sphere):
            approx = (f'conform is the first-order offset F(p − t·n(p)); '
                      f'it is exact only where F is a distance field '
                      f'(a sphere, or a plane-like reference) — '
                      f'"{shape_name}" is neither (8.3 item 6)')

        def G_local(u, v, w, p=None):
            p = p or world_coords(frame, u, v, w)
            tt = t_at(u, v, w)
            if plane_like:
                q = _sub(p, _scale(a, tt))
            else:
                _, g = _eval_spec_grad(spec, *p)
                if _norm(g) < 1e-12:
                    g = finite_difference_gradient(F, *p)
                nn = _unit(g) if _norm(g) > 0 else a
                q = _sub(p, _scale(nn, tt))
            return clipped(F(*q), u, v, w)
    else:                                    # custom
        expr, operands = _custom_source(manager, offset)
        if expr is None:
            return {'ok': False, 'refusal': operands['refusal']}
        if not expr:
            return {'ok': False,
                    'refusal': f'custom offset "{name}" has no '
                               f'expression (surface_eq_ref / '
                               f'surface_eq_json.expr)'}
        g_expr = rewrite_field_functions(expr)
        static, dynamic = {}, {}
        for sym, sp in operands.items():
            if isinstance(sp, (int, float)):
                static[sym] = float(sp)
            elif isinstance(sp, dict) and sp.get('kind') == 'scalar':
                static[sym] = float(sp.get('value', 0.0))
            elif isinstance(sp, str) and sp in knobs:
                static[sym] = knobs[sp]
            elif isinstance(sp, str) and sp in ('p', 'q'):
                dynamic[sym] = sp
            else:
                dynamic[sym] = sp

        def G_local(u, v, w, p=None):
            p = p or world_coords(frame, u, v, w)
            env = dict(knobs)
            env.update(static)
            env.update(u=u, v=v, w=w, t=t_at(u, v, w))
            for sym, sp in dynamic.items():
                if sp == 'p':
                    env[sym] = [p[0], p[1], p[2], 1.0]
                elif sp == 'q':
                    env[sym] = [u, v, w, 1.0]
                else:
                    env[sym] = resolve_field_operand(manager, sp, *p)
            return clipped(eval_field_expr(g_expr, env), u, v, w)

    def G(x, y, z):
        u, v, w = local_coords(frame, x, y, z)
        return G_local(u, v, w, [x, y, z])

    def composed(x, y, z):
        f, g = F(x, y, z), G(x, y, z)
        if op == 'add':
            return min(f, g)
        if op == 'subtract':
            return max(f, -g)
        return max(f, g)

    return {'ok': True, 'offset': name, 'anchor': getattr(anchor, 'name', ''),
            'shape': shape_name, 'mode': mode, 'op': op, 'frame': frame,
            't': t, 'offsetEq': offset_eq, 'knobs': knobs,
            'extent': extent, 'F': F, 'G': G, 'G_local': G_local,
            'composed': composed, 'approxReason': approx,
            'exact': approx == '', 'surfaces': surfaces,
            'bounds': _offset_bounds(manager, shape_name, frame, mode,
                                     t, extent)}


def _planar_surfaces(frame, mode, t, extent):
    """World-frame quadrics (label, Q) whose max is the planar solid:
    two slab planes + 4 side planes (square) or a cylinder about a
    (disk). Outward normals; inside < 0."""
    p0, a, b, c = frame['origin'], frame['a'], frame['b'], frame['c']
    lo, hi = min(0.0, t), max(0.0, t)
    out = [('slab-base', plane_quadric_matrix(_scale(a, -1.0),
                                              _add(p0, _scale(a, lo)))),
           ('slab-top', plane_quadric_matrix(a, _add(p0, _scale(a, hi))))]
    if mode == 'planar_square':
        half = float(extent.get('side', 1.0)) / 2.0
        for tag, e in (('b', b), ('c', c)):
            out.append((f'side+{tag}', plane_quadric_matrix(
                e, _add(p0, _scale(e, half)))))
            out.append((f'side-{tag}', plane_quadric_matrix(
                _scale(e, -1.0), _add(p0, _scale(e, -half)))))
    else:
        R = float(extent.get('radius', 0.5))
        out.append(('lateral', _cylinder_quadric(p0, a, R)))
    return out


def _cylinder_quadric(origin, axis, radius):
    """(p−p₀)ᵀ(I − aaᵀ)(p−p₀) − R² as a 4x4 — a cylinder of radius R
    about the line p₀ + s·a, any direction."""
    a = _unit(axis)
    P = [[(1.0 if i == j else 0.0) - a[i] * a[j] for j in range(3)]
         for i in range(3)]
    Q = [[0.0] * 4 for _ in range(4)]
    Pp0 = [sum(P[i][j] * origin[j] for j in range(3)) for i in range(3)]
    for i in range(3):
        for j in range(3):
            Q[i][j] = P[i][j]
        Q[i][3] = Q[3][i] = -Pp0[i]
    Q[3][3] = _dot(origin, Pp0) - radius * radius
    return Q


def _offset_bounds(manager, shape_name, frame, mode, t, extent):
    """Parent bounds grown to hold the offset solid (for sampling)."""
    shape = _shape_named(manager, shape_name)
    base = _shape_bounds(manager, shape) if shape is not None else None
    corners = []
    if mode in ('planar_square', 'planar_disk'):
        half = (float(extent.get('side', 1.0)) / 2.0
                if mode == 'planar_square'
                else float(extent.get('radius', 0.5)))
        us = vs = (-half, half)
        ws = (min(0.0, t), max(0.0, t))
    else:
        us = tuple(extent.get('u', (-abs(t), abs(t)))) or (-abs(t), abs(t))
        vs = tuple(extent.get('v', (-abs(t), abs(t)))) or (-abs(t), abs(t))
        ws = tuple(extent.get('w', (-abs(t), abs(t)))) or (-abs(t), abs(t))
    for u in us:
        for v in vs:
            for w in ws:
                corners.append(world_coords(frame, u, v, w))
    box = [[min(c[i] for c in corners), max(c[i] for c in corners)]
           for i in range(3)]
    if base:
        if mode in ('conform', 'custom'):
            pad = abs(t)
            base = [[b[0] - pad, b[1] + pad] for b in base]
        return [[min(base[i][0], box[i][0]), max(base[i][1], box[i][1])]
                for i in range(3)]
    return box


def evaluate_offset(manager, offset_name, x, y, z):
    """G, F and the composed field at one world point, with the
    local (u, v, w) so the person sees the frame they typed in."""
    built = offset_field(manager, offset_name)
    if not built.get('ok'):
        return built
    x, y, z = float(x), float(y), float(z)
    u, v, w = local_coords(built['frame'], x, y, z)
    try:
        g, f, r = built['G'](x, y, z), built['F'](x, y, z), \
            built['composed'](x, y, z)
    except (ValueError, NameError, TypeError, ZeroDivisionError,
            SyntaxError) as exc:
        return {'ok': False, 'offset': offset_name,
                'refusal': f'the offset expression does not evaluate: '
                           f'{type(exc).__name__}: {exc}'}
    return {'ok': True, 'offset': offset_name, 'point': [x, y, z],
            'local': [u, v, w], 'G': g, 'F': f, 'result': r,
            'insideOffset': g < 0.0, 'insideParent': f < 0.0,
            'insideResult': r < 0.0, 'op': built['op'],
            'mode': built['mode'], 'approxReason': built['approxReason']}


def sample_offset(manager, offset_name, resolution=24, bounds=None):
    """Grid-count volumes of parent / offset solid / result over the
    offset's bounds — the same method shape_properties uses for CSG,
    said as such (volume = inside cells × cell volume)."""
    built = offset_field(manager, offset_name)
    if not built.get('ok'):
        return built
    bounds = bounds or built['bounds']
    n = max(4, min(int(resolution), 80))
    (x0, x1), (y0, y1), (z0, z1) = bounds
    dx, dy, dz = (x1 - x0) / n, (y1 - y0) / n, (z1 - z0) / n
    cell = dx * dy * dz
    F, G = built['F'], built['G']
    probe = evaluate_offset(manager, offset_name, *[
        0.5 * (b[0] + b[1]) for b in bounds])
    if not probe.get('ok'):
        return probe
    nf = ng = nr = 0
    for i in range(n):
        x = x0 + (i + 0.5) * dx
        for j in range(n):
            y = y0 + (j + 0.5) * dy
            for k in range(n):
                z = z0 + (k + 0.5) * dz
                f = F(x, y, z)
                g = G(x, y, z)
                if f < 0.0:
                    nf += 1
                if g < 0.0:
                    ng += 1
                if built['op'] == 'add':
                    r = min(f, g)
                elif built['op'] == 'subtract':
                    r = max(f, -g)
                else:
                    r = max(f, g)
                if r < 0.0:
                    nr += 1
    return {'ok': True, 'offset': offset_name, 'op': built['op'],
            'mode': built['mode'], 'resolution': n,
            'bounds': [[round(v, 6) for v in ax] for ax in bounds],
            'parentVolume': nf * cell, 'offsetVolume': ng * cell,
            'resultVolume': nr * cell,
            'deltaVolume': (nr - nf) * cell,
            'approxReason': built['approxReason'],
            'method': f'grid-sample (N={n}); volume = inside cells × '
                      f'cell volume — a discretisation, not a closed '
                      f'form', 'unusedResultIsNoop': nr == nf}


# ------------------------------------------------------------------
# the no-code rows
# ------------------------------------------------------------------
def _g_row_expr(built):
    """The `<offset>--G` expr in q = [u, v, w, 1] + its operands."""
    mode, t, extent = built['mode'], built['t'], built['extent']
    operands = {'q': {'kind': 'matrixEquation',
                      'ref': f'{built["offset"]}--local'}}
    for k, v in built['knobs'].items():
        operands[k] = {'kind': 'scalar', 'value': v}
    operands['t'] = {'kind': 'scalar', 'value': t}
    if built['offsetEq']:
        t_text = '(' + _in_q(rewrite_field_functions(built['offsetEq'])) + ')'
    else:
        t_text = 't'
    sign = '-' if t < 0.0 else ''
    terms = []
    if mode in ('planar_square', 'planar_disk'):
        terms += [f'-({sign}q[2])', f'({sign}q[2]) - np.abs({t_text})']
        if mode == 'planar_square':
            half = float(extent.get('side', 1.0)) / 2.0
            terms += [f'np.abs(q[0]) - {half!r}', f'np.abs(q[1]) - {half!r}']
        else:
            R = float(extent.get('radius', 0.5))
            terms += [f'q[0]*q[0] + q[1]*q[1] - {R * R!r}']
    else:
        expr, raw_ops = built['customSource']
        terms += ['(' + _in_q(rewrite_field_functions(expr)) + ')']
        for sym, sp in raw_ops.items():
            if sym in ('q',):
                continue
            if sp == 'p':
                operands[sym] = 'p'
            elif isinstance(sp, str) and sp in built['knobs']:
                operands[sym] = {'kind': 'scalar', 'value': built['knobs'][sp]}
            elif isinstance(sp, (int, float)):
                operands[sym] = {'kind': 'scalar', 'value': float(sp)}
            else:
                operands[sym] = executor_operand(sp)
    for ax, lo, hi in _extent_clips(extent):
        s = _SYM[ax]
        terms += [f'{lo!r} - {s}', f'{s} - {hi!r}']
    expr = terms[0] if len(terms) == 1 else \
        'np.max(np.stack([' + ', '.join(terms) + ']))'
    return expr, operands


def offset_equation_rows(manager, offset_name):
    """All no-code rows for one offset: the parent's rows (+ its ∇F
    row), `<offset>--frame` (M), `--local` (q = M p), `--G` (in q),
    `--field` (composed with `<shape>--field`). Conform refuses by
    name (no row form in the executor yet)."""
    built = offset_field(manager, offset_name)
    if not built.get('ok'):
        return built
    if built['mode'] == 'conform':
        return {'ok': False, 'offset': offset_name,
                'refusal': 'conform has no row form yet: F(p − t·n(p)) '
                           'needs the executor to evaluate a referenced '
                           'equation at a translated point (a "rebind '
                           'p" operand) — a named absence; the python '
                           'leg evaluates it (evaluate / sample)',
                'kind': 'no-row-form'}
    row = offset_named(manager, offset_name)
    if built['mode'] == 'custom':
        built['customSource'] = _custom_source(manager, row)
    parent = gradient_rows(manager, built['shape'])
    if not parent.get('ok'):
        return parent
    frame = built['frame']
    matrix_rows = list(parent['matrixRows']) + [{
        'name': f'{offset_name}--frame',
        'description': f'World→anchor-frame 4x4 of offset '
                       f'"{offset_name}" (anchor "{built["anchor"]}", '
                       f'reference {frame["mode"]}): q = M p gives '
                       f'[u, v, w, 1]. Emitted by ms-anchor.',
        'shape_json': '[4, 4]', 'element_type': 'float',
        'values_json': json.dumps(frame['matrix']),
        'computation_json': '{"kind": "literal"}',
    }]
    g_expr, g_operands = _g_row_expr(built)
    op = built['op']
    if op == 'add':
        f_expr = 'np.min(np.stack([F, G]))'
    elif op == 'subtract':
        f_expr = 'np.max(np.stack([F, -(G)]))'
    else:
        f_expr = 'np.max(np.stack([F, G]))'
    eq_rows = list(parent['equationRows']) + [
        {'name': f'{offset_name}--local',
         'description': f'Local coordinates [u, v, w, 1] of p in the '
                        f'anchor frame of "{offset_name}" — bind '
                        f'p = [x, y, z, 1].',
         'latex': r'q = M p',
         'operation_json': json.dumps({'kind': 'expr', 'expr': 'M @ p'}),
         'operands_json': json.dumps(
             {'p': 'p', 'M': {'kind': 'matrix',
                              'ref': f'{offset_name}--frame'}})},
        {'name': f'{offset_name}--G',
         'description': f'Offset solid G(u, v, w) < 0 of "{offset_name}" '
                        f'({built["mode"]}) in its anchor frame; knobs '
                        f'are scalar operands (the Spreadsheet twins).',
         'latex': r'G(u, v, w) < 0',
         'operation_json': json.dumps({'kind': 'expr', 'expr': g_expr}),
         'operands_json': json.dumps(g_operands)},
        {'name': f'{offset_name}--field',
         'description': f'"{built["shape"]}" {op} "{offset_name}": '
                        f'the result solid, < 0 inside — the CSG '
                        f'algebra over the two fields.',
         'latex': r'F \oplus G',
         'operation_json': json.dumps({'kind': 'expr', 'expr': f_expr}),
         'operands_json': json.dumps(
             {'F': {'kind': 'matrixEquation',
                    'ref': f'{built["shape"]}--field'},
              'G': {'kind': 'matrixEquation',
                    'ref': f'{offset_name}--G'}})},
    ]
    return {'ok': True, 'offset': offset_name, 'shape': built['shape'],
            'matrixRows': matrix_rows, 'equationRows': eq_rows,
            'equationRefs': {
                'frame': f'{offset_name}--frame',
                'local': f'{offset_name}--local',
                'G': f'{offset_name}--G',
                'field': f'{offset_name}--field',
                'parentField': f'{built["shape"]}--field',
                'parentGradient': parent['equationRefs']['gradient']},
            'approxReason': built['approxReason']}


class _ShapeRow:
    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)


_CSG_OP = {'add': 'union', 'subtract': 'difference',
           'intersect': 'intersection'}


def result_shape_rows(manager, offset_name, persist=False):
    """For the planar modes with constant t: ordinary
    MathShapeDefinition rows — one family='quadric' row per bounding
    surface (world frame), `<offset>--solid` (csg intersection) and
    `<offset>--result` (csg op over parent + solid) — so the result
    rides the existing shape_properties / sample_surface path exactly.
    Other modes refuse by name: their solid is not a quadric set."""
    built = offset_field(manager, offset_name)
    if not built.get('ok'):
        return built
    if not built['surfaces']:
        return {'ok': False, 'offset': offset_name,
                'refusal': f'mode "{built["mode"]}"'
                           f'{" with a varying t" if built["offsetEq"] else ""}'
                           f' is not a set of quadrics — no '
                           f'MathShapeDefinition row form; use '
                           f'evaluate / sample (python) or the '
                           f'--field no-code row'}
    bounds = built['bounds']
    rows = []
    surf_names = []
    for label, Q in built['surfaces']:
        nm = f'{offset_name}--surf--{label}'
        surf_names.append(nm)
        rows.append(_ShapeRow(
            name=nm, display_name=f'{offset_name} {label}',
            family='quadric', primitive_kind='', csg_json='',
            parameters_json='{}', provenance_id=PROV,
            quadric_matrix_json=json.dumps([v for r in Q for v in r]),
            bounds_json=json.dumps(bounds),
            notes=f'bounding surface "{label}" of anchored offset '
                  f'"{offset_name}" in the WORLD frame (emitted; the '
                  f'offset row is the source of truth)'))
    solid = f'{offset_name}--solid'
    rows.append(_ShapeRow(
        name=solid, display_name=f'{offset_name} solid', family='csg',
        primitive_kind='', quadric_matrix_json='', parameters_json='{}',
        bounds_json=json.dumps(bounds), provenance_id=PROV,
        csg_json=json.dumps({'op': 'intersection', 'shapes': surf_names}),
        notes=f'the {built["mode"]} patch of "{offset_name}": '
              f'intersection of its surfaces'))
    result = f'{offset_name}--result'
    rows.append(_ShapeRow(
        name=result, display_name=f'{built["shape"]} {built["op"]} '
                                  f'{offset_name}',
        family='csg', primitive_kind='', quadric_matrix_json='',
        parameters_json='{}', bounds_json=json.dumps(bounds),
        provenance_id=PROV,
        csg_json=json.dumps({'op': _CSG_OP[built['op']],
                             'shapes': [built['shape'], solid]}),
        notes=f'anchored offset result: parent "{built["shape"]}" '
              f'{built["op"]} "{offset_name}"'))
    if persist:
        table = (getattr(manager, 'objectTables', None) or {}).get(
            'MathShapeDefinition')
        if isinstance(table, dict):
            for r in rows:
                table[r.name] = r
        row = offset_named(manager, offset_name)
        if row is not None:
            row.result_shape_ref = result
    return {'ok': True, 'offset': offset_name, 'resultShape': result,
            'solidShape': solid, 'surfaceShapes': surf_names,
            'rows': rows, 'persisted': bool(persist),
            'note': 'exact: planes + (disk) a cylinder quadric about '
                    'the reference axis; the csg difference/union is '
                    'the existing max/min path'}


def anchor_payload(pick, name, shape_name, reference='toward'):
    """The ShapeAnchor row fields from a pick_anchor result."""
    frame = anchor_frame(pick, reference)
    return {
        'name': name, 'display_name': name, 'shape_ref': shape_name,
        'ray_origin_json': json.dumps(pick['rayOrigin']),
        'ray_dir_json': json.dumps(pick['rayDir']),
        'hit_json': json.dumps(pick['hit']),
        'normal_json': json.dumps(pick['normal']),
        'normal_eq_ref': pick['normalEqRef'],
        'reference': reference,
        'frame_json': json.dumps({k: frame[k] for k in
                                  ('a', 'b', 'c', 'origin', 'matrix',
                                   'mode', 'note')}) if frame.get('ok')
        else '',
        'basis': pick['basis'], 'provenance_id': PROV,
        'notes': pick['method'],
    }
