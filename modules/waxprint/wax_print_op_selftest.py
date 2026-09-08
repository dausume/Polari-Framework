"""
Self-test for the WaxPrintOperation no-code state (wp-7) — the wax-printer
COMMAND engine callable from a no-code solution graph.

Run from polari-framework/:
    python3 -m waxprint.wax_print_op_selftest

Proves the no-code engine can run each wax-print command from a graph:
bind the assembly/feedstock/condition (+ height) instance fields into the
operation, run the validated waxprint physics, map a chosen output key to
a friendly context variable, and keep computing on it — the same weaving
EngineModelOperation does, but for wax-printer commands. Also checks the
honest refusal paths (unknown command, planned printer-control command)
surface in the trace without crashing.
"""

from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import (
    SolutionExecutionEngine, StepConfig)
from simulations.simulation_runner import _extract_final_context
from waxprint.waxprint_seed import (
    SEED_DEVICE_MATERIALS, SEED_FEEDSTOCKS, SEED_ASSEMBLIES, SEED_CONDITIONS)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}]'
          f' {label}{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'DeviceMaterialDefinition': _rows(SEED_DEVICE_MATERIALS),
        'WaxFeedstockDefinition': _rows(SEED_FEEDSTOCKS),
        'PrinterAssemblyDefinition': _rows(SEED_ASSEMBLIES),
        'PrintConditionDefinition': _rows(SEED_CONDITIONS),
    })


def _src_obj(path):
    return {'sourceType': 'from_source_object', 'sourceObjectPath': path}


def _state(name, cls, fields, out_to=None):
    out = {'index': 1, 'stateName': name, 'isInput': False, 'label': 'Out',
           'connectors': []}
    if out_to:
        out['connectors'].append({'id': 1, 'sourceSlot': 1,
                                  'targetStateName': out_to, 'sinkSlot': 0})
    slots = [{'index': 0, 'stateName': name, 'isInput': True, 'label': 'In',
              'connectors': []}, out]
    return {'stateName': name, 'id': f'{name}-state', 'index': 0,
            'stateClass': cls, 'boundObjectClass': cls,
            'boundObjectFieldValues': fields, 'slots': slots}


def _solution(command, result_key, context_var, return_var,
              extra_bindings=None):
    """InitialState → WaxPrintOperation(command) → ReturnValue."""
    bindings = [
        {'symbol': 'assembly', 'source': _src_obj('self.assembly')},
        {'symbol': 'feedstock', 'source': _src_obj('self.feedstock')},
        {'symbol': 'condition', 'source': _src_obj('self.condition')},
        {'symbol': 'height_mm', 'source': _src_obj('self.height_mm')},
        {'symbol': 'pattern', 'source': _src_obj('self.pattern')},
    ]
    bindings.extend(extra_bindings or [])
    op_fields = {
        'command': command,
        'inputBindings': bindings,
        'resultKeyMap': [{'resultKey': result_key, 'contextVar': context_var}],
        'resultTarget': 'result_variable',
        'resultVariableName': 'wax_report',
    }
    return {'solutionName': f'wax-op-{command}', 'stateInstances': [
        _state('Start', 'InitialState', {'inputParams': []}, out_to='Run'),
        _state('Run', 'WaxPrintOperation', op_fields, out_to='Done'),
        _state('Done', 'ReturnValue', {'returnValue': return_var})]}


def _run(mgr, solution, fields):
    engine = SolutionExecutionEngine(manager=mgr)
    return engine.execute(
        solution_data=solution, input_params={},
        config=StepConfig(mode='step', record_context=True),
        target_runtime='python_backend', instance_fields=fields)


def _logs(trace):
    lines = []
    for step in getattr(trace, 'steps', []) or []:
        sl = (getattr(step, 'log_output', None)
              or (step.get('log_output') if isinstance(step, dict) else None)
              or [])
        lines.extend(sl)
    return ' | '.join(lines)


_FIELDS = {'assembly': 'fine-nozzle-extruder', 'feedstock': 'carnauba-rich',
           'condition': 'fine-voxel', 'height_mm': 5.0, 'pattern': 'perimeter'}


