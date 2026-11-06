"""
@module mathshapes.custom.shape_equations

mq-1 (MATRIX_SHAPE_COHERENCE_PLAN; Dustin 2026-08-01: "all shapes
defined using matrix equations if possible ... so we can make
correlations between their equations later ... via no code"): the
SHAPE→EQUATION BRIDGE.

Every MathShapeDefinition's bounding surfaces become 4x4 quadric
matrices (planes are degenerate quadrics), and the shape's SOLID
becomes one implicit field F(p) composed by CSG algebra over the
surface values (inside < 0):

    intersection -> max,  union -> min,  difference -> max(a, -b)

Both live TWICE, deliberately, with parity pinned between them
(the winding rule, generalized):
- as NO-CODE ROWS — MatrixDefinition per surface Q, a pᵀQp
  MatrixEquationDefinition per surface, and one `<shape>--field`
  MatrixEquationDefinition per shape whose operands REFERENCE the
  others — evaluable by the EXISTING matrix_equation_executor with
  a single binding p = [x, y, z, 1]. Correlating two parts later
  (mq-3) is just another equation row referencing their matrices.
- as `field_value` here — a pure-python evaluator the stdlib
  selftests can run; the numpy-side executor result must equal it.

NAME-CONVENTION LINK: a shape's rows are `<shape>--Q--<label>`,
`<shape>--surf--<label>`, `<shape>--field`. The link is derivable
and reported (equationRefs in every payload) rather than a new
column on MathShapeDefinition — a deliberate deviation from the
plan's equation_refs_json, chosen to avoid schema churn; revisit
if a consumer genuinely needs the column.

HONEST ABSENCES: winding-family shapes are PARAMETRIC CURVES with
their own matrix equation (winding_matrix_equation, ws-1) — they
have no implicit field and say so. Mesh/CAD imports have no
equation form at all — refused by name, never faked.

ms-anchor (§8.5) adds, at the bottom of this file, the executor
function set (atan2 / mod / frac / lmin / lmax, rewritten into the
numpy spelling the real executor already accepts, with a pure-python
parity leg) and the ∇F operand (gradient_value + the `<shape>--grad`
rows) the anchored-offset tool needs.

@consumers mathshapes.shape_api (/api/shapes/equations),
polariServer seed pass (seed_shape_equations), mq-2/mq-3,
mathshapes.custom.shape_anchor (ms-anchor)
"""

import json
import math

from mathshapes.custom.shape_geometry import (
    box_plane_quadrics, cone_quadric_matrix,
    ellipsoid_quadric_matrix, plane_quadric_matrix, quadric_value,
    sphere_quadric_matrix,
)

PROV = 'mq-1'

_AXIS_INDEX = {'x': 0, 'y': 1, 'z': 2}


def _named(manager, shape_name):
    table = (getattr(manager, 'objectTables', None)
             or {}).get('MathShapeDefinition', {})
    if isinstance(table, dict):
        row = table.get(shape_name)
        if row is not None:
            return row
        for r in table.values():
            if getattr(r, 'name', '') == shape_name:
                return r
    return None


def _json_field(row, attr, default):
    try:
        return json.loads(getattr(row, attr, '') or '')
    except (TypeError, ValueError):
        return default


def _axis_caps(params):
    """The two cap planes of an axial primitive, outward normals."""
    axis = params.get('axis', 'z')
    ai = _AXIS_INDEX.get(axis, 2)
    center = list(params.get('center', [0.0, 0.0, 0.0]))
    h = float(params.get('height', 1.0))
    top = list(center)
    top[ai] += h / 2.0
    base = list(center)
    base[ai] -= h / 2.0
    n_top = [0.0, 0.0, 0.0]
    n_top[ai] = 1.0
    n_base = [0.0, 0.0, 0.0]
    n_base[ai] = -1.0
    return [('cap-top', plane_quadric_matrix(n_top, top)),
            ('cap-base', plane_quadric_matrix(n_base, base))]


