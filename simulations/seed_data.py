"""
Seed data for the simulations module — the pendulum-2d demo, composed
from two `*SimState` classes:

  * PendulumBobSimState    — the bob's recorded trajectory (one circle
                             per visible timestep)
  * PendulumStringSimState — the string's recorded trajectory (one line
                             from the pivot to the bob per visible step)

Both streams share a single SimulationRun and the same `time` grid, so
the viewer's scrubber animates them in lockstep. When the runtime
engine (Path-A simulation no-code) lands, the SAME SimulationRun will
be regenerable by running the bound step solution; today the trajectory
is precomputed via semi-implicit Euler so visualization works while the
engine is being built.

Idempotent: existing rows are left alone (matches the pattern in
simSpace2D/seed_data.py + simSpace3D/seed_data.py).
"""

import json
import math
from datetime import datetime, timezone


# Physical constants for the demo. Identical to what the future step
# function (no-code) will read from SimulationDefinition.parameters_json.
DEMO_G = 9.81           # gravitational acceleration (m/s²)
DEMO_L = 1.0            # pendulum length (m)
DEMO_MASS = 1.0         # bob mass (kg)
DEMO_THETA_0 = math.pi / 6   # 30° initial deflection
DEMO_OMEGA_0 = 0.0           # released from rest
DEMO_DURATION = 8.0     # seconds — about 4 full periods at L=1, g=9.81
DEMO_DT = 0.01          # 10 ms timestep — 800 computed steps total
DEMO_RECORDING_INTERVAL = 4  # record every 4 steps → ~200 persisted rows

SIM_DEF_NAME = 'pendulum-2d'
SIM_RUN_NAME = 'pendulum-2d-precomputed-001'


def _compute_pendulum_trajectory():
    """Semi-implicit Euler integration of θ'' = −(g/L) sin θ.

    Returns two parallel row-streams:
      bob_rows    — fields for PendulumBobSimState
      string_rows — fields for PendulumStringSimState

    Both keyed by (run, step) — same indexing so the viewer treats them
    as synchronized sub-system snapshots.
    """
    g, L, mass = DEMO_G, DEMO_L, DEMO_MASS
    theta, omega = DEMO_THETA_0, DEMO_OMEGA_0
    dt = DEMO_DT
    total_steps = int(math.ceil(DEMO_DURATION / dt))

    bob_rows = []
    string_rows = []
    for step in range(total_steps + 1):
        t = step * dt
        # Cartesian bob position (pivot at origin, +y up).
        x = L * math.sin(theta)
        y = -L * math.cos(theta)
        # Energies — KE + PE measured from lowest point.
        ke = 0.5 * mass * (L * omega) ** 2
        pe = mass * g * L * (1.0 - math.cos(theta))
        # String tension — radial-gravity + centripetal contributions.
        # A real solver would expose this directly; the approximation is
        # exact at the equilibrium point and a useful diagnostic elsewhere.
        tension = mass * g * math.cos(theta) + mass * L * (omega ** 2)

        if (
            step == 0
            or step == total_steps
            or step % DEMO_RECORDING_INTERVAL == 0
        ):
            # Composite-name pattern: "<run>-<role>-<step>". The role
            # segment ('bob' / 'string') keeps the two streams distinct
            # in the framework's name-keyed storage.
            # 3D embedding with the default swing-plane normal (0,0,1):
            #   world = x·normalize(Yup × n) + y·Yup → (x, y, 0).
            # The pendulum-3d-viz scene reads world_* off these rows. (Live
            # runs compute world_* via the no-code MatrixEquationOperation
            # embedding; the seeded demo precomputes it, like x/y.)
            bob_rows.append({
                'name': f'{SIM_RUN_NAME}-bob-{step}',
                'simulation_run_ref': SIM_RUN_NAME,
                'step': step,
                'time': round(t, 6),
                'theta': round(theta, 6),
                'omega': round(omega, 6),
                'x': round(x, 6),
                'y': round(y, 6),
                'energy_total': round(ke + pe, 6),
                'plane_nx': 0.0, 'plane_ny': 0.0, 'plane_nz': 1.0,
                'world_x': round(x, 6), 'world_y': round(y, 6), 'world_z': 0.0,
            })
            string_rows.append({
                'name': f'{SIM_RUN_NAME}-string-{step}',
                'simulation_run_ref': SIM_RUN_NAME,
                'step': step,
                'time': round(t, 6),
                'bob_x': round(x, 6),
                'bob_y': round(y, 6),
                'tension': round(tension, 6),
                'plane_nx': 0.0, 'plane_ny': 0.0, 'plane_nz': 1.0,
                'world_x': round(x, 6), 'world_y': round(y, 6), 'world_z': 0.0,
            })
        # Advance state (semi-implicit Euler — energy-stable enough for
        # short reference runs).
        alpha = -(g / L) * math.sin(theta)
        omega = omega + alpha * dt
        theta = theta + omega * dt
    return bob_rows, string_rows


SEED_PENDULUM_BOB_ROWS, SEED_PENDULUM_STRING_ROWS = _compute_pendulum_trajectory()


# SimulationDefinition: parameters the engine will eventually replay.
SEED_SIMULATION_DEFINITIONS = [
    {
        'name': SIM_DEF_NAME,
        'description': (
            '2D pendulum reference — 30° initial deflection, no friction. '
            'Composed of PendulumBobSimState (the bob) + PendulumStringSimState '
            '(the rod). Step solutions are wired via SimulationExecutionSolution '
            'rows whose simulation_definition_ref points at this row.'
        ),
        'participating_sim_state_classes_json': (
            '["PendulumBobSimState","PendulumStringSimState"]'
        ),
        'time_step_seconds': DEMO_DT,
        'duration_seconds': DEMO_DURATION,
        'recording_interval_steps': DEMO_RECORDING_INTERVAL,
        # Class-level defaults (declared on each *SimState) cover the
        # 30° release at rest baseline. No sim-level overrides needed
        # for the canonical demo; left empty to exercise the
        # "class-defaults-only" code path.
        'initial_conditions_overrides_json': '{}',
        'parameters_json': (
            f'{{"g": {DEMO_G}, "L": {DEMO_L}, "mass": {DEMO_MASS}}}'
        ),
        'termination_predicate': '',
        'time_unit': 'second',
    },
]


# SimulationRun: the precomputed run that both state streams belong to.
SEED_SIMULATION_RUNS = [
    {
        'name': SIM_RUN_NAME,
        'simulation_ref': SIM_DEF_NAME,
        # 'precomputed' is the dedicated status for trajectories baked at
        # seed time (vs. live runs which transition pending→running→complete).
        'status': 'precomputed',
        'started_at': datetime.now(timezone.utc).isoformat(),
        'completed_at': datetime.now(timezone.utc).isoformat(),
        'total_steps': int(math.ceil(DEMO_DURATION / DEMO_DT)),
        'recorded_steps': len(SEED_PENDULUM_BOB_ROWS),
        'last_recorded_step': (
            SEED_PENDULUM_BOB_ROWS[-1]['step'] if SEED_PENDULUM_BOB_ROWS else 0
        ),
        'error_message': '',
        'label': 'Pendulum 2D — precomputed reference',
    },
]


