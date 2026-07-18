"""
@cross-cutting
@module waxprint.sim_seed
@tags @xc:render-3d, @xc:bindings

Registers the wax-print simulation as a first-class, VIEWABLE multiscale
sim space (wp-5/wp-6): a SimulationDefinition + a MultiScaleSimulation
wrapper, a SimSpace3D scene (a stacked column of bead voxels colour-coded
by print state), live SimSpaceEvaluationEquation condition readouts, an
initial-condition picker, two pre-computed baseline runs, and a display
page. Importing this module APPENDS its rows to the shared framework seed
lists (same trigger-on-import pattern as material_space_scene_seed), so
polariServer only needs to import it + register the new WaxPrintSimState
rows + the page display.

The baseline run rows are computed HERE, at import, by the validated
wp-1..3 physics against a mock manager built from the waxprint seeds — so
what renders is real physics, not placeholder geometry.

@consumers
  - polariServer (imports this; registers WaxPrintSimState rows + page)
@see /WAX_PRINT_VOXEL_PLAN.md
"""

import json
from types import SimpleNamespace

from waxprint import sim_runner
from waxprint.waxprint_seed import (
    SEED_DEVICE_MATERIALS, SEED_FEEDSTOCKS, SEED_ASSEMBLIES, SEED_CONDITIONS)

# Shared framework seed lists (mutated on import — the trigger pattern).
from simulations.seed_data import (
    SEED_SIMULATION_DEFINITIONS, SEED_SIMULATION_RUNS,
    SEED_PENDULUM_SIMSPACES, SEED_PENDULUM_BINDINGS,
    SEED_PENDULUM_EQUATIONS, SEED_PENDULUM_EVALUATION_EQUATIONS,
)
from simulations.multi_scale_seed import (
    SEED_MULTI_SCALE_SIMS, SEED_IC_INTERFACES,
)
from simSpace3D.seed_data import SEED_MATERIALS_3D

SCENE = 'wax-print-wall'
SIM = 'wax-print'
MSIM = 'wax-print-multiscale'
_CLS = 'WaxPrintSimState'
_MAX_H = sim_runner.DEFAULT_MAX_HEIGHT_MM
_TARGET_VOX = sim_runner.DEFAULT_TARGET_VOXEL_XY_MM
_MARGIN_TOL = sim_runner.DEFAULT_MARGIN_TOL_MM


# --------------------------------------------------------------------------
# a mock manager over the waxprint seeds → compute real baseline rows
# --------------------------------------------------------------------------
def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


_MOCK = SimpleNamespace(objectTables={
    'DeviceMaterialDefinition': _rows(SEED_DEVICE_MATERIALS),
    'WaxFeedstockDefinition': _rows(SEED_FEEDSTOCKS),
    'PrinterAssemblyDefinition': _rows(SEED_ASSEMBLIES),
    'PrintConditionDefinition': _rows(SEED_CONDITIONS),
})


def _baseline_rows(assembly, feedstock, condition, run_name, x_off):
    out = sim_runner.compute_step_rows(
        _MOCK, assembly, feedstock, condition, run_name,
        max_height_mm=_MAX_H, target_voxel_xy_mm=_TARGET_VOX,
        margin_tol_mm=_MARGIN_TOL, pos_x_offset=x_off)
    return out['rows'] if out.get('ok') else []


# The two seeded runs: a room-temperature demo (printable but coarse) and
# a cooled fine-nozzle recipe (meets the target) — side by side.
_RUN_BASELINE = 'wax-print-baseline'
_RUN_FINE = 'wax-print-fine'
SEED_WAXPRINT_STATE_ROWS = (
    _baseline_rows('demo-auger-extruder', 'mvw-natural-blend',
                   'room-baseline', _RUN_BASELINE, 0.0)
    + _baseline_rows('fine-nozzle-extruder', 'carnauba-rich',
                     'fine-voxel', _RUN_FINE, 8.0))


