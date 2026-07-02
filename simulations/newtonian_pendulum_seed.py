"""
@module simulations.newtonian_pendulum_seed

Seed data for the NEWTONIAN PENDULUM (3D) — reality-first reformulation.

Real mass + gravity, a RIGID ROD (bilateral constraint → signed tension,
never clamped), full 3D vector state, and a step expressed entirely as
vector/matrix calculus (MatrixEquationOperation no-code states). Gravity is a
Partial contributing to the f_app_* accumulator; wind will be a sibling Partial
later. The rod + two force arrows render off the bob via cross-class
`depends_on`. Non-destructive: the Simple pendulum (in `seed_data.py`) is
untouched; everything here is `newtonian-pendulum-*`.

Split out of `seed_data.py` to keep both files comprehensible. Import is
ONE-DIRECTIONAL: this module imports the shared helpers + base SEED_PENDULUM_*
lists from `seed_data` and EXTENDS them in place (mutating the shared list
objects). `seed_data` does NOT import this module, so there is no circular
import — but it also means the Newtonian content only appears in the
SEED_PENDULUM_* lists once THIS module has been imported. The consumers that
need it (`polariServer`, the selftest) import this module explicitly, which
triggers the extends.
"""

import math
import json

from simulations.seed_data import (
    # Shared value-source + step-solution builders.
    _from_source,
    _array_source,
    _element_source,
    _step_solution_pair,
    _binding_param,
    _binding_sim_state,
    # Base SEED lists this module extends in place.
    SEED_SIMULATION_DEFINITIONS,
    SEED_SIMULATION_RUNS,
    SEED_PENDULUM_STEP_SOLUTION_DEFS,
    SEED_PENDULUM_STEP_SOLUTIONS,
    SEED_PENDULUM_STEP_EQUATIONS,
    SEED_PENDULUM_SIMSPACES,
    SEED_PENDULUM_BINDINGS,
    SEED_PENDULUM_EQUATIONS,
    SEED_PENDULUM_EVALUATION_EQUATIONS,
)
from simulations.newtonian_pendulum_bob_sim_state import (
    NewtonianPendulumBobSimState as _NBobCls,
)
from simulations.newtonian_pendulum_viz_states import (
    NewtonianPendulumRodSimState as _NRodCls,
)

NEWTON_SIM_DEF = 'newtonian-pendulum-3d'
NEWTON_RUN_NAME = 'newtonian-pendulum-run'
_NB = 'NewtonianPendulumBobSimState'
_NROD = 'NewtonianPendulumRodSimState'

_NEWTON_G = 9.81
_NEWTON_L = 1.0
_NEWTON_MASS = 1.0
_NEWTON_BOB_RADIUS = 0.08
_NEWTON_ROD_RADIUS = 0.01
_NEWTON_VIZ_FORCE_SCALE = 0.03
# Display timestep: semi-implicit Euler is first-order, so dt trades energy
# accuracy for live step count. 0.01 over 4 s ≈ 400 steps with ~5% peak energy
# drift (barely-visible amplitude overshoot). The selftest proves the
# formulation converges (<2% at dt=0.002); finer dt here just costs more steps.
_NEWTON_DT = 0.01
_NEWTON_DURATION = 4.0

# Geometry of the sphere bob + rod — derived constants. Only mass→gravity is
# ACTIVE now; surface area / volume / cross-sections are wired into the sim's
# parameters in advance so wind/buoyancy can read them without a reseed.
_n_bob_sa = 4.0 * math.pi * _NEWTON_BOB_RADIUS ** 2
_n_bob_vol = (4.0 / 3.0) * math.pi * _NEWTON_BOB_RADIUS ** 3
_n_bob_cs = math.pi * _NEWTON_BOB_RADIUS ** 2
_n_rod_lat = 2.0 * math.pi * _NEWTON_ROD_RADIUS * _NEWTON_L
_n_rod_cs = 2.0 * _NEWTON_ROD_RADIUS * _NEWTON_L

