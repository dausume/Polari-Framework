"""
@module simulations.wind_field_seed

Seed data for the WIND FIELD space + its coupling into the Newtonian
pendulum — the first working cross-space (multi-scale) composition.

Three pieces, all authored as no-code content:

  1. THE WIND SPACE — `wind-field-3d`: a SimulationDefinition over
     WindFieldGridState (the whole grid on one row as a matrix-valued
     `cells_json` field), stepping at dt=0.1 s — TEN TIMES coarser than
     the pendulum's 0.01 s. Its single Complete step solution evolves
     the field with one MatrixEquationOperation (`wind-field-evolve`, a
     deterministic spatial+temporal gust model over the cell centers).

  2. THE COUPLING — a SimulationCouplingDefinition declaring: when
     `newtonian-pendulum-3d` steps its bob, sample the wind run's grid
     at the bob's position (`field-sample-nearest`, itself a no-code
     matrix equation) and inject wind_vx/vy/vz + wind_on into the bob's
     step context. Runs opt in via `coupled_run_refs_json` — the new
     `newtonian-pendulum-wind-run` couples to `wind-field-run`, while
     the original vacuum run stays exactly as it was (defaults inject
     wind_on=0 → the drag Partial contributes zero).

  3. THE WIND FORCE — a sibling Partial on the bob (the seam the
     integrator was designed with): aerodynamic drag
     F = wind_on · ½·ρ·C_d·A·|w−v|·(w−v), `add`ed into the f_app_*
     accumulator and `set` onto fwind_* for the wind arrow. No change
     to the integrator.

Viz: a `field`-kind binding fans the grid row out into per-cell arrows
(sparse: deterministic hash(cell, step) decimation + a magnitude floor),
plus a cyan wind-force arrow on the bob. Both render in the existing
`newtonian-pendulum-viz` scene — its run scope expands to the coupled
wind run (simulations.run_scope).

Same registration pattern as newtonian_pendulum_seed: this module
EXTENDS the shared SEED_* lists in place and polariServer imports it
explicitly (AFTER the newtonian seed, so the scene + list mutations
land in order).
"""

import json
import math

from simulations.seed_data import (
    _from_source,
    _element_source,
    _step_solution_pair,
    _binding_sim_state,
    SEED_SIMULATION_DEFINITIONS,
    SEED_SIMULATION_RUNS,
    SEED_PENDULUM_STEP_SOLUTION_DEFS,
    SEED_PENDULUM_STEP_SOLUTIONS,
    SEED_PENDULUM_STEP_EQUATIONS,
    SEED_PENDULUM_BINDINGS,
    SEED_PENDULUM_EQUATIONS,
    SEED_PENDULUM_EVALUATION_EQUATIONS,
)
from simulations.newtonian_pendulum_seed import (
    _mat_step,
    _vec3,
    _newt_eq,
    _newt_eval,
    _NEWTON_SIMSPACE,
    NEWTON_SIM_DEF,
    _NB,
)
from simulations.newtonian_pendulum_bob_sim_state import (
    NewtonianPendulumBobSimState as _NBobCls,
)
from simulations.newtonian_pendulum_viz_states import (
    NewtonianPendulumRodSimState as _NRodCls,
)
from simulations.wind_field_grid_sim_state import (
    WindFieldGridState as _WGridCls,
)
from matrices.seed_data import SEED_MATRIX_EQUATIONS, _eq

WIND_SIM_DEF = 'wind-field-3d'
WIND_RUN_NAME = 'wind-field-run'
NEWTON_WIND_RUN_NAME = 'newtonian-pendulum-wind-run'
_WGRID = 'WindFieldGridState'

# The wind space's OWN timescale — 10× coarser than the pendulum's 0.01 s.
# The coupling's lazy pull advances the wind run only when the pendulum's
# time moves past its coverage; the pendulum samples the latest wind step
# ≤ its own time (zero-order hold across the dt gap).
_WIND_DT = 0.1
_WIND_DURATION = 4.0

