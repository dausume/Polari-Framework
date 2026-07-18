"""
@cross-cutting
@module aquaponics.plant_skeleton
@tags @xc:bindings, @xc:render-3d

Plant-growth-sim phase 1, the GEOMETRY layer (2026-07-15). Dustin,
verbatim: "when making the plants we should account for simulations
using something like animation bones, interconnected vectors that
define the direction of the roots and stem and canopy. The root and
stem and organ definitions... wrap those vector based definitions so
we can use the vectors as a math foundation to ensure the mapping
between the equations defining plants in simulation actually make
sense in reality and so we can do the reverse mapping from reality to
simulation as needed."

A Bone is one vector: a start point, an end point (both mm, in the
SAME pot-local coordinate frame aquaponics.hydraulics.water_slice_mesh
already uses — z vertical through the pot's own center, reused via
mathshapes.shape_modify._pot_core_dimensions so a skeleton drops into
the existing pot/soil/water rendering with no extra transform), a
start/end radius (the taper, now PER BONE rather than one global
curve), and a parent — a real graph, not a flat scalar profile. This
is deliberately a plain data structure (points + radii + parentage),
the same shape a 3-D root/plant SCAN would produce — the intent is
that a future "fit constants from a real scan" function can compare a
real bone graph to a generated one and adjust plant_growth_normalized
rows to match, i.e. the reverse mapping Dustin asked for. That fitting
function is NOT built here — this module only builds the FORWARD
direction (constants -> bones) — but the representation is chosen so
the reverse direction is a well-posed problem later, not an
afterthought bolted onto a scalar model.

plant_growth_normalized.py answers "how big/far along is each part
right now" (the shape equations) and "how fast does each part reach
that" (the growth equations, per Dustin's explicit shape/growth
equation split) — this module is what actually WALKS a recursive
branching structure using those two equation families, one call per
bone, so the vectors it emits are real consequences of the
constrained-limits math, not decorative randomness layered on top.

Two independent recursive walks off ONE shared core point (the seed
origin, at the pot's interior floor): roots (gravitropic, walks
DOWNWARD) and the stem/canopy (negatively gravitropic, walks UPWARD).
`RootSystemModel.pattern` and `OrganModel.arrangement` are the
existing per-species knobs that shape each walk — reused unchanged,
not reinvented, as the generator's branching-behavior config.

Reproducible: every random draw goes through `random.Random(seed)`
seeded from PotPlanting.random_seed — the SAME pot renders the SAME
skeleton every time until replanted, per Dustin's own requirement.

Hard caps (max_generations, max_bones) are the COMPUTATIONAL safety
valve — distinct from plant_growth_normalized.SANE_MAX_LINEAR_MM
(a PHYSICAL dimension cap). A species with a huge free-soil envelope
could otherwise recurse into an enormous bone count; hitting either
cap is reported in the response, never silently truncated.

Phase 13 (2026-07-15): each bone now carries a real `shapePrimitive`
(OrganModel.shape_primitive — lamina/ellipsoid/cone/cylinder — was
already computed by current_canopy_profile but discarded here before
this phase). Root/stem/branch AXIS bones are always explicitly
'cylinder' (a real physical taper); terminal organ bones (leaf/flower/
fruit) get their species' real shape instead of the same generic
tapered-cylinder stand-in every organ used to render as.

@consumers
  - the plant-viz SimSpace scene (mathshapes.pot_scene.
    ensure_pot_plant_viz_scene) + PlantSkeletonGeometryLibraryService
    (polari-platform-angular), which branches on shapePrimitive to
    build real per-organ geometry instead of uniform cylinders
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 6, phase 13
"""

import random

from aquaponics.plant_growth_normalized import (
    current_canopy_profile, current_root_profile, organ_part_name,
    _named, _rows, _f,
)

#: Computational safety valve — a hard ceiling on branch recursion
#: depth, independent of any species' declared size.
DEFAULT_MAX_GENERATIONS = 6

