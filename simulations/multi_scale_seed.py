"""
@module simulations.multi_scale_seed

Seed data for the Multi-Scale Simulation Page — the "Pendulum in Wind"
demo MultiScaleSimulationDefinition plus the bob-material
InitialConditionInterfaceDefinition, so the page works out of the box
against the already-seeded pendulum + wind spaces and their coupling.

The demo's stages_json is a single coStep stage (the live coupled
stepping proven in Milestone A). The material-precondition
runToCompletion stage is added when the material space lands (Milestone
B) — the schema supports it now; only the stage entry and its gate
solution will be new content, not new machinery.

Same registration pattern as the other sim seeds: polariServer imports
this module and wires the SEED_* lists into seed_pairs.
"""

import json
import math

from simulations.newtonian_pendulum_seed import (
    NEWTON_SIM_DEF,
    _NB,
    _NEWTON_BOB_RADIUS,
)
from simulations.wind_field_seed import WIND_SIM_DEF

MSIM_NAME = 'pendulum-in-wind'
IC_MATERIAL_PICKER = 'bob-material-picker'

# Preset masses = density × sphere volume at the demo bob radius, so a
# material choice is a REAL mass the wind visibly acts against (ice sways
# in the gusts; lead barely notices — same wind, same geometry).
_BOB_VOLUME = (4.0 / 3.0) * math.pi * _NEWTON_BOB_RADIUS ** 3
_MATERIALS = [
    ('ice',   'Ice ball',   917.0),
    ('oak',   'Oak ball',   700.0),
    ('steel', 'Steel ball', 7850.0),
    ('lead',  'Lead ball',  11340.0),
]

SEED_IC_INTERFACES = [{
    'name': IC_MATERIAL_PICKER,
    'description': (
        'Pick what the pendulum bob is made of. Each material sets the '
        'bob\'s real mass (density x volume at the fixed 8 cm radius), so '
        'the wind\'s effect changes physically: light materials get pushed '
        'around, heavy ones barely react. Selections re-validate the '
        'initial conditions automatically. When the material space lands '
        '(Milestone B), these hand-authored choices are replaced by real '
        'Material objects gated by the condensation-precondition '
        'simulation - same interface, generated choices.'
    ),
    'target_simulation_ref': NEWTON_SIM_DEF,
    'target_class_name': _NB,
    'interface_kind': 'choicePreset',
    'config_json': json.dumps({
        'label': 'Bob material',
        'choices': [
            {
                'key': key,
                'label': label,
                'description': f'density {density:g} kg/m^3',
                'setParams': {
                    'mass': round(density * _BOB_VOLUME, 4),
                    'bob_radius': _NEWTON_BOB_RADIUS,
                },
            }
            for key, label, density in _MATERIALS
        ],
        # Recomputed from the chosen bundle before validation (frontend
        # evaluates these simple expressions) so downstream physics —
        # the wind drag reads bob_cross_section — matches the selection.
        'derivedParams': {
            'bob_cross_section': 'pi * bob_radius ** 2',
            'bob_volume': '(4 / 3) * pi * bob_radius ** 3',
            'bob_surface_area': '4 * pi * bob_radius ** 2',
        },
    }),
    'enabled': True,
}]

# Demo graphs-over-time for the page's graph panels (Phase 3). GraphDefinition
# rows are normally frontend-authored; seeding these two gives the demo page
# live charts out of the box. `definition` matches the frontend
# GraphConfigData shape (renderStyle / xDimension / yDimensions / options).
SEED_MSIM_GRAPHS = [
    {
        'name': 'msim-pendulum-energy',
        'description': 'Total/kinetic/potential energy of the bob over time — '
                       'watch the wind do (negative) work vs the vacuum run.',
        'source_class': _NB,
        # Wrapped {graphConfig: {...}} form — what the frontend's
        # NamedGraphConfig.fromBackend expects, so the Graphs editor
        # pages read these seeds too (the msim graph panel normalizes
        # both shapes, but only this one round-trips through the editor).
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'time',
            'yDimensions': ['energy_total', 'ke', 'pe'],
            'seriesColors': [],
            'options': {'legend': True},
            'aggregation': None,
        }}),
    },
    {
        'name': 'msim-wind-force',
        'description': 'Sampled wind drag components on the bob over time — '
                       'zero until the first evolved wind step is sampleable.',
        'source_class': _NB,
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'time',
            'yDimensions': ['fwind_x', 'fwind_y', 'fwind_z'],
            'seriesColors': [],
            'options': {'legend': True},
            'aggregation': None,
        }}),
    },
]

SEED_MULTI_SCALE_SIMS = [{
    'name': MSIM_NAME,
    'description': (
        'The Milestone-A demo as a configured multi-scale simulation: the '
        'Newtonian pendulum coupled to the wind-field space (10x coarser '
        'timescale, lazy-pulled). Drive the pendulum run; the wind advances '
        'itself. Compare against the vacuum run to SEE the coupling.'
    ),
    'member_simulation_refs_json': json.dumps([NEWTON_SIM_DEF, WIND_SIM_DEF]),
    'coupling_refs_json': json.dumps(['wind-to-newtonian-pendulum']),
    'primary_simulation_ref': NEWTON_SIM_DEF,
    'stages_json': json.dumps([
        {
            'key': 'pendulum-in-wind',
            'label': 'Pendulum swinging in wind',
            'kind': 'coStep',
            'primarySimulationRef': NEWTON_SIM_DEF,
            'couplingRefs': ['wind-to-newtonian-pendulum'],
        },
    ]),
    'panels_json': json.dumps([
        {'kind': 'scene', 'simSpaceRef': 'newtonian-pendulum-viz', 'run': 'primary'},
        {'kind': 'graph', 'graphRef': 'msim-pendulum-energy',
         'sourceClass': _NB, 'runs': ['primary', 'compare']},
        {'kind': 'graph', 'graphRef': 'msim-wind-force',
         'sourceClass': _NB, 'runs': ['primary']},
        {'kind': 'ic', 'icInterfaceRef': IC_MATERIAL_PICKER},
    ]),
    'display_ref': '',
    'compare_run_policy_json': json.dumps({
        'mode': 'fanOutSteps',
        'runs': ['newtonian-pendulum-run'],
    }),
    'enabled': True,
}]
