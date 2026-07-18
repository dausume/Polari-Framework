"""
@cross-cutting
@module scoring.data_gathering
@tags @xc:bindings

DataGatheringSolutions (Dustin 2026-07-16) — the judicial client's
sibling on the SAME graph-compiler seam: an organization defines,
step by step, HOW it gathers the data behind a ScoreTerm — business
logic with explicit submission and validation steps — so the
credibility of logically equivalent terms applied toward a score can
be COMPARED procedure-against-procedure. Anyone may then assert that
a specific step ADDS or SUBTRACTS credibility, with a required
reason ("due to particular reasons" is the point); those assertions
are scr-6-style rows adjudicated by validity votes, never by this
module.

The procedure compiles (through the registered 'data-gathering'
GraphCompilerDefinition row) into a real SolutionDefinition: each
validation step is a ConditionalChain gating on a submitted
`<stepId>_ok` flag — an UNSUBMITTED validation honestly evaluates
false — and a failed validation routes to a terminal naming exactly
which step failed. The compiled graph is steppable in the same
engine and D3 editor as judicial fork graphs.

Comparison is a READING: `compare_gathering_solutions` lines up the
procedures behind equivalent terms (steps, validation coverage,
sources cited, credibility assertions) and deliberately declares NO
winner — legitimacy is decided by votes, not by this module.

@consumers
  - polariServer (registration; compiler seed via
    SEED_DATA_GATHERING_COMPILER)
  - scoring.term_competition (comparability input)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from polariNoCode import graph_builder as gb
from polariNoCode import graph_compilers as gc
from scoring.worldview_elections import _by_name, _rows

STEP_KINDS = ('collection', 'submission', 'validation',
              'transformation')
SOLUTION_STATUSES = ('draft', 'active', 'retired')
CREDIBILITY_DIRECTIONS = ('adds', 'subtracts')

#: Same defense as court_case.OUTCOME_PREFIX: the engine resolves
#: ReturnStatement literals context-first, so outcomes carry a
#: reserved prefix no sane context key collides with.
GATHER_PREFIX = '__gather__:'
ALL_PASSED = 'all-validations-passed'

GATHERING_COMPILER_NAME = 'data-gathering'
GATHERING_COMPILER_REF = ('scoring.data_gathering'
                          ':compile_gathering_solution')

#: For the main session's SEED_GRAPH_COMPILERS wiring.
SEED_DATA_GATHERING_COMPILER = {
    'name': GATHERING_COMPILER_NAME,
    'domain': 'data-gathering',
    'compiler_ref': GATHERING_COMPILER_REF,
    'description': 'DataGatheringSolution steps_json -> an '
                   'executable SolutionDefinition: validation steps '
                   'gate on submitted <stepId>_ok flags, a failed '
                   '(or unsubmitted) validation routes to a '
                   'terminal naming the failed step.',
    'enabled': True,
}


class DataGatheringSolution(treeObject):
    """One organization's data-gathering procedure for one term —
    a row, editable at the row."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 # The ScoreGroup that owns/practices the procedure.
                 organization_group: str = '',
                 # The ScoreTerm this procedure gathers data FOR.
                 term_name: str = '',
                 # GovSource / legal-source names drawn from (JSON
                 # list).
                 source_names_json: str = '[]',
                 # The ORDERED procedure: [{stepId, kind, description,
                 # method, toolOrSource}] — kinds in STEP_KINDS.
                 steps_json: str = '[]',
                 # Set when compiled through the seam.
                 compiled_solution_name: str = '',
                 version: int = 1,
                 status: str = 'draft',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.organization_group = organization_group
        self.term_name = term_name
        self.source_names_json = source_names_json
        self.steps_json = steps_json
        self.compiled_solution_name = compiled_solution_name
        self.version = version
        self.status = status
        self.notes = notes


class StepCredibilityAssertion(treeObject):
    """One party's claim that one STEP of a gathering procedure adds
    or subtracts credibility, with the reason required. Status stays
    'asserted' here — validity votes adjudicate, never this row."""

    @treeObjectInit
    def __init__(self, name: str = '',
                 gathering_solution_name: str = '',
                 step_id: str = '',
                 direction: str = 'adds',
                 magnitude_note: str = '',
                 reason: str = '',
                 asserted_by: str = '',
                 on_behalf_of_group: str = '',
                 evidence_url: str = '',
                 status: str = 'asserted',
                 notes: str = '', manager=None):
        self.name = name
        self.gathering_solution_name = gathering_solution_name
        self.step_id = step_id
        self.direction = direction
        self.magnitude_note = magnitude_note
        self.reason = reason
        self.asserted_by = asserted_by
        self.on_behalf_of_group = on_behalf_of_group
        self.evidence_url = evidence_url
        self.status = status
        self.notes = notes