# SimVariable rows — domain metadata about each tracked field. Read by
# tooltips and (future) plotting axes; not consumed by the simulator
# itself.
SEED_SIM_VARIABLES = [
    # Bob state variables (the integrator state + Cartesian projection).
    {
        'name': 'PendulumBobSimState.theta',
        'sim_state_class_name': 'PendulumBobSimState',
        'field_name': 'theta',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'radian',
        'role': 'state',
        'description': 'Angle from vertical (downward) — positive swings right.',
    },
    {
        'name': 'PendulumBobSimState.omega',
        'sim_state_class_name': 'PendulumBobSimState',
        'field_name': 'omega',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'rad/s',
        'role': 'state',
        'description': 'Angular velocity — dθ/dt.',
    },
    {
        'name': 'PendulumBobSimState.x',
        'sim_state_class_name': 'PendulumBobSimState',
        'field_name': 'x',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'm',
        'role': 'derived',
        'description': 'Cartesian X position of the bob (L·sin θ).',
    },
    {
        'name': 'PendulumBobSimState.y',
        'sim_state_class_name': 'PendulumBobSimState',
        'field_name': 'y',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'm',
        'role': 'derived',
        'description': 'Cartesian Y position of the bob (−L·cos θ).',
    },
    {
        'name': 'PendulumBobSimState.energy_total',
        'sim_state_class_name': 'PendulumBobSimState',
        'field_name': 'energy_total',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'J',
        'role': 'energy',
        'description': 'KE + PE — flat on a well-behaved integrator.',
    },
    # String state variables.
    {
        'name': 'PendulumStringSimState.bob_x',
        'sim_state_class_name': 'PendulumStringSimState',
        'field_name': 'bob_x',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'm',
        'role': 'derived',
        'description': 'String terminus X — matches the bob.',
    },
    {
        'name': 'PendulumStringSimState.bob_y',
        'sim_state_class_name': 'PendulumStringSimState',
        'field_name': 'bob_y',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'm',
        'role': 'derived',
        'description': 'String terminus Y — matches the bob.',
    },
    {
        'name': 'PendulumStringSimState.tension',
        'sim_state_class_name': 'PendulumStringSimState',
        'field_name': 'tension',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'N',
        'role': 'diagnostic',
        'description': 'String tension — centripetal + radial-gravity (mg·cos θ + mLω²).',
    },
    # Derived (equation-computed) variables. No sim_state_class_name /
    # field_name — these are produced by SimSpaceEvaluationEquation rows
    # at snapshot compile time. Unit + precision still live here so the
    # readout components have one place to read them from.
    {
        'name': 'kinetic_energy',
        'sim_state_class_name': '',
        'field_name': '',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'J',
        'precision': 3,
        'role': 'energy',
        'description': 'Kinetic energy of the bob (½ m L² ω²).',
    },
    {
        'name': 'potential_energy',
        'sim_state_class_name': '',
        'field_name': '',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'J',
        'precision': 3,
        'role': 'energy',
        'description': 'Potential energy of the bob (m g L (1 − cos θ)).',
    },
    {
        'name': 'total_energy',
        'sim_state_class_name': '',
        'field_name': '',
        'simulation_definition_name': SIM_DEF_NAME,
        'unit': 'J',
        'precision': 3,
        'role': 'energy',
        'description': 'KE + PE — should stay flat for an energy-stable integrator.',
    },
]


# EquationDefinitions for the three live readouts. Authored as
# `evaluate` operations — the executor substitutes bindings then computes.
def _equation_def(name, description, latex):
    return {
        'name': name,
        'description': description,
        'source_class': SIM_DEF_NAME,
        'definition': json.dumps({
            'latexExpression': latex,
            'operationType': 'evaluate',
            'variableBindings': [],   # bindings live on the SimSpaceEvaluationEquation
            'bounds': None,
            'options': {},
            'resultSpec': {'type': 'scalar'},
        }),
    }


SEED_PENDULUM_EQUATIONS = [
    _equation_def(
        name='pendulum-2d.kinetic-energy',
        description='Kinetic energy of the pendulum bob: ½ m L² ω².',
        # `\omega` reads as the angular-velocity symbol; bindings on the
        # SimSpaceEvaluationEquation row will map it to PendulumBobSimState.omega.
        latex=r'\frac{1}{2} \cdot m \cdot L^{2} \cdot \omega^{2}',
    ),
    _equation_def(
        name='pendulum-2d.potential-energy',
        description='Potential energy of the pendulum bob: m g L (1 − cos θ).',
        latex=r'm \cdot g \cdot L \cdot (1 - \cos(\theta))',
    ),
    _equation_def(
        name='pendulum-2d.total-energy',
        description='Total mechanical energy of the pendulum bob — KE + PE inlined.',
        latex=(
            r'\frac{1}{2} \cdot m \cdot L^{2} \cdot \omega^{2} '
            r'+ m \cdot g \cdot L \cdot (1 - \cos(\theta))'
        ),
    ),
]


# SimSpaceEvaluationEquation rows — one per readout overlay on the
# pendulum-2d-viz scene. The variable bindings here are what glue the
# equation's symbols to live simulation data; the snapshot compile pass
# evaluates each at every recorded step.
def _binding_param(symbol, software_name, param_name):
    return {
        'symbol': symbol,
        'softwareName': software_name,
        'source': {'kind': 'param', 'name': param_name},
    }


def _binding_sim_state(symbol, software_name, class_name, field):
    return {
        'symbol': symbol,
        'softwareName': software_name,
        'source': {'kind': 'simState', 'class': class_name, 'field': field},
    }


_PENDULUM_KE_PE_BINDINGS = [
    _binding_param('m', 'mass', 'mass'),
    _binding_param('L', 'L', 'L'),
    _binding_param('g', 'g', 'g'),
    _binding_sim_state(r'\theta', 'theta', 'PendulumBobSimState', 'theta'),
    _binding_sim_state(r'\omega', 'omega', 'PendulumBobSimState', 'omega'),
]


# --------------------------------------------------------------------------
# Step solutions — SimulationExecutionSolution rows authored as one
# SimStepNextState node each. Each output field carries its own value
# source that evaluates against the engine context (prev-row fields +
# params + dt/step + deps' current-step outputs).
# --------------------------------------------------------------------------

BOB_GRAVITY_SOLUTION_NAME    = f'{SIM_DEF_NAME}.bob.gravity-force'
BOB_INTEGRATOR_SOLUTION_NAME = f'{SIM_DEF_NAME}.bob.integrator'
STRING_STEP_SOLUTION_NAME    = f'{SIM_DEF_NAME}.string-step'


def _from_latex(latex: str):
    return {'sourceType': 'from_latex', 'latexExpression': latex}


def _simulation_step_initial_state(
    state_name, location_x, next_state, slot_id,
    sim_state_class_name, expected_fields,
    sim_step_role='simStepComplete',
    coding_comment='',
):
    """SimulationStateStep entry node. Declares:
      - the target *SimState class the step solution produces
      - the prev-step fields it reads (for documentation + so the
        editor doesn't fall into "No Solution Object defined")
      - the simStepRole that selects the runner's dispatch mode for
        this solution: simStepComplete | simStepPartial | simStepComposition.
    Roles MUST be set explicitly — the runner refuses to dispatch a
    binding whose step solution doesn't declare one.
    """
    input_params = [
        {'name': f, 'type': 'float', 'description': f'prev-step or param value for {f}'}
        for f in expected_fields
    ]
    role_terminator = {
        'simStepComplete':    'SimStepNextState',
        'simStepPartial':     'SimStepContribution',
        'simStepComposition': 'SimStepNextState',
    }.get(sim_step_role, 'SimStepNextState')
    return {
        'stateName': state_name,
        'id': f'{state_name}-state',
        'index': 0,
        'shapeType': 'circle',
        'solutionName': '',  # patched at row build time
        'stateClass': 'SimulationStateStep',
        'boundObjectClass': 'SimulationStateStep',
        'boundObjectFieldValues': {
            'displayName': state_name,
            'description': (
                f'Runs once per simulation timestep as a {sim_step_role} '
                f'solution. Reads prev-step {sim_state_class_name} fields + '
                f'simulation params from context; ends at a '
                f'{role_terminator} terminator.'
            ),
            'simStateClassName': sim_state_class_name,
            'simStepRole': sim_step_role,
            'expectedFields': expected_fields,
            'inputParams': input_params,
            # Per-state authoring note rendered by the overlay's
            # coding-comment strip. Empty by default; seed helpers pass
            # math/physics intuition through so the editor can read the
            # "why this state exists" without leaving the canvas.
            'codingComment': coding_comment,
        },
        # Step-solution states render large by default so the analyst
        # can read the declared class + expected fields without having
        # to click in. Generic no-code states keep their smaller
        # defaults — this is opt-in via the simulation seed helpers.
        'stateSvgRadius': 90,
        'layerName': 'start-layer',
        'stateLocationX': location_x,
        'stateLocationY': 260,
        'stateSvgName': 'circle',
        'backgroundColor': '#1e88e5',
        'slots': [
            {
                'index': 0,
                'stateName': state_name,
                'slotAngularPosition': 0,
                'connectors': [{
                    'id': slot_id,
                    'sourceSlot': 0,
                    'sinkSlot': 0,
                    'targetStateName': next_state,
                }],
                'isInput': False,
                'allowOneToMany': True,
                'allowManyToOne': False,
                'label': 'Out',
            },
        ],
        'slotRadius': 5,
    }