def surface_quadrics(shape):
    """The shape's bounding surfaces as labelled 4x4 quadrics
    (inside < 0 each; the SOLID is their max). Refusal-honest for
    families with no implicit form."""
    family = getattr(shape, 'family', 'primitive')
    name = getattr(shape, 'name', '?')
    if family == 'quadric':
        flat = _json_field(shape, 'quadric_matrix_json', None)
        if not flat or len(flat) != 16:
            return {'ok': False,
                    'refusal': f'"{name}" is quadric-family but '
                               f'its matrix does not parse'}
        Q = [flat[i * 4:i * 4 + 4] for i in range(4)]
        return {'ok': True, 'surfaces': [('surface', Q)]}
    if family == 'primitive':
        params = _json_field(shape, 'parameters_json', {})
        kind = getattr(shape, 'primitive_kind', '')
        center = list(params.get('center', [0.0, 0.0, 0.0]))
        if kind == 'box':
            return {'ok': True, 'surfaces': box_plane_quadrics(
                center, [float(c) for c in
                         params.get('size', [1, 1, 1])])}
        if kind == 'sphere':
            return {'ok': True, 'surfaces': [
                ('surface', sphere_quadric_matrix(
                    center, float(params.get('radius', 1.0))))]}
        if kind == 'ellipsoid':
            return {'ok': True, 'surfaces': [
                ('surface', ellipsoid_quadric_matrix(
                    center, [float(c) for c in
                             params.get('radii', [1, 1, 1])]))]}
        if kind == 'annular_sector':
            r_in = float(params.get('r_inner', 0.0))
            r_out = float(params.get('r_outer', 1.0))
            half = math.radians(
                float(params.get('half_angle_deg', 30.0)))
            az = math.radians(
                float(params.get('azimuth_deg', 0.0)))
            h = float(params.get('height', 1.0))
            axis = params.get('axis', 'z')
            ai = _AXIS_INDEX.get(axis, 2)
            perp = [i for i in range(3) if i != ai]
            surfaces = [('lateral-outer', cone_quadric_matrix(
                r_out, r_out, h, axis=axis, center=center))]
            if r_in > 0.0:
                # the BORE: same quadric, sign flipped — inside
                # the sector means OUTSIDE the inner cylinder.
                Q_in = cone_quadric_matrix(r_in, r_in, h,
                                           axis=axis,
                                           center=center)
                surfaces.append(('lateral-inner',
                                 [[-v for v in row]
                                  for row in Q_in]))
            for tag, th in (('cut-ccw', az + half),
                            ('cut-cw', az - half)):
                n = [0.0, 0.0, 0.0]
                sign = 1.0 if tag == 'cut-ccw' else -1.0
                n[perp[0]] = -sign * math.sin(th)
                n[perp[1]] = sign * math.cos(th)
                surfaces.append((tag, plane_quadric_matrix(
                    n, center)))
            return {'ok': True,
                    'surfaces': surfaces + _axis_caps(params)}
        if kind == 'arc_faced_bar':
            w = float(params.get('width', 1.0))
            r_face = float(params.get('r_face', 1.0))
            r_back = float(params.get('r_back', 2.0))
            az = math.radians(
                float(params.get('azimuth_deg', 0.0)))
            axis = params.get('axis', 'z')
            ai = _AXIS_INDEX.get(axis, 2)
            perp = [i for i in range(3) if i != ai]
            e_u = [0.0, 0.0, 0.0]
            e_u[perp[0]] = math.cos(az)
            e_u[perp[1]] = math.sin(az)
            e_v = [0.0, 0.0, 0.0]
            e_v[perp[0]] = -math.sin(az)
            e_v[perp[1]] = math.cos(az)
            back_pt = [center[i] + r_back * e_u[i]
                       for i in range(3)]
            side_a = [center[i] + (w / 2.0) * e_v[i]
                      for i in range(3)]
            side_b = [center[i] - (w / 2.0) * e_v[i]
                      for i in range(3)]
            h = float(params.get('height', 1.0))
            Q_face = cone_quadric_matrix(r_face, r_face, h,
                                         axis=axis,
                                         center=center)
            surfaces = [
                ('arc-face', [[-v for v in row]
                              for row in Q_face]),
                ('back', plane_quadric_matrix(e_u, back_pt)),
                ('side-ccw', plane_quadric_matrix(e_v, side_a)),
                ('side-cw', plane_quadric_matrix(
                    [-c for c in e_v], side_b)),
                # guards the MIRROR ghost: rho >= r_face also
                # holds behind the center; the bar lives on the
                # +azimuth side only.
                ('front-guard', plane_quadric_matrix(
                    [-c for c in e_u], center)),
            ]
            return {'ok': True,
                    'surfaces': surfaces + _axis_caps(params)}
        if kind in ('cylinder', 'cone', 'frustum'):
            h = float(params.get('height', 1.0))
            axis = params.get('axis', 'z')
            if kind == 'cylinder':
                base_r = top_r = float(params.get('radius', 1.0))
            else:
                base_r = float(params.get('base_radius', 1.0))
                top_r = (0.0 if kind == 'cone'
                         else float(params.get('top_radius', 0.5)))
            lateral = cone_quadric_matrix(base_r, top_r, h,
                                          axis=axis, center=center)
            return {'ok': True,
                    'surfaces': [('lateral', lateral)]
                    + _axis_caps(params)}
        return {'ok': False,
                'refusal': f'primitive kind "{kind}" has no '
                           f'quadric emission yet — a named seam, '
                           f'not an oversight (mq-5 territory)'}
    if family == 'winding':
        return {'ok': False,
                'refusal': 'a winding is a PARAMETRIC CURVE, not '
                           'an implicit solid — its matrix '
                           'equation is winding_matrix_equation '
                           '(ws-1), already a no-code spec',
                'kind': 'parametric-curve'}
    return {'ok': False,
            'refusal': f'family "{family}" has no equation form '
                       f'(imported meshes are measured, not '
                       f'derived) — carried as a named absence'}