def _persist(manager, row):
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception as exc:
        print(f'[DataGathering] DB save FAILED for '
              f'{getattr(row, "name", "?")}: {exc}', flush=True)


def _solution_row(manager, solution_name):
    return _by_name(manager, 'DataGatheringSolution').get(
        solution_name)


def parsed_steps(solution_row):
    """steps_json -> validated step list. Plain errors name the
    offending step and the legal kinds."""
    steps = json.loads(getattr(solution_row, 'steps_json', '[]')
                       or '[]')
    if not steps:
        raise ValueError(
            f"gathering solution '{solution_row.name}' has no steps "
            f'— steps_json is the procedure (kinds: '
            f'{", ".join(STEP_KINDS)})')
    seen = set()
    for step in steps:
        step_id = step.get('stepId', '')
        if not step_id:
            raise ValueError(
                f"a step in '{solution_row.name}' is missing "
                f"'stepId'")
        if step_id in seen:
            raise ValueError(
                f"duplicate stepId '{step_id}' in "
                f"'{solution_row.name}'")
        seen.add(step_id)
        kind = step.get('kind', '')
        if kind not in STEP_KINDS:
            kinds = ', '.join(STEP_KINDS)
            raise ValueError(
                f"step '{step_id}': unknown kind '{kind}' "
                f'(kinds: {kinds})')
    return steps


def _flag_var(step_id):
    return f'{step_id}_ok'


def _step_node_name(index, step_id):
    # Node names surface in the D3 editor — keep them readable.
    return f'Step{index}_{step_id.replace("-", "_")}'


def compile_gathering_solution(domain_rows):
    """Compiler-contract entry ('data-gathering'): {'manager',
    'solution_name'} -> the executable procedure graph.

    Mapping: non-validation steps chain as VariableAssignments
    recording the step (kind + description ride the trace context);
    each validation step is a ConditionalChain on
    self.<stepId>_ok — true continues, false (INCLUDING an
    unsubmitted flag, which honestly evaluates false) routes to a
    terminal naming exactly that step. The happy path ends at the
    ALL_PASSED terminal."""
    manager = domain_rows['manager']
    solution_name = domain_rows['solution_name']
    row = _solution_row(manager, solution_name)
    if row is None:
        known = sorted(_by_name(manager, 'DataGatheringSolution'))
        raise ValueError(
            f"no DataGatheringSolution named '{solution_name}' — "
            f'known: {known}')
    steps = parsed_steps(row)
    node_names = [_step_node_name(i, s['stepId'])
                  for i, s in enumerate(steps)]
    node_names.append('Completed')
    states = [gb.entry(nxt=node_names[0])]
    for i, step in enumerate(steps):
        nxt = node_names[i + 1]
        if step['kind'] == 'validation':
            fail_name = f'Failed_{step["stepId"].replace("-", "_")}'
            states.append(gb.cond(
                node_names[i],
                [gb.link(gb.var_src(
                    f'self.{_flag_var(step["stepId"])}'),
                    'isTrue', gb.lit_src(True))],
                nxt, fail_name,
                display_name=(f'validate: '
                              f'{step.get("description", "")}'
                              [:200])))
            states.append(gb.ret_statement(
                fail_name,
                GATHER_PREFIX + f'validation-failed:'
                                f'{step["stepId"]}'))
        else:
            # The step's kind+description ride the execution context
            # so a stepped run reads as the procedure narrative.
            states.append(gb.assign(
                node_names[i], f'step_{step["stepId"]}',
                f'{step["kind"]}: {step.get("description", "")}',
                nxt))
    states.append(gb.ret_statement('Completed',
                                   GATHER_PREFIX + ALL_PASSED))
    definition = gc.stamp_provenance(
        gb.solution(f'gathering--{solution_name}', *states),
        GATHERING_COMPILER_NAME,
        [f'solution:{solution_name}']
        + [f'step:{s["stepId"]}' for s in steps],
        notes=f'organization: '
              f'{getattr(row, "organization_group", "")}; term: '
              f'{getattr(row, "term_name", "")}'[:500])
    return {'definition': definition, 'artifacts': []}