def _next_sim_state(state_name, location_x, location_y, output_mappings,
                    target_class, index, slot_id_in,
                    coding_comment=''):
    """SimStepNextState — terminator for `simStepComplete` and
    `simStepComposition` step solutions. Declares the new `*SimState`
    row's field values by pulling each from a context variable that the
    upstream chain populated.

    `simStateClassName` mirrors the SimulationStateStep entry's
    declaration so the editor can tell at a glance which class this
    solution produces a row for."""
    return {
        'stateName': state_name,
        'id': f'{state_name}-state',
        'index': index,
        'shapeType': 'hexagon',
        'solutionName': '',
        'stateClass': 'SimStepNextState',
        'boundObjectClass': 'SimStepNextState',
        'boundObjectFieldValues': {
            'displayName': state_name,
            'description': (
                f'Commits the next {target_class} row from the variables '
                'computed above. Terminal — the engine stops walking here '
                'and the SimulationRunner projects the final context onto '
                'a new row.'
            ),
            'simStateClassName': target_class,
            'outputMappings': output_mappings,
            'codingComment': coding_comment,
        },
        'stateSvgRadius': 110,
        'layerName': 'next-sim-state-layer',
        'stateLocationX': location_x,
        'stateLocationY': location_y,
        'stateSvgName': 'hexagon',
        'backgroundColor': '#0f5d29',
        'slots': [
            {
                'index': 0,
                'stateName': state_name,
                'slotAngularPosition': 180,
                'connectors': [],
                'isInput': True,
                'allowOneToMany': False,
                'allowManyToOne': True,
                'label': 'In',
            },
        ],
        'slotRadius': 5,
    }


def _sim_step_contribution_terminator(
    state_name, location_x, location_y, contribution_mappings,
    target_class, index, slot_id_in,
    coding_comment='',
):
    """SimStepContribution — terminator for `simStepPartial` step
    solutions. Emits a sparse `{fieldName → {value, op}}` payload that
    the SimulationRunner harvests + aggregates with any other Partials
    targeting the same *SimState class.

    `contribution_mappings` is the runner-ready list:
        [{'outputFieldName': str, 'valueSource': dict, 'op': str}, ...]
    where `op` is one of 'set' | 'add' | 'mul' | 'min' | 'max' — the
    per-field merge semantic. Most physics-style contributions use
    'add' (forces sum into α) but operator-splitting compositions can
    mix ops freely."""
    return {
        'stateName': state_name,
        'id': f'{state_name}-state',
        'index': index,
        'shapeType': 'hexagon',
        'solutionName': '',
        'stateClass': 'SimStepContribution',
        'boundObjectClass': 'SimStepContribution',
        'boundObjectFieldValues': {
            'displayName': state_name,
            'description': (
                f'Emits a sparse {target_class} contribution payload. '
                'The SimulationRunner merges this with any other Partials '
                'for this class before handing the result to the '
                'Composition solution.'
            ),
            'simStateClassName': target_class,
            'outputMappings': contribution_mappings,
            'codingComment': coding_comment,
        },
        'stateSvgRadius': 110,
        'layerName': 'sim-step-contribution-layer',
        'stateLocationX': location_x,
        'stateLocationY': location_y,
        'stateSvgName': 'hexagon',
        'backgroundColor': '#a8501c',
        'slots': [
            {
                'index': 0,
                'stateName': state_name,
                'slotAngularPosition': 180,
                'connectors': [],
                'isInput': True,
                'allowOneToMany': False,
                'allowManyToOne': True,
                'label': 'In',
            },
        ],
        'slotRadius': 5,
    }


def _equation_definition(name, description, latex, default_bindings,
                         source_class):
    """Build a SolutionDefinition-compatible EquationDefinition row.
    Each pendulum math step has one of these — the LaTeX + the symbol
    binding defaults — and a CalculusOperation in the graph invokes
    it by name.

    `default_bindings` is a list of {symbol, defaultSource} entries.
    The CalculusOperation handler will use these unless the host state
    overrides per-symbol. Pointing them at `self.<var>` lets the
    runner's context merge resolve them automatically.
    """
    config = {
        'latexExpression': latex,
        'operationType': 'evaluate',
        'variableBindings': default_bindings,
        'bounds': None,
        'options': {},
        'resultSpec': {'type': 'scalar'},
    }
    return {
        'name': name,
        'description': description,
        'source_class': source_class,
        'definition': json.dumps(config),
    }


def _calculus_operation(state_name, location_x, location_y, equation_name,
                        result_var, description, index,
                        next_state, next_connector_id,
                        coding_comment=''):
    """One CalculusOperation node that invokes a saved
    EquationDefinition by name. The equation's own default bindings
    (typically `from_source_object` paths reading `self.<x>`) resolve
    each symbol from the engine context, and the numeric result is
    written to `result_var`. The node's output slot wires to
    `next_state`.

    Why CalculusOperation (vs. VariableAssignment+from_latex): the
    no-code editor already has a first-class UI for this state — pick
    the equation, see/override bindings, type-aware result preview —
    so the analyst can inspect + edit the math without the editor
    needing custom UI for inline LaTeX. The variable produced stays a
    plain numeric (float), which matches what the simulation actually
    needs."""
    return {
        'stateName': state_name,
        'id': f'{state_name}-state',
        'index': index,
        'shapeType': 'circle',
        'solutionName': '',
        'stateClass': 'CalculusOperation',
        'boundObjectClass': 'CalculusOperation',
        'boundObjectFieldValues': {
            'displayName': state_name,
            'description': description,
            'equationName': equation_name,
            'equationId': '',
            'bindings': [],  # equation's own defaults are sufficient
            'resultTarget': 'result_variable',
            'resultFieldPath': '',
            'resultVariableName': result_var,
            'codingComment': coding_comment,
        },
        'stateSvgRadius': 95,
        'layerName': 'math-layer',
        'stateLocationX': location_x,
        'stateLocationY': location_y,
        'stateSvgName': 'circle',
        'backgroundColor': '#FFB74D',
        'slots': [
            {
                'index': 0,
                'stateName': state_name,
                'slotAngularPosition': 180,
                'connectors': [],
                'isInput': True,
                'allowOneToMany': False,
                'allowManyToOne': True,
                'label': 'In',
            },
            {
                'index': 1,
                'stateName': state_name,
                'slotAngularPosition': 0,
                'connectors': [{
                    'id': next_connector_id,
                    'sourceSlot': 1,
                    'sinkSlot': 0,
                    'targetStateName': next_state,
                }],
                'isInput': False,
                'allowOneToMany': True,
                'allowManyToOne': False,
                'label': result_var,
                'passthroughVariableName': result_var,
            },
        ],
        'slotRadius': 5,
    }


def _matrix_equation_operation(state_name, location_x, location_y,
                               matrix_equation_name, operand_bindings,
                               result_var, description, index,
                               next_state, next_connector_id,
                               coding_comment=''):
    """One MatrixEquationOperation node — invokes a saved
    MatrixEquationDefinition by name, binding its operands from the
    engine context (scalars OR arrays via the 'array' source kind) and
    storing the array/scalar result in `result_var`. Makes the matrix /
    vector engine callable from a simulation step (used here for the
    2D→3D plane embedding: world = x·normalize(Yup×n) + y·Yup)."""
    return {
        'stateName': state_name,
        'id': f'{state_name}-state',
        'index': index,
        'shapeType': 'circle',
        'solutionName': '',
        'stateClass': 'MatrixEquationOperation',
        'boundObjectClass': 'MatrixEquationOperation',
        'boundObjectFieldValues': {
            'displayName': state_name,
            'description': description,
            'matrixEquationName': matrix_equation_name,
            'operandBindings': operand_bindings,
            'resultTarget': 'result_variable',
            'resultFieldPath': '',
            'resultVariableName': result_var,
            'codingComment': coding_comment,
        },
        'stateSvgRadius': 95,
        'layerName': 'math-layer',
        'stateLocationX': location_x,
        'stateLocationY': location_y,
        'stateSvgName': 'circle',
        'backgroundColor': '#9575CD',
        'slots': [
            {'index': 0, 'stateName': state_name, 'slotAngularPosition': 180,
             'connectors': [], 'isInput': True, 'allowOneToMany': False,
             'allowManyToOne': True, 'label': 'In'},
            {'index': 1, 'stateName': state_name, 'slotAngularPosition': 0,
             'connectors': [{'id': next_connector_id, 'sourceSlot': 1, 'sinkSlot': 0,
                             'targetStateName': next_state}],
             'isInput': False, 'allowOneToMany': True, 'allowManyToOne': False,
             'label': result_var, 'passthroughVariableName': result_var},
        ],
        'slotRadius': 5,
    }


def _from_source(path):
    """Shorthand for the no-code value-source that reads a context key
    by name. `self.<x>` and bare `<x>` are both resolved by the engine."""
    return {'sourceType': 'from_source_object', 'sourceObjectPath': path}