#: Computational safety valve — a hard ceiling on total bone count
#: (roots + stem/canopy + organ attachments combined).
DEFAULT_MAX_BONES = 500

#: Branching behavior per RootSystemModel.pattern — (num_children,
#: child_length_fraction, spread_angle_deg, downward_bias). downward_
#: bias in [0,1]: 1.0 = child direction stays close to straight down,
#: lower = spreads more horizontally.
ROOT_PATTERN_KNOBS = {
    # children=1 makes the PRIMARY axis a real, mostly-unbranched
    # taproot (correct — that's the defining trait) — but real taproot
    # systems (peppers included) also put out finer LATERAL roots off
    # that main axis as they mature, they aren't a single bare line
    # end to end. Dustin, 2026-07-16, after phase 14: "is the behavior
    # of only a single root straight down really accurate?" — no, this
    # was a real gap: with children=1, _walk_root's n_children could
    # never be anything but 1 (the "reduce by 1 sometimes" mechanic
    # bottoms out at max(1, 0)=1), so a taproot pattern was
    # STRUCTURALLY forbidden from ever branching. lateralChance/
    # lateralLengthFrac/lateralAngleDeg (new) give it real, thinner,
    # more-horizontal side roots at a real per-generation probability,
    # without turning it into a fibrous system (children still caps
    # the PRIMARY axis at 1; laterals are an explicit bonus branch).
    'taproot':     {'children': 1, 'lengthFrac': 0.55, 'angleDeg': 18,
                    'downwardBias': 0.9, 'lateralChance': 0.55,
                    'lateralLengthFrac': 0.35, 'lateralAngleDeg': 60,
                    'lateralDownwardBias': 0.35},
    'fibrous':     {'children': 3, 'lengthFrac': 0.6, 'angleDeg': 45,
                    'downwardBias': 0.55},
    'spreading':   {'children': 3, 'lengthFrac': 0.65, 'angleDeg': 65,
                    'downwardBias': 0.25},
    'rhizomatous': {'children': 2, 'lengthFrac': 0.7, 'angleDeg': 75,
                    'downwardBias': 0.15},
}

#: Branching behavior per OrganModel.arrangement, for stem/branch
#: axes — (num_children, child_length_fraction, spread_angle_deg).
CANOPY_ARRANGEMENT_KNOBS = {
    'rosette':  {'children': 5, 'lengthFrac': 0.15, 'angleDeg': 70},
    'basal':    {'children': 4, 'lengthFrac': 0.2, 'angleDeg': 60},
    'alternate': {'children': 2, 'lengthFrac': 0.65, 'angleDeg': 35},
    'opposite': {'children': 2, 'lengthFrac': 0.65, 'angleDeg': 30},
    'whorled':  {'children': 4, 'lengthFrac': 0.6, 'angleDeg': 40},
    'vining':   {'children': 1, 'lengthFrac': 0.8, 'angleDeg': 15},
}


def _rotate(direction, axis, angle_deg):
    """Rotates a 3-vector `direction` about `axis` by angle_deg
    (Rodrigues' rotation formula) — used to fan child bones out from
    a parent direction by a spread angle."""
    import math
    theta = math.radians(angle_deg)
    ax, ay, az = axis
    dx, dy, dz = direction
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    dot = ax * dx + ay * dy + az * dz
    cross = (ay * dz - az * dy, az * dx - ax * dz, ax * dy - ay * dx)
    return (
        dx * cos_t + cross[0] * sin_t + ax * dot * (1 - cos_t),
        dy * cos_t + cross[1] * sin_t + ay * dot * (1 - cos_t),
        dz * cos_t + cross[2] * sin_t + az * dot * (1 - cos_t),
    )


def _normalize(v):
    import math
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _perpendicular(v):
    """Any unit vector perpendicular to v — used as a rotation axis to
    fan children out around the parent direction."""
    v = _normalize(v)
    ref = (1.0, 0.0, 0.0) if abs(v[0]) < 0.9 else (0.0, 1.0, 0.0)
    cx = v[1] * ref[2] - v[2] * ref[1]
    cy = v[2] * ref[0] - v[0] * ref[2]
    cz = v[0] * ref[1] - v[1] * ref[0]
    return _normalize((cx, cy, cz))


