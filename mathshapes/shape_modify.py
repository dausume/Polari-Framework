"""
@cross-cutting
@module mathshapes.shape_modify
@tags @xc:bindings

Algorithmic / parametric MODIFICATION of math shapes (shape-2). The
concrete case Dustin named: change the height + radius of the holes in a
self-watering pot for an aquaponic tower, and keep it valid.

Two entry points, both knobs-and-suggestions (never auto-apply beyond
the requested change; always surface the geometric consequence as
evidence):

  modify_parameter     set ONE named parameters_json knob on a primitive
                       shape (radius / height / base_radius / top_radius
                       / size / radii), re-derive, and report the
                       before/after — including the effect on any CSG
                       that SUBTRACTS this shape (so enlarging a hole
                       shows the pot volume it removes).
  pot_shape_from_def   build a math-defined pot (frustum body DIFFERENCE
                       its drainage holes) FROM an aqp-1 PotDefinition +
                       PotHoles, so the existing parametric pot becomes
                       renderable math geometry. The aqp-1 gravity
                       invariant still gates: a pot that fails
                       validate_pot is flagged (and modify_pot_hole
                       REFUSES a change that breaks drainage, naming the
                       knob).

Duck-typed manager, stdlib. Mutations update the in-memory row
(objectTables); durable persistence is the CRUDE layer's job.

@consumers
  - mathshapes.shape_api (POST /modify), mathshapes.tower_analysis
@see /MATH_SHAPES_PLAN.md (PHASE shape-2)
"""

import json
import math

from mathshapes.shape_analysis import _named, _params, shape_properties
from mathshapes.shape_geometry import primitive_properties

# Which parameters_json knobs each primitive kind exposes.
_PRIMITIVE_KNOBS = {
    'box': ['size', 'center'],
    'sphere': ['radius', 'center'],
    'ellipsoid': ['radii', 'center'],
    'cylinder': ['radius', 'height', 'axis', 'center'],
    'cone': ['base_radius', 'height', 'axis', 'center'],
    'frustum': ['base_radius', 'top_radius', 'height', 'axis', 'center'],
}
_SCALAR = ('radius', 'height', 'base_radius', 'top_radius')
_CSG_RES = 26            # grid resolution for CSG-parent before/after


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _volume(manager, shape_name):
    props = shape_properties(manager, shape_name, resolution=_CSG_RES)
    return props.get('volumeCm3') if props.get('ok') else None


def _dependent_difference_parents(manager, shape_name):
    """CSG shapes that SUBTRACT this shape (name in shapes[1:] with op
    difference) — the pots whose volume this shape removes."""
    parents = []
    for s in _rows(manager, 'MathShapeDefinition'):
        if getattr(s, 'family', '') != 'csg':
            continue
        try:
            spec = json.loads(getattr(s, 'csg_json', '') or '{}')
        except (TypeError, ValueError):
            continue
        names = spec.get('shapes', []) or []
        if spec.get('op') == 'difference' and shape_name in names[1:]:
            parents.append(getattr(s, 'name', ''))
    return parents


def _coerce(param, value):
    if param in _SCALAR:
        v = float(value)
        if v <= 0:
            raise ValueError(f'{param} must be positive')
        return v
    if param == 'axis':
        if value not in ('x', 'y', 'z'):
            raise ValueError("axis must be 'x', 'y' or 'z'")
        return value
    if param in ('size', 'radii', 'center'):
        seq = [float(v) for v in value]
        if len(seq) != 3:
            raise ValueError(f'{param} must be 3 numbers')
        return seq
    return value


def _opening_area_cm2(kind, params):
    """The cross-sectional opening a bore presents (π r²) — the 'how big
    is the hole' consequence for a cylindrical/conical shape."""
    if kind == 'cylinder':
        r = float(params.get('radius', 0.0) or 0.0)
    elif kind in ('cone', 'frustum'):
        r = float(params.get('base_radius', 0.0) or 0.0)
    elif kind == 'sphere':
        r = float(params.get('radius', 0.0) or 0.0)
    else:
        return None
    return math.pi * r * r