_NEWTON_PARAMS = {
    'g': _NEWTON_G, 'L': _NEWTON_L, 'mass': _NEWTON_MASS,
    'bob_radius': _NEWTON_BOB_RADIUS, 'rod_radius': _NEWTON_ROD_RADIUS,
    # Geometry (bob_cross_section is ACTIVE now — the wind drag Partial
    # reads it; the rest stays ready for buoyancy / rod drag).
    'bob_surface_area': _n_bob_sa, 'bob_volume': _n_bob_vol,
    'bob_cross_section': _n_bob_cs,
    'rod_lateral_area': _n_rod_lat, 'rod_cross_section': _n_rod_cs,
    # Aerodynamics for the wind drag Partial (wind_field_seed):
    # F = wind_on · ½·ρ·C_d·A·|w−v|·(w−v). Sphere C_d ≈ 0.47; sea-level air.
    'air_density': 1.225,
    'drag_coefficient': 0.47,
    # Visualization: metres of arrow length per Newton of force.
    'viz_force_scale': _NEWTON_VIZ_FORCE_SCALE,
}


def _vec3(a, b, c):
    """Array value-source over three context paths (a 3-vector operand)."""
    return _array_source([_from_source(a), _from_source(b), _from_source(c)])


def _mat_step(state_name, var, eq_name, operands, description):
    """A MatrixEquationOperation compute step: invoke a saved
    MatrixEquationDefinition with operands bound from the solution context.
    `operands` is a list of (symbol, value_source) pairs."""
    return {
        'kind': 'matrixEquation',
        'name': state_name,
        'var': var,
        'matrixEquationName': eq_name,
        'operandBindings': [{'symbol': s, 'source': src} for s, src in operands],
        'description': description,
    }


_F_APP = _vec3('self.f_app_x', 'self.f_app_y', 'self.f_app_z')

# --- Bob: gravity Partial (contributes (0,−m·g,0) into the f_app accumulator) ---
_NEWTON_GRAVITY_STEPS = [
    {
        'name': 'GravityY',
        'var': 'g_force_y',
        'latex': r'-m \cdot g',
        'bindings': {'m': 'self.mass', 'g': 'self.g'},
        'description': 'Gravity force, y-component: −m·g (x and z are zero).',
    },
]
# f_app_y is a `derivable` field → resets to 0 each step, so `add` starts from
# zero. f_app_x / f_app_z stay at their 0.0 default (no contribution needed).
_NEWTON_GRAVITY_OUTPUT_MAP = {'f_app_y': ('g_force_y', 'add')}

