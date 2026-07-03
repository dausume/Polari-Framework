"""
@module simulations.material_space_seed

Seed data for the MATERIAL CONDENSATION space + its gate — Milestone B:
the FIRST-PRINCIPLES stage of the multi-scale pendulum composition.

Dustin's canonical flow: choose a substance → the material simulation
searches temperature/pressure for conditions where the substance
condenses into a SOLID ball → the gate (`solid-ball-achievable`, the
first REAL no-code gate) proves it and reports the ball's properties →
those properties feed the pendulum's initial conditions via the stage
`derive` map. The solution SEARCH runs this simulation once per
candidate (target_temp, pressure_pa) point; substance identity travels
as fixedParams so different substances keep separate attempt sets.

Physics (simplified but honest, all authored as no-code
MatrixEquationOperations — see MaterialCondensationState's docstring
for the model equations).

Same registration pattern as the other sim seeds: extends the shared
SEED_* lists in place; polariServer imports it (transitively via
multi_scale_seed, which references the sim + gate by name).
"""

import json
import math

from simulations.seed_data import (
    _from_source,
    _element_source,
    _step_solution_pair,
    _next_sim_state,
    SEED_SIMULATION_DEFINITIONS,
    SEED_SIMULATION_RUNS,
    SEED_PENDULUM_STEP_SOLUTION_DEFS,
    SEED_PENDULUM_STEP_SOLUTIONS,
    SEED_PENDULUM_STEP_EQUATIONS,
)
from simulations.newtonian_pendulum_seed import _mat_step
from simulations.material_condensation_state import (
    MaterialCondensationState as _MCCls,
)
from matrices.seed_data import SEED_MATRIX_EQUATIONS, _eq

MATERIAL_SIM_DEF = 'material-condensation'
MATERIAL_RUN_NAME = 'material-condensation-baseline'
GATE_SOLUTION = 'solid-ball-achievable'
_MC = 'MaterialCondensationState'

# Reference pressure the melting-line shift is measured from (1 atm, Pa).
_P_REF = 101325.0

# Default substance = PARAFFIN WAX (the Milestone F test-case material):
# melts ~327 K, solid density ~900 kg/m^3.
_MATERIAL_PARAMS = {
    # --- substance identity (a search's fixedParams override these) ---
    'melt_temp_ref': 327.0,          # K at 1 atm
    'melt_slope_k_per_pa': 2.5e-7,   # dT_m/dP (K/Pa), Clausius-Clapeyron-ish
    'density_solid_ref': 900.0,      # kg/m^3 at density_ref_temp
    'thermal_expansion': 8e-4,       # volumetric, 1/K
    'density_ref_temp': 293.15,      # K
    # --- process point (the solution-search CANDIDATE variables) ---
    'target_temp': 300.0,            # K the chamber holds the sample at
    'pressure_pa': _P_REF,           # Pa
    # --- process dynamics + goal geometry ---
    'cool_rate': 4.0,                # 1/s Newtonian relaxation rate
    'ambient_temp': 293.15,          # K starting sample temperature
    'ball_radius_target': 0.08,      # m — the bob radius we want to cast
}

_MATERIAL_DT = 0.05
_MATERIAL_DURATION = 1.0  # 20 steps — enough to settle at cool_rate=4/s


# ---------------------------------------------------------------------------
# Matrix equations (extended into matrices.seed_data's shared list — this
# module is imported before _seedMatrixEquations runs, same in-place-extend
# pattern as the wind seed).
# ---------------------------------------------------------------------------

SEED_MATRIX_EQUATIONS.extend([
    _eq('material-cool-step',
        'Newtonian cooling toward the chamber target: exact relaxation over '
        'one dt (unconditionally stable at any cool_rate).',
        r'T\' = T + (T_{target} - T)\,(1 - e^{-k\,dt})',
        {'kind': 'expr',
         'expr': 'np.array([t + (tt - t) * (1.0 - np.exp(-cr * dt))])'},
        {'t': 't', 'tt': 'tt', 'cr': 'cr', 'dt': 'dt'},
        'material-condensation,thermal'),

    _eq('material-phase-check',
        'Solid-phase check against the pressure-shifted melting line: '
        '1 when T < T_m(P) = T_m,ref + slope*(P - 101325). The comparison '
        'produces a bool the multiply lifts to 1.0/0.0.',
        r'solid = [\,T < T_{m,ref} + s\,(P - P_{ref})\,]',
        {'kind': 'expr',
         'expr': 'np.array([1.0 * (t < tm_ref + slope * (p - 101325.0))])'},
        {'t': 't', 'tm_ref': 'tm_ref', 'slope': 'slope', 'p': 'p'},
        'material-condensation,phase'),

    _eq('material-density',
        'Density at temperature via volumetric thermal expansion: '
        'rho(T) = rho_ref * (1 - alpha*(T - T_ref)). Meaningful for the '
        'solid phase; computed every step regardless.',
        r'\rho(T) = \rho_{ref}\,(1 - \alpha\,(T - T_{ref}))',
        {'kind': 'expr',
         'expr': 'np.array([rho0 * (1.0 - alpha * (t - t_ref))])'},
        {'rho0': 'rho0', 'alpha': 'alpha', 't': 't', 't_ref': 't_ref'},
        'material-condensation,density'),

    _eq('material-ball-mass',
        'Mass of the target ball at the current density: '
        'm = rho * (4/3) * pi * r^3.',
        r'm = \rho\,\tfrac{4}{3}\pi r^{3}',
        {'kind': 'expr',
         'expr': 'np.array([rho * (4.0 / 3.0) * np.pi * r ** 3])'},
        {'rho': 'rho', 'r': 'r'},
        'material-condensation,geometry'),
])