def field_spec(manager, shape_name, _depth=0):
    """The shape's implicit-field TREE: csg nodes over quadric
    leaves. Pure structure; both evaluators walk it."""
    if _depth > 8:
        return {'ok': False,
                'refusal': 'csg nesting exceeded max depth '
                           '(probable reference cycle)'}
    shape = _named(manager, shape_name)
    if shape is None:
        return {'ok': False,
                'refusal': f'no MathShapeDefinition named '
                           f'"{shape_name}"'}
    if getattr(shape, 'family', '') == 'csg':
        csg = _json_field(shape, 'csg_json', {})
        op = csg.get('op', '')
        children = csg.get('shapes', [])
        if op not in ('union', 'difference', 'intersection') \
                or not children:
            return {'ok': False,
                    'refusal': f'"{shape_name}" csg_json does not '
                               f'parse into op+shapes'}
        specs = []
        for child in children:
            sub = field_spec(manager, child, _depth + 1)
            if not sub.get('ok'):
                return {'ok': False,
                        'refusal': f'csg child "{child}": '
                                   f'{sub.get("refusal")}'}
            specs.append(sub)
        return {'ok': True, 'shape': shape_name, 'op': op,
                'children': specs}
    surf = surface_quadrics(shape)
    if not surf.get('ok'):
        return surf
    return {'ok': True, 'shape': shape_name,
            'surfaces': surf['surfaces']}


def _eval_spec(spec, x, y, z):
    if 'surfaces' in spec:
        return max(quadric_value(Q, x, y, z)
                   for _, Q in spec['surfaces'])
    vals = [_eval_spec(c, x, y, z) for c in spec['children']]
    if spec['op'] == 'union':
        return min(vals)
    if spec['op'] == 'intersection':
        return max(vals)
    return max([vals[0]] + [-v for v in vals[1:]])   # difference


def field_value(manager, shape_name, x, y, z):
    """F(p) by pure python — the parity partner of the emitted
    no-code rows. Inside < 0, surface = 0, outside > 0."""
    spec = field_spec(manager, shape_name)
    if not spec.get('ok'):
        return spec
    return {'ok': True, 'shape': shape_name,
            'value': _eval_spec(spec, x, y, z)}


# ------------------------------------------------------------------
# Emission — the no-code rows
# ------------------------------------------------------------------

def _matrix_row(name, Q, shape_name, label):
    return {
        'name': name,
        'description': f'Surface quadric of math shape '
                       f'"{shape_name}" ({label}): pᵀQp = 0 is '
                       f'the surface, < 0 the solid side. '
                       f'Emitted by mq-1; the shape row is the '
                       f'source of truth.',
        'shape_json': '[4, 4]',
        'element_type': 'float',
        # row-major FLAT list — the matrix executor's literal form.
        'values_json': json.dumps(
            [v for row in Q for v in row]),
        'computation_json': '{"kind": "literal"}',
    }


