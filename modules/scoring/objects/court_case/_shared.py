"""@module scoring.objects.court_case._shared — what the court_case row classes share (constants, seeds, helpers); split from court_case_basis.py (sap-2c)."""
from scoring.worldview_elections_basis import _by_name, _rows
from datetime import datetime, timezone
from collections import defaultdict
from polariNoCode import graph_builder as gb
from polariNoCode import graph_compilers as gc
import json
from scoring.logic_fork_vote_basis import resolved_procedure_summary
import threading

CASE_IN_PROGRESS = 'in-progress'
UNRECOGNIZED = 'unrecognized-determination'
FORK_COMPILER_NAME = 'judicial-fork'
FORK_COMPILER_REF = 'scoring.court_case_basis:compile_fork_graph'
OUTCOME_PREFIX = '__outcome__:'
RESERVED_FACT_KEYS = frozenset({'determination'})
_CASE_LOCKS = defaultdict(threading.Lock)
_CREATE_LOCK = threading.Lock()
def _persist(manager, row):
    """True when saved (or when there is honestly no DB to save to —
    in-memory selftest managers). A REAL save failure returns False
    so callers can surface it: this row IS the audit trail, and
    silent loss is the one thing it must never do."""
    db = getattr(manager, 'db', None)
    if db is None:
        return True
    try:
        db.saveInstanceInDB(row)
        return True
    except Exception as exc:
        print(f'[CourtCase] DB save FAILED for '
              f'{getattr(row, "name", "?")}: {exc}', flush=True)
        return False
def _edges_for(manager, procedure):
    return [e for e in _rows(manager, 'DecisionProcedureEdge')
            if getattr(e, 'decision_procedure_name', '') == procedure]
def fork_outcomes(manager, procedure, fork):
    """A fork's legal outcome labels = the from_outcome values its
    outgoing edges declare (ordered, deduped)."""
    seen, outcomes = set(), []
    for e in _edges_for(manager, procedure):
        if getattr(e, 'from_fork', '') == fork:
            outcome = getattr(e, 'from_outcome', '')
            if outcome and outcome not in seen:
                seen.add(outcome)
                outcomes.append(outcome)
    return outcomes
def compile_fork_graph(domain_rows):
    """The registered compiler (GraphCompilerDefinition
    'judicial-fork'): one fork + its resolved criterion + its legal
    outcomes -> one small executable graph. The judge/jury's
    determination (one of the outcome labels) flows in as context;
    a ConditionalChain per outcome routes it; an unmatched
    determination lands on an honest UNRECOGNIZED terminal instead
    of a silent default branch."""
    fork = domain_rows['fork']
    criterion = domain_rows.get('criterion', '')
    outcomes = domain_rows['outcomes']
    if not outcomes:
        raise ValueError(
            f"fork '{fork}' declares no outcomes — add "
            f"DecisionProcedureEdge rows (from_fork='{fork}', "
            f"from_outcome=<label>) so the fork can route")
    states = [gb.entry(nxt=_check_name(0))]
    for i, outcome in enumerate(outcomes):
        is_last = i == len(outcomes) - 1
        false_next = ('Unrecognized' if is_last
                      else _check_name(i + 1))
        states.append(gb.cond(
            _check_name(i),
            [gb.link(gb.var_src('self.determination'), 'equals',
                     gb.lit_src(outcome))],
            _ret_name(i), false_next,
            display_name=f'{fork}: {criterion}'[:200]))
        # OUTCOME_PREFIX makes the literal collision-proof against
        # the engine's context-first ReturnStatement resolution AND
        # keeps it a string ('5' would otherwise come back int 5).
        states.append(gb.ret_statement(_ret_name(i),
                                       OUTCOME_PREFIX + outcome))
    states.append(gb.ret_statement('Unrecognized',
                                   OUTCOME_PREFIX + UNRECOGNIZED))
    return gc.stamp_provenance(
        gb.solution(f'fork--{fork}', *states),
        FORK_COMPILER_NAME,
        [f'fork:{fork}'] + [f'outcome:{o}' for o in outcomes],
        notes=f'criterion: {criterion}'[:500])