# Gust model parameters. Magnitudes are picked so the drag on the default
# bob (m=1 kg, r=8 cm → A≈0.0201 m², C_d=0.47, sea-level air) peaks around
# ~0.5 N — a few-degree lean against 9.81 N of gravity, and (since the
# base flow has a strong +z component) a clearly visible OUT-OF-PLANE
# drift: the vacuum pendulum stays planar, the coupled one goes 3D.
_WIND_PARAMS = {
    'wind_amp': 4.5,        # gust amplitude (m/s)
    'wind_freq': 1.2,       # gust angular frequency (rad/s)
    'wind_base_x': 1.5,     # steady base flow (m/s)
    'wind_base_z': 2.8,
}


def _json_decode(inner):
    """Value-source that parses a JSON-string source (matrix-valued state
    fields, e.g. cells_json) into the nested list operands expect."""
    return {'sourceType': 'json_decode', 'source': inner}


def _json_encode(inner):
    """Value-source that serializes a source back to a JSON string (the
    write half of matrix-valued state fields)."""
    return {'sourceType': 'json_encode', 'source': inner}


# ---------------------------------------------------------------------------
# Matrix equations (appended into matrices.seed_data's shared list — this
# module is imported before _seedMatrixEquations runs, same in-place-extend
# pattern as the SEED_PENDULUM_* lists).
# ---------------------------------------------------------------------------

SEED_MATRIX_EQUATIONS.extend([
    _eq('wind-field-evolve',
        'Wind gust field over the grid: carry the cell centers through, '
        'recompute the velocity columns as a base flow plus spatially- and '
        'temporally-varying sinusoid gusts (deterministic — scrubbing back '
        'replays the same field). cells is N×6 [cx,cy,cz,wx,wy,wz].',
        r'\mathbf{w}(\mathbf{c}, t) = \mathbf{w}_{base} + a\,\sin(\omega t + \mathbf{k}\cdot\mathbf{c})',
        {'kind': 'expr',
         'expr': ('np.hstack([cells[:, :3], np.stack(['
                  'bx + a * np.sin(w * t + 2.1 * cells[:, 0] + 1.3 * cells[:, 2]), '
                  '0.25 * a * np.sin(1.7 * w * t + 2.9 * cells[:, 1] + 0.8 * cells[:, 0]), '
                  'bz + a * np.cos(0.8 * w * t + 1.9 * cells[:, 2] + 0.7 * cells[:, 0])'
                  '], axis=1)])')},
        {'cells': 'cells', 't': 't', 'a': 'a', 'w': 'w', 'bx': 'bx', 'bz': 'bz'},
        'wind-field,field,gust'),

    _eq('field-sample-nearest',
        'Sample a grid field at a point: the velocity columns of the cell '
        'whose center is nearest pos. THE cross-space sampler — cells is '
        'N×6 [cx,cy,cz,wx,wy,wz], pos a 3-vector; swapping this for a '
        'trilinear blend is authoring, not plumbing.',
        r'\mathbf{w}(\mathbf{p}) = \mathbf{w}_{\arg\min_i \lVert\mathbf{c}_i-\mathbf{p}\rVert}',
        {'kind': 'expr',
         'expr': 'cells[np.argmin(np.sum((cells[:, :3] - pos) ** 2, axis=1)), 3:]'},
        {'cells': 'cells', 'pos': 'pos'},
        'wind-field,field,sampling'),

    _eq('newton-wind-drag',
        'Aerodynamic drag on the bob from the sampled wind: '
        'F = won · ½·ρ·C_d·A·|w−v|·(w−v). Quadratic drag against the '
        'RELATIVE flow (w − v), so still air (w=0, won=1) would brake the '
        'bob; won=0 (uncoupled run) zeroes it exactly — vacuum preserved.',
        r'\mathbf{F}_{wind} = \tfrac{1}{2}\rho C_d A\,\lVert\mathbf{w}-\mathbf{v}\rVert(\mathbf{w}-\mathbf{v})',
        {'kind': 'expr',
         'expr': 'won * 0.5 * rho * cd * area * norm(w - v) * (w - v)'},
        {'won': 'won', 'rho': 'rho', 'cd': 'cd', 'area': 'area', 'w': 'w', 'v': 'v'},
        'newtonian-pendulum,wind-field,vector,force'),
])


# ---------------------------------------------------------------------------
# 1. The wind space — sim def, run, step solution, step-0 grid row.
# ---------------------------------------------------------------------------