def _pot_planting_geometry_mm(manager, pot_name):
    """The seed origin (mm, pot-local frame) + the REAL physical bounds
    a root system can occupy without passing through solid pot walls.

    Phase 14 (2026-07-16) correction — Dustin: "growing according to
    an ideal conditions with infinite ground scenario rather than a
    real constrained pot scenario... those seem to be straight down
    'tap roots' at the bottom". Two real, independent bugs, confirmed
    by direct API inspection before fixing (not guessed): (1) the seed
    origin was the pot's ABSOLUTE floor (-H/2, ignoring base_thickness
    entirely — literally inside the solid base slab), so canopy had to
    visually tunnel through the full water+soil column before
    "emerging", and root had nowhere further down to go without
    exiting the container; (2) nothing ever clamped root depth/spread
    to the pot's actual physical interior — `constrained_limits`'s
    dwarfFactor is a BIOLOGICAL root-bound estimate (dense root BALL
    volume vs container volume), not a geometric footprint check, so a
    sparse/wide free-soil root system (e.g. sweet-basil: dwarfFactor
    1.0, i.e. "not confined at all" by that metric) can still have a
    spread/depth envelope far larger than the container — confirmed
    live: basil's un-clamped root wanted 120mm spread radius against
    this pot's own ~92mm inner radius.

    Origin is now the SOIL SURFACE (interior floor + reservoir_height
    + soil_fill_height) — canopy starts right at ground level, root's
    downward budget is exactly the real water+soil column beneath it.
    maxRootDepthMm / maxRootRadiusMm are HARD geometric ceilings
    (never exceeded regardless of what the growth/dwarf math wants),
    enforced by _walk_root; canopy is deliberately NOT radius-clamped
    — above-ground foliage genuinely can and does spread wider than
    its own pot in reality, that part of the shape was never wrong."""
    pot = _named(manager, 'PotDefinition', pot_name)
    if pot is None:
        return None
    from mathshapes.shape_modify import _pot_core_dimensions
    dims = _pot_core_dimensions(pot)
    interior_floor_z_mm = dims['wall_bottom_z'] * 10.0
    usable_depth_mm = max(0.0, _f(pot, 'reservoir_height_mm', 40.0)
                          + _f(pot, 'soil_fill_height_mm', 180.0))
    soil_surface_z_mm = interior_floor_z_mm + usable_depth_mm
    max_root_radius_mm = dims['wall_bottom_inner_r'] * 10.0
    return {
        'coreMm': (0.0, 0.0, soil_surface_z_mm),
        'maxRootDepthMm': usable_depth_mm,
        'maxRootRadiusMm': max_root_radius_mm,
    }


class _BoneBuilder:
    """Accumulates bones + enforces the two hard caps while a
    recursive walk runs."""

    def __init__(self, max_generations, max_bones):
        self.bones = []
        self.max_generations = max_generations
        self.max_bones = max_bones
        self.capped_by_generations = False
        self.capped_by_bone_count = False
        self._next_id = 0

    def add(self, parent_id, part, organ, generation, start_mm, end_mm,
           start_radius_mm, end_radius_mm, shape_primitive='cylinder'):
        if len(self.bones) >= self.max_bones:
            self.capped_by_bone_count = True
            return None
        bone_id = f'b{self._next_id}'
        self._next_id += 1
        self.bones.append({
            'id': bone_id, 'parentId': parent_id, 'part': part,
            'organ': organ, 'generation': generation,
            'startPointMm': [round(c, 2) for c in start_mm],
            'endPointMm': [round(c, 2) for c in end_mm],
            'startRadiusMm': round(start_radius_mm, 3),
            'endRadiusMm': round(end_radius_mm, 3),
            # Real per-organ shape (OrganModel.shape_primitive:
            # lamina/ellipsoid/cone/cylinder), NOT a decorative label —
            # the frontend geometry builder branches on this field
            # instead of rendering every bone as a generic tapered
            # cylinder. Root/stem/branch AXIS bones are always
            # 'cylinder' explicitly (a real physical taper), so this
            # field is never missing/None — one code path on the
            # frontend, no special-casing "axis bones don't have one".
            'shapePrimitive': shape_primitive,
        })
        return bone_id

    def generation_capped(self, generation):
        if generation >= self.max_generations:
            self.capped_by_generations = True
            return True
        return False