def _check_name(i):
    return f'CheckOutcome{i}'
def _ret_name(i):
    return f'Outcome{i}'
def _compiler_row(manager):
    """The registered GraphCompilerDefinition row when the tree has
    one (the enable/disable knob lives there); a module-default
    otherwise so selftests and fresh instances still compile."""
    row = _by_name(manager, 'GraphCompilerDefinition').get(
        FORK_COMPILER_NAME) if manager is not None else None
    if row is not None:
        return row

    class _Default:
        name = FORK_COMPILER_NAME
        domain = 'judicial'
        compiler_ref = FORK_COMPILER_REF
        enabled = True
    return _Default()
def _resolved_criterion(manager, procedure, fork):
    summary = resolved_procedure_summary(manager, procedure)
    if not summary.get('ok'):
        return None, summary
    entry = next((f for f in summary['forks']
                  if f['fork'] == fork), None)
    if entry is None or not entry.get('resolvedCriterion'):
        return None, {
            'ok': False,
            'error': f"fork '{fork}' has no resolved criterion",
            'suggestion': {
                'knob': 'LogicForkCriterion.is_current_default '
                        'or a LogicForkVote apply',
                'action': f"give fork '{fork}' an incumbent default "
                          f'criterion or apply a vote for it'}}
    return entry['resolvedCriterion'], None
def advance_case(manager, case_name, determination,
                 supplied_by=''):
    """ONE orchestrator step: compile the current fork's graph, run
    the case context + this determination through the REAL engine,
    route on the outcome via the procedure's edge rows, persist.
    Serialized per case name — two adjudicators advancing the same
    case interleave whole steps, never partial writes."""
    if isinstance(determination, str) \
            and determination.startswith(OUTCOME_PREFIX):
        return {'ok': False,
                'error': f'determinations may not carry the '
                         f"reserved '{OUTCOME_PREFIX}' prefix"}
    if not isinstance(case_name, str):
        return {'ok': False,
                'error': 'case name must be a string'}
    with _CASE_LOCKS[case_name]:
        return _advance_locked(manager, case_name, determination,
                               supplied_by)
