"""
@module polariNoCode.nocode_tests

ncg-6 (the acct-6 seed): UNIT TESTING VIA NO-CODE — authorable test
cases over the seam's three subject domains, run through the SAME
machinery each domain already trusts:

  'solution'      a stored SolutionDefinition executed by the REAL
                  SolutionExecutionEngine (via graph_builder.execute)
  'circuit'       a CircuitDefinition row-set run through ngspice
                  (electrodevice.circuit_netlist.run_circuit)
  'logic-design'  a LogicBlockDesign evaluated by the python
                  reference evaluator (hwdigital.logic_sim)

A NoCodeTestCase is a row (arrange = input_bindings_json, act = the
subject's own runner, assert = expected_json); a NoCodeTestPack is a
module's set of cases with an `enabled` knob. Results are honest
three-state rows ({pass, fail, skip-honest} + evidence) — the same
shape the accountability matrix speaks, so pack runs can feed
CheckRun rows without translation.

The litmus pack tests the capability THROUGH itself across all three
domains (the recursion is the point): a summing solution through the
real engine, the proven 2.6123 mA LED branch, and the alarm gate's
truth table.

@consumers
  - testing (matrix registration — wired by the main session)
  - polariServer (registration + seed)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

SUBJECT_KINDS = ('solution', 'circuit', 'logic-design')

LITMUS_SOLUTION_NAME = 'litmus-sum-1-to-10'


class NoCodeTestCase(treeObject):
    """One authorable test case — arrange/act/assert as a row."""

    @treeObjectInit
    def __init__(self, name: str = '', pack_name: str = '',
                 subject_kind: str = 'solution',
                 # SolutionDefinition / CircuitDefinition /
                 # LogicBlockDesign name, per subject_kind.
                 subject_ref: str = '',
                 # Flat dict: solution input params / logic-design
                 # input node values (circuits take no inputs yet).
                 input_bindings_json: str = '{}',
                 # Assertions, all optional, all checked when
                 # present:
                 #  solution: finalReturnValue, status,
                 #            contextContains {var: value}
                 #  circuit:  measurementNear {name, value,
                 #            tolerance}
                 #  logic-design: outputs {node: value}, steps (int,
                 #            clock steps before asserting)
                 expected_json: str = '{}',
                 tags_json: str = '[]',
                 description: str = '', manager=None):
        self.name = name
        self.pack_name = pack_name
        self.subject_kind = subject_kind
        self.subject_ref = subject_ref
        self.input_bindings_json = input_bindings_json
        self.expected_json = expected_json
        self.tags_json = tags_json
        self.description = description


class NoCodeTestPack(treeObject):
    """A module's set of cases — modules become testable units."""

    @treeObjectInit
    def __init__(self, name: str = '', owning_module: str = '',
                 description: str = '', enabled: bool = True,
                 manager=None):
        self.name = name
        self.owning_module = owning_module
        self.description = description
        # The knob: a disabled pack skip-honests, never silently
        # vanishes ([[knobs-and-suggestions]]).
        self.enabled = enabled


def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _by_name(manager, class_name):
    return {getattr(r, 'name', ''): r
            for r in _rows(manager, class_name)}


def ensure_litmus_solution(manager=None):
    """The litmus solution as a built definition dict (sum 1..10 =
    55 through real loop execution — the turing pattern). Used as
    the fallback when no stored SolutionDefinition row carries it."""
    from polariNoCode import graph_builder as gb
    return gb.solution(
        LITMUS_SOLUTION_NAME,
        gb.entry(nxt='InitSum'),
        gb.assign('InitSum', 'sum', '0', 'Loop'),
        gb.for_loop('Loop', 'i', 1, 11, 'Add', 'Done'),
        gb.math('Add', 'sum', 'sum', 'add', 'i', ''),
        gb.ret('Done', 'sum'),
    )


class _MalformedField(ValueError):
    """A case field that cannot be trusted — the case must FAIL
    naming the field, never run with silently-emptied assertions."""


def _loads_field(case, field, default):
    raw = getattr(case, field, '') or ''
    if not str(raw).strip():
        return default
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise _MalformedField(f'{field} is not valid JSON ({exc}) — '
                              f'fix the field on the case row')
    if value is None:
        return default
    if not isinstance(value, type(default)):
        raise _MalformedField(
            f'{field} must be a JSON '
            f'{"object" if isinstance(default, dict) else "array"}, '
            f'got {type(value).__name__} — fix the field on the '
            f'case row')
    return value