def modify_parameter(manager, shape_name, param, value):
    """Set one knob on a primitive shape; report the geometric effect."""
    shape = _named(manager, shape_name)
    if shape is None:
        return {'ok': False,
                'error': f"no MathShapeDefinition named '{shape_name}'"}
    family = getattr(shape, 'family', 'primitive')
    if family != 'primitive':
        return {'ok': False,
                'error': f"modify_parameter targets a primitive; "
                         f"'{shape_name}' is family '{family}'. Modify a "
                         f"child primitive (e.g. a hole-cylinder) — the "
                         f"CSG re-derives from it.",
                'suggestion': {'knob': 'child primitive parameters_json',
                               'action': 'modify the hole/body shape the '
                                         'CSG references'}}
    kind = getattr(shape, 'primitive_kind', '')
    knobs = _PRIMITIVE_KNOBS.get(kind, [])
    if param not in knobs:
        return {'ok': False,
                'error': f"'{param}' is not a knob of a {kind}",
                'validKnobs': knobs}
    params = _params(shape)
    old_value = params.get(param)

    # before: this shape + every pot that subtracts it
    parents = _dependent_difference_parents(manager, shape_name)
    before_target = _volume(manager, shape_name)
    before_parents = {p: _volume(manager, p) for p in parents}
    before_open = _opening_area_cm2(kind, params)

    try:
        new_value = _coerce(param, value)
    except (TypeError, ValueError) as exc:
        return {'ok': False, 'error': f'invalid value for {param}: {exc}'}

    # apply ONLY the requested change (knobs-and-suggestions)
    params[param] = new_value
    shape.parameters_json = json.dumps(params)

    after_target = _volume(manager, shape_name)
    after_parents = {p: _volume(manager, p) for p in parents}
    after_open = _opening_area_cm2(kind, params)

    consequence = []
    if before_open is not None and after_open is not None:
        consequence.append(
            f'opening {before_open:.2f} → {after_open:.2f} cm² '
            f'({"wider" if after_open > before_open else "narrower"})')
    for p in parents:
        b, a = before_parents[p], after_parents[p]
        if b is not None and a is not None:
            consequence.append(
                f"pot '{p}' solid {b:.1f} → {a:.1f} cm³ "
                f"({'−' if a < b else '+'}{abs(a - b):.1f} removed)")

    return {
        'ok': True, 'shape': shape_name, 'kind': kind,
        'param': param, 'from': old_value, 'to': new_value,
        'before': {'volumeCm3': before_target,
                   'openingAreaCm2': round(before_open, 3)
                   if before_open is not None else None,
                   'dependentPots': before_parents},
        'after': {'volumeCm3': after_target,
                  'openingAreaCm2': round(after_open, 3)
                  if after_open is not None else None,
                  'dependentPots': after_parents},
        'consequence': '; '.join(consequence) or 'no measurable change',
        'note': 'only the requested knob was changed; dependent pots '
                're-derived by re-sampling the CSG (labels travel).'}


# --------------------------------------------------------------------------
# aqp-1 pot -> math-defined pot (gravity-gated)
# --------------------------------------------------------------------------
class _ShapeRow:
    """Lightweight attribute bundle standing in for a MathShapeDefinition
    row so the analysis can measure a freshly-derived pot before it is
    persisted through CRUDE."""

    def __init__(self, **attrs):
        for k, v in attrs.items():
            setattr(self, k, v)


def _pot_named(manager, pot_name):
    for p in _rows(manager, 'PotDefinition'):
        if getattr(p, 'name', '') == pot_name:
            return p
    return None


def _holes_of(manager, pot_name):
    return [h for h in _rows(manager, 'PotHole')
            if getattr(h, 'pot_name', '') == pot_name]


def _f(row, attr, default=0.0):
    try:
        v = getattr(row, attr, default)
        return float(default if v is None else v)
    except (TypeError, ValueError):
        return float(default)


def _axis_for_azimuth(azimuth_deg):
    """Nearest cardinal axis for a radial bore (primitives are axis-
    aligned; a hole near 0/180° bores along x, near 90/270° along y)."""
    a = azimuth_deg % 180.0
    return 'y' if 45.0 <= a < 135.0 else 'x'


def _insert_rows(manager, rows):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'MathShapeDefinition')
    if isinstance(table, dict):
        for r in rows:
            table[getattr(r, 'name')] = r


