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

SEED_PENDULUM_SIMSPACES.append(_MATERIAL_SIMSPACE)
SEED_PENDULUM_BINDINGS.extend(_MATERIAL_BINDINGS)