def _element_source(vec_var, index):
    """Value-source that extracts one component from an array-valued
    context variable (e.g. world_vec[0])."""
    return {'sourceType': 'element', 'index': index, 'source': _from_source(vec_var)}


def _array_source(elements):
    """Value-source that builds a vector/array from element sources
    (each a ValueSourceConfig or a literal)."""
    return {'sourceType': 'array', 'elements': elements}


def _step_solution_pair(name, description, target_class, expected_inputs,
                        compute_steps, output_field_to_context,
                        sim_step_role='simStepComplete',
                        order_index=0, depends_on=None,
                        entry_comment='', terminator_comment='',
                        sim_def_ref=SIM_DEF_NAME):
    """Build the three rows a simulation step solution needs:

      1. N `EquationDefinition` rows — one per math step in the chain.
      2. A `SolutionDefinition` whose graph is
            SimulationStateStep(role) → CalculusOperation × N → <terminator>
      3. A `SimulationExecutionSolution` metadata row pointing at the
         SolutionDefinition by name.

    Returns (solution_def_row, metadata_row, equation_rows).

    `sim_step_role` selects the runner dispatch mode AND the terminator:

        simStepComplete    → SimStepNextState. One solution per class
                             producing the full next row.
        simStepPartial     → SimStepContribution. Zero-or-more per class;
                             emits a sparse field-delta payload that the
                             runner aggregates with other Partials.
        simStepComposition → SimStepNextState. At most one per class;
                             reads the merged baseline (Partials' deltas
                             already applied) and produces the final row.

    `output_field_to_context` shape depends on the role:

        Complete / Composition (terminator = SimStepNextState):
            { simStateField: contextVar, ... }
        Partial (terminator = SimStepContribution):
            { simStateField: (contextVar, op), ... }
            where `op` ∈ {set, add, mul, min, max} per-field merge rule.

    `compute_steps` is an ordered list of dicts:
        { 'name', 'var', 'latex', 'bindings', 'description' }
    where `bindings` is the symbol → `self.<field>` map fed into the
    CalculusOperation's referenced EquationDefinition.
    """
    valid_roles = ('simStepComplete', 'simStepPartial', 'simStepComposition')
    if sim_step_role not in valid_roles:
        raise ValueError(
            f"sim_step_role must be one of {valid_roles}, got {sim_step_role!r}"
        )
    states = []
    equations = []
    spacing_x = 340
    base_y = 280
    start_state_name = 'Start'
    end_state_name = 'CommitNextRow'

    initial = _simulation_step_initial_state(
        start_state_name,
        location_x=160,
        next_state=(compute_steps[0]['name'] if compute_steps else end_state_name),
        slot_id=1,
        sim_state_class_name=target_class,
        expected_fields=expected_inputs,
        sim_step_role=sim_step_role,
        coding_comment=entry_comment,
    )
    states.append(initial)

    # Build one EquationDefinition + one CalculusOperation per step.
    next_connector_id = 2
    for i, step in enumerate(compute_steps):
        is_last = (i == len(compute_steps) - 1)
        next_name = end_state_name if is_last else compute_steps[i + 1]['name']

        # A step can be a MatrixEquationOperation (invokes a saved
        # MatrixEquationDefinition with operands bound from context) instead
        # of a scalar CalculusOperation. Used for the 2D→3D plane embedding.
        if step.get('kind') == 'matrixEquation':
            states.append(_matrix_equation_operation(
                state_name=step['name'],
                location_x=160 + spacing_x * (i + 1),
                location_y=base_y,
                matrix_equation_name=step['matrixEquationName'],
                operand_bindings=step['operandBindings'],
                result_var=step['var'],
                description=step['description'],
                index=i + 1,
                next_state=next_name,
                next_connector_id=next_connector_id,
                coding_comment=step.get('comment', ''),
            ))
            next_connector_id += 1
            continue

        # Equation name convention: <solution>.<step-var>.
        # Bindings come from the step's `bindings` dict — explicit
        # symbol → context-path mappings so the semi-implicit Euler
        # order (some symbols read prev-step values, others read the
        # just-computed `_new` versions) is captured authoritatively
        # by the equation itself.
        #
        # Each binding also carries a `potential` declaring the input
        # SHAPE the symbol expects — driving the locked-class hint and
        # "From Object Instance" branch lockdown in the host editor.
        # `defaultSource` is the concrete fallback the runner uses when
        # the hosting CalculusOperation state hasn't overridden the
        # binding.
        eq_name = f"{name}.{step['var']}"
        default_bindings = [
            {
                'symbol': sym,
                'potential': {
                    'kind': 'from_object',
                    'className': target_class,
                },
                'defaultSource': {
                    'sourceType': 'from_source_object',
                    'sourceObjectPath': path,
                },
            }
            for sym, path in step.get('bindings', {}).items()
        ]
        equations.append(_equation_definition(
            name=eq_name,
            description=step['description'],
            latex=step['latex'],
            default_bindings=default_bindings,
            source_class=target_class,
        ))

        states.append(_calculus_operation(
            state_name=step['name'],
            location_x=160 + spacing_x * (i + 1),
            location_y=base_y,
            equation_name=eq_name,
            result_var=step['var'],
            description=step['description'],
            index=i + 1,
            next_state=next_name,
            next_connector_id=next_connector_id,
            coding_comment=step.get('comment', ''),
        ))
        next_connector_id += 1

    # Terminator depends on role. Complete and Composition both
    # commit a full *SimState row (SimStepNextState); Partial emits a
    # sparse contribution payload (SimStepContribution).
    if sim_step_role == 'simStepPartial':
        contribution_mappings = []
        for field, spec in output_field_to_context.items():
            if isinstance(spec, tuple) and len(spec) == 2:
                ctx_var, op = spec
            else:
                raise ValueError(
                    f"Partial step solution '{name}' output_field_to_context "
                    f"entry for '{field}' must be a (ctx_var, op) tuple; "
                    f"got {spec!r}."
                )
            # Like the Complete/Composition path below: a bare string is
            # shorthand for from_source_object; a dict is a full
            # ValueSourceConfig used verbatim (e.g. an 'element' source
            # extracting one component of a computed force vector).
            value_source = ctx_var if isinstance(ctx_var, dict) else _from_source(ctx_var)
            contribution_mappings.append({
                'outputFieldName': field,
                'valueSource': value_source,
                'op': op,
            })
        states.append(_sim_step_contribution_terminator(
            state_name=end_state_name,
            location_x=160 + spacing_x * (len(compute_steps) + 1),
            location_y=base_y,
            contribution_mappings=contribution_mappings,
            target_class=target_class,
            index=len(compute_steps) + 1,
            slot_id_in=next_connector_id,
            coding_comment=terminator_comment,
        ))
    else:
        output_mappings = []
        for field, ctx_var in output_field_to_context.items():
            if isinstance(ctx_var, tuple):
                raise ValueError(
                    f"{sim_step_role} step solution '{name}' output_field_to_context "
                    f"entry for '{field}' should be a bare ctx_var string, "
                    f"not a tuple — only simStepPartial uses (ctx_var, op)."
                )
            # A bare string is shorthand for from_source_object; a dict is a
            # full ValueSourceConfig used verbatim (e.g. an 'element' source
            # extracting world_vec[0]).
            value_source = ctx_var if isinstance(ctx_var, dict) else _from_source(ctx_var)
            output_mappings.append(
                {'outputFieldName': field, 'valueSource': value_source}
            )
        states.append(_next_sim_state(
            state_name=end_state_name,
            location_x=160 + spacing_x * (len(compute_steps) + 1),
            location_y=base_y,
            output_mappings=output_mappings,
            target_class=target_class,
            index=len(compute_steps) + 1,
            slot_id_in=next_connector_id,
            coding_comment=terminator_comment,
        ))

    for s in states:
        s['solutionName'] = name

    definition = {
        'solutionName': name,
        'description': description,
        'stateInstances': states,
    }
    solution_def_row = {
        'name': name,
        'description': description,
        'function_name': name.replace('.', '_').replace('-', '_'),
        'target_runtime': 'python_backend',
        'definition': json.dumps(definition),
    }
    metadata_row = {
        'name': name,
        'description': description,
        'simulation_definition_ref': sim_def_ref,
        'sim_state_class_name': target_class,
        'solution_definition_ref': name,
        'expected_inputs_json': json.dumps(expected_inputs),
        'expected_outputs_json': json.dumps(list(output_field_to_context.keys())),
        'order_index': order_index,
        'depends_on_json': json.dumps(depends_on or []),
        'enabled': True,
    }
    return solution_def_row, metadata_row, equations


