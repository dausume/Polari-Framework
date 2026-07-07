"""
@module simulations.multi_scale_seed

Seed data for the Multi-Scale Simulation Page — the "Pendulum in Wind"
demo MultiScaleSimulationDefinition plus the bob-material
InitialConditionInterfaceDefinition, so the page works out of the box
against the already-seeded pendulum + wind spaces and their coupling.

The demo's stages_json: the material-precondition runToCompletion stage
(Milestone B, landed — searches temperature/pressure until the chosen
substance provably condenses into a solid ball, then derives the ball's
properties into the pendulum) followed by the coStep pendulum-in-wind
stage (the live coupled stepping proven in Milestone A).

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
# Importing the material seed registers the material-condensation space +
# the solid-ball-achievable gate into the shared seed lists (Milestone B —
# the first-principles stage this composition's stage 1 references).
from simulations.material_space_seed import MATERIAL_SIM_DEF, GATE_SOLUTION
# Importing the scene seed registers the material-condensation-viz 3D
# scene + phase-appearance binding (Phase B) and the fixed-camera
# solid-material-selector selection space (Phase C).
from simulations.material_space_scene_seed import MATERIAL_SCENE, SELECTOR_SCENE

MSIM_NAME = 'pendulum-in-wind'
IC_MATERIAL_PICKER = 'bob-material-picker'
_MC = 'MaterialCondensationState'

# Preset masses = density × sphere volume at the demo bob radius, so a
# material choice is a REAL mass the wind visibly acts against (ice sways
# in the gusts; lead barely notices — same wind, same geometry).
#
# Milestone B: each choice is now a SUBSTANCE carrying its physical
# identity (`substanceParams` — melting line + density behavior) that the
# material-condensation space uses as the search's fixedParams to PROVE a
# solid ball is possible and derive its real properties. The setParams
# presets remain as the direct channel until the frontend wires
# choice → substance search (both channels coexist).
_BOB_VOLUME = (4.0 / 3.0) * math.pi * _NEWTON_BOB_RADIUS ** 3
_MATERIALS = [
    # (key, label, density kg/m^3, substanceParams)
    ('paraffin-wax', 'Paraffin wax ball', 900.0, {
        'melt_temp_ref': 327.0, 'melt_slope_k_per_pa': 2.5e-7,
        'density_solid_ref': 900.0, 'thermal_expansion': 8e-4,
        'density_ref_temp': 293.15,
    }),
    ('water-ice', 'Water-ice ball', 917.0, {
        # Ice melts UNDER pressure — the slope is negative (skate-blade
        # physics), so high-pressure candidates can fail where low do not.
        'melt_temp_ref': 273.15, 'melt_slope_k_per_pa': -7.4e-8,
        'density_solid_ref': 917.0, 'thermal_expansion': 1.5e-4,
        'density_ref_temp': 263.15,
    }),
    ('lead', 'Lead ball', 11340.0, {
        'melt_temp_ref': 600.6, 'melt_slope_k_per_pa': 7.9e-8,
        'density_solid_ref': 11340.0, 'thermal_expansion': 8.7e-5,
        'density_ref_temp': 293.15,
    }),
]

SEED_IC_INTERFACES = [{
    'name': IC_MATERIAL_PICKER,
    'description': (
        'Pick what the pendulum bob is made of. Each choice is a real '
        'SUBSTANCE: the material space searches temperature/pressure for '
        'conditions where it condenses into a solid ball, proves it is '
        'possible, and derives the ball\'s real mass and size for the '
        'pendulum\'s initial conditions. Light materials get pushed around '
        'by the wind; heavy ones barely react. Selections re-validate the '
        'initial conditions automatically.'
    ),
    'target_simulation_ref': NEWTON_SIM_DEF,
    'target_class_name': _NB,
    'interface_kind': 'choicePreset',
    'config_json': json.dumps({
        'label': 'Bob material',
        # The composition + stage whose solution search proves a choice.
        'provingStage': {'msim': MSIM_NAME, 'stageKey': 'material-precondition'},
        'choices': [
            {
                'key': key,
                'label': label,
                'description': f'density {density:g} kg/m^3',
                'substanceParams': substance,
                'setParams': {
                    'mass': round(density * _BOB_VOLUME, 4),
                    'bob_radius': _NEWTON_BOB_RADIUS,
                },
            }
            for key, label, density, substance in _MATERIALS
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
            'options': {'legend': True, 'xLabel': 'time (s)', 'yLabel': 'energy (J)'},
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
            'options': {'legend': True, 'xLabel': 'time (s)', 'yLabel': 'force (N)'},
            'aggregation': None,
        }}),
    },
    # --- Material-condensation stage graphs (explainability): plot the
    # precondition stage's per-step physics so "prove a solid ball" is
    # visible as data, not just a PROVEN/IMPOSSIBLE verdict. The melt
    # line is itself a computed state field (melt_temp) because the
    # graph engine has no reference-line feature — the crossing IS data.
    {
        'name': 'msim-material-temperature',
        'description': ('The sample cooling toward the chamber target vs the '
                        'pressure-shifted melting line T_m(P). The ball is '
                        'solid exactly while temperature is below the line — '
                        'the crossing is the moment of solidification.'),
        'source_class': _MC,
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'time',
            'yDimensions': ['temperature', 'melt_temp'],
            'seriesColors': [],
            'options': {'legend': True, 'xLabel': 'time (s)', 'yLabel': 'temperature (K)'},
            'aggregation': None,
        }}),
    },
    {
        'name': 'msim-material-phase',
        'description': ('Solid-phase flag over time: 0 while the sample would '
                        'be liquid, 1 once it condenses solid. The stage gate '
                        'passes when the final step is 1.'),
        'source_class': _MC,
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'time',
            'yDimensions': ['phase_solid'],
            'seriesColors': [],
            'options': {'legend': True, 'xLabel': 'time (s)', 'yLabel': 'phase (1 = solid, 0 = liquid)'},
            'aggregation': None,
        }}),
    },
    {
        'name': 'msim-material-density',
        'description': ('Density at the current temperature (thermal '
                        'expansion) and the mass of the target ball it '
                        'implies — the values the pendulum inherits when the '
                        'gate proves the ball.'),
        'source_class': _MC,
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'time',
            'yDimensions': ['density', 'ball_mass'],
            'seriesColors': [],
            'options': {'legend': True, 'xLabel': 'time (s)', 'yLabel': 'density (kg/m³) · ball mass (kg)'},
            'aggregation': None,
        }}),
    },
    {
        'name': 'msim-out-of-plane',
        'description': ('Out-of-plane motion: pz (position) and vz (velocity) '
                        'over time. In vacuum both are exactly zero; under '
                        'wind the bob leaves its swing plane and wobbles '
                        'through it — a true 3D spherical pendulum.'),
        'source_class': _NB,
        'definition': json.dumps({'graphConfig': {
            'renderStyle': 'lineY',
            'xDimension': 'time',
            'yDimensions': ['pz', 'vz'],
            'seriesColors': [],
            'options': {'legend': True, 'xLabel': 'time (s)', 'yLabel': 'position pz (m) · velocity vz (m/s)'},
            'aggregation': None,
        }}),
    },
]

SEED_MULTI_SCALE_SIMS = [{
    'name': MSIM_NAME,
    # The family this msim instantiates (multi_scale_profile_seed) —
    # the retrofit proof that the profile abstraction generalizes.
    'profile_ref': 'pendulum-in-wind',
    'description': (
        'The Milestone-A demo as a configured multi-scale simulation: the '
        'Newtonian pendulum coupled to the wind-field space (10x coarser '
        'timescale, lazy-pulled). Drive the pendulum run; the wind advances '
        'itself. Compare against the vacuum run to SEE the coupling.'
    ),
    'member_simulation_refs_json': json.dumps(
        [MATERIAL_SIM_DEF, NEWTON_SIM_DEF, WIND_SIM_DEF]),
    'coupling_refs_json': json.dumps(['wind-to-newtonian-pendulum']),
    'primary_simulation_ref': NEWTON_SIM_DEF,
    'stages_json': json.dumps([
        # Stage 1 — THE FIRST-PRINCIPLES STAGE (Milestone B): search
        # temperature/pressure candidates until the substance provably
        # condenses into a solid ball; the gate reports the ball's
        # properties, which `derive` sends into the pendulum's params.
        # Substance identity arrives per-search as fixedParams (see the
        # bob-material-picker's per-choice substanceParams).
        {
            'key': 'material-precondition',
            'label': 'Prove a solid ball is possible',
            'kind': 'runToCompletion',
            'intent': 'search',
            'simulationRef': MATERIAL_SIM_DEF,
            'gate': {
                'solutionRef': GATE_SOLUTION,
                'failReason': ('No solid phase at the tried temperature/'
                               'pressure — the ball would be liquid.'),
            },
            'derive': {
                'params': {
                    f'{NEWTON_SIM_DEF}.mass': 'ball_mass',
                    f'{NEWTON_SIM_DEF}.bob_radius': 'ball_radius',
                },
            },
            'search': {
                'candidates': {
                    'kind': 'grid',
                    'parameters': {
                        'target_temp': {'from': 260.0, 'to': 340.0, 'steps': 5},
                        'pressure_pa': {'from': 50000.0, 'to': 200000.0, 'steps': 2},
                    },
                },
                'stepsPerAttempt': 20,
                'batchSize': 5,
            },
        },
        {
            'key': 'pendulum-in-wind',
            'label': 'Pendulum swinging in wind',
            'kind': 'coStep',
            'intent': 'observe',
            'primarySimulationRef': NEWTON_SIM_DEF,
            'couplingRefs': ['wind-to-newtonian-pendulum'],
        },
    ]),
    'panels_json': json.dumps([
        # The 3D material selection space (Phase C): click a preview
        # ball to choose the substance; the picker below follows via the
        # shared display-context key and runs the proof. Items are pure
        # config — objectId matches the scene's freestanding ids.
        {
            'kind': 'selector',
            'simSpaceRef': SELECTOR_SCENE,
            'stageKey': 'material-precondition',
            'contextKey': 'selectedMaterialKey',
            'items': [
                {'key': key, 'label': label,
                 'objectId': f'choice-{key}',
                 'description': f'density {density:g} kg/m^3 — melts at '
                                f'{substance["melt_temp_ref"]:g} K',
                 'overlayRef': 'material-choice', 'popup': True}
                for key, label, density, substance in _MATERIALS
            ],
        },
        {'kind': 'ic', 'icInterfaceRef': IC_MATERIAL_PICKER,
         'followContextKey': 'selectedMaterialKey'},
        # Explainability (all show* flags are knobs; body is editable
        # config — the panel augments it with LIVE facts read from this
        # msim's own stage config so the text cannot drift from behavior).
        {
            'kind': 'explainer',
            'stageKey': 'material-precondition',
            'title': 'How the material stage works',
            'body': (
                'Before the pendulum can swing, the composition must prove '
                'its bob can exist. The chosen substance is held at a '
                'candidate temperature and pressure; its temperature relaxes '
                'toward the chamber target (Newtonian cooling) and is checked '
                'each step against the pressure-shifted melting line '
                'T_m(P) = T_ref + s·(P − 101325). If the sample ends below '
                'the line it has condensed into a SOLID ball; the gate then '
                'reports the ball\'s real mass, radius and density, and those '
                'flow into the pendulum\'s initial conditions. If no tried '
                'condition produces a solid, that material is impossible for '
                'this pendulum — the search shows every condition it tried '
                'and why each failed.'
            ),
            'showSearchSpace': True,
            'showGate': True,
            'showDerive': True,
            'showConditionMap': True,
            'showMeltLine': True,
        },
        # Material graphs are FAMILY panels: the same graph pivoted
        # across the picker's materials — per-material tabs + an
        # all-materials comparison chart (one series per material; the
        # y-space is coherent by construction: same class, same fields).
        {'kind': 'graph', 'graphRef': 'msim-material-temperature',
         'sourceClass': _MC, 'runs': ['stage:material-precondition'],
         'family': {'icInterfaceRef': IC_MATERIAL_PICKER,
                    'stageKey': 'material-precondition'}},
        {'kind': 'graph', 'graphRef': 'msim-material-phase',
         'sourceClass': _MC, 'runs': ['stage:material-precondition'],
         'family': {'icInterfaceRef': IC_MATERIAL_PICKER,
                    'stageKey': 'material-precondition'}},
        {'kind': 'graph', 'graphRef': 'msim-material-density',
         'sourceClass': _MC, 'runs': ['stage:material-precondition'],
         'family': {'icInterfaceRef': IC_MATERIAL_PICKER,
                    'stageKey': 'material-precondition',
                    'combineFields': ['density']}},
        # The condensation ball itself — appearance follows the phase,
        # size follows the proven ball_radius (Phase B). Revealed only
        # once the precondition stage has actually run: before that the
        # scene is just the empty chamber plate, which reads as noise
        # (or worse, a broken pivot) next to the selection balls. The
        # disclosure is a knob — the user can always expand it by hand.
        {'kind': 'scene', 'simSpaceRef': MATERIAL_SCENE,
         'run': 'stage:material-precondition',
         'reveal': {'when': 'stageActivity',
                    'stageKey': 'material-precondition',
                    'label': 'Condensation chamber (fills in when the '
                             'material proof search runs)'}},
        {'kind': 'scene', 'simSpaceRef': 'newtonian-pendulum-viz', 'run': 'primary'},
        {'kind': 'graph', 'graphRef': 'msim-out-of-plane',
         'sourceClass': _NB, 'runs': ['primary', 'compare']},
        {'kind': 'graph', 'graphRef': 'msim-pendulum-energy',
         'sourceClass': _NB, 'runs': ['primary', 'compare']},
        {'kind': 'graph', 'graphRef': 'msim-wind-force',
         'sourceClass': _NB, 'runs': ['primary']},
    ]),
    'display_ref': '',
    'compare_run_policy_json': json.dumps({
        'mode': 'fanOutSteps',
        'runs': ['newtonian-pendulum-run'],
    }),
    'enabled': True,
}]


# ---------------------------------------------------------------------
# Config-knob upgrade pass (idempotent-by-name leaves existing rows
# alone, so knob additions to a seed's config blobs — e.g. a panel's
# `reveal` disclosure — would never reach a volume seeded earlier).
# A row is refreshed ONLY when its panel shape signature (the ordered
# (kind, ref) sequence) still matches the seed's: adding/removing/
# reordering panels in Configure mode changes the signature, so admin
# customizations are never clobbered — only knob-level drift inside an
# untouched layout is healed.
# ---------------------------------------------------------------------

def _panel_shape_sig(panels_json):
    """Ordered (kind, primary-ref) sequence of a panels_json blob — the
    layout identity knob edits don't change. None on unparseable JSON."""
    try:
        panels = json.loads(panels_json or '[]')
    except (TypeError, ValueError):
        return None
    if not isinstance(panels, list):
        return None
    return [
        (p.get('kind'), p.get('simSpaceRef') or p.get('graphRef')
         or p.get('icInterfaceRef') or '')
        for p in panels if isinstance(p, dict)
    ]


