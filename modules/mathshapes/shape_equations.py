"""
@module mathshapes.shape_equations

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

@consumers mathshapes.shape_api (/api/shapes/equations),
polariServer seed pass (seed_shape_equations), mq-2/mq-3
"""

import json
import math

from mathshapes.shape_geometry import (
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
    from mathshapes.shape_analysis import (
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
    from composition.seed_upsert import upsert_seed_pairs
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