SEED_SIMULATION_DEFINITIONS.append({
    'name': WIND_SIM_DEF,
    'description': (
        'Wind-field space — a 4×4×4 grid of wind vectors filling the '
        'pendulum box, evolved as a deterministic gust model at dt=0.1 s '
        '(10× coarser than the pendulum: a genuinely different timescale). '
        'The whole grid is ONE matrix-valued row per step (cells_json, '
        'N×6). Output: a sampleable vector field other spaces couple to.'
    ),
    'participating_sim_state_classes_json': json.dumps([_WGRID]),
    'time_step_seconds': _WIND_DT,
    'duration_seconds': _WIND_DURATION,
    'recording_interval_steps': 1,
    'initial_conditions_overrides_json': '{}',
    'parameters_json': json.dumps(_WIND_PARAMS),
    'termination_predicate': '',
    'time_unit': 'second',
})

SEED_SIMULATION_RUNS.append({
    'name': WIND_RUN_NAME,
    'simulation_ref': WIND_SIM_DEF,
    'status': 'pending',
    'started_at': '',
    'completed_at': '',
    'total_steps': int(math.ceil(_WIND_DURATION / _WIND_DT)),
    'recorded_steps': 1,
    'last_recorded_step': 0,
    'error_message': '',
    'label': 'Wind field — advanced lazily by coupled pendulum runs',
})

_WIND_STEP_DEF, _WIND_STEP_META, _WIND_STEP_EQ = _step_solution_pair(
    name=f'{WIND_SIM_DEF}.grid.evolve',
    description=('Complete — evolve the wind grid one wind-step: decode the '
                 'matrix-valued cells_json state, recompute the velocity '
                 'columns from the gust model at the new time, encode back. '
                 'One MatrixEquationOperation; centers pass through.'),
    target_class=_WGRID,
    expected_inputs=['cells_json', 'time',
                     'wind_amp', 'wind_freq', 'wind_base_x', 'wind_base_z'],
    compute_steps=[
        _mat_step('EvolveField', 'cells_new', 'wind-field-evolve',
                  [('cells', _json_decode(_from_source('self.cells_json'))),
                   ('t', _from_source('self.time')),
                   ('a', _from_source('self.wind_amp')),
                   ('w', _from_source('self.wind_freq')),
                   ('bx', _from_source('self.wind_base_x')),
                   ('bz', _from_source('self.wind_base_z'))],
                  'cells_new = [centers | gust(centers, t)]'),
    ],
    output_field_to_context={
        'cells_json': _json_encode(_from_source('cells_new')),
    },
    sim_step_role='simStepComplete', order_index=0, depends_on=[],
    sim_def_ref=WIND_SIM_DEF,
)

SEED_WIND_GRID_ROWS = [{
    'name': f'{WIND_RUN_NAME}-wind-field-grid-0',
    'simulation_run_ref': WIND_RUN_NAME,
    'step': 0,
    'time': 0.0,
    **_WGridCls.default_initial_field_values,
}]


# ---------------------------------------------------------------------------
# 2. The coupling — definition row + the coupled pendulum run (and its
#    step-0 rows; the vacuum run + its rows stay untouched in the
#    newtonian seed).
# ---------------------------------------------------------------------------

SEED_SIMULATION_COUPLINGS = [{
    'name': 'wind-to-newtonian-pendulum',
    'description': (
        'When the Newtonian pendulum steps its bob, sample the coupled '
        'wind run\'s grid at the bob\'s (previous) position and inject '
        'wind_vx/vy/vz + wind_on=1 into the step context; the wind drag '
        'Partial turns them into force. Runs without a coupled wind run '
        'get the defaults (wind_on=0 → exact vacuum behavior).'
    ),
    'target_simulation_ref': NEWTON_SIM_DEF,
    'target_class_name': _NB,
    'source_simulation_ref': WIND_SIM_DEF,
    'source_class_name': _WGRID,
    'sampler_equation_ref': 'field-sample-nearest',
    'config_json': json.dumps({
        'sampler': {
            'operands': {
                'cells': {'kind': 'source_field_json', 'field': 'cells_json'},
                'pos': {'kind': 'target_fields', 'fields': ['px', 'py', 'pz']},
            },
        },
        'inject': {
            'wind_vx': {'kind': 'sample_element', 'index': 0},
            'wind_vy': {'kind': 'sample_element', 'index': 1},
            'wind_vz': {'kind': 'sample_element', 'index': 2},
            'wind_on': {'kind': 'constant', 'value': 1.0},
        },
        'defaults': {
            'wind_vx': 0.0, 'wind_vy': 0.0, 'wind_vz': 0.0, 'wind_on': 0.0,
        },
    }),
    'enabled': True,
}]