def _compiler_row(manager):
    row = _by_name(manager, 'GraphCompilerDefinition').get(
        GATHERING_COMPILER_NAME) if manager is not None else None
    if row is not None:
        return row

    class _Default:
        name = GATHERING_COMPILER_NAME
        domain = 'data-gathering'
        compiler_ref = GATHERING_COMPILER_REF
        enabled = True
    return _Default()


def run_gathering_walkthrough(manager, solution_name,
                              submissions=None):
    """ONE complete execution of the compiled procedure with this
    run's submitted validation flags ({'<stepId>_ok': True, ...}).
    Returns which validations passed/failed — an unsubmitted flag is
    honestly a failure, never a silent pass."""
    if submissions is not None and not isinstance(submissions, dict):
        return {'ok': False,
                'error': 'submissions must be a dict of '
                         '<stepId>_ok flags'}
    row = _solution_row(manager, solution_name)
    if row is None:
        return {'ok': False,
                'error': f"no DataGatheringSolution named "
                         f"'{solution_name}'",
                'knownSolutions': sorted(
                    _by_name(manager, 'DataGatheringSolution'))}
    try:
        steps = parsed_steps(row)
        compiled = gc.compile_with(
            _compiler_row(manager),
            {'manager': manager, 'solution_name': solution_name})
    except (RuntimeError, ValueError) as exc:
        return {'ok': False, 'error': str(exc)}
    step = gc.advance(compiled['definition'], {}, submissions or {},
                      manager=manager)
    if step['status'] != 'completed':
        trace = step.get('trace')
        detail = (getattr(trace, 'error_summary', None)
                  or f"engine status '{step['status']}'")
        return {'ok': False,
                'error': f'the procedure graph did not complete: '
                         f'{detail}'}
    raw = step['outcome']
    outcome = (raw[len(GATHER_PREFIX):]
               if isinstance(raw, str)
               and raw.startswith(GATHER_PREFIX) else raw)
    validation_ids = [s['stepId'] for s in steps
                      if s['kind'] == 'validation']
    if outcome == ALL_PASSED:
        passed, failed = validation_ids, []
    else:
        failed_id = str(outcome).split(':', 1)[-1]
        cut = validation_ids.index(failed_id) \
            if failed_id in validation_ids else 0
        passed = validation_ids[:cut]
        failed = [failed_id]
    unreached = [v for v in validation_ids
                 if v not in passed and v not in failed]
    return {'ok': True, 'solution': solution_name,
            'outcome': outcome,
            'validationsPassed': passed,
            'validationsFailed': failed,
            'validationsUnreached': unreached,
            'compiledSolution':
                compiled['definition']['solutionName']}


def assert_step_credibility(manager, gathering_solution_name,
                            step_id, direction, reason,
                            asserted_by, on_behalf_of_group='',
                            magnitude_note='', evidence_url='',
                            notes=''):
    """File one step-credibility assertion. The REASON is required —
    'this step subtracts credibility' with no why is noise."""
    row = _solution_row(manager, gathering_solution_name)
    if row is None:
        return {'ok': False,
                'error': f"no DataGatheringSolution named "
                         f"'{gathering_solution_name}'",
                'knownSolutions': sorted(
                    _by_name(manager, 'DataGatheringSolution'))}
    try:
        steps = parsed_steps(row)
    except ValueError as exc:
        return {'ok': False, 'error': str(exc)}
    step_ids = [s['stepId'] for s in steps]
    if step_id not in step_ids:
        return {'ok': False,
                'error': f"'{gathering_solution_name}' has no step "
                         f"'{step_id}'",
                'validStepIds': step_ids}
    if direction not in CREDIBILITY_DIRECTIONS:
        return {'ok': False,
                'error': f"direction must be one of "
                         f'{CREDIBILITY_DIRECTIONS}'}
    if not (reason or '').strip():
        return {'ok': False,
                'error': 'a step-credibility assertion REQUIRES a '
                         'reason — state why this step '
                         f'{direction} credibility'}
    if not (asserted_by or '').strip():
        return {'ok': False,
                'error': 'asserted_by is required (assertions carry '
                         'attribution)'}
    existing = _by_name(manager, 'StepCredibilityAssertion')
    base = (f'{gathering_solution_name}--{step_id}--{direction}--'
            f'{asserted_by}')
    name = base
    suffix = 2
    while name in existing:
        name = f'{base}-{suffix}'
        suffix += 1
    assertion = StepCredibilityAssertion(
        name=name,
        gathering_solution_name=gathering_solution_name,
        step_id=step_id, direction=direction,
        magnitude_note=magnitude_note, reason=reason,
        asserted_by=asserted_by,
        on_behalf_of_group=on_behalf_of_group,
        evidence_url=evidence_url, status='asserted', notes=notes,
        manager=manager)
    table = manager.objectTables.setdefault(
        'StepCredibilityAssertion', {})
    if not any(existing_row is assertion
               for existing_row in table.values()):
        table[name] = assertion
    _persist(manager, assertion)
    return {'ok': True, 'assertion': name, 'status': 'asserted',
            'note': 'validity votes adjudicate — this row is a '
                    'claim, not a ruling'}


