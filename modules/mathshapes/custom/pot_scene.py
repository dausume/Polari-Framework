"""
@cross-cutting
@module mathshapes.custom.pot_scene
@tags @xc:render-shared, @xc:render-3d, @xc:bindings

aquaponics-pot-shape phase 1 — the SimSpace side of "render the aqp-1
pot as a math-defined shape". `pot_shape_from_definition` (shape_modify)
already derives the pot's wall (ONE integrated mesh, holes cut in) +
bottom-slab + hole primitives as MathShapeDefinition rows; this module
turns THAT into a viewable 3D scene.

Design choice (not a *SimState wrapper, not a class binding): the pot
is ONE object made of several math-shape primitives (body + N holes) —
SimSpaceBindingDefinition's per-class binding model emits exactly one
SimSpaceObject per class instance, which can't express that. The scene
already has a mechanism for a curated, hand-placed set of shapes
independent of any class binding — a SimSpaceDefinition's own
`definition.freestanding` list (`freestandingOnly: true`, the same
pattern the 3D "selection space" scenes use for choice-shelf shapes).
That's what this module populates: one freestanding entry per derived
primitive, each `shapeRef` prefixed `mathshape:` so the frontend
renderer resolves it via MathShapeGeometryLibraryService (fetches
`/api/shapes/{name}/surface`) instead of the Mesh3DDefinition catalogue.

@impact-on-edit
  Ephemeral by design, same as pot_shape_from_definition's derived
  MathShapeDefinition rows: this writes directly into
  manager.objectTables['SimSpaceDefinition'], bypassing CRUDE/DB
  persistence. It does NOT survive a backend restart — re-POST
  /api/shapes/from-pot/{pot_name} to rebuild it. Deliberate: this scene
  has no source of truth beyond the pot's own PotDefinition/PotHole
  rows, so re-deriving on demand (like the shapes themselves) avoids a
  second, driftable copy of "what this pot looks like." If a scene
  needs to survive restarts un-rederived, promote it to a real CRUDE
  POST instead — flagged here for whoever hits that need.
@consumers
  - mathshapes.shape_api (POST /api/shapes/from-pot/{pot_name})
@see /AQUAPONICS_POT_SHAPE_PLAN.md (phase 1)
"""

import json
from types import SimpleNamespace

#: wall + bottom-slab are the SAME physical material (the vessel) —
#: one style. Holes are empty space; a distinct gray marker is the
#: placeholder for "nothing is here" (there's no clean way to render
#: an absence, see the plan doc). Soil (phase 4) gets its own earth
#: tone (simSpace3D/seed_data.py's 'soil-brown'). Vessel/soil each
#: have a '-transparent' variant (phase 5) toggled by the pot's own
#: wall_transparent/soil_transparent knobs — never a blanket
#: "make everything see-through" switch. Holes are the one exception
#: (2026-07-15, Dustin): they're bore-position markers, not solid
#: geometry worth hiding water behind, so they ALWAYS render at
#: 'matte-gray-transparent' — untouched by either toggle, same as
#: before, just permanently the see-through variant now.
VESSEL_STYLE_REF = 'matte-blue'
VESSEL_TRANSPARENT_STYLE_REF = 'matte-blue-transparent'
HOLE_STYLE_REF = 'matte-gray-transparent'
SOIL_STYLE_REF = 'soil-brown'
SOIL_TRANSPARENT_STYLE_REF = 'soil-brown-transparent'
WATER_STYLE_REF = 'water-blue'


def _scene_name(pot_name):
    return f'{pot_name}-viz'


def _water_scene_name(pot_name):
    return f'{pot_name}-water-viz'


def _freestanding_entry(shape_name, style_ref):
    return {
        'id': shape_name,
        'shapeRef': f'mathshape:{shape_name}',
        'styleRef': style_ref,
        'position': [0.0, 0.0, 0.0],
    }


def _water_freestanding_entry(pot_name):
    """`waterslice:` is a DIFFERENT resolution scheme from `mathshape:`
    — there's no stored MathShapeDefinition row backing it (the mesh
    depends on water_level_mm, which changes every animation tick), so
    the frontend resolves it via GET /api/aquaponics/pots/{pot_name}/
    water-slice instead of /api/shapes/{name}/surface. Same freestanding-
    entry shape either way; only the shapeRef prefix differs."""
    return {
        'id': f'{pot_name}-water-slice',
        'shapeRef': f'waterslice:{pot_name}',
        'styleRef': WATER_STYLE_REF,
        'position': [0.0, 0.0, 0.0],
    }


def _plant_scene_name(planting_name):
    return f'{planting_name}-plant-viz'