# --- Bob: vector Newtonian integrator (Composition) ---
# Order matters: the rigid-rod tension (the constraint force) is computed from
# the CURRENT state and folded into the acceleration BEFORE integrating, so the
# bob follows the curved (circular) path instead of flying off tangentially and
# being hard-snapped back (which dissipates energy). The position/velocity
# projection at the end only cleans up first-order numerical drift.
_CUR_P = _vec3('self.px', 'self.py', 'self.pz')
_CUR_V = _vec3('self.vx', 'self.vy', 'self.vz')
_NEWTON_INTEGRATOR_STEPS = [
    # 1. Rod direction from the CURRENT position (pivot = origin).
    _mat_step('RodDir', 'rhat', 'newton-rhat',
              [('p', _CUR_P)], 'rhat = normalize(p)'),
    # 2. Rigid-rod tension (SIGNED constraint force) from the current state.
    _mat_step('Tension', 'ftens', 'newton-tension',
              [('f', _F_APP), ('rhat', _from_source('rhat')),
               ('m', _from_source('self.mass')), ('v', _CUR_V),
               ('L', _from_source('self.L'))],
              'F_tension = −(F·rhat + m|v|²/L)·rhat'),
    # 3. Net force, then 4. net acceleration — tension is now IN the accel.
    _mat_step('NetForce', 'fnet', 'newton-net-force',
              [('f', _F_APP), ('t', _from_source('ftens'))],
              'F_net = F_applied + F_tension'),
    _mat_step('Accel', 'a', 'newton-accel',
              [('f', _from_source('fnet')), ('m', _from_source('self.mass'))],
              'a = F_net / m'),
    # 5/6. Semi-implicit (symplectic) Euler with the constraint-aware accel.
    _mat_step('VelStep', 'v1', 'newton-vel-step',
              [('v', _CUR_V), ('a', _from_source('a')), ('dt', _from_source('self.dt'))],
              'v1 = v + a·dt'),
    _mat_step('PosStep', 'p1', 'newton-pos-step',
              [('p', _CUR_P), ('v', _from_source('v1')), ('dt', _from_source('self.dt'))],
              'p1 = p + v1·dt'),
    # 7. Project back onto the rod sphere (numerical-drift cleanup only).
    _mat_step('RodDir2', 'rhat2', 'newton-rhat',
              [('p', _from_source('p1'))], 'rhat2 = normalize(p1)'),
    _mat_step('ConstrainPos', 'p_c', 'newton-constrain-pos',
              [('L', _from_source('self.L')), ('rhat', _from_source('rhat2'))],
              'p_c = L·rhat2 (rigid rod)'),
    _mat_step('ConstrainVel', 'v_c', 'newton-constrain-vel',
              [('v', _from_source('v1')), ('rhat', _from_source('rhat2'))],
              'v_c = v1 − (v1·rhat2)rhat2'),
    # 8. Diagnostics: gravity vector + energies (DERIVED).
    _mat_step('GravForce', 'fgrav', 'newton-grav-force',
              [('m', _from_source('self.mass')), ('g', _from_source('self.g')),
               ('d', _array_source([0, -1, 0]))],
              'F_grav = m·g·(0,−1,0)'),
    _mat_step('KE', 'ke', 'newton-ke',
              [('m', _from_source('self.mass')), ('v', _from_source('v_c'))],
              'KE = ½m|v|²'),
    _mat_step('PE', 'pe', 'newton-pe',
              [('m', _from_source('self.mass')), ('g', _from_source('self.g')),
               ('p', _from_source('p_c')), ('L', _from_source('self.L'))],
              'PE = m·g·(p_y + L)'),
    _mat_step('ETot', 'etot', 'newton-etot',
              [('ke', _from_source('ke')), ('pe', _from_source('pe'))],
              'E = KE + PE'),
    _mat_step('Speed', 'speed_v', 'newton-speed',
              [('v', _from_source('v_c'))], '|v|'),
]
_NEWTON_INTEGRATOR_OUTPUT_MAP = {
    'px': _element_source('p_c', 0), 'py': _element_source('p_c', 1), 'pz': _element_source('p_c', 2),
    'vx': _element_source('v_c', 0), 'vy': _element_source('v_c', 1), 'vz': _element_source('v_c', 2),
    'fgrav_x': _element_source('fgrav', 0), 'fgrav_y': _element_source('fgrav', 1), 'fgrav_z': _element_source('fgrav', 2),
    'ftens_x': _element_source('ftens', 0), 'ftens_y': _element_source('ftens', 1), 'ftens_z': _element_source('ftens', 2),
    'fnet_x': _element_source('fnet', 0), 'fnet_y': _element_source('fnet', 1), 'fnet_z': _element_source('fnet', 2),
    'ke': _element_source('ke', 0), 'pe': _element_source('pe', 0),
    'energy_total': _element_source('etot', 0), 'speed': _element_source('speed_v', 0),
}

# --- Viz companion: the rod (a connection that mirrors the bob position). The
# force ARROWS are NOT companion classes anymore — they're viz-only "State
# Projection" vector bindings on the bob itself (see _NEWTON_BINDINGS), reading
# its core fgrav_*/fnet_* fields directly. No companion class, rows, or deps. ---
_NB_GRAV_DEF, _NB_GRAV_META, _NB_GRAV_EQ = _step_solution_pair(
    name=f'{NEWTON_SIM_DEF}.bob.gravity-force',
    description=('Partial — gravity force on the bob: contributes (0,−m·g,0) to '
                 'the f_app accumulator. Wind will be a sibling Partial added to '
                 'the same f_app fields, with no change to the integrator.'),
    target_class=_NB, expected_inputs=['mass', 'g'],
    compute_steps=_NEWTON_GRAVITY_STEPS,
    output_field_to_context=_NEWTON_GRAVITY_OUTPUT_MAP,
    sim_step_role='simStepPartial', order_index=0, depends_on=[],
    sim_def_ref=NEWTON_SIM_DEF,
)
_NB_INT_DEF, _NB_INT_META, _NB_INT_EQ = _step_solution_pair(
    name=f'{NEWTON_SIM_DEF}.bob.integrator',
    description=('Composition — vector Newtonian integrator: a=F/m, semi-implicit '
                 'Euler, rigid-rod constraint projection (position + velocity), '
                 'signed tension, net force, and derived energies. All steps are '
                 'MatrixEquationOperations over 3-vectors.'),
    target_class=_NB,
    expected_inputs=['px', 'py', 'pz', 'vx', 'vy', 'vz',
                     'f_app_x', 'f_app_y', 'f_app_z', 'mass', 'g', 'L', 'dt'],
    compute_steps=_NEWTON_INTEGRATOR_STEPS,
    output_field_to_context=_NEWTON_INTEGRATOR_OUTPUT_MAP,
    sim_step_role='simStepComposition', order_index=1, depends_on=[],
    sim_def_ref=NEWTON_SIM_DEF,
)
_NB_ROD_DEF, _NB_ROD_META, _NB_ROD_EQ = _step_solution_pair(
    name=f'{NEWTON_SIM_DEF}.rod.step',
    description='Rigid rod endpoint — mirrors the bob position (pivot→bob connection).',
    target_class=_NROD, expected_inputs=['p_c'], compute_steps=[],
    output_field_to_context={
        'bob_x': _element_source('p_c', 0),
        'bob_y': _element_source('p_c', 1),
        'bob_z': _element_source('p_c', 2),
    },
    sim_step_role='simStepComplete', order_index=0, depends_on=[_NB],
    sim_def_ref=NEWTON_SIM_DEF,
)