# --------------------------------------------------------------------------
# Pendulum bob — semi-implicit Euler integration of θ'' = −(g/L) sin θ
# decomposed into a Partial (gravity force) + a Composition (integrator).
#
# The math is the same as a monolithic Complete solution but the
# decomposition demonstrates the multi-scale composability the runner
# is built for:
#
#   PARTIAL (this file: gravity-force):
#       gravity_alpha = −(g/L) sin θ
#       emit α += gravity_alpha
#
#   (future Partials can be added WITHOUT touching the integrator:
#       AirDrag      → emit α += −c·ω
#       DrivingForce → emit α += F(t)/(m·L)
#    Each just registers another Partial binding at order_index=0; the
#    runner sums their contributions into α before the Composition
#    runs.)
#
#   COMPOSITION (this file: integrator):
#       Reads `self.alpha_new` (already the sum of all Partials'
#       contributions, courtesy of the runner's _apply_step_contributions).
#       Runs the semi-implicit Euler chain:
#           ω_new = ω + α·dt
#           θ_new = θ + ω_new·dt      ← uses the just-computed ω_new
#       Then projects:
#           x_new = L sin θ_new
#           y_new = −L cos θ_new
#           energy_new = ½ m L² ω² + m g L (1 − cos θ)
#       Emits the SimStepNextState row.
#
# Semi-implicit Euler ordering still lives in the Composition's chain
# (ω before θ, θ_new before projections) — the Partial→Composition
# split only factors out the FORCE COMPUTATION as a reusable, additive
# operator. The integrator stays atomic because its read-after-write
# dependencies are intrinsic to the algorithm, not composable.
# --------------------------------------------------------------------------

# Gravity Partial — one CalculusOperation, contributes to α.
_BOB_GRAVITY_STEPS = [
    {'name': 'ComputeGravityAlpha',
     'var': 'gravity_alpha',
     'latex': r'-(g/L) \cdot \sin(\theta)',
     'bindings': {'g': 'self.g', 'L': 'self.L', r'\theta': 'self.theta'},
     'description': 'Gravity contribution to angular acceleration: −(g/L) sin θ.',
     'comment': (
         "Newton's 2nd law applied to a pendulum about its pivot:\n"
         "    torque τ = -mgL·sin(θ)   (gravity component perpendicular to the rod)\n"
         "    moment of inertia I = mL²\n"
         "    angular accel α = τ/I = -(g/L)·sin(θ)\n\n"
         "This is the α the bob experiences from gravity ALONE. Other force\n"
         "Partials targeting α (drag, driving torque, magnetic coupling) emit\n"
         "their own contributions; the runner sums them all into self.alpha_new\n"
         "before the integrator Composition reads it."
     )},
]
# Partial output spec uses (ctx_var, op) tuples. `op='add'` makes
# additional force Partials compose naturally — drop in air-drag or a
# driving force later and the integrator picks up the summed α with
# zero edits.
_BOB_GRAVITY_OUTPUT_MAP = {
    'alpha_new': ('gravity_alpha', 'add'),
}

# Composition integrator. `alpha_new` is read straight off `self`
# because the runner pre-merges Partial contributions onto the baseline
# before invoking the Composition solution.
_BOB_INTEGRATOR_STEPS = [
    {'name': 'AdvanceOmega',
     'var': 'omega_new',
     'latex': r'\omega + \alpha \cdot dt',
     'bindings': {
         r'\omega': 'self.omega',
         r'\alpha': 'self.alpha_new',   # merged Partials sum
         'dt': 'self.dt',
     },
     'description': 'Semi-implicit Euler: ω_new = ω + (Σ α_partials)·dt.',
     'comment': (
         "Velocity update — first half of semi-implicit (symplectic) Euler:\n"
         "    ω_new = ω + α · dt\n\n"
         "α here is self.alpha_new, which the runner has already populated\n"
         "with the SUM of every Partial's α contribution for this step (gravity,\n"
         "and any future drag/driving/etc.). The integrator is intentionally\n"
         "ignorant of WHICH forces contributed — composability lives in the\n"
         "Partials.\n\n"
         "'Semi-implicit' means the NEXT step's position update (AdvanceTheta\n"
         "below) will read this freshly-computed ω_new, not the prev-step ω.\n"
         "That ordering keeps total energy bounded over long runs where pure\n"
         "explicit Euler would drift outward."
     )},
    {'name': 'AdvanceTheta',
     'var': 'theta_new',
     'latex': r'\theta + \omega \cdot dt',
     'bindings': {r'\theta': 'self.theta', r'\omega': 'self.omega_new', 'dt': 'self.dt'},
     'description': 'Semi-implicit Euler: θ_new = θ + ω_new·dt. Uses ω_new.',
     'comment': (
         "Position update — second half of semi-implicit Euler:\n"
         "    θ_new = θ + ω_new · dt\n\n"
         "Reads the JUST-computed ω_new (the binding for ω points at\n"
         "self.omega_new, not self.omega). This 'use the new velocity for\n"
         "the position update' is the symplectic trick: it's still O(dt)\n"
         "accurate, but it conserves a discrete approximation of the energy\n"
         "rather than drifting like explicit Euler does."
     )},
    {'name': 'ProjectX',
     'var': 'x_new',
     'latex': r'L \cdot \sin(\theta)',
     'bindings': {'L': 'self.L', r'\theta': 'self.theta_new'},
     'description': 'Cartesian x of the bob at the new θ: L sin θ_new.',
     'comment': (
         "Cartesian projection of the bob from polar (θ) to (x, y):\n"
         "    x = L · sin(θ_new)\n\n"
         "Computed at step time so the SimSpace's X-axis binding can read\n"
         "x directly without redoing the trig. The pivot is at the origin\n"
         "and θ is measured from the downward vertical (positive θ swings\n"
         "the bob to the +x side)."
     )},
    {'name': 'ProjectY',
     'var': 'y_new',
     'latex': r'-L \cdot \cos(\theta)',
     'bindings': {'L': 'self.L', r'\theta': 'self.theta_new'},
     'description': 'Cartesian y of the bob at the new θ: −L cos θ_new.',
     'comment': (
         "Cartesian projection — y component:\n"
         "    y = -L · cos(θ_new)\n\n"
         "Negative because +y is UP and the bob hangs DOWN from the pivot:\n"
         "at rest (θ = 0) the bob sits at y = -L; at horizontal (θ = π/2)\n"
         "it sits at y = 0."
     )},
    {'name': 'ComputeEnergy',
     'var': 'energy_total_new',
     'latex': (
         r'0.5 \cdot m \cdot L^{2} \cdot \omega^{2} '
         r'+ m \cdot g \cdot L \cdot (1 - \cos(\theta))'
     ),
     'bindings': {
         'm': 'self.mass', 'L': 'self.L', 'g': 'self.g',
         r'\omega': 'self.omega_new', r'\theta': 'self.theta_new',
     },
     'description': 'KE + PE at the new state. Conservation diagnostic.',
     'comment': (
         "Total mechanical energy of the pendulum at the new state:\n"
         "    E = KE + PE\n"
         "      = ½ · m · v²    + m · g · h\n"
         "      = ½ · m · (Lω)² + m · g · L · (1 - cos θ)\n\n"
         "PE is measured from the rest position (h = L - L·cos θ = L(1-cos θ))\n"
         "so E = 0 when the bob hangs motionless at θ = 0.\n\n"
         "Conservation diagnostic only — for a frictionless pendulum this\n"
         "should hover near its initial value across the whole run (~1.31 J\n"
         "for our 30° release). If E drifts visibly, the integrator is\n"
         "leaking energy and dt is too coarse OR a non-conservative Partial\n"
         "(e.g. drag) is in play."
     )},
    # 2D→3D embedding (no-code): invoke the `pendulum-embed` matrix equation
    # to place the bob's 2D (x_new, y_new) into the 3D swing plane defined by
    # the validated normal n = (plane_nx, plane_ny, plane_nz). Result is the
    # 3-vector world_vec; the terminator extracts its components into
    # world_x/y/z. This is what makes a LIVE run animate in 3D (the seeded
    # demo precomputes the same thing in Python).
    {'name': 'EmbedWorld3D',
     'kind': 'matrixEquation',
     'var': 'world_vec',
     'matrixEquationName': 'pendulum-embed',
     'operandBindings': [
         {'symbol': 'x', 'source': _from_source('self.x_new')},
         {'symbol': 'y', 'source': _from_source('self.y_new')},
         {'symbol': 'n', 'source': _array_source([
             _from_source('self.plane_nx'),
             _from_source('self.plane_ny'),
             _from_source('self.plane_nz')])},
         {'symbol': 'Yup', 'source': _array_source([0, 1, 0])},
     ],
     'description': '3D embedding of the bob into the swing plane: '
                    'world = x·normalize(Yup×n) + y·Yup.',
     'comment': (
         "Embeds the 2D pendulum into 3D via the matrix/vector engine —\n"
         "exercising no-code MatrixEquationOperation + vector ops:\n"
         "    h     = normalize(Yup × n)   (horizontal swing direction)\n"
         "    world = x·h + y·Yup          (Yup = (0,1,0) is 'up')\n\n"
         "n is the swing-plane normal (validated parallel to the ground).\n"
         "Default n = (0,0,1) ⇒ h = (1,0,0) ⇒ world = (x, y, 0) (X–Y plane)."
     )},
]
_BOB_INTEGRATOR_OUTPUT_MAP = {
    'theta': 'theta_new',
    'omega': 'omega_new',
    'x': 'x_new',
    'y': 'y_new',
    'energy_total': 'energy_total_new',
    # 3D embedding components (extracted from world_vec) + the swing-plane
    # normal passed through so it persists for the next step.
    'world_x': _element_source('world_vec', 0),
    'world_y': _element_source('world_vec', 1),
    'world_z': _element_source('world_vec', 2),
    'plane_nx': 'self.plane_nx',
    'plane_ny': 'self.plane_ny',
    'plane_nz': 'self.plane_nz',
}