def _plant_freestanding_entry(planting_name):
    """`plantskeleton:` — a THIRD resolution scheme, alongside
    `mathshape:`/`waterslice:` (plant-growth-sim phase 6/7,
    2026-07-15). No stored row backs it either (the bone graph depends
    on the planting's CURRENT normalized_growth, which changes every
    advance_growth() call) — the frontend resolves it via GET
    /api/aquaponics/plantings/{planting_name}/skeleton instead."""
    return {
        'id': f'{planting_name}-skeleton',
        'shapeRef': f'plantskeleton:{planting_name}',
        # A living plant needs its own material, not the vessel/soil
        # tones — reuses simSpace3D/seed_data.py's 'plant-green'
        # (added alongside 'water-blue' this phase).
        'styleRef': 'plant-green',
        'position': [0.0, 0.0, 0.0],
    }


def ensure_pot_viz_scene(manager, pot_name, wall_name, bottom_name,
                         soil_name, hole_names, wall_transparent=False,
                         soil_transparent=False):
    """Idempotently create/refresh the `{pot_name}-viz` SimSpaceDefinition
    so it always lists the CURRENT wall/bottom-slab/soil/hole shapes.
    Safe to call every time from-pot re-derives the pot (e.g. after a
    phase-2 CRUDE edit) — updates `definition` in place rather than
    duplicating the row. `soil_name=None` (e.g. soil_fill_height_mm
    resolves to ~0) simply omits the soil entry — an honest gap, not a
    placeholder object. `wall_transparent`/`soil_transparent` (phase 5,
    from the pot's own knobs) pick the '-transparent' style variant for
    that layer — wall+bottom (the vessel "shell") share ONE toggle,
    soil its own."""
    table = (getattr(manager, 'objectTables', None) or {}).setdefault(
        'SimSpaceDefinition', {})
    scene_name = _scene_name(pot_name)

    vessel_style = VESSEL_TRANSPARENT_STYLE_REF if wall_transparent else VESSEL_STYLE_REF
    soil_style = SOIL_TRANSPARENT_STYLE_REF if soil_transparent else SOIL_STYLE_REF

    freestanding = [
        _freestanding_entry(wall_name, vessel_style),
        _freestanding_entry(bottom_name, vessel_style),
    ]
    if soil_name:
        freestanding.append(_freestanding_entry(soil_name, soil_style))
    freestanding += [_freestanding_entry(h, HOLE_STYLE_REF) for h in hole_names]
    definition_json = json.dumps({
        'freestandingOnly': True,
        'freestanding': freestanding,
    })
    # Recomputed on EVERY call, not just at creation — hole count (and
    # therefore this text) could change across re-derives even though
    # Phase 2 doesn't expose add/remove-hole editing today; freezing it
    # at creation would silently drift from the actual scene contents.
    description = (f'Math-defined render of aqp-1 pot "{pot_name}" '
                   f'(hollow wall shell + solid base'
                   f'{" + soil fill" if soil_name else ""} + '
                   f'{len(hole_names)} drainage holes).')

    # Configured interface (2026-07-14): the pot-geometry-editor IS this
    # scene's "how to set it up" — it edits the exact PotDefinition/
    # PotHole rows that from-pot derives this scene from. Shown as the
    # default tab in the viewer's Initial Conditions panel (generalizes
    # msim's icInterfaceRef pattern to any SimSpace, not just multi-
    # scale sims — this pot has no bound SimulationDefinition at all
    # yet, so without this the panel would have nothing configured to
    # show ahead of the — here inapplicable — generic manual form).
    configured_interfaces_json = json.dumps([{
        'componentName': 'pot-geometry-editor',
        'inputs': {'potName': pot_name},
        'label': f'Pot geometry — {pot_name}',
    }])

    existing = table.get(scene_name)
    if existing is not None:
        existing.definition = definition_json
        existing.description = description
        existing.configured_interfaces_json = configured_interfaces_json
        return scene_name

    table[scene_name] = SimpleNamespace(
        name=scene_name,
        description=description,
        dimensionality='3d',
        coordinate_system='math',
        unit_scale=1.0,
        viewport_json='',
        bound_classes_json='[]',
        definition=definition_json,
        axis_labels_json='{}',
        camera_json='',
        category='',
        owning_module='aquaponics',
        xr_mode='unset',
        xr_framing='unset',
        configured_interfaces_json=configured_interfaces_json,
    )
    return scene_name