SEED_SIMULATION_RUNS.append({
    'name': NEWTON_WIND_RUN_NAME,
    'simulation_ref': NEWTON_SIM_DEF,
    'status': 'pending',
    'started_at': '',
    'completed_at': '',
    'total_steps': 400,
    'recorded_steps': 1,
    'last_recorded_step': 0,
    'error_message': '',
    'label': 'Newtonian pendulum + WIND — coupled to the wind-field run',
    # THE run-level pairing: which source run feeds each coupled sim.
    'coupled_run_refs_json': json.dumps({WIND_SIM_DEF: WIND_RUN_NAME}),
})


def _wind_run_step0_row(cls, role_slug):
    """Step-0 IC row for the coupled run — same release state as the
    vacuum run, so any divergence between the two IS the wind."""
    row = {
        'name': f'{NEWTON_WIND_RUN_NAME}-{role_slug}-0',
        'simulation_run_ref': NEWTON_WIND_RUN_NAME,
        'step': 0,
        'time': 0.0,
    }
    row.update(cls.default_initial_field_values)
    return row


SEED_NEWTON_WIND_BOB_ROWS = [_wind_run_step0_row(_NBobCls, 'newtonian-pendulum-bob')]
SEED_NEWTON_WIND_ROD_ROWS = [_wind_run_step0_row(_NRodCls, 'newtonian-pendulum-rod')]


# ---------------------------------------------------------------------------
# 3. The wind force — a sibling Partial on the bob (gravity's designed peer).
# ---------------------------------------------------------------------------

_WIND_DRAG_DEF, _WIND_DRAG_META, _WIND_DRAG_EQ = _step_solution_pair(
    name=f'{NEWTON_SIM_DEF}.bob.wind-force',
    description=('Partial — aerodynamic drag from the coupling-sampled wind: '
                 'F = wind_on·½·ρ·C_d·A·|w−v|·(w−v), added into the f_app '
                 'accumulator beside gravity (no integrator change) and set '
                 'onto fwind_* for the wind arrow. wind_* context keys are '
                 'injected by the wind-to-newtonian-pendulum coupling '
                 '(defaults wind_on=0 → contributes exactly zero).'),
    target_class=_NB,
    expected_inputs=['vx', 'vy', 'vz',
                     'wind_vx', 'wind_vy', 'wind_vz', 'wind_on',
                     'air_density', 'drag_coefficient', 'bob_cross_section'],
    compute_steps=[
        _mat_step('WindDrag', 'fwind', 'newton-wind-drag',
                  [('won', _from_source('self.wind_on')),
                   ('rho', _from_source('self.air_density')),
                   ('cd', _from_source('self.drag_coefficient')),
                   ('area', _from_source('self.bob_cross_section')),
                   ('w', _vec3('self.wind_vx', 'self.wind_vy', 'self.wind_vz')),
                   ('v', _vec3('self.vx', 'self.vy', 'self.vz'))],
                  'F_wind = won·½ρ·C_d·A·|w−v|·(w−v)'),
    ],
    output_field_to_context={
        'f_app_x': (_element_source('fwind', 0), 'add'),
        'f_app_y': (_element_source('fwind', 1), 'add'),
        'f_app_z': (_element_source('fwind', 2), 'add'),
        'fwind_x': (_element_source('fwind', 0), 'set'),
        'fwind_y': (_element_source('fwind', 1), 'set'),
        'fwind_z': (_element_source('fwind', 2), 'set'),
    },
    sim_step_role='simStepPartial', order_index=0, depends_on=[],
    sim_def_ref=NEWTON_SIM_DEF,
)


# ---------------------------------------------------------------------------
# Visualization — wind cells in the pendulum scene + a wind arrow on the bob.
# ---------------------------------------------------------------------------