# --------------------------------------------------------------------------
# 3D materials (colour by print state) + the scene + binding
# --------------------------------------------------------------------------
def _mat(name, color, desc):
    return {'name': name, 'description': desc, 'material_type': 'standard',
            'color': color, 'emissive': '#000000', 'emissive_intensity': 0.0,
            'metalness': 0.1, 'roughness': 0.7, 'opacity': 1.0,
            'transparent': False, 'double_sided': False, 'flat_shading': False,
            'wireframe': False}


SEED_MATERIALS_3D.extend([
    _mat('wax-unsafe', '#c62828', 'Unsafe / unprintable step (red).'),
    _mat('wax-coarse', '#f9a825', 'Printable but coarse voxel (amber).'),
    _mat('wax-fine', '#2e7d32', 'Printable + meets resolution target (green).'),
    _mat('extruder-steel', '#78909c', 'Static extruder body (gray).'),
])

_WAXPRINT_SCENE = {
    'name': SCENE,
    'description': 'Wax print building up by build height — each bead voxel '
                   'coloured by print state (red=unsafe/unprintable, '
                   'amber=printable-coarse, green=meets target). Left column '
                   '= room-temp demo, right = cooled fine recipe. Scrub to '
                   'watch the wall grow and resolution change with height.',
    'dimensionality': '3d',
    'coordinate_system': 'math',
    'unit_scale': 1.0,
    'viewport_json': json.dumps({'center': [4, _MAX_H / 2.0, 0],
                                 'extent': [12, _MAX_H * 0.7, 12]}),
    'bound_classes_json': json.dumps([{'className': _CLS}]),
    'definition': json.dumps({'freestanding': [
        {'id': 'nozzle', 'position': [0, _MAX_H + 3, 0], 'shapeRef': 'cone',
         'styleRef': 'extruder-steel', 'scale': [1.5, 3, 1.5],
         'label': 'Nozzle'},
        {'id': 'barrel', 'position': [0, _MAX_H + 9, 0], 'shapeRef': 'cylinder',
         'styleRef': 'extruder-steel', 'scale': [3, 8, 3],
         'label': 'Auger barrel'},
    ]}),
    'owning_module': 'waxprint',
}

_WAXPRINT_BINDINGS = [{
    'name': f'{_CLS}-3d', 'class_name': _CLS, 'dimensionality': '3d',
    'enabled': True,
    'binding_json': json.dumps({
        'enabled': True, 'dimensionality': '3d', 'kind': 'object',
        'position': {'kind': 'fields',
                     'fields': {'x': 'pos_x', 'y': 'pos_y', 'z': 'pos_z'}},
        'visual': {'shapeRef': 'cube', 'styleRef': {
            'fromField': 'render_state',
            'map': {'0': 'wax-unsafe', '1': 'wax-coarse', '2': 'wax-fine'},
            'default': 'wax-coarse'}},
        # voxel width is sub-mm; exaggerate ~8x so the column is legible.
        'scale': {'kind': 'uniform', 'field': 'voxel_xy_mm', 'factor': 8.0},
        'clickAction': 'navigate-to-instance', 'defaultVisible': True,
        'temporal': {'kind': 'time', 'field': 'time', 'unit': 'mm',
                     'cumulative': True},
    }),
}]

SEED_PENDULUM_SIMSPACES.append(_WAXPRINT_SCENE)
SEED_PENDULUM_BINDINGS.extend(_WAXPRINT_BINDINGS)


# --------------------------------------------------------------------------
# live condition-readout equations (SimSpaceEvaluationEquation overlays)
# --------------------------------------------------------------------------
def _eqdef(name, description, latex):
    return {
        'name': name, 'description': description, 'source_class': SIM,
        'definition': json.dumps({
            'latexExpression': latex, 'operationType': 'evaluate',
            'variableBindings': [], 'bounds': None, 'options': {},
            'resultSpec': {'type': 'scalar'}}),
    }


def _b_state(symbol, software, field):
    return {'symbol': symbol, 'softwareName': software,
            'source': {'kind': 'simState', 'class': _CLS, 'field': field}}


def _b_const(symbol, software, value):
    return {'symbol': symbol, 'softwareName': software,
            'source': {'kind': 'const', 'value': value}}