# --------------------------------------------------------------------------
# Pendulum string — three computations.
#
#   1. `bob_x_new` / 2. `bob_y_new` — the string's terminus tracks the
#      bob exactly. Recomputed from θ rather than read off the bob's
#      output because the runner's dep merge happens to put `theta` /
#      `omega` (the bob's current-step values) into the string's
#      context already, so this is cheaper than pulling x/y too.
#
#   3. `tension_new` = m g cos θ + m L ω² — radial-gravity + centripetal
#      contributions. Diagnostic; rendered as the line width / color in
#      a future extension.
#
# The binding's depends_on: ["PendulumBobSimState"] is what makes the
# bob's current-step (theta, omega) available here.
# --------------------------------------------------------------------------

_STRING_STEPS = [
    {'name': 'BobX',
     'var': 'bob_x_new',
     'latex': r'L \cdot \sin(\theta)',
     'bindings': {'L': 'self.L', r'\theta': 'self.theta'},
     'description': 'String terminus x — matches the bob at the current step.',
     'comment': (
         "String terminus x = L · sin(θ).\n\n"
         "This SimState class participates in the same step as the bob;\n"
         "the cross-class dep (PendulumStringSimState depends_on\n"
         "PendulumBobSimState) makes the bob's current-step (theta, omega)\n"
         "available in our context.\n\n"
         "Recomputing the projection from θ here (instead of reading the\n"
         "bob's x directly) keeps the string's solution self-contained AND\n"
         "trivially correct if the bob later starts producing x/y in a\n"
         "different convention."
     )},
    {'name': 'BobY',
     'var': 'bob_y_new',
     'latex': r'-L \cdot \cos(\theta)',
     'bindings': {'L': 'self.L', r'\theta': 'self.theta'},
     'description': 'String terminus y — matches the bob at the current step.',
     'comment': (
         "String terminus y = -L · cos(θ). Same convention as the bob's\n"
         "ProjectY: pivot at origin, +y up, so the terminus sits below the\n"
         "pivot when θ = 0."
     )},
    {'name': 'ComputeTension',
     'var': 'tension_new',
     'latex': r'm \cdot g \cdot \cos(\theta) + m \cdot L \cdot \omega^{2}',
     'bindings': {
         'm': 'self.mass', 'g': 'self.g', 'L': 'self.L',
         r'\theta': 'self.theta', r'\omega': 'self.omega',
     },
     'description': 'Tension = mg cos θ + mLω² (radial-gravity + centripetal).',
     'comment': (
         "String tension along the rod, from Newton's 2nd law in the\n"
         "radial direction:\n"
         "    T = m·g·cos(θ)   +   m·L·ω²\n"
         "        ─────┬─────       ───┬───\n"
         "       gravity component   centripetal\n"
         "       along the rod       acceleration\n\n"
         "At rest (θ=0, ω=0): T = m·g. The string just holds up the bob.\n"
         "At the bottom of a swing (θ=0, ω≠0): T = m·g + m·L·ω² > m·g —\n"
         "the string must supply extra force to bend the bob's straight-line\n"
         "momentum into a circular arc.\n\n"
         "Diagnostic only today; a future visualization will use this to\n"
         "drive the rendered string's color/thickness."
     )},
    # 2D→3D embedding of the string's bob endpoint — same `pendulum-embed`
    # matrix equation as the bob, fed the string's (bob_x_new, bob_y_new).
    {'name': 'EmbedStringWorld3D',
     'kind': 'matrixEquation',
     'var': 'world_vec',
     'matrixEquationName': 'pendulum-embed',
     'operandBindings': [
         {'symbol': 'x', 'source': _from_source('self.bob_x_new')},
         {'symbol': 'y', 'source': _from_source('self.bob_y_new')},
         {'symbol': 'n', 'source': _array_source([
             _from_source('self.plane_nx'),
             _from_source('self.plane_ny'),
             _from_source('self.plane_nz')])},
         {'symbol': 'Yup', 'source': _array_source([0, 1, 0])},
     ],
     'description': '3D embedding of the string endpoint into the swing plane.',
     'comment': "Mirrors the bob's embedding for the string's bob-endpoint."},
]
_STRING_OUTPUT_MAP = {
    'bob_x': 'bob_x_new',
    'bob_y': 'bob_y_new',
    'tension': 'tension_new',
    'world_x': _element_source('world_vec', 0),
    'world_y': _element_source('world_vec', 1),
    'world_z': _element_source('world_vec', 2),
    'plane_nx': 'self.plane_nx',
    'plane_ny': 'self.plane_ny',
    'plane_nz': 'self.plane_nz',
}


