"""
Self-test for MaterialScaleDefinition execution (msci-3).

Run from polari-framework/:
    python3 -m materialsScience.selftest_scale_execution
"""

import json
import sys
from types import SimpleNamespace

from materialsScience.materials_basis_seed import SEED_MS_SCALE_DEFINITIONS
from materialsScience import scale_execution
from materialsScience.scale_execution import (
    ENGINE_REGISTRY, execute_scale_definition,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


class _FakeDB:
    def __init__(self):
        self.saved = []
    def saveInstanceInDB(self, row):
        self.saved.append(row.name)
        return True


def _manager():
    rows = {}
    for seed in SEED_MS_SCALE_DEFINITIONS:
        rows[seed['name']] = SimpleNamespace(**{
            'scale_level': 0, 'status': 'defined', 'material_name': '',
            'definition_class': '', 'parameters_json': '{}', **seed})
    return SimpleNamespace(
        objectTables={'MaterialScaleDefinition': rows}, db=_FakeDB())


def test_registry_and_refusals():
    print('[registry + refusals]')
    check('registry has both engines',
          {'fem.conduction', 'dft.molecular-energy'} <= set(ENGINE_REGISTRY))
    manager = _manager()
    check('unknown row refuses',
          execute_scale_definition(manager, 'nope')['ok'] is False)
    verdict = execute_scale_definition(manager, 'beeswax@L0')
    check('non-EngineComputation row refuses',
          verdict['ok'] is False and 'not an EngineComputation'
          in verdict['error'])
    row = manager.objectTables['MaterialScaleDefinition']['beeswax@L1']
    row.parameters_json = json.dumps({'engine': 'not-real', 'inputs': {}})
    verdict = execute_scale_definition(manager, 'beeswax@L1')
    check('unknown engine lists registry',
          verdict['ok'] is False
          and 'fem.conduction' in verdict['suggestion']['evidence'])


def test_fem_execution_end_to_end():
    print('[fem execution — real solve, result persisted]')
    manager = _manager()
    verdict = execute_scale_definition(manager, 'beeswax@L1')
    check('beeswax@L1 executes', verdict['ok'])
    check('result carries FEM numbers',
          verdict['result']['maxTemperature'] > 0)
    # k=0.25 → max T ≈ 0.0736/0.25
    check('wax-k solve matches analytic scaling',
          abs(verdict['result']['maxTemperature'] - 0.07367 / 0.25) < 0.006)
    row = manager.objectTables['MaterialScaleDefinition']['beeswax@L1']
    stored = json.loads(row.parameters_json)
    check('result stored ON the row (object coherence)',
          stored['result']['maxTemperature']
          == verdict['result']['maxTemperature'])
    check('status partial -> defined', row.status == 'defined')
    check('row persisted', 'beeswax@L1' in manager.db.saved
          and verdict['persisted'])
    # Idempotent re-run: still ok, result refreshed
    check('re-execution ok', execute_scale_definition(
        manager, 'beeswax@L1')['ok'])


def test_homogenization_execution():
    print('[homogenization execution — msci-4]')
    check('registry has fem.effective-conductivity',
          'fem.effective-conductivity' in ENGINE_REGISTRY)
    manager = _manager()
    verdict = execute_scale_definition(manager, 'beeswax-carnauba-blend@L1')
    check('blend@L1 executes', verdict['ok'])
    if verdict['ok']:
        result = verdict['result']
        check('k_eff within Voigt/Reuss bounds', result['withinBounds'])
        check('k_eff between constituent conductivities',
              0.25 < result['effectiveK'] < 0.30)
        row = manager.objectTables['MaterialScaleDefinition'][
            'beeswax-carnauba-blend@L1']
        check('lineage preserved after execution',
              row.derived_from_name == 'beeswax-carnauba-blend@L0'
              and row.derivation_method == 'homogenized')
    from materialsScience.engines.fem_engine import effective_conductivity
    bad = effective_conductivity(1.0, 1.0, 0.8)
    check('volume fraction bound enforced', bad['ok'] is False)


def test_dft_execution_paths():
    print('[dft execution — refusal passthrough or real run]')
    manager = _manager()
    verdict = execute_scale_definition(manager, 'paraffin-wax@L4')
    if verdict['ok']:
        # Only when the host has pyscf or a reachable worker.
        check('propane fragment energy sane (-119.2 < E < -118.4 Ha)',
              -119.2 < verdict['result']['totalEnergyHa'] < -118.4)
        check('status flipped', manager.objectTables[
            'MaterialScaleDefinition']['paraffin-wax@L4'].status == 'defined')
    else:
        check('DFT refusal passes engine suggestion through',
              bool(verdict.get('suggestion')))
        row = manager.objectTables['MaterialScaleDefinition'][
            'paraffin-wax@L4']
        check('failed execution leaves row partial', row.status == 'partial')
        check('failed execution stores no result',
              'result' not in json.loads(row.parameters_json))


def main():
    test_registry_and_refusals()
    test_fem_execution_end_to_end()
    test_homogenization_execution()
    test_dft_execution_paths()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
