"""
@cross-cutting
@module waxprint.sim_step_seed
@tags @xc:bindings

The NO-CODE STEP for the wax-print simulation (wp-8): a SolutionDefinition
whose graph is

    SimulationStateStep(simStepComplete)
        → WaxPrintOperation(command='print-step')
        → SimStepNextState

so the standard SimulationRunner advances the sim entirely through the
no-code engine (the WaxPrintOperation runs the validated physics; the
terminator projects its outputs onto the next WaxPrintSimState row). This
is what makes the sim testable + steppable via no-code, and the template
for authoring OTHER commands as steps. A SimulationExecutionSolution row
links it to the 'wax-print' sim.

The step reads the row's own config refs (assembly/feedstock/condition)
and height, so it is self-contained no-code. Importing this module
appends the solution + wiring rows to the shared framework seed lists.

@consumers
  - polariServer (imported via sim_seed) — seeds the step solution
  - waxprint.selftest_sim_step (executes the graph through the engine)
"""

import json

from simulations.seed_data import (
    _simulation_step_initial_state, _next_sim_state, _from_source,
    SEED_PENDULUM_STEP_SOLUTION_DEFS, SEED_PENDULUM_STEP_SOLUTIONS)

STEP_SOLUTION = 'wax-print.print-step'
_CLS = 'WaxPrintSimState'
_SIM = 'wax-print'

# The physics fields the print-step command emits → projected onto the row
# from the operation's waxprint.* context outputs.
_PHYSICS_FIELDS = [
    'exit_temp_c', 'melt_fraction', 'nozzle_pressure_pa', 'voxel_xy_mm',
    'voxel_z_mm', 'spread_mm', 'margin_mm', 't_solidify_s', 'warp_index',
    'thermally_safe', 'printable', 'movements_viable', 'movements_total',
    'substrate_temp_c']
# Config + height carried forward unchanged from the current row.
_CARRY_FIELDS = ['assembly_ref', 'feedstock_ref', 'condition_ref', 'height_mm']


def _wax_print_operation_state(state_name, location_x, location_y, command,
                               next_state, next_connector_id, index):
    """A WaxPrintOperation node as a sim-step operation — clones the
    MatrixEquationOperation node shape but hosts a wax-printer command,
    binding its inputs from the current row's config refs + height."""
    input_bindings = [
        {'symbol': 'assembly', 'source': _from_source('self.assembly_ref')},
        {'symbol': 'feedstock', 'source': _from_source('self.feedstock_ref')},
        {'symbol': 'condition', 'source': _from_source('self.condition_ref')},
        {'symbol': 'height_mm', 'source': _from_source('self.height_mm')},
    ]
    return {
        'stateName': state_name, 'id': f'{state_name}-state', 'index': index,
        'shapeType': 'circle', 'solutionName': '',
        'stateClass': 'WaxPrintOperation',
        'boundObjectClass': 'WaxPrintOperation',
        'boundObjectFieldValues': {
            'displayName': state_name,
            'description': f'Run the wax-printer "{command}" command on this '
                           f'row\'s config + height.',
            'command': command, 'inputBindings': input_bindings,
            'resultKeyMap': [], 'resultTarget': 'result_variable',
            'resultFieldPath': '', 'resultVariableName': 'wax_step_result',
            'codingComment': 'Outputs land in context as waxprint.<key>.'},
        'stateSvgRadius': 95, 'layerName': 'physics-layer',
        'stateLocationX': location_x, 'stateLocationY': location_y,
        'stateSvgName': 'circle', 'backgroundColor': '#8D6E63',
        'slots': [
            {'index': 0, 'stateName': state_name, 'slotAngularPosition': 180,
             'connectors': [], 'isInput': True, 'allowOneToMany': False,
             'allowManyToOne': True, 'label': 'In'},
            {'index': 1, 'stateName': state_name, 'slotAngularPosition': 0,
             'connectors': [{'id': next_connector_id, 'sourceSlot': 1,
                             'sinkSlot': 0, 'targetStateName': next_state}],
             'isInput': False, 'allowOneToMany': True, 'allowManyToOne': False,
             'label': 'outputs', 'passthroughVariableName': 'wax_step_result'}],
        'slotRadius': 5}


def _build():
    initial = _simulation_step_initial_state(
        'Start', location_x=160, next_state='RunPrintStep', slot_id=1,
        sim_state_class_name=_CLS,
        expected_fields=_CARRY_FIELDS, sim_step_role='simStepComplete',
        coding_comment='Reads the row config refs + height for the command.')
    op = _wax_print_operation_state(
        'RunPrintStep', 500, 280, 'print-step', 'CommitNextRow', 2, 1)
    output_mappings = (
        [{'outputFieldName': f, 'valueSource': _from_source(f'waxprint.{f}')}
         for f in _PHYSICS_FIELDS]
        + [{'outputFieldName': f, 'valueSource': _from_source(f'self.{f}')}
           for f in _CARRY_FIELDS])
    terminator = _next_sim_state(
        'CommitNextRow', 860, 280, output_mappings, _CLS, index=2,
        slot_id_in=2,
        coding_comment='Projects the command outputs onto the next row.')
    states = [initial, op, terminator]
    for s in states:
        s['solutionName'] = STEP_SOLUTION
    definition = {'solutionName': STEP_SOLUTION,
                  'description': 'No-code wax-print step via WaxPrintOperation.',
                  'stateInstances': states}
    solution_def_row = {
        'name': STEP_SOLUTION,
        'description': 'No-code wax-print step: run the print-step command '
                       'and commit the next WaxPrintSimState row.',
        'function_name': 'wax_print_print_step',
        'target_runtime': 'python_backend',
        'definition': json.dumps(definition)}
    metadata_row = {
        'name': STEP_SOLUTION,
        'description': 'Binds the no-code print-step to the wax-print sim.',
        'simulation_definition_ref': _SIM, 'sim_state_class_name': _CLS,
        'solution_definition_ref': STEP_SOLUTION,
        'expected_inputs_json': json.dumps(_CARRY_FIELDS),
        'expected_outputs_json': json.dumps(_PHYSICS_FIELDS + _CARRY_FIELDS),
        'order_index': 0, 'depends_on_json': '[]', 'enabled': True}
    return solution_def_row, metadata_row


STEP_SOLUTION_DEF, STEP_EXECUTION_SOLUTION = _build()
SEED_PENDULUM_STEP_SOLUTION_DEFS.append(STEP_SOLUTION_DEF)
SEED_PENDULUM_STEP_SOLUTIONS.append(STEP_EXECUTION_SOLUTION)