def _clip_length_to_container(origin_mm, direction, remaining_length_mm,
                              max_radius_mm, floor_z_mm):
    """How much of this bone (if any) fits inside the pot's real
    physical interior before hitting the wall (radius) or the floor —
    a HARD geometric ceiling, independent of whatever the growth/dwarf
    math wanted. Returns (clipped_length_mm, was_clipped). A length of
    0 means the origin itself is already at/past a boundary (stop
    immediately, draw nothing further from here)."""
    import math
    ox, oy, oz = origin_mm
    dx, dy, dz = direction
    clipped = remaining_length_mm

    # Radial (wall) clip — solve |xy(t)| = max_radius_mm for the
    # smallest t>0 where the path crosses the wall, treating the
    # origin as already-inside (c = ox^2+oy^2-max_radius_mm^2 <= 0 in
    # the normal case; if the origin itself is already outside, clip
    # to 0 rather than let the bone travel further out).
    a = dx * dx + dy * dy
    c = ox * ox + oy * oy - max_radius_mm * max_radius_mm
    if c > 0:
        return 0.0, True
    if a > 1e-12:
        b = 2.0 * (ox * dx + oy * dy)
        disc = b * b - 4.0 * a * c
        if disc >= 0.0:
            t_wall = (-b + math.sqrt(disc)) / (2.0 * a)
            if 0.0 <= t_wall < clipped:
                clipped = t_wall

    # Floor clip — a straight z-distance check (roots grow generally
    # downward; dz is negative).
    if dz < -1e-9:
        t_floor = (floor_z_mm - oz) / dz
        if 0.0 <= t_floor < clipped:
            clipped = t_floor
    elif oz <= floor_z_mm:
        clipped = 0.0

    clipped = max(0.0, clipped)
    return clipped, clipped < remaining_length_mm - 1e-6