_BOB_GRAVITY_SOL_DEF, _BOB_GRAVITY_META, _BOB_GRAVITY_EQUATIONS = _step_solution_pair(
    name=BOB_GRAVITY_SOLUTION_NAME,
    description=(
        'Partial — contributes gravity\'s acceleration term −(g/L) sin θ '
        'to α. Composes additively with any other Partials targeting α '
        '(e.g. air drag, driving force) before the integrator runs.'
    ),
    target_class='PendulumBobSimState',
    expected_inputs=['theta', 'g', 'L'],
    compute_steps=_BOB_GRAVITY_STEPS,
    output_field_to_context=_BOB_GRAVITY_OUTPUT_MAP,
    sim_step_role='simStepPartial',
    # Partial — runs first within the bob group so its contribution
    # is merged before the integrator Composition reads alpha_new.
    order_index=0,
    depends_on=[],
    entry_comment=(
        "Entry node for the gravity-force Partial.\n\n"
        "The runner invokes this solution once per timestep for the\n"
        "PendulumBobSimState class. The context at entry already contains\n"
        "the prev-step bob row's fields (theta, omega, ...) plus the\n"
        "simulation parameters (g, L, mass) plus step metadata (dt, time,\n"
        "step), all keyed by their field name.\n\n"
        "This solution is a Partial — it does NOT produce the next row.\n"
        "It emits a sparse contribution payload via SimStepContribution,\n"
        "which the runner sums into self.alpha_new before invoking the\n"
        "integrator Composition. Adding more α-contributing Partials\n"
        "(drag, driving torque, etc.) doesn't require ANY change to the\n"
        "integrator — that's the multi-scale composability point."
    ),
    terminator_comment=(
        "Emits the gravity Partial's contribution:\n"
        "    {alpha_new: {value: gravity_alpha, op: 'add'}}\n\n"
        "`op='add'` is what makes forces compose naturally — if a drag\n"
        "Partial also emits {alpha_new: {value: -c·ω, op: 'add'}}, the\n"
        "runner sums them: alpha_new = gravity_alpha + drag_alpha. Use\n"
        "'set' instead only if a Partial needs to OVERRIDE other Partials'\n"
        "contributions to that field (e.g. a constraint solver), not\n"
        "compose with them."
    ),
)
_BOB_INTEGRATOR_SOL_DEF, _BOB_INTEGRATOR_META, _BOB_INTEGRATOR_EQUATIONS = _step_solution_pair(
    name=BOB_INTEGRATOR_SOLUTION_NAME,
    description=(
        'Composition — semi-implicit Euler integrator. Reads `self.alpha_new` '
        '(already the merged Σ α_partials, applied by the runner) and produces '
        'the next bob row: ω_new → θ_new → projections → energy.'
    ),
    target_class='PendulumBobSimState',
    expected_inputs=['theta', 'omega', 'alpha_new', 'g', 'L', 'mass', 'dt',
                     'plane_nx', 'plane_ny', 'plane_nz'],
    compute_steps=_BOB_INTEGRATOR_STEPS,
    output_field_to_context=_BOB_INTEGRATOR_OUTPUT_MAP,
    sim_step_role='simStepComposition',
    # Composition — runs AFTER the gravity Partial. The runner merges
    # partials by their `op` semantics before invoking this row.
    order_index=1,
    depends_on=[],
    entry_comment=(
        "Entry node for the bob's integrator Composition.\n\n"
        "By the time the runner invokes this solution, every Partial that\n"
        "targets PendulumBobSimState has already run and emitted its\n"
        "contribution payload. The runner has merged those contributions\n"
        "onto the baseline context using their per-field ops, so\n"
        "self.alpha_new is the SUM of every Partial's α contribution for\n"
        "this step. We treat α as a given input and march forward.\n\n"
        "The chain that follows is the semi-implicit (symplectic) Euler\n"
        "integrator plus the Cartesian projection + total-energy diagnostic:\n"
        "    ω_new = ω + α · dt          ← AdvanceOmega\n"
        "    θ_new = θ + ω_new · dt      ← AdvanceTheta (uses NEW ω)\n"
        "    x_new = L · sin(θ_new)      ← ProjectX\n"
        "    y_new = -L · cos(θ_new)     ← ProjectY\n"
        "    E_new = ½mL²ω² + mgL(1-cosθ) ← ComputeEnergy\n\n"
        "Then SimStepNextState commits the new row."
    ),
    terminator_comment=(
        "Commits the new PendulumBobSimState row from the integrator\n"
        "chain's outputs:\n"
        "    theta        ← theta_new\n"
        "    omega        ← omega_new\n"
        "    x            ← x_new\n"
        "    y            ← y_new\n"
        "    energy_total ← energy_total_new\n\n"
        "The SimulationRunner takes this terminator's accumulated context,\n"
        "projects the named fields onto a fresh PendulumBobSimState row,\n"
        "stamps the run/step/time identity, and persists it. From the\n"
        "next timestep's perspective, this row is what 'self' looks like."
    ),
)
_STRING_SOL_DEF, _STRING_META, _STRING_EQUATIONS = _step_solution_pair(
    name=STRING_STEP_SOLUTION_NAME,
    description='Pendulum string endpoint + tension diagnostic; reads the bob\'s current-step θ/ω.',
    target_class='PendulumStringSimState',
    expected_inputs=['theta', 'omega', 'g', 'L', 'mass',
                     'plane_nx', 'plane_ny', 'plane_nz'],
    compute_steps=_STRING_STEPS,
    output_field_to_context=_STRING_OUTPUT_MAP,
    sim_step_role='simStepComplete',
    # Reads bob's current-step θ/ω, so the string class must wait for
    # the bob class to commit its new row first.
    order_index=0,
    depends_on=['PendulumBobSimState'],
    entry_comment=(
        "Entry node for the string's step solution.\n\n"
        "This binding declares depends_on=['PendulumBobSimState'], so the\n"
        "runner topo-sorts the bob class before the string class within\n"
        "each step. By the time we run here, the bob's current-step row\n"
        "(theta, omega, x, y, energy_total) has been committed AND merged\n"
        "into our context — that's how 'self.theta' / 'self.omega' refer\n"
        "to the BOB's just-computed values inside this graph.\n\n"
        "Role is simStepComplete: a single closed-form update to the\n"
        "string state. The string has no internal dynamics that benefit\n"
        "from Partial composition — its values are pure functions of the\n"
        "bob's current state."
    ),
    terminator_comment=(
        "Commits the new PendulumStringSimState row from the three\n"
        "computed variables:\n"
        "    bob_x   ← bob_x_new\n"
        "    bob_y   ← bob_y_new\n"
        "    tension ← tension_new\n\n"
        "The string row's identity (name, run, step, time) is stamped by\n"
        "the runner; this terminator only declares the field values."
    ),
)

# SolutionDefinition rows — the actual no-code graphs the editor reads.
# Bob is split into a Partial (gravity force) and a Composition
# (integrator); string is a single Complete monolithic solution.
SEED_PENDULUM_STEP_SOLUTION_DEFS = [
    _BOB_GRAVITY_SOL_DEF,
    _BOB_INTEGRATOR_SOL_DEF,
    _STRING_SOL_DEF,
]

# SimulationExecutionSolution rows — metadata wrappers tagging each
# SolutionDefinition with its simulation role.
SEED_PENDULUM_STEP_SOLUTIONS = [
    _BOB_GRAVITY_META,
    _BOB_INTEGRATOR_META,
    _STRING_META,
]

# EquationDefinition rows — one per math step in each solution. The
# CalculusOperation states in the graphs above reference these by
# name; the analyst can edit any of them in the Equations page
# without touching the solution graph.
SEED_PENDULUM_STEP_EQUATIONS = (
    _BOB_GRAVITY_EQUATIONS + _BOB_INTEGRATOR_EQUATIONS + _STRING_EQUATIONS
)


# --------------------------------------------------------------------------
# SolutionTestCases — Manual-Process test inputs for the step solutions.
# Each test case runs the solution through the existing
# /executeSolutionStepped endpoint with the listed `instance_fields`
# pre-merged into context, asserting the final state on completion.
# The pendulum's first tick from initial conditions has a well-known
# expected output (alpha=-4.905, omega_new=-0.04905, theta_new=0.523108)
# so the test case acts as a coherence check after editing the math.
# --------------------------------------------------------------------------

_BOB_GRAVITY_ALPHA_T0 = -(DEMO_G / DEMO_L) * math.sin(DEMO_THETA_0)

SEED_PENDULUM_STEP_TEST_CASES = [
    {
        'solution_id': BOB_GRAVITY_SOLUTION_NAME,
        'name': f'{BOB_GRAVITY_SOLUTION_NAME}.first-tick-emits-gravity-alpha',
        'description': (
            'Gravity Partial from t=0 initial conditions (theta=π/6 ≈ 0.5236). '
            'Should emit a SimStepContribution with alpha_new += −(g/L)·sin θ '
            f'≈ {_BOB_GRAVITY_ALPHA_T0:.5f} rad/s².'
        ),
        'input_params': '{}',
        'instance_fields': json.dumps({
            'theta': DEMO_THETA_0,
            'g': DEMO_G,
            'L': DEMO_L,
        }),
        'target_runtime': 'python_backend',
        'expected_return_value': '',
        'expected_status': 'completed',
        'tags': 'simulation,pendulum,partial,smoke',
    },
    {
        'solution_id': BOB_INTEGRATOR_SOLUTION_NAME,
        'name': f'{BOB_INTEGRATOR_SOLUTION_NAME}.first-tick-from-30deg-rest',
        'description': (
            'Integrator Composition with pre-merged α (the runner would '
            'inject this from the gravity Partial). At t=0 with theta=π/6, '
            'alpha_new = −(g/L) sin θ. One tick at dt=0.01 should produce '
            'omega≈-0.04905, theta≈0.523108, energy_total≈1.3131.'
        ),
        'input_params': '{}',
        'instance_fields': json.dumps({
            'theta': DEMO_THETA_0,
            'omega': DEMO_OMEGA_0,
            'alpha_new': _BOB_GRAVITY_ALPHA_T0,
            'g': DEMO_G,
            'L': DEMO_L,
            'mass': DEMO_MASS,
            'dt': DEMO_DT,
            'time': DEMO_DT,
            'step': 1,
        }),
        'target_runtime': 'python_backend',
        'expected_return_value': '',
        'expected_status': 'completed',
        'tags': 'simulation,pendulum,composition,smoke',
    },
    {
        'solution_id': STRING_STEP_SOLUTION_NAME,
        'name': f'{STRING_STEP_SOLUTION_NAME}.first-tick-reads-bob',
        'description': (
            'String step reading bob\'s current-step (theta=0.523108, '
            'omega=-0.04905). Should produce bob_x≈0.4996, '
            'bob_y≈-0.8663, tension≈8.5005 N.'
        ),
        'input_params': '{}',
        'instance_fields': json.dumps({
            'theta': 0.523108,
            'omega': -0.04905,
            'g': DEMO_G,
            'L': DEMO_L,
            'mass': DEMO_MASS,
            'dt': DEMO_DT,
            'time': DEMO_DT,
            'step': 1,
        }),
        'target_runtime': 'python_backend',
        'expected_return_value': '',
        'expected_status': 'completed',
        'tags': 'simulation,pendulum,smoke',
    },
]


