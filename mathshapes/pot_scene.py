"""
@cross-cutting
@module mathshapes.pot_scene
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
#: tone (simSpace3D/seed_data.py's 'soil-brown'). Each has a
#: '-transparent' variant (phase 5) toggled by the pot's own
#: wall_transparent/soil_transparent knobs — never a blanket
#: "make everything see-through" switch.
VESSEL_STYLE_REF = 'matte-blue'
VESSEL_TRANSPARENT_STYLE_REF = 'matte-blue-transparent'
HOLE_STYLE_REF = 'matte-gray'
SOIL_STYLE_REF = 'soil-brown'
SOIL_TRANSPARENT_STYLE_REF = 'soil-brown-transparent'


def _scene_name(pot_name):
    return f'{pot_name}-viz'


def _freestanding_entry(shape_name, style_ref):
    return {
        'id': shape_name,
        'shapeRef': f'mathshape:{shape_name}',
        'styleRef': style_ref,
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

    existing = table.get(scene_name)
    if existing is not None:
        existing.definition = definition_json
        existing.description = description
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
    )
    return scene_name