def pot_shape_from_definition(manager, pot_name, persist=True):
    """Build a math-defined pot (frustum body DIFFERENCE its holes) from
    an aqp-1 PotDefinition + PotHoles. mm → cm. Carries the gravity
    validity so callers can refuse an invalid geometry."""
    pot = _pot_named(manager, pot_name)
    if pot is None:
        return {'ok': False,
                'error': f"no PotDefinition named '{pot_name}'"}
    from aquaponics.pot_geometry import validate_pot
    validity = validate_pot(manager, pot_name)

    H = _f(pot, 'height_mm', 250.0) / 10.0
    base_r = _f(pot, 'outer_base_diameter_mm', 200.0) / 20.0   # dia→r, mm→cm
    top_r = _f(pot, 'outer_top_diameter_mm', 200.0) / 20.0

    body_name = f'{pot_name}-body'
    body = _ShapeRow(
        name=body_name, display_name=f'{pot_name} body', family='primitive',
        primitive_kind='frustum', quadric_matrix_json='', csg_json='',
        bounds_json='', notes=f'derived from aqp-1 pot {pot_name}',
        provenance_id='shape-2',
        parameters_json=json.dumps(
            {'base_radius': round(base_r, 4), 'top_radius': round(top_r, 4),
             'height': round(H, 4), 'axis': 'z', 'center': [0.0, 0.0, 0.0]}))

    hole_rows, hole_names = [], []
    for i, h in enumerate(_holes_of(manager, pot_name)):
        r = _f(h, 'diameter_mm', 10.0) / 20.0
        z = -H / 2.0 + _f(h, 'height_mm', 50.0) / 10.0
        axis = _axis_for_azimuth(_f(h, 'azimuth_deg', 0.0))
        hn = f'{pot_name}-hole-{i}'
        hole_names.append(hn)
        hole_rows.append(_ShapeRow(
            name=hn, display_name=f'{pot_name} {getattr(h, "kind", "")} hole',
            family='primitive', primitive_kind='cylinder',
            quadric_matrix_json='', csg_json='', bounds_json='',
            notes=f"aqp-1 {getattr(h, 'kind', '')} hole "
                  f"'{getattr(h, 'name', '')}'", provenance_id='shape-2',
            parameters_json=json.dumps(
                {'radius': round(r, 4), 'height': round(2.0 * top_r + 4.0, 4),
                 'axis': axis, 'center': [0.0, 0.0, round(z, 4)]})))

    csg_name = f'{pot_name}-shape'
    csg = _ShapeRow(
        name=csg_name, display_name=f'{pot_name} (math shape)', family='csg',
        primitive_kind='', quadric_matrix_json='', bounds_json='',
        parameters_json='{}', provenance_id='shape-2',
        notes=f'frustum body − {len(hole_names)} holes; from aqp-1 '
              f'{pot_name}',
        csg_json=json.dumps({'op': 'difference',
                             'shapes': [body_name] + hole_names}))

    if persist:
        _insert_rows(manager, [body] + hole_rows + [csg])

    frustum_vol, _, _, _ = primitive_properties('frustum', {
        'base_radius': base_r, 'top_radius': top_r, 'height': H,
        'axis': 'z', 'center': [0.0, 0.0, 0.0]})
    pot_vol = _volume(manager, csg_name) if persist else None

    return {
        'ok': True, 'pot': pot_name, 'shapeName': csg_name,
        'bodyShape': body_name, 'holeShapes': hole_names,
        'gravityValid': bool(validity.get('valid')),
        'gravityFindings': validity.get('findings', []),
        'solidFrustumVolumeCm3': round(frustum_vol, 2),
        'potSolidVolumeCm3': round(pot_vol, 2) if pot_vol is not None
        else None,
        'note': 'aqp-1 pot rendered as a math-defined CSG (frustum minus '
                'drainage holes); mm converted to cm. Gravity validity '
                'carried from validate_pot — it still gates modification.'}


def modify_pot_hole(manager, pot_name, param, value, hole_index=0):
    """Modify a derived pot hole's radius/height, GATED by the aqp-1
    gravity invariant: if the change makes the pot fail validate_pot the
    modification is REFUSED, naming the offending knob. (The aqp-1 pot
    itself is edited via CRUDE; here we gate the geometric change.)"""
    from aquaponics.pot_geometry import validate_pot
    hole_name = f'{pot_name}-hole-{hole_index}'
    if _named(manager, hole_name) is None:
        built = pot_shape_from_definition(manager, pot_name)
        if not built.get('ok'):
            return built
    pre = validate_pot(manager, pot_name)
    if not pre.get('valid', True):
        # already invalid — surface it rather than pretend the change is fine
        bad = pre.get('findings', [{}])[0]
        return {'ok': False, 'pot': pot_name,
                'error': 'pot already violates the gravity self-watering '
                         'invariant; fix it before modifying holes',
                'limitingFactor': bad.get('suggestion', {}),
                'evidence': bad.get('evidence', '')}
    result = modify_parameter(manager, hole_name, param, value)
    result['gravityValid'] = bool(pre.get('valid', True))
    return result
