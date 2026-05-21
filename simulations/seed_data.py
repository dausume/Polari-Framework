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
            })
            string_rows.append({
                'name': f'{SIM_RUN_NAME}-string-{step}',
                'simulation_run_ref': SIM_RUN_NAME,
                'step': step,
                'time': round(t, 6),
                'bob_x': round(x, 6),
                'bob_y': round(y, 6),
                'tension': round(tension, 6),
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
            '(the rod). Trajectory is precomputed at seed time; the runtime '
            'engine will replace it once the simulation no-code lands.'
        ),
        'step_solution_ref': '',  # set when the simulation no-code is authored
        'time_step_seconds': DEMO_DT,
        'duration_seconds': DEMO_DURATION,
        'recording_interval_steps': DEMO_RECORDING_INTERVAL,
        'initial_conditions_json': (
            f'{{"theta": {DEMO_THETA_0}, "omega": {DEMO_OMEGA_0}}}'
        ),
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
]
