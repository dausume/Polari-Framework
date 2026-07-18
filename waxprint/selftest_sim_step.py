"""
Self-test for the no-code wax-print STEP (wp-8) — the full step graph
SimulationStateStep → WaxPrintOperation(print-step) → SimStepNextState,
executed through the SAME SolutionExecutionEngine the SimulationRunner
uses, proving the physics projects onto the next WaxPrintSimState row's
fields entirely via no-code.

Run from polari-framework/:
    python3 -m waxprint.selftest_sim_step
"""

import json
from types import SimpleNamespace

from polariNoCode.SolutionExecutionEngine import (
    SolutionExecutionEngine, StepConfig)
from simulations.simulation_runner import _extract_final_context
from waxprint import sim_step_seed
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


def _run(mgr, solution, fields):
    engine = SolutionExecutionEngine(manager=mgr)
    return engine.execute(
        solution_data=solution, input_params={},
        config=StepConfig(mode='step', record_context=True),
        target_runtime='python_backend', instance_fields=fields)


if __name__ == '__main__':
    print('\nNo-code wax-print STEP — full step graph via the engine\n')
    mgr = _mgr()
    solution = json.loads(sim_step_seed.STEP_SOLUTION_DEF['definition'])

    check('step graph is entry → WaxPrintOperation → SimStepNextState',
          [s['stateClass'] for s in solution['stateInstances']]
          == ['SimulationStateStep', 'WaxPrintOperation', 'SimStepNextState'])

    # A good cooled recipe row.
    fields = {'assembly_ref': 'fine-nozzle-extruder',
              'feedstock_ref': 'carnauba-rich', 'condition_ref': 'fine-voxel',
              'height_mm': 5.0}
    trace = _run(mgr, solution, fields)
    final = _extract_final_context(trace)

    check('step ran to completion', getattr(trace, 'status', '') == 'completed',
          getattr(trace, 'status', ''))
    check('operation output reached the context (waxprint.voxel_xy_mm)',
          isinstance(final.get('waxprint.voxel_xy_mm'), float),
          f"={final.get('waxprint.voxel_xy_mm')}")
    # SimStepNextState projects onto the row fields:
    check('next-row voxel_xy_mm projected + sensible',
          isinstance(final.get('voxel_xy_mm'), float)
          and 0.1 < final['voxel_xy_mm'] < 1.0,
          f"voxel_xy={final.get('voxel_xy_mm')}")
    check('next-row melt_fraction projected',
          isinstance(final.get('melt_fraction'), float)
          and final['melt_fraction'] > 0.9,
          f"mf={final.get('melt_fraction')}")
    check('next-row thermally_safe projected (1.0)',
          final.get('thermally_safe') == 1.0)
    check('next-row movements_total projected (7)',
          final.get('movements_total') == 7.0)
    check('config refs carried forward onto the next row',
          final.get('assembly_ref') == 'fine-nozzle-extruder'
          and final.get('height_mm') == 5.0)

    # A row over the wax safety ceiling → the step still completes but the
    # projected safety flag is 0.
    unsafe = {'assembly_ref': 'demo-auger-extruder',
              'feedstock_ref': 'mvw-natural-blend', 'condition_ref': 'hot-unsafe',
              'height_mm': 0.0}
    trace2 = _run(mgr, solution, unsafe)
    final2 = _extract_final_context(trace2)
    check('unsafe condition projects thermally_safe=0 (gate visible in-row)',
          final2.get('thermally_safe') == 0.0,
          f"safe={final2.get('thermally_safe')}")

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