# ---------------------------------------------------------------------------
# The condensation step — ONE Complete solution on the state class.
# ---------------------------------------------------------------------------

# SHAPE CONVENTION (learned the hard way): each equation returns a
# length-1 vector (np.array([...])), which lands in context as a
# 1-element LIST. Chained operands must therefore be ELEMENT-extracted
# back to scalars — feeding the list straight in double-wraps the next
# np.array([...]) into a (1,1) matrix whose element-extraction leaves a
# LIST on the state row (which the object tree wraps as an uncopyable
# polariList and poisons the next step's context).
_MATERIAL_STEPS = [
    _mat_step('CoolStep', 't_new', 'material-cool-step',
              [('t', _from_source('self.temperature')),
               ('tt', _from_source('self.target_temp')),
               ('cr', _from_source('self.cool_rate')),
               ('dt', _from_source('self.dt'))],
              "T' = T + (target - T)(1 - exp(-k dt))"),
    _mat_step('PhaseCheck', 'solid_flag', 'material-phase-check',
              [('t', _element_source('t_new', 0)),
               ('tm_ref', _from_source('self.melt_temp_ref')),
               ('slope', _from_source('self.melt_slope_k_per_pa')),
               ('p', _from_source('self.pressure_pa'))],
              'solid = T\' < T_m(P)'),
    _mat_step('Density', 'rho_now', 'material-density',
              [('rho0', _from_source('self.density_solid_ref')),
               ('alpha', _from_source('self.thermal_expansion')),
               ('t', _element_source('t_new', 0)),
               ('t_ref', _from_source('self.density_ref_temp'))],
              'rho(T\')'),
    _mat_step('BallMass', 'm_ball', 'material-ball-mass',
              [('rho', _element_source('rho_now', 0)),
               ('r', _from_source('self.ball_radius_target'))],
              'm = rho (4/3) pi r^3'),
]

_MATERIAL_OUTPUT_MAP = {
    'temperature': _element_source('t_new', 0),
    'phase_solid': _element_source('solid_flag', 0),
    'density': _element_source('rho_now', 0),
    'ball_mass': _element_source('m_ball', 0),
    'ball_radius': 'self.ball_radius_target',
}

_MC_STEP_DEF, _MC_STEP_META, _MC_STEP_EQ = _step_solution_pair(
    name=f'{MATERIAL_SIM_DEF}.sample.step',
    description=('Complete — one condensation-process step: relax the sample '
                 'temperature toward the chamber target, check the phase '
                 'against the pressure-shifted melting line, and evaluate the '
                 'density + target-ball mass at the new temperature.'),
    target_class=_MC,
    expected_inputs=['temperature', 'target_temp', 'pressure_pa', 'cool_rate',
                     'melt_temp_ref', 'melt_slope_k_per_pa',
                     'density_solid_ref', 'thermal_expansion',
                     'density_ref_temp', 'ball_radius_target', 'dt'],
    compute_steps=_MATERIAL_STEPS,
    output_field_to_context=_MATERIAL_OUTPUT_MAP,
    sim_step_role='simStepComplete', order_index=0, depends_on=[],
    sim_def_ref=MATERIAL_SIM_DEF,
)


# ---------------------------------------------------------------------------
# THE GATE — `solid-ball-achievable`, the first real no-code gate.
#
# Executed by the stage evaluator (multi_scale_stages.evaluate_stage_gate)
# over the flattened stage-results context ('<Class>.<field>' keys of the
# run's LATEST rows + 'params.*'). The graph is deliberately minimal:
# an InitialState entry flowing into a SimStepNextState terminal whose
# output mappings LIFT the flattened values into the gate's output
# contract: `complete` (numeric truthiness — the evaluator's fallback
# when no textual `outcome` is set) plus the proven ball's properties,
# which the stage's `derive` map sends into the pendulum's parameters.
# ---------------------------------------------------------------------------