def _surf_eq_row(name, matrix_name, shape_name, label):
    return {
        'name': name,
        'description': f'pᵀQp for surface "{label}" of '
                       f'"{shape_name}" — bind p = [x, y, z, 1].',
        'latex': r'p^{\top} Q p',
        'operation_json': json.dumps(
            {'kind': 'expr', 'expr': 'p @ Q @ p'}),
        'operands_json': json.dumps(
            {'p': 'p', 'Q': {'kind': 'matrix',
                             'ref': matrix_name}}),
    }


def _field_expr(spec, sym_of):
    """Compose the numpy expr + operands for a field node."""
    if 'surfaces' in spec:
        syms = [sym_of(spec['shape'], label)
                for label, _ in spec['surfaces']]
        if len(syms) == 1:
            return syms[0]
        return ('np.max(np.stack(['
                + ', '.join(syms) + ']))')
    parts = [_field_expr(c, sym_of) for c in spec['children']]
    if spec['op'] == 'union':
        return 'np.min(np.stack([' + ', '.join(parts) + ']))'
    if spec['op'] == 'intersection':
        return 'np.max(np.stack([' + ', '.join(parts) + ']))'
    inner = [parts[0]] + [f'-({p})' for p in parts[1:]]
    return 'np.max(np.stack([' + ', '.join(inner) + ']))'


def shape_equation_rows(manager, shape_name):
    """All no-code rows for one shape: matrices, per-surface
    equations, and the ONE `<shape>--field` equation whose
    operands reference them. Refusal rides through."""
    spec = field_spec(manager, shape_name)
    if not spec.get('ok'):
        return spec
    matrix_rows, eq_rows = [], []
    operands = {'p': 'p'}
    sym_index = {}

    def sym_of(owner, label):
        key = (owner, label)
        if key not in sym_index:
            sym_index[key] = f's{len(sym_index)}'
        return sym_index[key]

    def walk(node):
        if 'surfaces' in node:
            owner = node['shape']
            for label, Q in node['surfaces']:
                m_name = f'{owner}--Q--{label}'
                e_name = f'{owner}--surf--{label}'
                matrix_rows.append(
                    _matrix_row(m_name, Q, owner, label))
                eq_rows.append(
                    _surf_eq_row(e_name, m_name, owner, label))
                operands[sym_of(owner, label)] = {
                    'kind': 'matrixEquation', 'ref': e_name}
        else:
            for c in node['children']:
                walk(c)

    walk(spec)
    expr = _field_expr(spec, sym_of)
    eq_rows.append({
        'name': f'{shape_name}--field',
        'description': f'Implicit solid field of "{shape_name}": '
                       f'< 0 inside, 0 on the surface. CSG algebra '
                       f'(max/min/negate) over the surface '
                       f'equations — bind p = [x, y, z, 1]. '
                       f'Correlate parts by referencing this row.',
        'latex': r'F(p) < 0 \iff p \in \text{solid}',
        'operation_json': json.dumps({'kind': 'expr',
                                      'expr': expr}),
        'operands_json': json.dumps(operands),
    })
    return {'ok': True, 'shape': shape_name,
            'matrixRows': matrix_rows, 'equationRows': eq_rows,
            'equationRefs': {
                'field': f'{shape_name}--field',
                'surfaces': [r['name'] for r in eq_rows[:-1]],
                'matrices': [r['name'] for r in matrix_rows]},
            'note': 'name-convention link: <shape>--Q--<label> / '
                    '--surf--<label> / --field'}