def _newton_step0_row(cls, role_slug):
    """Step-0 initial-conditions row from a class's declared defaults — gives
    the scene a correct initial frame and lets the runner step forward from 1."""
    row = {
        'name': f'{NEWTON_RUN_NAME}-{role_slug}-0',
        'simulation_run_ref': NEWTON_RUN_NAME,
        'step': 0,
        'time': 0.0,
    }
    row.update(cls.default_initial_field_values)
    return row


SEED_NEWTON_BOB_ROWS = [_newton_step0_row(_NBobCls, 'newtonian-pendulum-bob')]
SEED_NEWTON_ROD_ROWS = [_newton_step0_row(_NRodCls, 'newtonian-pendulum-rod')]

_NEWTON_SIMSPACE = {
    'name': 'newtonian-pendulum-viz',
    'description': (
        '3D visualization of the Newtonian pendulum. The bob is a sphere sized '
        'to its metric radius; the rigid rod is a connection that tracks the bob. '
        'The gravity (red) + net (green) force arrows are State-Projection vector '
        'bindings on the bob — viz-only projections of its fgrav_*/fnet_* fields. '
        'Energies are derived (KE/PE/E_total) and shown for conservation checking.'
    ),
    'dimensionality': '3d',
    'coordinate_system': 'math',
    'unit_scale': 1.0,
    'viewport_json': '{"center": [0, 0, 0], "extent": [1.5, 1.5, 1.5]}',
    'bound_classes_json': json.dumps([
        {'className': _NB}, {'className': _NROD},
    ]),
    'definition': (
        '{"freestanding": ['
        '{"id":"pivot","position":[0,0,0],"shapeRef":"sphere","styleRef":"matte-gray",'
        '"scale":0.06,"label":"Pivot"}'
        ']}'
    ),
}