SEED_PENDULUM_EVALUATION_EQUATIONS = [
    {
        'name': 'pendulum-2d-viz.kinetic-energy',
        'description': 'Live KE readout — top-right HUD.',
        'sim_space_ref': 'pendulum-2d-viz',
        'equation_ref': 'pendulum-2d.kinetic-energy',
        'variable_bindings_json': json.dumps(_PENDULUM_KE_PE_BINDINGS),
        'result_variable_ref': 'kinetic_energy',
        'anchor_kind': 'screen',
        'anchor_data_json': '{"corner": "top-right"}',
        'sort_order': 0,
        'enabled': True,
    },
    {
        'name': 'pendulum-2d-viz.potential-energy',
        'description': 'Live PE readout — top-right HUD (below KE).',
        'sim_space_ref': 'pendulum-2d-viz',
        'equation_ref': 'pendulum-2d.potential-energy',
        'variable_bindings_json': json.dumps(_PENDULUM_KE_PE_BINDINGS),
        'result_variable_ref': 'potential_energy',
        'anchor_kind': 'screen',
        'anchor_data_json': '{"corner": "top-right"}',
        'sort_order': 1,
        'enabled': True,
    },
    {
        'name': 'pendulum-2d-viz.total-energy',
        'description': 'Live total-energy readout — top-right HUD (below PE). '
                       'Should hover near 1.31 J for the 30° release.',
        'sim_space_ref': 'pendulum-2d-viz',
        'equation_ref': 'pendulum-2d.total-energy',
        'variable_bindings_json': json.dumps(_PENDULUM_KE_PE_BINDINGS),
        'result_variable_ref': 'total_energy',
        'anchor_kind': 'screen',
        'anchor_data_json': '{"corner": "top-right"}',
        'sort_order': 2,
        'enabled': True,
    },
]


# SimSpace + bindings so the demo is visible out of the box.
SEED_PENDULUM_SIMSPACES = [
    {
        'name': 'pendulum-2d-viz',
        'description': (
            'Visualizes the pendulum-2d simulation. The bob renders as a '
            'circle (PendulumBobSimState binding) and the string renders '
            'as a line from pivot to bob (PendulumStringSimState binding). '
            'The scrubber drives both sub-systems together.'
        ),
        'dimensionality': '2d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        # ±1.5 fits a unit-length pendulum (bob range is ±L=1 with margin).
        'viewport_json': '{"center": [0, 0], "extent": [1.5, 1.5]}',
        # Engine output is opt-in by default via the binding's
        # defaultVisible flag; we explicitly list both classes so the
        # scene renders the demo without further config.
        'bound_classes_json': (
            '['
            '{"className": "PendulumBobSimState"},'
            '{"className": "PendulumStringSimState"}'
            ']'
        ),
        # Freestanding pivot marker at the origin — visual anchor for the
        # string. The string's connection-mode binding uses a literal
        # (0, 0) constant for its source endpoint, so this freestanding
        # shape is purely cosmetic (no functional coupling to the line).
        'definition': (
            '{"freestanding": ['
            '{"id":"pivot","position":[0,0],"shapeRef":"circle","styleRef":"muted","label":"Pivot"}'
            ']}'
        ),
    },
    {
        'name': 'pendulum-3d-viz',
        'description': (
            '3D visualization of the pendulum-2d simulation. The bob renders '
            'as a sphere and the string as a rod from the pivot to the bob, '
            'embedded in a vertical swing plane (default: the X–Y plane). The '
            'plane orientation is set per run by a normal vector validated '
            'parallel to the ground. Reuses the same bob/string state — '
            'world_x/y/z hold the 3D embedding of the 2D (x, y).'
        ),
        'dimensionality': '3d',
        'coordinate_system': 'math',
        'unit_scale': 1.0,
        'viewport_json': '{"center": [0, 0, 0], "extent": [1.5, 1.5, 1.5]}',
        'bound_classes_json': (
            '['
            '{"className": "PendulumBobSimState"},'
            '{"className": "PendulumStringSimState"}'
            ']'
        ),
        # Freestanding pivot sphere at the origin — the string's anchor.
        'definition': (
            '{"freestanding": ['
            '{"id":"pivot","position":[0,0,0],"shapeRef":"sphere","styleRef":"matte-gray",'
            '"scale":0.06,"label":"Pivot"}'
            ']}'
        ),
    },
]


# Bindings — one per *SimState class.
#
# PendulumBobSimState  → kind='object'     (circles at x, y, scrubber on time)
# PendulumStringSimState → kind='connection' (line from (0,0) to (bob_x, bob_y),
#                                             scrubber on time)
SEED_PENDULUM_BINDINGS = [
    {
        'name': 'PendulumBobSimState-2d',
        'class_name': 'PendulumBobSimState',
        'dimensionality': '2d',
        'enabled': True,
        'binding_json': (
            '{'
            '"enabled": true,'
            '"dimensionality": "2d",'
            '"kind": "object",'
            '"position": {"kind": "fields", "fields": {"x": "x", "y": "y"}},'
            '"visual": {"shapeRef": "circle", "styleRef": "default"},'
            '"clickAction": "navigate-to-instance",'
            '"defaultVisible": true,'
            '"temporal": {'
            '  "kind": "time", "field": "time", "unit": "second", "cumulative": false'
            '}'
            '}'
        ),
    },
    {
        'name': 'PendulumStringSimState-2d',
        'class_name': 'PendulumStringSimState',
        'dimensionality': '2d',
        'enabled': True,
        'binding_json': (
            '{'
            '"enabled": true,'
            '"dimensionality": "2d",'
            '"kind": "connection",'
            # Pivot is fixed at the origin; the bob endpoint comes from
            # this row's bob_x / bob_y fields.
            '"source": {"kind": "constant", "value": [0, 0]},'
            '"target": {"kind": "fields", "fields": {"x": "bob_x", "y": "bob_y"}},'
            '"visual": {"shapeRef": "", "styleRef": "muted"},'
            '"clickAction": "navigate-to-instance",'
            '"defaultVisible": true,'
            '"temporal": {'
            '  "kind": "time", "field": "time", "unit": "second", "cumulative": false'
            '}'
            '}'
        ),
    },
    {
        'name': 'PendulumBobSimState-3d',
        'class_name': 'PendulumBobSimState',
        'dimensionality': '3d',
        'enabled': True,
        'binding_json': (
            '{'
            '"enabled": true,'
            '"dimensionality": "3d",'
            '"kind": "object",'
            # 3D embedding: read world_x/y/z — the bob (x,y) placed into the
            # swing plane defined by the (validated-horizontal) normal. The
            # no-code EmbedWorld3D step computes these live; the seed demo
            # precomputes them. Default normal (0,0,1) → world = (x, y, 0).
            '"position": {"kind": "fields", "fields": {"x": "world_x", "y": "world_y", "z": "world_z"}},'
            '"visual": {"shapeRef": "sphere", "styleRef": "matte-blue"},'
            '"scale": {"kind": "constant", "value": 0.12},'
            '"clickAction": "navigate-to-instance",'
            '"defaultVisible": true,'
            '"temporal": {'
            '  "kind": "time", "field": "time", "unit": "second", "cumulative": false'
            '}'
            '}'
        ),
    },
    {
        'name': 'PendulumStringSimState-3d',
        'class_name': 'PendulumStringSimState',
        'dimensionality': '3d',
        'enabled': True,
        'binding_json': (
            '{'
            '"enabled": true,'
            '"dimensionality": "3d",'
            '"kind": "connection",'
            # Pivot fixed at the origin; the bob endpoint is the 3D embedding
            # (world_x/y/z) so the string tracks the bob in the swing plane.
            '"source": {"kind": "constant", "value": [0, 0, 0]},'
            '"target": {"kind": "fields", "fields": {"x": "world_x", "y": "world_y", "z": "world_z"}},'
            '"visual": {"styleRef": "metal-steel"},'
            '"clickAction": "navigate-to-instance",'
            '"defaultVisible": true,'
            '"temporal": {'
            '  "kind": "time", "field": "time", "unit": "second", "cumulative": false'
            '}'
            '}'
        ),
    },
]