def _assertions_for(manager, solution_name):
    return [a for a in _rows(manager, 'StepCredibilityAssertion')
            if getattr(a, 'gathering_solution_name', '')
            == solution_name]


def gathering_credibility_profile(manager, solution_name):
    """One procedure's steps + its credibility assertions grouped by
    direction, reasons attached."""
    row = _solution_row(manager, solution_name)
    if row is None:
        return {'ok': False,
                'error': f"no DataGatheringSolution named "
                         f"'{solution_name}'",
                'knownSolutions': sorted(
                    _by_name(manager, 'DataGatheringSolution'))}
    try:
        steps = parsed_steps(row)
    except ValueError as exc:
        return {'ok': False, 'error': str(exc)}
    by_step = {}
    for assertion in _assertions_for(manager, solution_name):
        entry = {'direction': assertion.direction,
                 'reason': assertion.reason,
                 'assertedBy': assertion.asserted_by,
                 'group': assertion.on_behalf_of_group or None,
                 'magnitude': assertion.magnitude_note,
                 'evidenceUrl': assertion.evidence_url,
                 'status': assertion.status}
        by_step.setdefault(assertion.step_id, {
            'adds': [], 'subtracts': []})[
            assertion.direction].append(entry)
    return {'ok': True, 'solution': solution_name,
            'organization': getattr(row, 'organization_group', ''),
            'term': getattr(row, 'term_name', ''),
            'sources': json.loads(
                getattr(row, 'source_names_json', '[]') or '[]'),
            'steps': [dict(s, credibility=by_step.get(
                s['stepId'], {'adds': [], 'subtracts': []}))
                for s in steps],
            'validationCoverage': sum(
                1 for s in steps if s['kind'] == 'validation')}


def _equivalence_set(manager, term_names):
    """The requested terms + their declared logical equivalents
    (ScoreTerm.equivalent_terms_json, read-only)."""
    wanted = set(term_names)
    terms = _by_name(manager, 'ScoreTerm')
    for name in list(wanted):
        term = terms.get(name)
        if term is None:
            continue
        try:
            wanted |= set(json.loads(
                getattr(term, 'equivalent_terms_json', '[]')
                or '[]'))
        except (TypeError, ValueError):
            pass
    return wanted


def compare_gathering_solutions(manager, term_names):
    """Line up the gathering procedures behind (logically
    equivalent) terms — a COMPARISON READING. Deliberately declares
    NO winner: which procedure is more legitimate is a question for
    votes (term competition), never for this module."""
    if not term_names:
        return {'ok': False,
                'error': 'name at least one term to compare'}
    wanted = _equivalence_set(manager, term_names)
    solutions = [s for s in _rows(manager, 'DataGatheringSolution')
                 if getattr(s, 'term_name', '') in wanted]
    if not solutions:
        return {'ok': False,
                'error': f'no DataGatheringSolution rows gather for '
                         f'terms {sorted(wanted)}',
                'suggestion': {
                    'knob': 'DataGatheringSolution',
                    'action': 'organizations declare their '
                              'procedures as rows; comparison needs '
                              'at least one'}}
    entries = []
    for solution in sorted(solutions,
                           key=lambda s: getattr(s, 'name', '')):
        profile = gathering_credibility_profile(manager,
                                                solution.name)
        if not profile.get('ok'):
            entries.append({'solution': solution.name,
                            'error': profile['error']})
            continue
        entries.append({
            'solution': solution.name,
            'organization': profile['organization'],
            'term': profile['term'],
            'stepCount': len(profile['steps']),
            'validationCoverage': profile['validationCoverage'],
            'sourcesCited': profile['sources'],
            'credibilityAssertions': {
                'adds': sum(len(s['credibility']['adds'])
                            for s in profile['steps']),
                'subtracts': sum(len(s['credibility']['subtracts'])
                                 for s in profile['steps'])},
            'steps': profile['steps']})
    return {'ok': True, 'termsCompared': sorted(wanted),
            'procedures': entries,
            'note': 'a comparison reading — no winner is declared '
                    'here; legitimacy is decided by votes'}