def _walk_root(builder, rng, parent_id, generation, origin_mm, direction,
               remaining_length_mm, start_radius_mm, taper_samples,
               distance_so_far_mm, pattern_knobs, max_radius_mm,
               floor_z_mm):
    if remaining_length_mm <= 0.5 or start_radius_mm <= 0.01:
        return
    if builder.generation_capped(generation):
        return

    remaining_length_mm, hit_boundary = _clip_length_to_container(
        origin_mm, direction, remaining_length_mm, max_radius_mm,
        floor_z_mm)
    if remaining_length_mm <= 0.5:
        return

    end_mm = tuple(o + d * remaining_length_mm
                   for o, d in zip(origin_mm, direction))
    distance_at_end = distance_so_far_mm + remaining_length_mm
    end_radius_mm = _sample_taper(taper_samples, distance_at_end)
    bone_id = builder.add(parent_id, 'root', None, generation,
                          origin_mm, end_mm, start_radius_mm,
                          end_radius_mm)
    if bone_id is None:
        return
    # A bone that got clipped by the wall/floor has reached the real
    # physical edge of the container — real roots deflect/stop there
    # rather than punch through solid material, so no children spawn
    # from this bone.
    if hit_boundary:
        return

    knobs = pattern_knobs
    n_children = knobs['children'] if rng.random() < 0.85 else max(
        1, knobs['children'] - 1)
    perp = _perpendicular(direction)
    down = (0.0, 0.0, -1.0)
    for i in range(n_children):
        spread = knobs['angleDeg'] * (0.6 + 0.4 * rng.random())
        azimuth = (360.0 / max(1, n_children)) * i + rng.uniform(-15, 15)
        child_dir = _rotate(direction, perp, spread)
        child_dir = _rotate(child_dir, direction, azimuth)
        # Blend toward straight-down by downwardBias, then renormalize —
        # gravitropism, stated as a simple directional blend.
        bias = knobs['downwardBias']
        blended = tuple(c * (1 - bias) + d * bias
                        for c, d in zip(child_dir, down))
        child_dir = _normalize(blended)
        child_length = remaining_length_mm * knobs['lengthFrac'] \
            * (0.75 + 0.5 * rng.random())
        _walk_root(builder, rng, bone_id, generation + 1, end_mm,
                  child_dir, child_length, end_radius_mm, taper_samples,
                  distance_at_end, pattern_knobs, max_radius_mm,
                  floor_z_mm)

    # Lateral roots — a real branch OFF the primary axis (taproot's
    # own children=1 above is the tap continuing, not a side root).
    # No-op for patterns without lateralChance (fibrous/spreading/
    # rhizomatous already branch via children, they don't need this).
    # Recurses through the SAME _walk_root, so a lateral can spawn its
    # own finer sub-laterals too — real root systems do this.
    lateral_chance = knobs.get('lateralChance', 0.0)
    if lateral_chance > 0.0 and rng.random() < lateral_chance:
        spread = knobs['lateralAngleDeg'] * (0.7 + 0.6 * rng.random())
        azimuth = rng.uniform(0, 360)
        lateral_dir = _rotate(direction, perp, spread)
        lateral_dir = _rotate(lateral_dir, direction, azimuth)
        bias = knobs['lateralDownwardBias']
        blended = tuple(c * (1 - bias) + d * bias
                        for c, d in zip(lateral_dir, down))
        lateral_dir = _normalize(blended)
        lateral_length = remaining_length_mm * knobs['lateralLengthFrac'] \
            * (0.75 + 0.5 * rng.random())
        # A lateral is a thinner offshoot, not a full-radius sibling
        # of the primary axis.
        lateral_start_radius = end_radius_mm * 0.6
        _walk_root(builder, rng, bone_id, generation + 1, end_mm,
                  lateral_dir, lateral_length, lateral_start_radius,
                  taper_samples, distance_at_end, pattern_knobs,
                  max_radius_mm, floor_z_mm)


def _sample_taper(taper_samples, distance_mm):
    if not taper_samples:
        return 0.2
    if distance_mm <= taper_samples[0]['distanceMm']:
        return taper_samples[0]['diameterMm'] / 2.0
    for a, b in zip(taper_samples, taper_samples[1:]):
        if a['distanceMm'] <= distance_mm <= b['distanceMm']:
            span = b['distanceMm'] - a['distanceMm']
            t = (distance_mm - a['distanceMm']) / span if span > 1e-9 else 0
            diam = a['diameterMm'] + t * (b['diameterMm'] - a['diameterMm'])
            return diam / 2.0
    return taper_samples[-1]['diameterMm'] / 2.0