def _run_solution_case(manager, case, bindings, expected):
    from polariNoCode import graph_builder as gb
    from polariNoCode.graph_compilers import final_context_of
    row = _by_name(manager, 'SolutionDefinition').get(
        case.subject_ref)
    fallback_note = ''
    if row is not None:
        raw = getattr(row, 'definition', '')
        definition = (json.loads(raw) if isinstance(raw, str)
                      else raw)
    elif case.subject_ref == LITMUS_SOLUTION_NAME:
        definition = ensure_litmus_solution(manager)
        fallback_note = (' (no stored row — built-in litmus '
                         'definition used)')
    else:
        return {'status': 'fail',
                'evidence': f'no SolutionDefinition named '
                            f'{case.subject_ref!r}'}
    trace = gb.execute(definition, manager=manager, params=bindings)
    problems, facts = [], []
    if 'status' in expected:
        facts.append(f'status={trace.status}')
        if trace.status != expected['status']:
            problems.append(f'status {trace.status!r} != '
                            f'{expected["status"]!r}')
    if 'finalReturnValue' in expected:
        got = trace.final_return_value
        facts.append(f'finalReturnValue={got!r}')
        if got != expected['finalReturnValue']:
            problems.append(
                f'finalReturnValue {got!r} != expected '
                f'{expected["finalReturnValue"]!r}')
    if 'contextContains' in expected:
        context = final_context_of(trace)
        for var, want in expected['contextContains'].items():
            got = context.get(var)
            if got != want:
                problems.append(f'context[{var!r}] {got!r} != '
                                f'{want!r}')
    evidence = '; '.join(facts) + fallback_note
    if problems:
        return {'status': 'fail',
                'evidence': '; '.join(problems) + fallback_note}
    return {'status': 'pass', 'evidence': evidence}


def _run_circuit_case(manager, case, expected):
    from electrodevice.circuit_netlist import run_circuit
    result = run_circuit(manager, case.subject_ref)
    if not result.get('ok'):
        error = result.get('error', '')
        if 'ngspice not available' in error:
            return {'status': 'skip-honest',
                    'evidence': error + ' — the circuit case needs '
                                'the ngspice binary'}
        return {'status': 'fail', 'evidence': error or 'run failed'}
    near = expected.get('measurementNear')
    if not near:
        return {'status': 'pass',
                'evidence': f"ran; measurements: "
                            f"{sorted(result['measurements'])}"}
    name = near['name'].lower()
    got = result['measurements'].get(name)
    if got is None:
        return {'status': 'fail',
                'evidence': f'no measurement {name!r}; got '
                            f"{sorted(result['measurements'])}"}
    want, tolerance = near['value'], near.get('tolerance', 0.0)
    if abs(got - want) <= tolerance:
        return {'status': 'pass',
                'evidence': f'{name} = {got:.6g} (within '
                            f'{tolerance:g} of {want:.6g})'}
    return {'status': 'fail',
            'evidence': f'{name} = {got:.6g}, expected {want:.6g} '
                        f'± {tolerance:g}'}


def _run_logic_case(manager, case, bindings, expected):
    from hwdigital.logic_sim import LogicSimulator, design_specs
    specs = design_specs(manager, case.subject_ref)
    sim = LogicSimulator(specs)
    if bindings:
        sim.set_inputs(**bindings)
    for _ in range(int(expected.get('steps', 0))):
        sim.step()
    outputs = sim.outputs()
    problems = []
    for node, want in (expected.get('outputs') or {}).items():
        got = outputs.get(node)
        if got != want:
            problems.append(f'{node} = {got!r}, expected {want!r}')
    if problems:
        return {'status': 'fail', 'evidence': '; '.join(problems)}
    return {'status': 'pass', 'evidence': f'outputs: {outputs}'}


def run_case(manager, case):
    """One case -> an honest {'status', 'evidence'} row. Never
    raises — a broken case is a FAILING case with plain evidence
    (including malformed JSON fields, which must never silently
    empty the assertions)."""
    try:
        bindings = _loads_field(case, 'input_bindings_json', {})
        expected = _loads_field(case, 'expected_json', {})
    except _MalformedField as exc:
        return {'status': 'fail', 'evidence': str(exc)}
    kind = getattr(case, 'subject_kind', '')
    try:
        if kind == 'solution':
            return _run_solution_case(manager, case, bindings,
                                      expected)
        if kind == 'circuit':
            return _run_circuit_case(manager, case, expected)
        if kind == 'logic-design':
            return _run_logic_case(manager, case, bindings, expected)
        kinds = ', '.join(SUBJECT_KINDS)
        return {'status': 'fail',
                'evidence': f'unknown subject_kind {kind!r} '
                            f'(kinds: {kinds})'}
    except Exception as exc:
        return {'status': 'fail',
                'evidence': f'case crashed: {type(exc).__name__}: '
                            f'{exc}'}