def upgrade_msim_rows(manager):
    """Refresh untouched MultiScaleSimulationDefinition rows from the
    current seeds:
      - panels_json (shape-signature guarded, see module note);
      - profile_ref, filled ONLY when the row has none (a family
        declaration is additive — an admin-set family is never
        overwritten)."""
    table = manager.objectTables.get('MultiScaleSimulationDefinition', {}) or {}
    rows_by_name = {getattr(r, 'name', None): r for r in table.values()}
    for seed in SEED_MULTI_SCALE_SIMS:
        row = rows_by_name.get(seed.get('name'))
        if row is None:
            continue
        changed = []
        seed_profile = seed.get('profile_ref') or ''
        if seed_profile and not (getattr(row, 'profile_ref', '') or ''):
            row.profile_ref = seed_profile
            changed.append(f'profile_ref={seed_profile}')
        seed_panels = seed.get('panels_json') or '[]'
        row_panels = getattr(row, 'panels_json', '') or '[]'
        if row_panels != seed_panels:
            row_sig = _panel_shape_sig(row_panels)
            if row_sig is None or row_sig != _panel_shape_sig(seed_panels):
                print(f'[SeedSimulations] msim "{seed.get("name")}" panels '
                      'customized; leaving as-is (upgrade skipped)', flush=True)
            else:
                row.panels_json = seed_panels
                changed.append('panels_json (layout unchanged, knobs refreshed)')
        if not changed:
            continue
        try:
            manager.db.saveInstanceInDB(row)
            print(f'[SeedSimulations] Upgraded msim "{seed.get("name")}": '
                  + '; '.join(changed), flush=True)
        except Exception as e:
            print(f'[SeedSimulations] msim "{seed.get("name")}" upgrade save '
                  f'failed: {e}', flush=True)
