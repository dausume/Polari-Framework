"""
@cross-cutting
@module mathshapes.custom.shape_modify
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
  - mathshapes.shape_api (POST /modify), mathshapes.custom.tower_analysis
@see /MATH_SHAPES_PLAN.md (PHASE shape-2)
"""

import json
import math

from mathshapes.custom.shape_analysis import _named, _params, shape_properties
from mathshapes.custom.shape_geometry import cone_quadric_latex, cone_quadric_matrix, radius_at_z

_AXIS_INDEX = {'x': 0, 'y': 1, 'z': 2}

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


#: How far a hole's bore extends past the wall's inner+outer faces
#: combined (cm) — just enough that the ends visibly clear both
#: surfaces (no z-fighting flush faces), NOT enough to reach the far
#: wall or the pot's axis. Dustin 2026-07-13: "just big enough to go
#: fully through ... on ONE side of it."
HOLE_LENGTH_MARGIN_CM = 0.4


def _axis_and_sign_for_azimuth(azimuth_deg):
    """Nearest cardinal (axis, sign) for a radial bore (primitives are
    axis-aligned; a hole near 0° bores along +x, 180° along -x, 90°
    along +y, 270° along -y). The sign is which SIDE of that axis the
    hole sits on — needed so the short bore is positioned ON the wall
    at that azimuth rather than centered on the pot's own axis."""
    a = azimuth_deg % 360.0
    if 45.0 <= a < 135.0:
        return 'y', 1
    if 135.0 <= a < 225.0:
        return 'x', -1
    if 225.0 <= a < 315.0:
        return 'y', -1
    return 'x', 1


def _insert_rows(manager, rows):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        'MathShapeDefinition')
    if isinstance(table, dict):
        for r in rows:
            table[getattr(r, 'name')] = r


def _quadric_bounds_json(axis, center, half_len, xy_cap):
    """[[xmin,xmax],[ymin,ymax],[zmin,zmax]] bounds_json for a
    cone_quadric_matrix row — tight along its OWN axis (±half_len from
    center), generously capped perpendicular. This only sizes the
    CSG grid-sample SCAN region (`_shape_bounds`); it is NOT a clip on
    the quadric's own inside-test (`quadric_value(Q,...) < 0`, which
    is evaluated as the true infinite equation at every scanned grid
    point) — safe because nothing outside this box is ever scanned, so
    the equation's mathematical extension beyond it is simply never
    queried."""
    ai = _AXIS_INDEX[axis]
    b = [[center[i] - xy_cap, center[i] + xy_cap] for i in range(3)]
    b[ai] = [center[ai] - half_len, center[ai] + half_len]
    return b


def build_quadric_eq_row(name, display, base_r_eq, top_r_eq, height, axis,
                         center, extra_notes, bound_cap):
    """Build a `family='quadric'` MathShapeDefinition row (the equation
    is the source of truth — see pot_shape_from_definition's docstring)
    + its Q matrix. Shared by pot_shape_from_definition (wall/bottom)
    and soil_modify.soil_shape_from_definition (soil) — a single place
    for the row-construction/JSON-encoding contract so both can never
    drift apart."""
    Q = cone_quadric_matrix(base_r_eq, top_r_eq, height, axis, center)
    z0 = center[_AXIS_INDEX[axis]] - height / 2.0
    latex = cone_quadric_latex(base_r_eq, top_r_eq, height, z0, axis)
    return _ShapeRow(
        name=name, display_name=display, family='quadric',
        primitive_kind='', csg_json='', parameters_json='{}',
        provenance_id='shape-2',
        # _quadric_matrix (shape_analysis) expects a FLAT 16-number
        # row-major list, not the nested 4x4 cone_quadric_matrix()
        # returns.
        quadric_matrix_json=json.dumps([v for row in Q for v in row]),
        bounds_json=json.dumps(
            _quadric_bounds_json(axis, center, height / 2.0, bound_cap)),
        notes=f'{extra_notes} — equation (derived LaTeX display): '
              f'${latex}$'), Q