def _walk_canopy(builder, rng, parent_id, generation, origin_mm,
                 direction, remaining_length_mm, start_radius_mm,
                 end_radius_mm, arrangement_knobs, terminal_organs,
                 part_name):
    if remaining_length_mm <= 0.5 or start_radius_mm <= 0.01:
        return
    if builder.generation_capped(generation):
        return

    end_mm = tuple(o + d * remaining_length_mm
                   for o, d in zip(origin_mm, direction))
    bone_id = builder.add(parent_id, part_name, None, generation,
                          origin_mm, end_mm, start_radius_mm,
                          end_radius_mm)
    if bone_id is None:
        return

    # Terminal organ attachments (leaves/flowers/fruit) along this
    # bone — a real branching chain for stem/branch, but leaves etc.
    # are single attachments, not further-branching axes. terminal_
    # organs is EVERY non-axis organ (not filtered by part_name — a
    # leaf's OWN growth-tracking part is 'leaf', never 'stem', so
    # matching by part_name would never find it), each already
    # carrying a currentCount PRE-DIVIDED by the estimated axis bone
    # count (generate_skeleton) so the total attached across the
    # whole axis approximates the real plant-wide count instead of
    # placing the full count at every single bone.
    for organ in terminal_organs:
        _attach_organs(builder, rng, bone_id, generation, origin_mm,
                       end_mm, organ)

    knobs = arrangement_knobs
    n_children = knobs['children']
    perp = _perpendicular(direction)
    up = (0.0, 0.0, 1.0)
    for i in range(n_children):
        spread = knobs['angleDeg'] * (0.6 + 0.4 * rng.random())
        azimuth = (360.0 / max(1, n_children)) * i + rng.uniform(-15, 15)
        child_dir = _rotate(direction, perp, spread)
        child_dir = _rotate(child_dir, direction, azimuth)
        blended = tuple(c * 0.7 + d * 0.3 for c, d in zip(child_dir, up))
        child_dir = _normalize(blended)
        child_length = remaining_length_mm * knobs['lengthFrac'] \
            * (0.75 + 0.5 * rng.random())
        child_end_radius = end_radius_mm * 0.6
        _walk_canopy(builder, rng, bone_id, generation + 1, end_mm,
                    child_dir, child_length, end_radius_mm,
                    child_end_radius, arrangement_knobs, terminal_organs,
                    part_name)


def _chain_reach_factor(length_frac, max_generations):
    """How much a SINGLE-CHAIN axis's cumulative reach (its own bone,
    THEN a child continuing from its tip by length_frac, THEN a
    grandchild continuing from THAT tip by length_frac again, ...)
    exceeds any one generation's own stated length — a geometric
    series (1 + f + f^2 + ... + f^max_generations). Every generation
    STARTS FROM THE PREVIOUS ONE'S TIP (see _walk_root), so a chain
    with children==1 (taproot) genuinely reaches this many multiples
    of its first bone's length, not just that first bone's length —
    used to size gen-0's OWN length so the WHOLE chain's total reach
    lands on the intended depth budget, instead of gen-0 alone
    consuming it and leaving zero room for any child/lateral (Dustin,
    2026-07-16: "is the behavior of only a single root straight down
    really accurate?" — root cause was gen-0 eating the entire depth
    cap in one bone, starving every generation after it to a clipped
    length of 0 at the floor before any branch could exist)."""
    total, term = 0.0, 1.0
    for _ in range(max_generations + 1):
        total += term
        term *= length_frac
    return max(total, 1e-6)


def _estimate_axis_bone_count(knobs, max_generations):
    """Geometric-series estimate of how many bones ONE axis walk
    (_walk_canopy's fixed knobs['children'] per generation, no
    randomization of branch COUNT) will produce by max_generations —
    used only to pre-divide terminal-organ counts across the axis, not
    to predict the exact bone list (remaining_length_mm / max_bones
    can still cut a real walk shorter; underestimating here just means
    a few more organs land on the last bones than a perfect split
    would, never a crash)."""
    total, per_generation = 1, 1
    for _ in range(max_generations):
        per_generation *= knobs['children']
        total += per_generation
    return max(1, total)


def _attach_organs(builder, rng, parent_bone_id, generation, bone_start_mm,
                   bone_end_mm, organ):
    """count-many short terminal bones (leaves/flowers/fruit) placed
    along a stem/branch bone, per organ_geometry (plant_morphology)'s
    own current-scaled dimensions — reused, not recomputed here."""
    current_count = int(organ.get('currentCount', 0))
    if current_count <= 0:
        return
    half_length_mm = max(organ.get('currentLengthMm', 20.0), 1.0) / 2.0
    for i in range(current_count):
        t = (i + 0.5) / current_count
        base_mm = tuple(a + (b - a) * t
                        for a, b in zip(bone_start_mm, bone_end_mm))
        outward = (rng.uniform(-1, 1), rng.uniform(-1, 1),
                   rng.uniform(-0.3, 0.3))
        outward = _normalize(outward)
        tip_mm = tuple(o + d * half_length_mm * 2
                       for o, d in zip(base_mm, outward))
        builder.add(parent_bone_id, organ['part'], organ['organ'],
                   generation + 1, base_mm, tip_mm,
                   organ.get('currentWidthMm', 10.0) / 2.0, 0.5,
                   shape_primitive=organ.get('shapePrimitive', 'ellipsoid'))


