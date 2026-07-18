"""
Selftest — ncg-6: unit testing VIA no-code (NoCodeTestCase/Pack).

Run from polari-framework/:
    python3 -m polariNoCode.selftest_nocode_tests

The litmus pack must prove the capability across all three seam
domains — a solution through the REAL engine (sum 1..10 = 55), the
row-form LED branch at its PROVEN current through REAL ngspice, and
the alarm gate's truth table through the reference evaluator. Then
the honesty paths: a wrong expectation fails WITH the actual value
in evidence, a disabled pack skip-honests naming the knob, unknown
subject kinds and packs fail plainly.
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

# mp-3: this suite exercises feature-module code — refuse honestly
# when that code is not downloaded instead of a raw ImportError.
from moduleService.module_loading import feature_downloaded, missing_message
for _m in ('electrodevice', 'hwdigital'):
    if not feature_downloaded(_m):
        raise SystemExit(missing_message(_m))
from electrodevice import device_derive as dd
from electrodevice.circuit_basis import (SEED_CIRCUIT_COMPONENTS,
                                         SEED_CIRCUIT_NETS,
                                         SEED_CIRCUITS)
from electrodevice.spice_run import ngspice_bin
from hwdigital.logic_basis import SEED_LOGIC_DESIGNS, SEED_LOGIC_NODES
from polariNoCode.nocode_tests import (SEED_TEST_CASES,
                                       SEED_TEST_PACKS, run_case,
                                       run_pack)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _device():
    return types.SimpleNamespace(
        name='cnt-solgel-led-resistor', device_type='resistor',
        sim_model='cnt-solgel-percolation', length_m=0.002,
        cross_section_m2=1.4e-8, sigma_s_per_m=0.0,
        resistance_ohm=0.0, derived_at='',
        provenance_json='{}', notes='')


def _executor(sigma):
    return lambda m, n: {
        'ok': True, 'engine': 'analytic.percolation-conductivity',
        'inputs': {}, 'result': {'effectiveSigma': sigma,
                                 'validity': 'idealized'}}


def _seed_table(seeds):
    return {s['name']: types.SimpleNamespace(**s) for s in seeds}


def _mgr():
    mgr = types.SimpleNamespace(idList=[], db=None, objectTables={
        'NoCodeTestPack': _seed_table(SEED_TEST_PACKS),
        'NoCodeTestCase': _seed_table(SEED_TEST_CASES),
        'SolutionDefinition': {},
        'CircuitDefinition': _seed_table(SEED_CIRCUITS),
        'CircuitNetDefinition': _seed_table(SEED_CIRCUIT_NETS),
        'CircuitComponentDefinition': _seed_table(
            SEED_CIRCUIT_COMPONENTS),
        'ElectronicDeviceDefinition': {}, 'SpiceModelCard': {},
        'MaterialScaleDefinition': {},
        'LogicBlockDesign': _seed_table(SEED_LOGIC_DESIGNS),
        'LogicBlockNode': _seed_table(SEED_LOGIC_NODES),
    })
    device = _device()
    mgr.objectTables['ElectronicDeviceDefinition'][
        device.name] = device
    dd.derive_device(mgr, device, executor=_executor(227.267))
    return mgr


def _litmus():
    print('the litmus pack (all three seam domains)')
    m = _mgr()
    report = run_pack(m, 'polari-nocode-litmus')
    by_case = {r['case']: r for r in report['results']}
    solution = by_case.get('litmus-solution-sum', {})
    check('solution case: sum 1..10 = 55 through the REAL engine',
          solution.get('status') == 'pass',
          solution.get('evidence', '')[:90])
    check('  ...noting the built-in fallback (no stored row)',
          'built-in litmus' in solution.get('evidence', ''))
    circuit = by_case.get('litmus-circuit-led-branch', {})
    expected_circuit = ('pass' if ngspice_bin() else 'skip-honest')
    check(f'circuit case: proven LED current ({expected_circuit} '
          f'on this node)',
          circuit.get('status') == expected_circuit,
          circuit.get('evidence', '')[:90])
    logic = by_case.get('litmus-logic-alarm', {})
    check('logic-design case: armed door trips the alarm',
          logic.get('status') == 'pass',
          logic.get('evidence', '')[:90])
    # Verdict is 'pass' either way (a skip among passes never fails
    # a pack) — the HONEST assertion is the passed COUNT, which
    # drops by exactly the ngspice leg when the binary is absent.
    expected_passed = 3 if ngspice_bin() else 2
    check('pack verdict aggregates honestly',
          report['status'] == 'pass' and report['total'] == 3
          and report['passed'] == expected_passed,
          f"{report['status']} {report['passed']}/{report['total']}")


def _honesty():
    print('honesty paths')
    m = _mgr()
    wrong = types.SimpleNamespace(
        name='wrong-sum', pack_name='polari-nocode-litmus',
        subject_kind='solution', subject_ref='litmus-sum-1-to-10',
        input_bindings_json='{}',
        expected_json='{"finalReturnValue": 54}',
        tags_json='[]', description='')
    row = run_case(m, wrong)
    check('wrong expectation FAILS with the actual value in '
          'evidence',
          row['status'] == 'fail' and '55' in row['evidence']
          and '54' in row['evidence'], row['evidence'][:90])

    m.objectTables['NoCodeTestPack'][
        'polari-nocode-litmus'].enabled = False
    disabled = run_pack(m, 'polari-nocode-litmus')
    check('disabled pack skip-honests naming the knob',
          disabled['status'] == 'skip-honest'
          and 'enabled knob' in disabled['evidence'])

    unknown_kind = types.SimpleNamespace(
        name='mystery', pack_name='x', subject_kind='quantum',
        subject_ref='y', input_bindings_json='{}',
        expected_json='{}', tags_json='[]', description='')
    row = run_case(m, unknown_kind)
    check('unknown subject_kind fails plainly listing kinds',
          row['status'] == 'fail' and 'logic-design'
          in row['evidence'])

    missing = run_pack(m, 'no-such-pack')
    check('unknown pack fails plainly listing known packs',
          missing['status'] == 'fail'
          and missing['knownPacks'] == ['polari-nocode-litmus'])

    ghost = types.SimpleNamespace(
        name='ghost', pack_name='x', subject_kind='solution',
        subject_ref='no-such-solution', input_bindings_json='{}',
        expected_json='{}', tags_json='[]', description='')
    row = run_case(m, ghost)
    check('missing solution row fails plainly (no crash)',
          row['status'] == 'fail'
          and 'no-such-solution' in row['evidence'])

    broken = types.SimpleNamespace(
        name='broken', pack_name='x', subject_kind='logic-design',
        subject_ref='demo-alarm-gate',
        input_bindings_json='{"not-an-input": 1}',
        expected_json='{}', tags_json='[]', description='')
    row = run_case(m, broken)
    check('a crashing case is a FAILING case with the exception '
          'named', row['status'] == 'fail'
          and 'not an input' in row['evidence'])

    # Review regression (finding: malformed JSON silently emptied
    # the assertions -> green): a broken expected_json that HIDES a
    # failing expectation (56 != 55) must FAIL naming the field.
    malformed = types.SimpleNamespace(
        name='malformed', pack_name='x', subject_kind='solution',
        subject_ref='litmus-sum-1-to-10', input_bindings_json='{}',
        expected_json='{"finalReturnValue": 56,,}',
        tags_json='[]', description='')
    row = run_case(m, malformed)
    check('malformed expected_json FAILS naming the field (never '
          'assertion-free green)',
          row['status'] == 'fail'
          and 'expected_json' in row['evidence'], row['evidence'][:90])
    wrong_shape = types.SimpleNamespace(
        name='wrong-shape', pack_name='x', subject_kind='solution',
        subject_ref='litmus-sum-1-to-10',
        input_bindings_json='[1, 2]', expected_json='{}',
        tags_json='[]', description='')
    row = run_case(m, wrong_shape)
    check('non-object input_bindings_json FAILS naming the field',
          row['status'] == 'fail'
          and 'input_bindings_json' in row['evidence'])

    # Review regression (finding: an enabled pack with ZERO cases
    # read green): it must skip-honest naming the NoCodeTestCase
    # knob.
    m.objectTables['NoCodeTestPack']['empty-pack'] = (
        types.SimpleNamespace(name='empty-pack', owning_module='x',
                              description='', enabled=True))
    empty = run_pack(m, 'empty-pack')
    check('an enabled pack with zero cases skip-honests naming the '
          'NoCodeTestCase knob',
          empty['status'] == 'skip-honest'
          and 'NoCodeTestCase' in empty['evidence']
          and empty['total'] == 0, empty['evidence'][:90])


def main():
    _litmus()
    _honesty()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