def ensure_pot_water_viz_scene(manager, pot_name, wall_name, bottom_name,
                               soil_name, hole_names):
    """Idempotently create/refresh `{pot_name}-water-viz` — a
    SEPARATE SimSpaceDefinition from `{pot_name}-viz` (2026-07-15,
    Dustin: "this simulation should be separate from the pot with soil
    that lacks water flowing through"), not a mode toggle on the same
    scene. Same wall/bottom/soil/hole shapes, but ALWAYS at their
    transparent style variants regardless of the pot's own
    wall_transparent/soil_transparent knobs — seeing the water is the
    entire point of this scene, so it doesn't defer to a toggle meant
    for the no-water view. Adds ONE more freestanding entry, the live
    water-slice mesh (see water_freestanding_entry / hydraulics.py's
    water_slice_mesh) — its shapeRef resolves dynamically per-request
    (water_level_mm changes every animation tick), unlike the static
    `mathshape:` entries here which resolve once per re-derive."""
    table = (getattr(manager, 'objectTables', None) or {}).setdefault(
        'SimSpaceDefinition', {})
    scene_name = _water_scene_name(pot_name)

    freestanding = [
        _freestanding_entry(wall_name, VESSEL_TRANSPARENT_STYLE_REF),
        _freestanding_entry(bottom_name, VESSEL_TRANSPARENT_STYLE_REF),
    ]
    if soil_name:
        freestanding.append(
            _freestanding_entry(soil_name, SOIL_TRANSPARENT_STYLE_REF))
    freestanding += [_freestanding_entry(h, HOLE_STYLE_REF) for h in hole_names]
    freestanding.append(_water_freestanding_entry(pot_name))
    definition_json = json.dumps({
        'freestandingOnly': True,
        'freestanding': freestanding,
    })
    description = (f'Water-flow visualization of aqp-1 pot "{pot_name}" '
                   f'(always-transparent shell'
                   f'{" + soil" if soil_name else ""} + '
                   f'{len(hole_names)} holes + the live Darcy '
                   f'cross-section) — separate from "{pot_name}-viz", '
                   'the static no-water view.')
    configured_interfaces_json = json.dumps([{
        'componentName': 'pot-geometry-editor',
        'inputs': {'potName': pot_name},
        'label': f'Pot geometry — {pot_name}',
    }])

    existing = table.get(scene_name)
    if existing is not None:
        existing.definition = definition_json
        existing.description = description
        existing.configured_interfaces_json = configured_interfaces_json
        return scene_name

    table[scene_name] = SimpleNamespace(
        name=scene_name,
        description=description,
        dimensionality='3d',
        coordinate_system='math',
        unit_scale=1.0,
        viewport_json='',
        bound_classes_json='[]',
        definition=definition_json,
        axis_labels_json='{}',
        camera_json='',
        category='',
        owning_module='aquaponics',
        xr_mode='unset',
        xr_framing='unset',
        configured_interfaces_json=configured_interfaces_json,
    )
    return scene_name


def ensure_pot_plant_viz_scene(manager, planting_name, pot_name, wall_name,
                               bottom_name, soil_name, hole_names):
    """Idempotently create/refresh `{planting_name}-plant-viz` — keyed
    by PLANTING, not pot (2026-07-15, plant-growth-sim phase 6/7): a
    pot can have more than one PotPlanting bound to it (this session's
    own real seed data does — the same demo-herb-pot under two
    different what-if PotSystemDefinitions), and two plants can't
    physically occupy the same pot at once, so a pot-keyed scene would
    be ambiguous the moment a second planting exists. One scene per
    planting sidesteps that entirely — each shows THAT planting's own
    pot/soil/holes (always-transparent, same rationale as the water-
    viz scene: seeing the plant/roots through the shell is the whole
    point) plus its own live `plantskeleton:` mesh, which resolves to
    a DIFFERENT bone graph per planting even when they share a pot
    (different normalized_growth, possibly a different random_seed)."""
    table = (getattr(manager, 'objectTables', None) or {}).setdefault(
        'SimSpaceDefinition', {})
    scene_name = _plant_scene_name(planting_name)

    freestanding = [
        _freestanding_entry(wall_name, VESSEL_TRANSPARENT_STYLE_REF),
        _freestanding_entry(bottom_name, VESSEL_TRANSPARENT_STYLE_REF),
    ]
    if soil_name:
        freestanding.append(
            _freestanding_entry(soil_name, SOIL_TRANSPARENT_STYLE_REF))
    freestanding += [_freestanding_entry(h, HOLE_STYLE_REF) for h in hole_names]
    freestanding.append(_plant_freestanding_entry(planting_name))
    definition_json = json.dumps({
        'freestandingOnly': True,
        'freestanding': freestanding,
    })
    description = (f'Plant-growth visualization of "{planting_name}" '
                   f'(always-transparent shell'
                   f'{" + soil" if soil_name else ""} + '
                   f'{len(hole_names)} holes + the live animation-bones '
                   f'skeleton) in pot "{pot_name}".')
    configured_interfaces_json = json.dumps([{
        'componentName': 'pot-geometry-editor',
        'inputs': {'potName': pot_name},
        'label': f'Pot geometry — {pot_name}',
    }])

    existing = table.get(scene_name)
    if existing is not None:
        existing.definition = definition_json
        existing.description = description
        existing.configured_interfaces_json = configured_interfaces_json
        return scene_name

    table[scene_name] = SimpleNamespace(
        name=scene_name,
        description=description,
        dimensionality='3d',
        coordinate_system='math',
        unit_scale=1.0,
        viewport_json='',
        bound_classes_json='[]',
        definition=definition_json,
        axis_labels_json='{}',
        camera_json='',
        category='',
        owning_module='aquaponics',
        xr_mode='unset',
        xr_framing='unset',
        configured_interfaces_json=configured_interfaces_json,
    )
    return scene_name