# Single-letter symbols on purpose (SymPy parse_latex reads multi-letter
# tokens as products — see newtonian_pendulum_seed note).
_EQ_DEFS = [
    _eqdef(f'{SCENE}.melt', 'Melt fraction (target >= 0.98).', r'f'),
    _eqdef(f'{SCENE}.voxel-headroom',
           'Resolution headroom: target minus voxel width (>=0 = met).',
           r't - x'),
    _eqdef(f'{SCENE}.margin', 'Repeatability margin (mm, smaller better).',
           r'm'),
    _eqdef(f'{SCENE}.movement-fraction',
           'Fraction of movement patterns viable.', r'\frac{a}{b}'),
    _eqdef(f'{SCENE}.warp', 'Fan warp asymmetry index (0 = none).', r'w'),
]

_EVALS = [
    {'name': f'{SCENE}.melt-eval', 'description': 'Live melt fraction.',
     'sim_space_ref': SCENE, 'equation_ref': f'{SCENE}.melt',
     'variable_bindings_json': json.dumps(
         [_b_state('f', 'melt_fraction', 'melt_fraction')]),
     'result_variable_ref': '', 'anchor_kind': 'screen',
     'anchor_data_json': '{"corner": "top-right"}', 'sort_order': 0,
     'enabled': True},
    {'name': f'{SCENE}.voxel-headroom-eval',
     'description': 'Target minus voxel width (>=0 means target met).',
     'sim_space_ref': SCENE, 'equation_ref': f'{SCENE}.voxel-headroom',
     'variable_bindings_json': json.dumps(
         [_b_const('t', 'target_voxel_xy_mm', _TARGET_VOX),
          _b_state('x', 'voxel_xy_mm', 'voxel_xy_mm')]),
     'result_variable_ref': '', 'anchor_kind': 'screen',
     'anchor_data_json': '{"corner": "top-right"}', 'sort_order': 1,
     'enabled': True},
    {'name': f'{SCENE}.margin-eval', 'description': 'Repeatability margin.',
     'sim_space_ref': SCENE, 'equation_ref': f'{SCENE}.margin',
     'variable_bindings_json': json.dumps(
         [_b_state('m', 'margin_mm', 'margin_mm')]),
     'result_variable_ref': '', 'anchor_kind': 'screen',
     'anchor_data_json': '{"corner": "top-right"}', 'sort_order': 2,
     'enabled': True},
    {'name': f'{SCENE}.movement-eval',
     'description': 'Fraction of movement patterns viable.',
     'sim_space_ref': SCENE, 'equation_ref': f'{SCENE}.movement-fraction',
     'variable_bindings_json': json.dumps(
         [_b_state('a', 'movements_viable', 'movements_viable'),
          _b_state('b', 'movements_total', 'movements_total')]),
     'result_variable_ref': '', 'anchor_kind': 'screen',
     'anchor_data_json': '{"corner": "top-right"}', 'sort_order': 3,
     'enabled': True},
    {'name': f'{SCENE}.warp-eval', 'description': 'Fan warp asymmetry.',
     'sim_space_ref': SCENE, 'equation_ref': f'{SCENE}.warp',
     'variable_bindings_json': json.dumps(
         [_b_state('w', 'warp_index', 'warp_index')]),
     'result_variable_ref': '', 'anchor_kind': 'screen',
     'anchor_data_json': '{"corner": "top-right"}', 'sort_order': 4,
     'enabled': True},
]

SEED_PENDULUM_EQUATIONS.extend(_EQ_DEFS)
SEED_PENDULUM_EVALUATION_EQUATIONS.extend(_EVALS)

# The no-code STEP solution (wp-8): importing appends the SolutionDefinition
# + SimulationExecutionSolution rows so the runner can step this sim via the
# no-code WaxPrintOperation.
from waxprint import sim_step_seed  # noqa: E402,F401