def run_pack(manager, pack_name):
    """Run one pack -> per-case results + the pack verdict (any fail
    -> fail; else all-skip -> skip-honest; else pass)."""
    pack = _by_name(manager, 'NoCodeTestPack').get(pack_name)
    if pack is None:
        return {'pack': pack_name, 'status': 'fail',
                'evidence': f'no NoCodeTestPack named {pack_name!r}',
                'knownPacks': sorted(_by_name(manager,
                                              'NoCodeTestPack')),
                'results': [], 'passed': 0, 'total': 0}
    if not getattr(pack, 'enabled', True):
        return {'pack': pack_name, 'status': 'skip-honest',
                'evidence': f"pack '{pack_name}' is disabled — the "
                            f'enabled knob is on the NoCodeTestPack '
                            f'row',
                'results': [], 'passed': 0, 'total': 0}
    cases = sorted(
        (c for c in _rows(manager, 'NoCodeTestCase')
         if getattr(c, 'pack_name', '') == pack_name),
        key=lambda c: getattr(c, 'name', ''))
    if not cases:
        return {'pack': pack_name, 'status': 'skip-honest',
                'evidence': f"pack '{pack_name}' has no cases — add "
                            f'NoCodeTestCase rows naming '
                            f"pack_name='{pack_name}' (or fix their "
                            f'pack_name) so the pack proves '
                            f'something',
                'results': [], 'passed': 0, 'total': 0}
    results = []
    for case in cases:
        row = run_case(manager, case)
        results.append({'case': case.name,
                        'subjectKind': case.subject_kind,
                        'subjectRef': case.subject_ref,
                        'status': row['status'],
                        'evidence': row['evidence']})
    passed = sum(1 for r in results if r['status'] == 'pass')
    failed = sum(1 for r in results if r['status'] == 'fail')
    if failed:
        status = 'fail'
    elif results and passed == 0:
        status = 'skip-honest'
    else:
        status = 'pass'
    return {'pack': pack_name, 'status': status, 'results': results,
            'passed': passed, 'total': len(results)}


#: The litmus pack: the test capability proving ITSELF across every
#: seam domain — engine, circuit, digital logic.
SEED_TEST_PACKS = [
    {
        'name': 'polari-nocode-litmus',
        'owning_module': 'polariNoCode',
        'description': 'The self-test of the no-code test '
                       'capability: one solution through the real '
                       'engine, the proven LED branch current, the '
                       'alarm-gate truth table.',
        'enabled': True,
    },
]

SEED_TEST_CASES = [
    {
        'name': 'litmus-solution-sum',
        'pack_name': 'polari-nocode-litmus',
        'subject_kind': 'solution',
        'subject_ref': LITMUS_SOLUTION_NAME,
        'input_bindings_json': '{}',
        'expected_json': '{"finalReturnValue": 55, '
                         '"status": "completed"}',
        'tags_json': '["litmus"]',
        'description': 'sum 1..10 through real ForLoop execution.',
    },
    {
        'name': 'litmus-circuit-led-branch',
        'pack_name': 'polari-nocode-litmus',
        'subject_kind': 'circuit',
        'subject_ref': 'led-branch-row',
        'input_bindings_json': '{}',
        # Source convention: current INTO the branch reads negative
        # at the source — the proven 2.6123 mA leg.
        'expected_json': '{"measurementNear": {"name": "i(vvpin0)", '
                         '"value": -2.6123e-3, "tolerance": 1e-4}}',
        'tags_json': '["litmus"]',
        'description': 'the row-form LED branch at its proven '
                       'current.',
    },
    {
        'name': 'litmus-logic-alarm',
        'pack_name': 'polari-nocode-litmus',
        'subject_kind': 'logic-design',
        'subject_ref': 'demo-alarm-gate',
        'input_bindings_json': '{"alarm-door": 1, '
                               '"alarm-disarmed": 0, '
                               '"alarm-panic": 0}',
        'expected_json': '{"outputs": {"alarm-out": 1}}',
        'tags_json': '["litmus"]',
        'description': 'armed door trips the alarm.',
    },
]