_NEWTON_BINDINGS = [
    {
        'name': f'{_NB}-3d', 'class_name': _NB, 'dimensionality': '3d', 'enabled': True,
        'binding_json': json.dumps({
            'enabled': True, 'dimensionality': '3d', 'kind': 'object',
            'position': {'kind': 'fields', 'fields': {'x': 'px', 'y': 'py', 'z': 'pz'}},
            'visual': {'shapeRef': 'sphere', 'styleRef': 'matte-blue'},
            # Sphere radius 0.5 × scale = metric bob_radius → scale = 2·radius.
            'scale': {'kind': 'constant', 'value': 2.0 * _NEWTON_BOB_RADIUS},
            'clickAction': 'navigate-to-instance', 'defaultVisible': True,
            'temporal': {'kind': 'time', 'field': 'time', 'unit': 'second', 'cumulative': False},
        }),
    },
    {
        'name': f'{_NROD}-3d', 'class_name': _NROD, 'dimensionality': '3d', 'enabled': True,
        'binding_json': json.dumps({
            'enabled': True, 'dimensionality': '3d', 'kind': 'connection',
            'source': {'kind': 'constant', 'value': [0, 0, 0]},
            'target': {'kind': 'fields', 'fields': {'x': 'bob_x', 'y': 'bob_y', 'z': 'bob_z'}},
            'visual': {'styleRef': 'metal-steel'},
            'clickAction': 'navigate-to-instance', 'defaultVisible': True,
            'temporal': {'kind': 'time', 'field': 'time', 'unit': 'second', 'cumulative': False},
        }),
    },
    # State-Projection force arrows — viz-only `vector` bindings on the BOB
    # itself. They read the bob's own core force fields (fgrav_*/fnet_*) and
    # draw an arrow from its position; no companion *SimState class, rows, or
    # dependency chain. scale = viz_force_scale (world units per Newton).
    {
        'name': f'{_NB}-gravity-arrow-3d', 'class_name': _NB, 'dimensionality': '3d', 'enabled': True,
        'binding_json': json.dumps({
            'enabled': True, 'dimensionality': '3d', 'kind': 'vector',
            'origin': {'kind': 'fields', 'fields': {'x': 'px', 'y': 'py', 'z': 'pz'}},
            'vector': {'kind': 'fields', 'fields': {'x': 'fgrav_x', 'y': 'fgrav_y', 'z': 'fgrav_z'}},
            'scale': _NEWTON_VIZ_FORCE_SCALE, 'headScale': 0.18,
            'visual': {'styleRef': 'arrow-gravity'},
            'clickAction': 'navigate-to-instance', 'defaultVisible': True,
            'temporal': {'kind': 'time', 'field': 'time', 'unit': 'second', 'cumulative': False},
        }),
    },
    {
        'name': f'{_NB}-net-arrow-3d', 'class_name': _NB, 'dimensionality': '3d', 'enabled': True,
        'binding_json': json.dumps({
            'enabled': True, 'dimensionality': '3d', 'kind': 'vector',
            'origin': {'kind': 'fields', 'fields': {'x': 'px', 'y': 'py', 'z': 'pz'}},
            'vector': {'kind': 'fields', 'fields': {'x': 'fnet_x', 'y': 'fnet_y', 'z': 'fnet_z'}},
            'scale': _NEWTON_VIZ_FORCE_SCALE, 'headScale': 0.18,
            'visual': {'styleRef': 'arrow-net'},
            'clickAction': 'navigate-to-instance', 'defaultVisible': True,
            'temporal': {'kind': 'time', 'field': 'time', 'unit': 'second', 'cumulative': False},
        }),
    },
]

# Register everything into the existing pendulum seed lists (seeded by
# polariServer._seedSimulations). The *_ROWS lists are wired separately in
# polariServer (one seed_pair per new class).
SEED_SIMULATION_DEFINITIONS.append({
    'name': NEWTON_SIM_DEF,
    'description': (
        'Newtonian pendulum (3D) — reality-first: real mass + gravity, a rigid '
        'rod (signed bilateral tension), full 3D vector state, and a step built '
        'from vector/matrix calculus. Gravity is a Partial; wind layers in later '
        'as a sibling Partial. Energies are derived, not seeded.'
    ),
    'participating_sim_state_classes_json': json.dumps([_NB, _NROD]),
    'time_step_seconds': _NEWTON_DT,
    'duration_seconds': _NEWTON_DURATION,
    'recording_interval_steps': 1,
    'initial_conditions_overrides_json': '{}',
    'parameters_json': json.dumps(_NEWTON_PARAMS),
    'termination_predicate': '',
    'time_unit': 'second',
})
SEED_SIMULATION_RUNS.append({
    'name': NEWTON_RUN_NAME,
    'simulation_ref': NEWTON_SIM_DEF,
    'status': 'pending',
    'started_at': '',
    'completed_at': '',
    'total_steps': int(math.ceil(_NEWTON_DURATION / _NEWTON_DT)),
    'recorded_steps': 1,
    'last_recorded_step': 0,
    'error_message': '',
    'label': 'Newtonian pendulum — live run (press play to integrate)',
})
SEED_PENDULUM_STEP_SOLUTION_DEFS.extend(
    [_NB_GRAV_DEF, _NB_INT_DEF, _NB_ROD_DEF]
)
SEED_PENDULUM_STEP_SOLUTIONS.extend(
    [_NB_GRAV_META, _NB_INT_META, _NB_ROD_META]
)
SEED_PENDULUM_STEP_EQUATIONS.extend(
    _NB_GRAV_EQ + _NB_INT_EQ + _NB_ROD_EQ
)
SEED_PENDULUM_SIMSPACES.append(_NEWTON_SIMSPACE)
SEED_PENDULUM_BINDINGS.extend(_NEWTON_BINDINGS)