def generate_skeleton(manager, planting_name,
                      max_generations=DEFAULT_MAX_GENERATIONS,
                      max_bones=DEFAULT_MAX_BONES):
    """The forward mapping: constrained_limits + current normalized
    growth (plant_growth_normalized) -> a real connected bone/vector
    graph, in the pot's own coordinate frame. Two independent
    recursive walks (root: down, canopy: up) off one shared core
    point."""
    from aquaponics.plant_growth_normalized import _named as _pn_named
    planting = _pn_named(manager, 'PotPlanting', planting_name)
    if planting is None:
        return {'ok': False,
                'error': f"no PotPlanting named '{planting_name}'"}

    pot_geometry = _pot_planting_geometry_mm(manager, planting.pot_name)
    if pot_geometry is None:
        return {'ok': False,
                'error': f"no PotDefinition named '{planting.pot_name}'"}
    core_mm = pot_geometry['coreMm']
    max_root_depth_mm = pot_geometry['maxRootDepthMm']
    max_root_radius_mm = pot_geometry['maxRootRadiusMm']
    floor_z_mm = core_mm[2] - max_root_depth_mm

    root_profile = current_root_profile(manager, planting_name)
    if not root_profile.get('ok'):
        return root_profile
    canopy_profile = current_canopy_profile(manager, planting_name)
    if not canopy_profile.get('ok'):
        return canopy_profile

    root_row = None
    for r in _rows(manager, 'RootSystemModel'):
        if getattr(r, 'plant_name', '') == planting.plant_name:
            root_row = r
            break
    pattern = getattr(root_row, 'pattern', 'fibrous') if root_row else \
        'fibrous'
    root_knobs = ROOT_PATTERN_KNOBS.get(pattern, ROOT_PATTERN_KNOBS[
        'fibrous'])

    rng = random.Random(int(planting.random_seed))
    builder = _BoneBuilder(max_generations, max_bones)

    # --- Root tree: walks DOWN from the core. root_depth_mm is hard-
    # capped to the pot's real physical usable depth (see
    # _pot_planting_geometry_mm's docstring) — the growth/dwarf math's
    # OWN depth can exceed this (a real, confirmed gap: dwarfFactor is
    # a root-BALL-vs-container-volume estimate, not a footprint check),
    # so this is an independent, always-enforced geometric ceiling, on
    # top of (not instead of) the per-bone wall/floor clip in
    # _walk_root. Reported honestly, never a silent clamp. ---
    taper_samples = root_profile['taperSamples']
    root_depth_mm = min(root_profile['currentDepthMm'], max_root_depth_mm)
    root_depth_clamped_to_container = (
        root_profile['currentDepthMm'] > max_root_depth_mm + 1e-6)
    # Single-chain patterns (taproot, children==1) reach FAR beyond any
    # one generation's own length — each generation starts at the
    # previous one's TIP, so the chain's total cumulative reach is a
    # geometric series in lengthFrac, not just gen-0's stated length
    # (see _chain_reach_factor). Feeding the full depth budget straight
    # into gen-0 left every later generation (primary continuation AND
    # lateral branches) with a clipped length of 0 at the floor — the
    # exact single-bare-line result Dustin flagged. Shrinking gen-0's
    # own length by the chain's reach factor makes the WHOLE chain's
    # total depth land on the real budget, leaving genuine room for
    # branching along the way. Multi-children patterns (fibrous/
    # spreading/rhizomatous) are NOT touched — they already branch
    # richly at every generation and this reshaping isn't needed there
    # (confirmed: basil's fibrous root already looked right).
    gen0_length_mm = root_depth_mm
    if root_knobs['children'] == 1:
        gen0_length_mm = root_depth_mm / _chain_reach_factor(
            root_knobs['lengthFrac'], max_generations)
    if root_depth_mm > 0.5:
        start_radius_mm = _sample_taper(taper_samples, 0.0)
        _walk_root(builder, rng, None, 0, core_mm, (0.0, 0.0, -1.0),
                  gen0_length_mm, start_radius_mm, taper_samples, 0.0,
                  root_knobs, max_root_radius_mm, floor_z_mm)

    # --- Canopy tree: walks UP from the core, ONE sub-tree for the
    # primary structural axis (stem/branch); leaf/flower/fruit are
    # NOT structural axes — they attach as terminal organs along every
    # bone of that one axis (organ's OWN mapped part only decides ITS
    # growth ceiling, not which axis it structurally attaches to —
    # there is exactly one axis today, so this is unambiguous). Each
    # terminal organ's currentCount is pre-divided by the axis's
    # estimated bone count so the SUM across the whole axis
    # approximates the real plant-wide count, instead of placing the
    # full count at every bone. ---
    axis_organs = [o for o in canopy_profile['organs']
                   if o['organ'] in ('stem', 'branch')]
    terminal_organs_raw = [o for o in canopy_profile['organs']
                           if o['organ'] not in ('stem', 'branch')]
    canopy_height_mm = canopy_profile['currentHeightMm']
    if axis_organs and canopy_height_mm > 0.5:
        primary = max(axis_organs, key=lambda o: o['currentLengthMm'])
        arrangement = primary.get('arrangement', 'alternate')
        canopy_knobs = CANOPY_ARRANGEMENT_KNOBS.get(
            arrangement, CANOPY_ARRANGEMENT_KNOBS['alternate'])
        axis_bone_estimate = _estimate_axis_bone_count(
            canopy_knobs, max_generations)
        terminal_organs = []
        for o in terminal_organs_raw:
            adjusted = dict(o)
            full_count = int(o.get('currentCount', 0))
            adjusted['currentCount'] = (
                max(1, round(full_count / axis_bone_estimate))
                if full_count > 0 else 0)
            terminal_organs.append(adjusted)
        start_radius_mm = max(primary['currentWidthMm'] / 2.0, 0.1)
        _walk_canopy(builder, rng, None, 0, core_mm, (0.0, 0.0, 1.0),
                    canopy_height_mm, start_radius_mm,
                    start_radius_mm * 0.5, canopy_knobs, terminal_organs,
                    primary['part'])

    return {
        'ok': True,
        'planting': planting_name,
        'pot': planting.pot_name,
        'plant': planting.plant_name,
        'randomSeed': int(planting.random_seed),
        'coreOriginMm': [round(c, 2) for c in core_mm],
        'bones': builder.bones,
        'boneCount': len(builder.bones),
        'cappedByGenerations': builder.capped_by_generations,
        'cappedByBoneCount': builder.capped_by_bone_count,
        'maxGenerations': max_generations,
        'maxBones': max_bones,
        'rootPattern': pattern,
        # Never silent — the growth/dwarf math's own root depth CAN
        # exceed the pot's real usable interior; when it does, both
        # this flag AND the per-bone wall/floor clip in _walk_root
        # (see hit_boundary) are what actually keep the rendered root
        # inside the container, not the growth math alone.
        'rootDepthClampedToContainer': root_depth_clamped_to_container,
        'maxRootDepthMm': round(max_root_depth_mm, 1),
        'maxRootRadiusMm': round(max_root_radius_mm, 1),
        'note': 'a real connected vector graph (start/end point + '
                'radius per bone, parentage explicit) in the pot\'s own '
                '(cm*10=mm, z-vertical-through-center) frame — the same '
                'representation a real root/plant scan would produce, '
                'so a future "fit constants from a scan" pass has a '
                'well-posed reverse-mapping target. Branching pattern '
                'is reproducibly random (randomSeed), sized/scaled '
                'entirely by plant_growth_normalized\'s free-soil + '
                'constrained-limits + current normalized-growth math — '
                'randomization decides the PATTERN, the growth engine '
                'decides the BUDGET.',
    }