def _gate_entry(next_state):
    return {
        'stateName': 'GateEntry',
        'id': 'GateEntry-state',
        'index': 0,
        'shapeType': 'circle',
        'solutionName': GATE_SOLUTION,
        'stateClass': 'InitialState',
        'boundObjectClass': 'InitialState',
        'boundObjectFieldValues': {
            'displayName': 'GateEntry',
            'description': ('Entry — receives the stage run\'s flattened '
                            'results (latest row fields + params) as context.'),
            'inputParams': [],
            'codingComment': ('The stage evaluator supplies '
                              'MaterialCondensationState.* and params.* keys.'),
        },
        'stateSvgRadius': 60,
        'layerName': 'start-layer',
        'stateLocationX': 160,
        'stateLocationY': 260,
        'stateSvgName': 'circle',
        'backgroundColor': '#1e88e5',
        'slots': [{
            'index': 0, 'stateName': 'GateEntry', 'slotAngularPosition': 0,
            'connectors': [{'id': 1, 'sourceSlot': 0, 'sinkSlot': 0,
                            'targetStateName': next_state}],
            'isInput': False, 'allowOneToMany': True, 'allowManyToOne': False,
            'label': 'Out',
        }],
        'slotRadius': 5,
    }


_GATE_MAPPINGS = [
    # The verdict: numeric truthiness of the latest row's phase flag.
    {'outputFieldName': 'complete',
     'valueSource': _from_source(f'{_MC}.phase_solid')},
    # The proven ball's properties — consumed by the stage `derive` map.
    {'outputFieldName': 'ball_mass',
     'valueSource': _from_source(f'{_MC}.ball_mass')},
    {'outputFieldName': 'ball_radius',
     'valueSource': _from_source(f'{_MC}.ball_radius')},
    {'outputFieldName': 'ball_density',
     'valueSource': _from_source(f'{_MC}.density')},
]

_GATE_TERMINAL = _next_sim_state(
    'ProveSolidBall', 520, 260, _GATE_MAPPINGS,
    target_class=_MC, index=1, slot_id_in=2,
    coding_comment=('Lifts the stage results into the gate contract: '
                    'complete = phase_solid; ball_* = the proven ball.'),
)
_GATE_STATES = [_gate_entry('ProveSolidBall'), _GATE_TERMINAL]
for _s in _GATE_STATES:
    _s['solutionName'] = GATE_SOLUTION

_GATE_SOLUTION_DEF = {
    'name': GATE_SOLUTION,
    'description': ('Gate — a solid ball is achievable: passes when the '
                    'material run\'s latest state is solid-phase, and reports '
                    'the ball\'s mass/radius/density for downstream initial '
                    'conditions. The first-principles condition of the '
                    'multi-scale pendulum composition.'),
    'function_name': 'solid_ball_achievable',
    'target_runtime': 'python_backend',
    'definition': json.dumps({
        'solutionName': GATE_SOLUTION,
        'description': 'Valid-solution condition for the material space.',
        'stateInstances': _GATE_STATES,
    }),
}


# ---------------------------------------------------------------------------
# Sim def + baseline run + step-0 row + registration into the seed lists.
# ---------------------------------------------------------------------------

SEED_SIMULATION_DEFINITIONS.append({
    'name': MATERIAL_SIM_DEF,
    'description': (
        'Material condensation space — the first-principles stage: hold a '
        'substance at a candidate temperature/pressure, relax to it, and '
        'check whether it condenses solid (pressure-shifted melting line), '
        'evaluating the density and the target ball\'s mass. The solution '
        'search sweeps (target_temp, pressure_pa) candidates; substance '
        'identity arrives as fixedParams / per-run parameter overrides.'
    ),
    'intent': 'search',
    'participating_sim_state_classes_json': json.dumps([_MC]),
    'time_step_seconds': _MATERIAL_DT,
    'duration_seconds': _MATERIAL_DURATION,
    'recording_interval_steps': 1,
    'initial_conditions_overrides_json': '{}',
    'parameters_json': json.dumps(_MATERIAL_PARAMS),
    'termination_predicate': '',
    'time_unit': 'second',
})

SEED_SIMULATION_RUNS.append({
    'name': MATERIAL_RUN_NAME,
    'simulation_ref': MATERIAL_SIM_DEF,
    'status': 'pending',
    'started_at': '',
    'completed_at': '',
    'total_steps': int(math.ceil(_MATERIAL_DURATION / _MATERIAL_DT)),
    'recorded_steps': 1,
    'last_recorded_step': 0,
    'error_message': '',
    'label': 'Material condensation — baseline (wax at 300 K, 1 atm)',
})

SEED_MATERIAL_ROWS = [{
    'name': f'{MATERIAL_RUN_NAME}-material-condensation-0',
    'simulation_run_ref': MATERIAL_RUN_NAME,
    'step': 0,
    'time': 0.0,
    **_MCCls.default_initial_field_values,
}]

SEED_PENDULUM_STEP_SOLUTION_DEFS.extend([_MC_STEP_DEF, _GATE_SOLUTION_DEF])
SEED_PENDULUM_STEP_SOLUTIONS.extend([_MC_STEP_META])
SEED_PENDULUM_STEP_EQUATIONS.extend(_MC_STEP_EQ)