# The scene declares the wind class so (a) the field binding renders and
# (b) run-scope expansion has a reason to matter. participatingSimulations
# stays newtonian-first (binding seed order), so the run panel / play
# button keep driving the pendulum — the wind run advances via lazy pull.
_scene_classes = json.loads(_NEWTON_SIMSPACE['bound_classes_json'])
_scene_classes.append({'className': _WGRID})
_NEWTON_SIMSPACE['bound_classes_json'] = json.dumps(_scene_classes)

SEED_WIND_BINDINGS = [
    # The FIELD projection: the grid row fans out into per-cell arrows.
    # Sparse/intermittent: deterministic hash(cell, step) decimation at
    # `density`, plus a magnitude floor — hidden cells emit zero-length
    # vectors so the renderer retires their arrows scrub-safely.
    {
        'name': f'{_WGRID}-3d', 'class_name': _WGRID, 'dimensionality': '3d', 'enabled': True,
        'binding_json': json.dumps({
            'enabled': True, 'dimensionality': '3d', 'kind': 'field',
            'matrixField': 'cells_json',
            'layout': {'originCols': [0, 3], 'vectorCols': [3, 6]},
            # metres of arrow per (m/s) of wind — |w|≈9 m/s → 0.54 m.
            'scale': 0.06, 'headScale': 0.3,
            'decimation': {'density': 0.35, 'magnitudeMin': 0.5},
            'visual': {'styleRef': 'arrow-wind'},
            'defaultVisible': True,
            'temporal': {'kind': 'time', 'field': 'time', 'unit': 'second', 'cumulative': False},
        }),
    },
    # The sampled wind-drag force on the bob — same State-Projection kind
    # as the gravity/net arrows. Drag is ~0.5 N vs gravity's 9.81 N, so it
    # gets its own viz scale; on the vacuum run fwind is zero → degenerate
    # skip → no arrow (correct).
    {
        'name': f'{_NB}-wind-arrow-3d', 'class_name': _NB, 'dimensionality': '3d', 'enabled': True,
        'binding_json': json.dumps({
            'enabled': True, 'dimensionality': '3d', 'kind': 'vector',
            'origin': {'kind': 'fields', 'fields': {'x': 'px', 'y': 'py', 'z': 'pz'}},
            'vector': {'kind': 'fields', 'fields': {'x': 'fwind_x', 'y': 'fwind_y', 'z': 'fwind_z'}},
            'scale': 0.6, 'headScale': 0.18,
            'visual': {'styleRef': 'arrow-wind'},
            'clickAction': 'navigate-to-instance', 'defaultVisible': True,
            'temporal': {'kind': 'time', 'field': 'time', 'unit': 'second', 'cumulative': False},
        }),
    },
]

# HUD readout: |F_wind| beside the energies/tension (bob fields only, so
# the eval's step intersection stays within the pendulum run's rows).
SEED_PENDULUM_EQUATIONS.append(
    _newt_eq('newtonian-pendulum-3d.wind-force', 'Sampled wind drag magnitude |F_wind|.',
             r'\sqrt{a^{2} + b^{2} + c^{2}}')
)
SEED_PENDULUM_EVALUATION_EQUATIONS.append(
    _newt_eval('newtonian-pendulum-viz.wind-force', 'newtonian-pendulum-3d.wind-force',
               [
                   _binding_sim_state('a', 'fwind_x', _NB, 'fwind_x'),
                   _binding_sim_state('b', 'fwind_y', _NB, 'fwind_y'),
                   _binding_sim_state('c', 'fwind_z', _NB, 'fwind_z'),
               ],
               'wind_force', 4)
)


# Register everything into the shared seed lists (the *_ROWS and
# SEED_SIMULATION_COUPLINGS lists are wired separately in polariServer).
SEED_PENDULUM_STEP_SOLUTION_DEFS.extend([_WIND_STEP_DEF, _WIND_DRAG_DEF])
SEED_PENDULUM_STEP_SOLUTIONS.extend([_WIND_STEP_META, _WIND_DRAG_META])
SEED_PENDULUM_STEP_EQUATIONS.extend(_WIND_STEP_EQ + _WIND_DRAG_EQ)
SEED_PENDULUM_BINDINGS.extend(SEED_WIND_BINDINGS)