# --- Live-evaluation HUD readouts (top-right) ------------------------------
# The bob already computes ke / pe / energy_total / speed and the tension
# vector as row fields; these eval equations recompute the energies from the
# primary fields (speed, py) and the tension magnitude from ftens_*, so the
# HUD shows the evaluation system pulling live sim data each step.
def _newt_eq(name, description, latex):
    return {
        'name': name,
        'description': description,
        'source_class': NEWTON_SIM_DEF,
        'definition': json.dumps({
            'latexExpression': latex,
            'operationType': 'evaluate',
            'variableBindings': [],   # bindings live on the SimSpaceEvaluationEquation
            'bounds': None,
            'options': {},
            'resultSpec': {'type': 'scalar'},
        }),
    }


SEED_NEWTON_EVAL_EQUATION_DEFS = [
    _newt_eq('newtonian-pendulum-3d.kinetic-energy', 'KE = ½ m |v|².',
             r'\frac{1}{2} \cdot m \cdot v^{2}'),
    _newt_eq('newtonian-pendulum-3d.potential-energy', 'PE = m·g·(y + L).',
             r'm \cdot g \cdot (y + L)'),
    _newt_eq('newtonian-pendulum-3d.total-energy', 'Total mechanical energy KE + PE.',
             r'\frac{1}{2} \cdot m \cdot v^{2} + m \cdot g \cdot (y + L)'),
    # Single-letter symbols (a/b/c) ON PURPOSE: SymPy's parse_latex reads a
    # multi-letter token like `Tx` as the PRODUCT T·x, so it never substitutes
    # the binding and the eval errors with "cannot convert expression to float".
    _newt_eq('newtonian-pendulum-3d.rod-tension', 'Rigid-rod tension magnitude |F_T|.',
             r'\sqrt{a^{2} + b^{2} + c^{2}}'),
]

# Symbols → live sim data. Energies read mass/g/L params + the bob's speed/py
# fields; tension reads the bob's ftens_* components.
_NEWT_ENERGY_BINDINGS = [
    _binding_param('m', 'mass', 'mass'),
    _binding_param('g', 'g', 'g'),
    _binding_param('L', 'L', 'L'),
    _binding_sim_state('v', 'speed', _NB, 'speed'),
    _binding_sim_state('y', 'py', _NB, 'py'),
]
_NEWT_TENSION_BINDINGS = [
    _binding_sim_state('a', 'ftens_x', _NB, 'ftens_x'),
    _binding_sim_state('b', 'ftens_y', _NB, 'ftens_y'),
    _binding_sim_state('c', 'ftens_z', _NB, 'ftens_z'),
]


def _newt_eval(name, equation_ref, bindings, result_ref, sort_order):
    return {
        'name': name,
        'description': f'Live readout on the Newtonian scene — {result_ref}.',
        'sim_space_ref': 'newtonian-pendulum-viz',
        'equation_ref': equation_ref,
        'variable_bindings_json': json.dumps(bindings),
        'result_variable_ref': result_ref,
        'anchor_kind': 'screen',
        'anchor_data_json': '{"corner": "top-right"}',
        'sort_order': sort_order,
        'enabled': True,
    }


SEED_NEWTON_EVALUATION_EQUATIONS = [
    _newt_eval('newtonian-pendulum-viz.total-energy', 'newtonian-pendulum-3d.total-energy',
               _NEWT_ENERGY_BINDINGS, 'total_energy', 0),
    _newt_eval('newtonian-pendulum-viz.kinetic-energy', 'newtonian-pendulum-3d.kinetic-energy',
               _NEWT_ENERGY_BINDINGS, 'kinetic_energy', 1),
    _newt_eval('newtonian-pendulum-viz.potential-energy', 'newtonian-pendulum-3d.potential-energy',
               _NEWT_ENERGY_BINDINGS, 'potential_energy', 2),
    _newt_eval('newtonian-pendulum-viz.rod-tension', 'newtonian-pendulum-3d.rod-tension',
               _NEWT_TENSION_BINDINGS, 'rod_tension', 3),
]

# EquationDefinitions are seeded with SEED_PENDULUM_EQUATIONS; the eval rows
# with SEED_PENDULUM_EVALUATION_EQUATIONS (both already in _seedSimulations).
SEED_PENDULUM_EQUATIONS.extend(SEED_NEWTON_EVAL_EQUATION_DEFS)
SEED_PENDULUM_EVALUATION_EQUATIONS.extend(SEED_NEWTON_EVALUATION_EQUATIONS)