# --------------------------------------------------------------------------
# the SimulationDefinition, its baseline runs, the msim wrapper + IC picker
# --------------------------------------------------------------------------
SEED_SIMULATION_DEFINITIONS.append({
    'name': SIM,
    'description': 'Pellet-fed auger-screw wax printer, sampled along build '
                   'HEIGHT: each step = the melt (scale A) + bead/voxel '
                   '(scale B) + movement viability at that height, driven by '
                   'the validated waxprint Python engine.',
    'intent': 'feasibility',
    'participating_sim_state_classes_json': json.dumps([_CLS]),
    'time_step_seconds': 1.0,
    'duration_seconds': float(sim_runner.DEFAULT_N_STEPS),
    'recording_interval_steps': 1,
    'initial_conditions_overrides_json': '{}',
    'parameters_json': json.dumps({
        'default_assembly': 'demo-auger-extruder',
        'default_feedstock': 'mvw-natural-blend',
        'default_condition': 'room-baseline',
        'target_voxel_xy_mm': _TARGET_VOX, 'margin_tol_mm': _MARGIN_TOL,
        'max_height_mm': _MAX_H}),
})

for _rn, _label in ((_RUN_BASELINE, 'room demo (mvw)'),
                    (_RUN_FINE, 'cooled fine (carnauba)')):
    SEED_SIMULATION_RUNS.append({
        'name': _rn, 'simulation_ref': SIM, 'status': 'completed',
        'total_steps': sim_runner.DEFAULT_N_STEPS,
        'recorded_steps': sim_runner.DEFAULT_N_STEPS,
        'last_recorded_step': sim_runner.DEFAULT_N_STEPS - 1, 'label': _label})

SEED_MULTI_SCALE_SIMS.append({
    'name': MSIM,
    'description': 'Wax-print multiscale space — melt (A) + bead/voxel (B) '
                   'sampled over build height, with live condition readouts.',
    'member_simulation_refs_json': json.dumps([SIM]),
    'coupling_refs_json': '[]',
    'primary_simulation_ref': SIM,
    'stages_json': '[]',
    'panels_json': json.dumps([
        {'kind': 'scene', 'simSpaceRef': SCENE, 'run': _RUN_BASELINE},
        {'kind': 'ic', 'icInterfaceRef': 'wax-print-condition-picker'},
    ]),
    'display_ref': '', 'compare_run_policy_json': json.dumps(
        {'mode': 'fanOutSteps', 'runs': [_RUN_BASELINE, _RUN_FINE]}),
    'profile_ref': '', 'enabled': True,
})

SEED_IC_INTERFACES.append({
    'name': 'wax-print-condition-picker',
    'description': 'Pick a print condition to run the wax-print sim under.',
    'target_simulation_ref': SIM, 'target_class_name': _CLS,
    'interface_kind': 'choicePreset',
    'config_json': json.dumps({
        'label': 'Print condition',
        'choices': [{'key': c['name'], 'label': c.get('display_name',
                     c['name']), 'setParams': {'default_condition': c['name']}}
                    for c in SEED_CONDITIONS]}),
    'enabled': True,
})


# --------------------------------------------------------------------------
# display page
# --------------------------------------------------------------------------
SEED_WAXPRINT_PAGE_DISPLAYS = [{
    'name': 'wax-print-sim', 'description': 'View + verify the wax-print '
    'physics: the 3D voxel wall + live condition readouts.',
    'source_class': _CLS, 'isPage': True, 'pageRoute': 'wax-print-sim',
    'linkedSolutions': '[]',
    'definition': json.dumps({'rows': [{
        'index': 0, 'rowSegments': 12, 'minRowHeight': 560, 'maxRowHeight': 0,
        'autoHeight': True, 'cssClass': '',
        'items': [{
            'id': 'wax-print-scene-item', 'index': 0, 'type': 'component',
            'rowSegmentsUsed': 12, 'gridColumnStart': None,
            'title': 'Wax print — voxel wall', 'visible': True,
            'collapsed': False, 'cssClass': '',
            'componentProps': {'componentName': 'sim-space-viewer',
                               'inputs': {'simSpaceName': SCENE}},
            'item': None, 'nestedRows': []}],
    }]}),
}]