def _pot_core_dimensions(pot):
    """The pot's derived geometry (clamped thickness, wall z-range,
    inner/outer radii at the wall's bottom/top) — everything BOTH
    pot_shape_from_definition (wall/bottom) and soil_modify's
    soil_shape_from_definition (soil, which must sit exactly on the
    same floor and never poke past the same inner wall) need. A single
    source for this so the two can never compute a different floor/
    radius for what is physically the same interior."""
    from aquaponics.pot_basis import (
        MIN_BASE_THICKNESS_MM, MIN_WALL_THICKNESS_MM,
    )
    H = _f(pot, 'height_mm', 250.0) / 10.0
    base_r = _f(pot, 'outer_base_diameter_mm', 200.0) / 20.0   # dia→r, mm→cm
    top_r = _f(pot, 'outer_top_diameter_mm', 200.0) / 20.0
    # Scan-region sizing ONLY (see _quadric_bounds_json) — kept TIGHT
    # (no padding, matching how the old primitive-family bounds worked:
    # rad = max(base_r, top_r), exactly). A thin wall (~mm) is a small
    # fraction of the pot's own radius; padding this out further starves
    # _grid_properties' fixed grid-cell count and can silently zero out
    # the reported volume (found live: 0.0 cm³ with a 3x+5cm pad, fixed
    # by using the exact radius).
    xy_cap = max(base_r, top_r)

    wall_th_mm_raw = _f(pot, 'wall_thickness_mm', 8.0)
    base_th_mm_raw = _f(pot, 'base_thickness_mm', 12.0)
    wall_clamped = wall_th_mm_raw < MIN_WALL_THICKNESS_MM
    base_clamped = base_th_mm_raw < MIN_BASE_THICKNESS_MM
    wall_th = max(MIN_WALL_THICKNESS_MM, wall_th_mm_raw) / 10.0
    base_th = max(MIN_BASE_THICKNESS_MM, base_th_mm_raw) / 10.0

    def outer_radius_at(z):
        frac = (z + H / 2.0) / H if H > 1e-9 else 0.0
        return base_r + (top_r - base_r) * frac

    wall_height = max(0.01, H - base_th)
    wall_bottom_z = -H / 2.0 + base_th
    wall_center_z = wall_bottom_z + wall_height / 2.0
    wall_bottom_outer_r = outer_radius_at(wall_bottom_z)
    wall_top_outer_r = top_r
    wall_bottom_inner_r = max(0.01, wall_bottom_outer_r - wall_th)
    wall_top_inner_r = max(0.01, wall_top_outer_r - wall_th)

    return {
        'H': H, 'base_r': base_r, 'top_r': top_r, 'xy_cap': xy_cap,
        'wall_th_mm_raw': wall_th_mm_raw, 'base_th_mm_raw': base_th_mm_raw,
        'wall_clamped': wall_clamped, 'base_clamped': base_clamped,
        'wall_th': wall_th, 'base_th': base_th,
        'outer_radius_at': outer_radius_at,
        'wall_height': wall_height, 'wall_bottom_z': wall_bottom_z,
        'wall_center_z': wall_center_z,
        'wall_bottom_outer_r': wall_bottom_outer_r,
        'wall_top_outer_r': wall_top_outer_r,
        'wall_bottom_inner_r': wall_bottom_inner_r,
        'wall_top_inner_r': wall_top_inner_r,
    }