def equation_parity(manager, shape_name, n=24):
    """The winding rule, generalized: the DRAWN surface must sit
    on the equations. Samples the shape's own rendered surface and
    reports the worst |F| relative to the shape's scale, plus the
    interior/exterior sign probes. Tolerance absorbs voxel-fallback
    meshes honestly by REPORTING method alongside."""
    from mathshapes.custom.shape_analysis import (
        sample_surface, shape_properties,
    )
    props = shape_properties(manager, shape_name)
    if not props.get('ok'):
        return {'ok': False, 'refusal': props.get('error',
                                                  'no properties')}
    spec = field_spec(manager, shape_name)
    if not spec.get('ok'):
        return spec
    bounds = props.get('boundingBox') or props.get('bounds')
    if not bounds:
        return {'ok': False,
                'refusal': 'shape reports no bounds — nothing to '
                           'scale the residual against'}
    scale = max(abs(b[1] - b[0]) for b in bounds) or 1.0
    centroid = props.get('centroid') or [
        (b[0] + b[1]) / 2.0 for b in bounds]
    inside = _eval_spec(spec, *centroid)
    far = [bounds[0][1] + 3.0 * scale, bounds[1][1] + 3.0 * scale,
           bounds[2][1] + 3.0 * scale]
    outside = _eval_spec(spec, *far)
    sampled = sample_surface(manager, shape_name, n=n)
    pts = (sampled.get('points') if isinstance(sampled, dict)
           else sampled) or []
    residuals = sorted(
        abs(_eval_spec(spec, *p[:3])) / (scale * scale)
        for p in pts)
    median = (residuals[len(residuals) // 2] if residuals
              else None)
    worst = residuals[-1] if residuals else None
    return {
        'ok': True, 'shape': shape_name,
        'insideValue': inside, 'outsideValue': outside,
        'signsCorrect': inside < 0.0 < outside,
        'surfaceSamples': len(residuals),
        'medianResidual': median, 'worstResidual': worst,
        'scale': scale,
        'note': 'residuals are |F|/scale² over the DRAWN surface '
                'samples — exact meshes sit near 0; a voxel-'
                'fallback mesh reports its discretization here '
                'instead of hiding it'}


def seed_shape_equations(manager, shape_names=None):
    """Emit + upsert the no-code rows for every (or the named)
    MathShapeDefinition. Refusals are REPORTED per shape, never
    silently dropped. Guarded on the matrices module."""
    try:
        from matrices.matrix_definition import MatrixDefinition
        from matrices.matrix_equation_definition import (
            MatrixEquationDefinition,
        )
    except ImportError:
        return [{'class': 'MatrixDefinition',
                 'inserted': [], 'updated': [],
                 'errors': ['matrices module not importable — '
                            'shape equations need it enabled']}]
    from moduleService.seed_upsert import upsert_seed_pairs
    table = (getattr(manager, 'objectTables', None)
             or {}).get('MathShapeDefinition', {})
    names = shape_names or sorted(
        getattr(r, 'name', '') for r in
        (table.values() if isinstance(table, dict) else []))
    matrix_rows, eq_rows, refusals = [], [], []
    for name in names:
        out = shape_equation_rows(manager, name)
        if not out.get('ok'):
            refusals.append({'shape': name,
                             'refusal': out.get('refusal')})
            continue
        matrix_rows.extend(out['matrixRows'])
        eq_rows.extend(out['equationRows'])
    # de-dup by name (csg children shared between shapes)
    matrix_rows = list({r['name']: r for r in matrix_rows}
                       .values())
    eq_rows = list({r['name']: r for r in eq_rows}.values())
    reports = upsert_seed_pairs(manager, [
        ('MatrixDefinition', MatrixDefinition, matrix_rows),
        ('MatrixEquationDefinition', MatrixEquationDefinition,
         eq_rows),
    ], tag='ShapeEquationSeed')
    for r in reports:
        r['shapeRefusals'] = refusals
    return reports


# ------------------------------------------------------------------
# ms-anchor executor additions (MECH_FREECAD_INTERCHANGE_PLAN §8.5:
# "atan2, mod/frac, min/max over a list, a per-point normal (2Qp) as
# an operand. All small.")
#
# The REAL executor (matrices.matrix_equation_executor, kind 'expr')
# evaluates a numpy expression in a sandbox whose scope has `np`; it
# is NOT edited here. The additions live on the mathshapes side in
# two legs that must agree (the parity rule of this file):
#   - FIELD_FUNCTIONS + rewrite_field_functions: the friendly spelling
#     a person types (atan2, mod, frac, lmin, lmax, abs, sqrt, sin,
#     cos, floor, pi) rewritten into the numpy spelling the executor
#     already accepts, so an emitted row needs nothing new upstream;
#   - eval_field_expr: a pure-python (stdlib) evaluator of the SAME
#     rewritten string — the parity partner the selftests can run
#     without numpy — through a tiny `np` shim over scalars.
# The ∇F operand: gradient_value (exact 2Qp of the ACTIVE surface,
# propagated through CSG by the active branch) and gradient_rows
# (the `<shape>--grad` no-code row the real executor evaluates);
# an operand {"kind": "shapeGradient", "ref": <shape>} in a mathshapes
# equation resolves to it on both legs.
# ------------------------------------------------------------------

import re as _re

#: friendly name -> (numpy open text, close text, meaning). The call's
#: argument list is kept verbatim between open and close.
FIELD_FUNCTIONS = {
    'atan2': ('np.arctan2(', ')',
              'atan2(y, x) — the angle around the frame axis (θ)'),
    'mod': ('np.mod(', ')',
            'mod(x, m) — numpy semantics: result has the sign of m'),
    'frac': ('np.mod(', ', 1.0)',
             'frac(x) = x − floor(x) in [0, 1)'),
    'lmin': ('np.min(np.stack([', ']))',
             'lmin(a, b, ...) — min over a LIST (union of fields)'),
    'lmax': ('np.max(np.stack([', ']))',
             'lmax(a, b, ...) — max over a LIST (intersection)'),
    'abs': ('np.abs(', ')', 'absolute value'),
    'sqrt': ('np.sqrt(', ')', 'square root'),
    'sin': ('np.sin(', ')', 'sine (radians)'),
    'cos': ('np.cos(', ')', 'cosine (radians)'),
    'floor': ('np.floor(', ')', 'floor'),
}

_IDENT_BEFORE = _re.compile(r'[A-Za-z0-9_.]')


def _rewrite_call(expr, name, open_text, close_text):
    """Replace every `name(...)` call (paren-matched) with
    open_text + args + close_text. A `name` preceded by an identifier
    character or a '.' (e.g. np.abs) is left alone."""
    out, i, n = [], 0, len(expr)
    pat = name + '('
    while i < n:
        j = expr.find(pat, i)
        if j < 0:
            out.append(expr[i:])
            break
        if j > 0 and _IDENT_BEFORE.match(expr[j - 1]):
            out.append(expr[i:j + len(pat)])
            i = j + len(pat)
            continue
        depth, k = 1, j + len(pat)
        while k < n and depth:
            if expr[k] == '(':
                depth += 1
            elif expr[k] == ')':
                depth -= 1
            k += 1
        if depth:
            raise ValueError(f'unbalanced parentheses after {name}(')
        inner = _rewrite_call(expr[j + len(pat):k - 1], name,
                              open_text, close_text)
        out.append(expr[i:j] + open_text + inner + close_text)
        i = k
    return ''.join(out)


def rewrite_field_functions(expr):
    """The friendly spelling -> the executor's numpy spelling. Also
    `pi` -> np.pi and `^` -> `**`. Idempotent on already-numpy text."""
    s = str(expr).replace('^', '**')
    for name, (open_text, close_text, _) in FIELD_FUNCTIONS.items():
        s = _rewrite_call(s, name, open_text, close_text)
    s = _re.sub(r'(?<![A-Za-z0-9_.])pi(?![A-Za-z0-9_])', 'np.pi', s)
    return s


class _NpShim:
    """Just enough of `np` for the rewritten expressions over
    SCALARS (and lists for stack/min/max/argmax) — the stdlib leg."""
    pi = math.pi
    arctan2 = staticmethod(math.atan2)
    floor = staticmethod(math.floor)
    sqrt = staticmethod(math.sqrt)
    sin = staticmethod(math.sin)
    cos = staticmethod(math.cos)
    exp = staticmethod(math.exp)
    abs = staticmethod(abs)

    @staticmethod
    def mod(x, m):
        return x - m * math.floor(x / m)

    @staticmethod
    def stack(seq):
        return list(seq)

    @staticmethod
    def min(seq):
        return min(seq) if isinstance(seq, (list, tuple)) else seq

    @staticmethod
    def max(seq):
        return max(seq) if isinstance(seq, (list, tuple)) else seq

    @staticmethod
    def argmax(seq):
        return max(range(len(seq)), key=lambda i: seq[i])

    @staticmethod
    def argmin(seq):
        return min(range(len(seq)), key=lambda i: seq[i])

    maximum = staticmethod(max)
    minimum = staticmethod(min)

    @staticmethod
    def where(c, a, b):
        return a if c else b

    @staticmethod
    def asarray(x):
        return x


_EXPR_CACHE = {}


def eval_field_expr(expr, env):
    """Evaluate a (rewritten) field expression over scalar bindings —
    the pure-python parity partner of the numpy executor's 'expr'
    kind. Sandboxed like the executor: no builtins, '__' refused."""
    if '__' in expr:
        raise ValueError('field expression may not contain "__"')
    code = _EXPR_CACHE.get(expr)
    if code is None:
        code = compile(expr, '<field-expr>', 'eval')
        _EXPR_CACHE[expr] = code
    scope = {'np': _NpShim, 'abs': abs, 'min': min, 'max': max}
    scope.update(env)
    return float(eval(code, {'__builtins__': {}}, scope))   # noqa: S307


# ---- the ∇F operand ------------------------------------------------

def quadric_gradient(Q, x, y, z):
    """∇(pᵀQp) = 2Qp (first three rows), Q symmetric."""
    p = (x, y, z, 1.0)
    return [2.0 * sum(Q[i][j] * p[j] for j in range(4))
            for i in range(3)]


def _eval_spec_grad(spec, x, y, z):
    """(value, gradient) of the ACTIVE branch — the surface that wins
    the max/min at this point. Exact everywhere except ON an edge
    where two surfaces tie, where it is one-sided (a named limit)."""
    if 'surfaces' in spec:
        best = None
        for _, Q in spec['surfaces']:
            v = quadric_value(Q, x, y, z)
            if best is None or v > best[0]:
                best = (v, quadric_gradient(Q, x, y, z))
        return best
    results = [_eval_spec_grad(c, x, y, z) for c in spec['children']]
    if spec['op'] == 'union':
        return min(results, key=lambda r: r[0])
    if spec['op'] == 'intersection':
        return max(results, key=lambda r: r[0])
    cands = [results[0]] + [(-v, [-g for g in grad])
                            for v, grad in results[1:]]
    return max(cands, key=lambda r: r[0])


def gradient_value(manager, shape_name, x, y, z):
    """∇F at a point, by pure python — exact 2Qp of the active surface.
    Refuses like field_value when the shape has no equation form."""
    spec = field_spec(manager, shape_name)
    if not spec.get('ok'):
        return spec
    v, g = _eval_spec_grad(spec, x, y, z)
    return {'ok': True, 'shape': shape_name, 'value': v, 'gradient': g,
            'method': 'exact: 2Qp of the active surface (one-sided on '
                      'an edge where surfaces tie)'}


def finite_difference_gradient(F, x, y, z, h=1e-5):
    """Central differences on any scalar field F(x, y, z) — the
    fallback when no exact ∇F exists. Error O(h²); says so by name."""
    return [(F(x + h, y, z) - F(x - h, y, z)) / (2 * h),
            (F(x, y + h, z) - F(x, y - h, z)) / (2 * h),
            (F(x, y, z + h) - F(x, y, z - h)) / (2 * h)]


def _grad_expr(spec, sym_of, gsym_of):
    """numpy expr for ∇F of a node: the gradient of the branch that
    wins the node's max/min (np.argmax/argmin over the stacked
    values) — the row form of _eval_spec_grad."""
    if 'surfaces' in spec:
        labels = [label for label, _ in spec['surfaces']]
        if len(labels) == 1:
            return gsym_of(spec['shape'], labels[0])
        vals = ', '.join(sym_of(spec['shape'], lb) for lb in labels)
        grads = ', '.join(gsym_of(spec['shape'], lb) for lb in labels)
        return (f'np.stack([{grads}])'
                f'[np.argmax(np.stack([{vals}]))]')
    vals = [_field_expr(c, sym_of) for c in spec['children']]
    grads = [_grad_expr(c, sym_of, gsym_of) for c in spec['children']]
    if spec['op'] == 'union':
        pick = 'argmin'
    else:
        pick = 'argmax'
        if spec['op'] == 'difference':
            vals = [vals[0]] + [f'-({v})' for v in vals[1:]]
            grads = [grads[0]] + [f'-({g})' for g in grads[1:]]
    return (f'np.stack([{", ".join(grads)}])'
            f'[np.{pick}(np.stack([{", ".join(vals)}]))]')


def gradient_rows(manager, shape_name):
    """The ∇F no-code rows: one `<shape>--grad--<label>` per surface
    (expr `2 (Q p)[:3]`) and ONE `<shape>--grad` selecting the active
    branch — evaluable by the real executor with p = [x, y, z, 1].
    Rides on shape_equation_rows (the matrices + surface equations
    are the same rows)."""
    base = shape_equation_rows(manager, shape_name)
    if not base.get('ok'):
        return base
    spec = field_spec(manager, shape_name)
    operands = {'p': 'p'}
    sym_index, gsym_index = {}, {}
    grad_rows = []

    def sym_of(owner, label):
        key = (owner, label)
        if key not in sym_index:
            sym_index[key] = f's{len(sym_index)}'
            operands[sym_index[key]] = {
                'kind': 'matrixEquation',
                'ref': f'{owner}--surf--{label}'}
        return sym_index[key]

    def gsym_of(owner, label):
        key = (owner, label)
        if key not in gsym_index:
            gsym_index[key] = f'g{len(gsym_index)}'
            g_name = f'{owner}--grad--{label}'
            grad_rows.append({
                'name': g_name,
                'description': f'∇(pᵀQp) = 2Qp for surface "{label}" '
                               f'of "{owner}" — bind p = [x, y, z, 1]; '
                               f'a 3-vector.',
                'latex': r'\nabla F = 2 Q p',
                'operation_json': json.dumps(
                    {'kind': 'expr', 'expr': '(2.0 * (Q @ p))[:3]'}),
                'operands_json': json.dumps(
                    {'p': 'p', 'Q': {'kind': 'matrix',
                                     'ref': f'{owner}--Q--{label}'}}),
            })
            operands[gsym_index[key]] = {'kind': 'matrixEquation',
                                         'ref': g_name}
        return gsym_index[key]

    expr = _grad_expr(spec, sym_of, gsym_of)
    grad_rows.append({
        'name': f'{shape_name}--grad',
        'description': f'∇F of "{shape_name}": the gradient of the '
                       f'surface that wins the CSG max/min at p (the '
                       f'per-point normal before normalising) — bind '
                       f'p = [x, y, z, 1]. The ∇F operand of ms-anchor.',
        'latex': r'\nabla F(p)',
        'operation_json': json.dumps({'kind': 'expr', 'expr': expr}),
        'operands_json': json.dumps(operands),
    })
    return {'ok': True, 'shape': shape_name,
            'matrixRows': base['matrixRows'],
            'equationRows': base['equationRows'] + grad_rows,
            'equationRefs': dict(base['equationRefs'],
                                 gradient=f'{shape_name}--grad')}


def resolve_field_operand(manager, spec, x, y, z):
    """Pure-python resolution of one operand of a mathshapes field
    equation at a world point: a number, {"kind":"scalar"},
    {"kind":"shapeField","ref"} (F at p), {"kind":"shapeGradient",
    "ref"} (∇F at p, a 3-list), or a plain binding name looked up in
    nothing (refused — bindings are the caller's)."""
    if isinstance(spec, (int, float)):
        return float(spec)
    if isinstance(spec, dict):
        kind = spec.get('kind')
        if kind == 'scalar':
            return float(spec.get('value', 0.0))
        ref = spec.get('ref', '')
        if kind == 'shapeField':
            out = field_value(manager, ref, x, y, z)
            if not out.get('ok'):
                raise ValueError(out.get('refusal'))
            return out['value']
        if kind == 'shapeGradient':
            out = gradient_value(manager, ref, x, y, z)
            if not out.get('ok'):
                raise ValueError(out.get('refusal'))
            return out['gradient']
    raise ValueError(f'operand {spec!r} is not resolvable on the '
                     f'pure-python leg (bind it, or use scalar / '
                     f'shapeField / shapeGradient)')


def executor_operand(spec):
    """The same operand in the real executor's vocabulary: the
    mathshapes kinds become matrixEquation refs to the emitted
    `<shape>--field` / `<shape>--grad` rows."""
    if isinstance(spec, dict):
        kind = spec.get('kind')
        if kind == 'shapeField':
            return {'kind': 'matrixEquation',
                    'ref': f'{spec.get("ref", "")}--field'}
        if kind == 'shapeGradient':
            return {'kind': 'matrixEquation',
                    'ref': f'{spec.get("ref", "")}--grad'}
    return spec