def _advance_locked(manager, case_name, determination, supplied_by):
    case = _by_name(manager, 'CourtCase').get(case_name)
    if case is None:
        return {'ok': False,
                'error': f"no CourtCase named '{case_name}'",
                'knownCases': sorted(_by_name(manager, 'CourtCase'))}
    if case.status != CASE_IN_PROGRESS:
        return {'ok': False,
                'error': f"case '{case_name}' already concluded: "
                         f'{case.status}'}
    procedure = case.decision_procedure_name
    fork = case.current_fork
    criterion, err = _resolved_criterion(manager, procedure, fork)
    if err is not None:
        return err
    outcomes = fork_outcomes(manager, procedure, fork)
    if not outcomes:
        return {'ok': False,
                'error': f"fork '{fork}' has no outgoing "
                         f'DecisionProcedureEdge rows',
                'suggestion': {
                    'knob': 'DecisionProcedureEdge',
                    'action': f"declare outcomes for '{fork}' "
                              f'(from_fork/from_outcome rows)'}}
    try:
        compiled = gc.compile_with(
            _compiler_row(manager),
            {'fork': fork, 'criterion': criterion,
             'outcomes': outcomes})
    except (RuntimeError, ValueError) as exc:
        return {'ok': False, 'error': str(exc),
                'suggestion': {
                    'knob': 'GraphCompilerDefinition.enabled',
                    'action': f"the '{FORK_COMPILER_NAME}' compiler "
                              f'row gates fork compilation'}}
    stored = json.loads(case.context_json or '{}')
    step = gc.advance(compiled['definition'], stored,
                      {'determination': determination},
                      manager=manager)
    if step['status'] != 'completed':
        # An engine failure (including a single-writer-gate queue
        # refusal while a simulation holds the lease) is NOT the
        # adjudicator's fault — never blame the determination.
        trace = step.get('trace')
        detail = (getattr(trace, 'error_summary', None)
                  or f"engine status '{step['status']}'")
        return {'ok': False,
                'error': f'the fork graph did not complete: {detail}',
                'suggestion': {
                    'knob': 'retry after the running '
                            'simulation/solution releases the '
                            'single-writer gate',
                    'action': 'the determination was NOT judged — '
                              'resubmit unchanged'}}
    raw_outcome = step['outcome']
    outcome = (raw_outcome[len(OUTCOME_PREFIX):]
               if isinstance(raw_outcome, str)
               and raw_outcome.startswith(OUTCOME_PREFIX)
               else raw_outcome)
    if outcome == UNRECOGNIZED:
        return {'ok': False,
                'error': f"determination {determination!r} is not a "
                         f"legal outcome of fork '{fork}'",
                'legalOutcomes': outcomes,
                'criterion': criterion}
    edge = next((e for e in _edges_for(manager, procedure)
                 if getattr(e, 'from_fork', '') == fork
                 and getattr(e, 'from_outcome', '') == outcome), None)
    if edge is None:
        return {'ok': False,
                'error': f"no edge routes fork '{fork}' outcome "
                         f"'{outcome}' — the procedure graph is "
                         f'incomplete',
                'suggestion': {
                    'knob': 'DecisionProcedureEdge',
                    'action': f"add an edge from_fork='{fork}' "
                              f"from_outcome='{outcome}'"}}
    to_fork = getattr(edge, 'to_fork', '')
    terminal = getattr(edge, 'to_terminal', '')
    if not to_fork and not terminal:
        return {'ok': False,
                'error': f"edge '{getattr(edge, 'name', '?')}' "
                         f'routes nowhere (to_fork and to_terminal '
                         f'both empty) — the case cannot advance',
                'suggestion': {
                    'knob': 'DecisionProcedureEdge',
                    'action': 'set to_fork OR to_terminal on that '
                              'edge row'}}
    log = json.loads(case.execution_log_json or '[]')
    log.append({'fork': fork, 'criterion': criterion,
                'determination': determination,
                'suppliedBy': supplied_by, 'outcome': outcome,
                'next': to_fork or terminal,
                'at': datetime.now(timezone.utc).isoformat()})
    case.execution_log_json = json.dumps(log)
    # 'determination' is engine transport — the audit log keeps it;
    # the persisted FACT bag must not (it would read as an
    # accumulated case fact and clobber any real key of that name).
    facts = {k: v for k, v in step['final_context'].items()
             if k not in RESERVED_FACT_KEYS}
    case.context_json = json.dumps(facts)
    if to_fork:
        case.current_fork = to_fork
    else:
        case.status = terminal or 'concluded'
        case.current_fork = ''
    persisted = _persist(manager, case)
    result = {'ok': True, 'fork': fork, 'outcome': outcome,
              'criterion': criterion,
              'nextFork': to_fork or None,
              'terminal': terminal or None,
              'status': case.status,
              'compiledSolution':
                  compiled['definition']['solutionName'],
              'case': case_report(manager, case_name)}
    if not persisted:
        result['persistWarning'] = (
            'the DB save FAILED — this step exists in memory only '
            'and will not survive a restart (check the backend log)')
    return result
def case_report(manager, case_name):
    """Current state + the full step-by-step audit trail."""
    case = _by_name(manager, 'CourtCase').get(case_name)
    if case is None:
        return {'ok': False,
                'error': f"no CourtCase named '{case_name}'",
                'knownCases': sorted(_by_name(manager, 'CourtCase'))}
    return {'ok': True, 'name': case.name,
            'decisionProcedure': case.decision_procedure_name,
            'status': case.status,
            'currentFork': case.current_fork or None,
            'adjudicator': {'type': case.adjudicator_type,
                            'name': case.adjudicator_name},
            'context': json.loads(case.context_json or '{}'),
            'executionLog': json.loads(
                case.execution_log_json or '[]')}