def pot_shape_from_definition(manager, pot_name, persist=True):
    """Build a math-defined HOLLOW pot from an aqp-1 PotDefinition +
    PotHoles. mm → cm. Carries the gravity validity so callers can
    refuse an invalid geometry.

    Dustin 2026-07-13's model, TWO rounds of feedback deep:
    (1) the SIDE wall is the volume BETWEEN two concentric tapered
    surfaces (`wall-outer`/`wall-inner`), the BOTTOM its own solid
    slab (`bottom-slab`) — two independently-thick, independently-
    derived parts, not one solid block; each drainage hole is a SHORT
    cylinder clearing only the wall thickness on the side it sits
    (not a full-diameter bore through the pot's own axis).
    (2) the wall should render as ONE INTEGRATED solid, not two
    separate floating surfaces, and each hole should visibly SUBTRACT
    from it (a real opening, not a marker rod poking through a solid
    wall).
    (3) "leverage matrix equations ... to form volumetric shapes":
    every surface here (wall-outer, wall-inner, bottom, each hole) is
    DEFINED by an actual quadric matrix equation
    (`shape_geometry.cone_quadric_matrix` — a frustum's lateral
    surface IS a bounded slice of a cone quadric; a straight-walled
    hole IS the degenerate cylinder case of the same formula) —
    that's the SOURCE OF TRUTH, persisted as its own `{name}-eq`
    MathShapeDefinition row (family='quadric') with a human-readable
    LaTeX form in `notes` as a DERIVED DISPLAY (not authoritative —
    read directly off the same inputs, never re-derived from Q).
    Every renderable/CSG-bookkeeping number below (radii, the combined
    wall mesh's params) is DERIVED by evaluating that equation
    (`radius_at_z`), not independently specified.

    `wall_thickness_mm`/`base_thickness_mm`/each hole's `diameter_mm`
    are CLAMPED to the buildable physical minimums
    (MIN_WALL_THICKNESS_MM/MIN_BASE_THICKNESS_MM/MIN_HOLE_DIAMETER_MM
    in aquaponics.pot_basis) so a too-thin pot still derives a real
    shape instead of a degenerate/negative-radius one; validate_pot
    flags the underlying value as a finding so a clamp is never
    silent (knobs-and-suggestions)."""
    pot = _pot_named(manager, pot_name)
    if pot is None:
        return {'ok': False,
                'error': f"no PotDefinition named '{pot_name}'"}
    from aquaponics.custom.pot_geometry import validate_pot
    from aquaponics.pot_basis import MIN_HOLE_DIAMETER_MM
    validity = validate_pot(manager, pot_name)

    dims = _pot_core_dimensions(pot)
    H, base_r, top_r, xy_cap = dims['H'], dims['base_r'], dims['top_r'], dims['xy_cap']
    wall_th_mm_raw, base_th_mm_raw = dims['wall_th_mm_raw'], dims['base_th_mm_raw']
    wall_clamped, base_clamped = dims['wall_clamped'], dims['base_clamped']
    wall_th, base_th = dims['wall_th'], dims['base_th']
    outer_radius_at = dims['outer_radius_at']
    wall_height = dims['wall_height']
    wall_bottom_z, wall_center_z = dims['wall_bottom_z'], dims['wall_center_z']
    wall_bottom_outer_r = dims['wall_bottom_outer_r']
    wall_top_outer_r = dims['wall_top_outer_r']
    wall_bottom_inner_r = dims['wall_bottom_inner_r']
    wall_top_inner_r = dims['wall_top_inner_r']

    wall_outer_eq_name = f'{pot_name}-wall-outer-eq'
    wall_outer_center = [0.0, 0.0, wall_center_z]
    wall_outer_row, wall_outer_Q = build_quadric_eq_row(
        wall_outer_eq_name, f'{pot_name} wall outer (equation)',
        wall_bottom_outer_r, wall_top_outer_r, wall_height, 'z',
        wall_outer_center, 'outer surface of the side wall', xy_cap)

    wall_inner_eq_name = f'{pot_name}-wall-inner-eq'
    wall_inner_row, wall_inner_Q = build_quadric_eq_row(
        wall_inner_eq_name, f'{pot_name} wall inner (equation)',
        wall_bottom_inner_r, wall_top_inner_r, wall_height, 'z',
        wall_outer_center,
        f'inner surface of the side wall, offset {wall_th_mm_raw:.1f}mm '
        f'in from the outer', xy_cap)

    bottom_center = [0.0, 0.0, -H / 2.0 + base_th / 2.0]
    bottom_eq_name = f'{pot_name}-bottom-eq'
    bottom_row, bottom_Q = build_quadric_eq_row(
        bottom_eq_name, f'{pot_name} bottom (equation)',
        base_r, wall_bottom_outer_r, base_th, 'z', bottom_center,
        f'solid base, {base_th_mm_raw:.1f}mm thick', xy_cap)

    # Renderable/CSG-bookkeeping numbers DERIVED from the equations
    # above (radius_at_z), never independently specified.
    wo_base = radius_at_z(wall_outer_Q, 'z', wall_bottom_z)
    wo_top = radius_at_z(wall_outer_Q, 'z', wall_bottom_z + wall_height)
    wi_base = radius_at_z(wall_inner_Q, 'z', wall_bottom_z)
    wi_top = radius_at_z(wall_inner_Q, 'z', wall_bottom_z + wall_height)
    bo_base = radius_at_z(bottom_Q, 'z', -H / 2.0)
    bo_top = radius_at_z(bottom_Q, 'z', -H / 2.0 + base_th)

    hole_eq_rows, hole_names, hole_diameters_clamped = [], [], []
    hole_render_specs = []
    for i, h in enumerate(_holes_of(manager, pot_name)):
        diameter_mm_raw = _f(h, 'diameter_mm', 10.0)
        hole_clamped = diameter_mm_raw < MIN_HOLE_DIAMETER_MM
        hole_diameters_clamped.append(hole_clamped)
        r_hole = max(MIN_HOLE_DIAMETER_MM, diameter_mm_raw) / 20.0
        z_hole = -H / 2.0 + _f(h, 'height_mm', 50.0) / 10.0
        r_outer_here = outer_radius_at(z_hole)
        r_inner_here = max(0.01, r_outer_here - wall_th)
        mid_r = (r_outer_here + r_inner_here) / 2.0
        axis, sign = _axis_and_sign_for_azimuth(_f(h, 'azimuth_deg', 0.0))
        # Capped so the bore can NEVER reach past the pot's own central
        # axis to the opposite side, regardless of how large
        # wall_thickness_mm is set to (there's no upper-bound knob on
        # it — this is the physical backstop, not just the "clears the
        # wall" length). The bore is centered at ±mid_r along its axis;
        # keeping half-length under 0.8×mid_r leaves a real margin
        # before the near edge could reach the axis at mid_r=0.
        hole_length = min(wall_th + HOLE_LENGTH_MARGIN_CM, mid_r * 1.6)
        hole_center = [sign * mid_r if axis == 'x' else 0.0,
                       sign * mid_r if axis == 'y' else 0.0,
                       round(z_hole, 4)]
        eq_name = f'{pot_name}-hole-{i}-eq'
        # Tight, hole-scale bound (NOT the pot-scale xy_cap) — a hole's
        # own radius is ~mm, so scanning it against the whole pot's
        # extent would starve _grid_properties the same way an
        # oversized wall bound zeroed out the pot's volume (see xy_cap
        # above).
        hole_bound_cap = mid_r + r_hole * 4.0 + 0.5
        hole_row, hole_Q = build_quadric_eq_row(
            eq_name, f'{pot_name} {getattr(h, "kind", "")} hole '
            f'{i} (equation)', r_hole, r_hole, hole_length, axis,
            hole_center,
            f"aqp-1 {getattr(h, 'kind', '')} hole "
            f"'{getattr(h, 'name', '')}' — bores only through the wall "
            f"thickness on its own side", hole_bound_cap)
        hole_eq_rows.append(hole_row)
        hn = f'{pot_name}-hole-{i}'
        hole_names.append(hn)
        r_derived = radius_at_z(hole_Q, axis, hole_center[_AXIS_INDEX[axis]])
        hole_render_specs.append({
            'name': hn, 'radius': round(r_derived, 4),
            'height': round(hole_length, 4), 'axis': axis,
            'center': hole_center,
            'notes': hole_row.notes})

    # Renderable primitives — DERIVED from the equations above, not
    # independently specified. Holes stay individual 'cylinder'
    # primitives (real analytic volume, real mesh, visible bore
    # lining through the wall's cut opening); the wall is ONE combined
    # 'hollow_frustum' mesh (Dustin: "integrated ... into a single
    # solid shape") with those same hole specs cut into it — see
    # shape_geometry.hollow_frustum_shell_mesh.
    hole_rows = [_ShapeRow(
        name=spec['name'], display_name=spec['name'], family='primitive',
        primitive_kind='cylinder', quadric_matrix_json='', csg_json='',
        bounds_json='', provenance_id='shape-2', notes=spec['notes'],
        parameters_json=json.dumps({
            'radius': spec['radius'], 'height': spec['height'],
            'axis': spec['axis'], 'center': spec['center'],
            # A proper CLOSED solid — Dustin 2026-07-13 round 3: "the
            # cylinders should not be hollow, they should be defined
            # volumes like the other shapes." Same `holes` spec (radius/
            # height/axis/center) is what the wall mesh's cut-test uses
            # to remove material — capping this render copy doesn't
            # change WHAT gets subtracted, only that the marker for it
            # reads as a real solid, not an open tube.
            'cap_base': True, 'cap_top': True}))
        for spec in hole_render_specs]

    wall_render_name = f'{pot_name}-wall-shell-mesh'
    wall_render = _ShapeRow(
        name=wall_render_name, display_name=f'{pot_name} wall (render mesh)',
        family='primitive', primitive_kind='hollow_frustum',
        quadric_matrix_json='', csg_json='', bounds_json='',
        provenance_id='shape-2',
        notes=f'single integrated mesh derived from {wall_outer_eq_name}/'
              f'{wall_inner_eq_name}, holes cut from the same equations '
              f'as {", ".join(hole_names) or "(none)"}',
        parameters_json=json.dumps({
            'base_outer_radius': round(wo_base, 4),
            'top_outer_radius': round(wo_top, 4),
            'base_inner_radius': round(wi_base, 4),
            'top_inner_radius': round(wi_top, 4),
            'height': round(wall_height, 4), 'axis': 'z',
            'center': [0.0, 0.0, round(wall_center_z, 4)],
            'holes': [{'radius': s['radius'], 'height': s['height'],
                       'axis': s['axis'], 'center': s['center']}
                      for s in hole_render_specs]}))

    bottom_name = f'{pot_name}-bottom-slab'
    bottom = _ShapeRow(
        name=bottom_name, display_name=f'{pot_name} bottom slab',
        family='primitive', primitive_kind='frustum',
        quadric_matrix_json='', csg_json='', bounds_json='',
        notes=f'derived from {bottom_eq_name}', provenance_id='shape-2',
        parameters_json=json.dumps({
            'base_radius': round(bo_base, 4), 'top_radius': round(bo_top, 4),
            'height': round(base_th, 4), 'axis': 'z',
            'center': list(bottom_center),
            # A solid slab needs BOTH end caps to read as solid.
            'cap_base': True, 'cap_top': True}))

    # Nested CSG over the EQUATIONS themselves (each -eq row carries
    # its own bounds_json — see _quadric_bounds_json) purely for volume
    # BOOKKEEPING (shape_properties / modify_parameter's before/after
    # consequence reporting). The renderer never draws these CSG rows
    # directly (sample_surface only gives a real triangulated mesh for
    # 'primitive' family) — it draws wall-shell-mesh/bottom-slab/holes.
    wall_shell_name = f'{pot_name}-wall-shell'
    wall_shell = _ShapeRow(
        name=wall_shell_name, display_name=f'{pot_name} wall shell (net)',
        family='csg', primitive_kind='', quadric_matrix_json='',
        bounds_json='', parameters_json='{}', provenance_id='shape-2',
        notes='outer wall equation minus inner wall equation',
        csg_json=json.dumps({'op': 'difference',
                             'shapes': [wall_outer_eq_name, wall_inner_eq_name]}))
    solid_name = f'{pot_name}-solid'
    solid = _ShapeRow(
        name=solid_name, display_name=f'{pot_name} solid (no bores)',
        family='csg', primitive_kind='', quadric_matrix_json='',
        bounds_json='', parameters_json='{}', provenance_id='shape-2',
        notes='wall shell + bottom equation, before drainage holes',
        csg_json=json.dumps({'op': 'union',
                             'shapes': [wall_shell_name, bottom_eq_name]}))
    csg_name = f'{pot_name}-shape'
    hole_eq_names = [f'{pot_name}-hole-{i}-eq'
                     for i in range(len(hole_names))]
    csg = _ShapeRow(
        name=csg_name, display_name=f'{pot_name} (math shape)', family='csg',
        primitive_kind='', quadric_matrix_json='', bounds_json='',
        parameters_json='{}', provenance_id='shape-2',
        notes=f'wall shell + bottom, minus {len(hole_names)} drainage '
              f'hole equations; from aqp-1 {pot_name}',
        csg_json=json.dumps({'op': 'difference',
                             'shapes': [solid_name] + hole_eq_names}))

    if persist:
        _insert_rows(manager, [wall_outer_row, wall_inner_row, bottom_row]
                     + hole_eq_rows + hole_rows
                     + [wall_render, bottom, wall_shell, solid, csg])

    pot_vol = _volume(manager, csg_name) if persist else None

    return {
        'ok': True, 'pot': pot_name, 'shapeName': csg_name,
        'wallOuterEquation': wall_outer_eq_name,
        'wallInnerEquation': wall_inner_eq_name,
        'bottomEquation': bottom_eq_name,
        'wallShape': wall_render_name, 'bottomShape': bottom_name,
        'holeShapes': hole_names,
        'gravityValid': bool(validity.get('valid')),
        'gravityFindings': validity.get('findings', []),
        'wallThicknessMm': round(wall_th * 10.0, 2),
        'baseThicknessMm': round(base_th * 10.0, 2),
        'wallThicknessClamped': wall_clamped,
        'baseThicknessClamped': base_clamped,
        'holeDiametersClamped': hole_diameters_clamped,
        'potMaterialVolumeCm3': round(pot_vol, 2) if pot_vol is not None
        else None,
        # Phase 5 — read straight off the pot row so on_post_from_pot
        # can pick the opaque-vs-'-transparent' style variant without
        # a second lookup.
        'wallTransparent': bool(getattr(pot, 'wall_transparent', False)),
        'soilTransparent': bool(getattr(pot, 'soil_transparent', False)),
        'note': 'aqp-1 pot geometry is DEFINED by quadric matrix '
                'equations (wall-outer/wall-inner/bottom/each hole, '
                'each a bounded cone-quadric — see the *Equation shape '
                'names, with a derived LaTeX form in their own notes '
                'field): a source-of-truth equation, not a shape a '
                'human hand-picked. The wall renders as ONE integrated '
                'mesh (wallShape) with holes actually cut through it, '
                'derived by evaluating those equations, not specified '
                'independently. mm converted to cm. wall/base thickness '
                'and hole diameters are clamped to the buildable minimum '
                'when the pot specifies less (*Clamped flags say when '
                'that happened — see validate_pot for the finding). '
                'Gravity validity carried from validate_pot — it still '
                'gates modification.'}


def modify_pot_hole(manager, pot_name, param, value, hole_index=0):
    """Modify a derived pot hole's radius/height, GATED by the aqp-1
    gravity invariant: if the change makes the pot fail validate_pot the
    modification is REFUSED, naming the offending knob. (The aqp-1 pot
    itself is edited via CRUDE; here we gate the geometric change.)

    Targets `{pot}-hole-{i}` — the RENDER-only cylinder primitive
    (family='primitive'; modify_parameter only supports that family).
    Since 2026-07-13's quadric redesign the pot's authoritative volume
    is computed from `{pot}-hole-{i}-eq` (family='quadric', a separate
    row this does NOT touch), so a change here is cosmetic-preview
    only — it won't show up in modify_parameter's dependentPots volume
    consequence, and re-deriving via from-pot overwrites it. Matches
    this function's existing "preview only, not the primary edit path"
    contract (the primary path is CRUDE PUT on PotHole, then re-POST
    from-pot)."""
    from aquaponics.custom.pot_geometry import validate_pot
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