if __name__ == '__main__':
    print('\nWaxPrintOperation — no-code wax-printer commands\n')
    mgr = _mgr()

    # melt command
    trace = _run(mgr, _solution('melt', 'melt_fraction', 'mf', 'mf'), _FIELDS)
    final = _extract_final_context(trace)
    check('melt command ran in-graph; mapped output in context',
          isinstance(final.get('mf'), float) and final.get('mf') > 0.9,
          f"mf={final.get('mf')}")
    check('melt outputs also under waxprint.* namespace',
          isinstance(final.get('waxprint.exit_temp_c'), float),
          f"exit={final.get('waxprint.exit_temp_c')}")

    # bead-voxel command
    trace = _run(mgr, _solution('bead-voxel', 'voxel_xy_mm', 'vox', 'vox'),
                 _FIELDS)
    final = _extract_final_context(trace)
    check('bead-voxel command computed a voxel',
          isinstance(final.get('vox'), float) and 0.1 < final.get('vox') < 1.0,
          f"voxel_xy={final.get('vox')}")

    # movement command
    trace = _run(mgr, _solution('movement', 'verdict_ord', 'v', 'v'), _FIELDS)
    final = _extract_final_context(trace)
    check('movement command returned a verdict ordinal',
          final.get('v') in (0.0, 1.0, 2.0), f"verdict_ord={final.get('v')}")

    # print-step command (the full sim-step payload)
    trace = _run(mgr, _solution('print-step', 'voxel_xy_mm', 'vx', 'vx'),
                 _FIELDS)
    final = _extract_final_context(trace)
    check('print-step command produced the full state (voxel + more)',
          isinstance(final.get('vx'), float)
          and isinstance(final.get('waxprint.melt_fraction'), float)
          and isinstance(final.get('waxprint.movements_viable'), float),
          f"voxel={final.get('vx')}")

    # OVERRIDES flow through the no-code node: same rows, but the graph
    # supplies a finer nozzle + a chilled ambient → a finer voxel.
    trace = _run(mgr, _solution('bead-voxel', 'voxel_xy_mm', 'v0', 'v0'),
                 {**_FIELDS, 'condition': 'room-baseline',
                  'assembly': 'demo-auger-extruder',
                  'feedstock': 'mvw-natural-blend', 'height_mm': 0.0})
    base_vox = _extract_final_context(trace).get('v0')
    over = _solution('bead-voxel', 'voxel_xy_mm', 'v1', 'v1', extra_bindings=[
        {'symbol': 'nozzle_diameter_mm', 'source': _src_obj('self.noz')},
        {'symbol': 'ambient_temp_c', 'source': _src_obj('self.amb')},
        {'symbol': 'bed_temp_c', 'source': _src_obj('self.amb')},
        {'symbol': 'wind_mm_s', 'source': _src_obj('self.wind')}])
    trace = _run(mgr, over, {**_FIELDS, 'condition': 'room-baseline',
                             'assembly': 'demo-auger-extruder',
                             'feedstock': 'mvw-natural-blend', 'height_mm': 0.0,
                             'noz': 0.25, 'amb': 4.0, 'wind': 800.0})
    over_vox = _extract_final_context(trace).get('v1')
    check('scalar OVERRIDES flow through the no-code node (finer voxel)',
          isinstance(base_vox, float) and isinstance(over_vox, float)
          and over_vox < base_vox,
          f"{base_vox:.3f} -> {over_vox:.3f} mm")

    # new analysis commands via the node
    trace = _run(mgr, _solution('optimize', 'best_voxel_xy_mm', 'bv', 'bv'),
                 {**_FIELDS, 'assembly': 'fine-nozzle-extruder',
                  'feedstock': 'carnauba-rich'})
    check('optimize command returns a best-recipe voxel',
          isinstance(_extract_final_context(trace).get('bv'), float)
          and 0.1 < _extract_final_context(trace)['bv'] < 0.6,
          f"best_voxel={_extract_final_context(trace).get('bv')}")
    trace = _run(mgr, _solution('resolution-profile', 'degradation_mm', 'd',
                                'd'), _FIELDS)
    check('resolution-profile command returns a degradation figure',
          isinstance(_extract_final_context(trace).get('d'), float)
          and _extract_final_context(trace)['d'] >= 0.0)

    # honest refusals
    trace = _run(mgr, _solution('bogus-cmd', 'x', 'x', 'x'), _FIELDS)
    check('unknown command refuses in the trace log, no crash',
          'refused' in _logs(trace) and getattr(trace, 'status', '')
          == 'completed')
    trace = _run(mgr, _solution('move-to', 'x', 'x', 'x'), _FIELDS)
    check('planned printer-control command refuses honestly (not wired yet)',
          'refused' in _logs(trace))
    trace = _run(mgr, _solution('melt', 'melt_fraction', 'mf', 'mf'),
                 {**_FIELDS, 'assembly': 'no-such-assembly'})
    check('missing row refuses in the trace log',
          'refused' in _logs(trace))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
