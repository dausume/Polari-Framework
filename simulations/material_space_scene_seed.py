"""
@module simulations.material_space_scene_seed

3D scene for the MATERIAL CONDENSATION space — the ball forming as the
sample cools. Pure configuration (Phase B of solid-materials-selection):

  - SimSpaceDefinition 'material-condensation-viz': a tight viewport
    around the origin where the candidate ball sits.
  - SimSpaceBindingDefinition on MaterialCondensationState: a sphere at
    the origin whose APPEARANCE follows the phase (the styleRef
    {fromField, map, default} primitive, composed from the substance's
    MaterialPhaseAppearance row so the two cannot drift) and whose SIZE
    follows ball_radius (uniform field scale, factor 2 — the shared
    unit sphere has radius 0.5).

The seeded binding wears the DEFAULT substance's (paraffin wax) phase
map — per-substance preview objects with their own maps arrive with the
selection space (Phase C). Kept out of material_space_seed per the
small-file convention; registered into the shared pendulum seed lists
like the other scene seeds.
"""

import json

from simulations.seed_data import (
    SEED_PENDULUM_SIMSPACES,
    SEED_PENDULUM_BINDINGS,
)
from simSpace3D.seed_data import SEED_MATERIAL_PHASE_APPEARANCES
from simSpace3D.material_phase_appearance import binding_style_map

MATERIAL_SCENE = 'material-condensation-viz'
_MC = 'MaterialCondensationState'

# The demo default substance's appearance row (wax) — the binding's
# inline style map is COMPOSED from it, never hand-written.
_WAX_APPEARANCE = next(
    row for row in SEED_MATERIAL_PHASE_APPEARANCES
    if row['substance_ref'] == 'paraffin-wax')

_MATERIAL_SIMSPACE = {
    'name': MATERIAL_SCENE,
    'description': (
        'The material-condensation process point: the candidate ball at '
        'the chamber origin. Its look follows the phase — translucent '
        'liquid until the sample cools below the melting line, then the '
        'solid material — and its size is the real ball_radius the gate '
        'proves. Scrub a run to watch the ball solidify.'
    ),
    'dimensionality': '3d',
    'coordinate_system': 'math',
    'unit_scale': 1.0,
    'viewport_json': '{"center": [0, 0.05, 0], "extent": [0.25, 0.25, 0.25]}',
    'bound_classes_json': json.dumps([{'className': _MC}]),
    # A thin chamber plate under the ball for spatial grounding.
    'definition': (
        '{"freestanding": ['
        '{"id":"chamber-plate","position":[0,-0.09,0],"shapeRef":"cylinder",'
        '"styleRef":"matte-gray","scale":[0.4,0.02,0.4],"label":"Chamber"}'
        ']}'
    ),
}

_MATERIAL_BINDINGS = [
    {
        'name': f'{_MC}-3d', 'class_name': _MC, 'dimensionality': '3d',
        'enabled': True,
        'binding_json': json.dumps({
            'enabled': True, 'dimensionality': '3d', 'kind': 'object',
            'position': {'kind': 'constant', 'value': [0.0, 0.0, 0.0]},
            'visual': {
                'shapeRef': 'sphere',
                # Appearance BY PHASE, composed from the wax appearance
                # row (object coherence: the map lives on the row).
                'styleRef': binding_style_map(_WAX_APPEARANCE),
            },
            # Size BY DATA: unit sphere r=0.5 × (2·ball_radius) → the
            # rendered radius equals the proven metric radius.
            'scale': {'kind': 'uniform', 'field': 'ball_radius',
                      'factor': 2.0},
            'clickAction': 'navigate-to-instance', 'defaultVisible': True,
            'temporal': {'kind': 'time', 'field': 'time', 'unit': 'second',
                         'cumulative': False},
        }),
    },
]

# ---------------------------------------------------------------------------
# The SOLID-MATERIAL SELECTOR scene (Phase C) — a fixed-camera SELECTION
# SPACE: one preview ball per picker substance, each wearing its SOLID-
# phase material (what you'd get if the proof succeeds). Pure config:
# adding a material = one freestanding entry + its appearance row.
# The sim-space-selector component anchors choice overlays on these
# objects' projected shell rects and publishes clicks into the display
# selection context.
# ---------------------------------------------------------------------------

SELECTOR_SCENE = 'solid-material-selector'


def _selector_ball(index, substance_ref, label):
    """One selectable preview ball, spaced along X, wearing the
    substance's SOLID-phase material (from its appearance row)."""
    row = next(r for r in SEED_MATERIAL_PHASE_APPEARANCES
               if r['substance_ref'] == substance_ref)
    solid_material = json.loads(row['appearance_map_json']).get('1') \
        or row['default_material_ref']
    return {
        'id': f'choice-{substance_ref}',
        'position': [(index - 1) * 0.35, 0.0, 0.0],
        'shapeRef': 'sphere',
        'styleRef': solid_material,
        'scale': 0.24,
        'label': label,
    }


_SELECTOR_SIMSPACE = {
    'name': SELECTOR_SCENE,
    'description': (
        'Material selection space — pick what the ball is made of by '
        'clicking it. Each preview ball wears its substance\'s SOLID-phase '
        'look; the badge above it carries the proof verdict, and its popup '
        'shows the tried temperature/pressure conditions. Fixed camera: '
        'a selection shelf, not a navigable scene.'
    ),
    'dimensionality': '3d',
    'coordinate_system': 'math',
    'unit_scale': 1.0,
    'viewport_json': '{"center": [0, 0, 0], "extent": [0.7, 0.35, 0.35]}',
    'camera_json': json.dumps({
        'mode': 'fixed',
        'position': [0.0, 0.35, 1.05],
        'target': [0.0, 0.0, 0.0],
        'up': [0, 1, 0],
        'projection': 'perspective',
        'fov': 45,
    }),
    'bound_classes_json': '[]',
    'definition': json.dumps({'freestanding': [
        _selector_ball(0, 'paraffin-wax', 'Paraffin wax'),
        _selector_ball(1, 'water-ice', 'Water ice'),
        _selector_ball(2, 'lead', 'Lead'),
        # A shelf under the balls for spatial grounding.
        {'id': 'selector-shelf', 'position': [0, -0.16, 0],
         'shapeRef': 'cube', 'styleRef': 'matte-gray',
         'scale': [1.15, 0.03, 0.4], 'label': 'Shelf'},
    ]}),
}

SEED_PENDULUM_SIMSPACES.append(_MATERIAL_SIMSPACE)
SEED_PENDULUM_SIMSPACES.append(_SELECTOR_SIMSPACE)
SEED_PENDULUM_BINDINGS.extend(_MATERIAL_BINDINGS)
