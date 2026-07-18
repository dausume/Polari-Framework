"""
@module scoring.court_case

ncg-2: judicial adjudication as the FIRST DOMAIN CLIENT of the
no-code generalization seam (JUDICIAL_ADJUDICATION_GRAPH_PLAN.md,
built through polariNoCode.graph_builder/graph_compilers) — Dustin's
ask: a case's context flows through drag-and-drop-able logic blocks,
adjudicated fork by fork by a judge or jury.

The engine has NO pause/resume (verified, still true), so a case is
NOT one long graph execution: each fork compiles to its OWN small
SolutionDefinition (inspectable/editable in the existing D3 editor),
and `advance_case()` runs one complete execution per judge/jury
determination — the evaluate_stage_gate pattern, factored through
graph_compilers.advance(). The CourtCase row is what persists between
runs: accumulated fact context + an append-only execution log (the
audit trail).

Fork semantics come from rows that ALREADY exist (mechanism C):
  * LogicForkCriterion + LogicForkVote resolve WHAT a fork tests
    (resolved_procedure_summary — vote-elected else incumbent).
  * DecisionProcedureEdge rows define each fork's legal OUTCOMES and
    where each outcome leads (next fork or terminal) — the same rows
    the human-readable summary reads; here they also route the case.

@consumers
  - scoring.scoring_api (court-case routes)
  - polariServer (registration + CRUDE)
"""

import json
import threading
from collections import defaultdict
from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit
from polariNoCode import graph_builder as gb
from polariNoCode import graph_compilers as gc
from scoring.logic_fork_vote import resolved_procedure_summary
from scoring.worldview_elections import _by_name, _rows

CASE_IN_PROGRESS = 'in-progress'
UNRECOGNIZED = 'unrecognized-determination'

FORK_COMPILER_NAME = 'judicial-fork'
FORK_COMPILER_REF = 'scoring.court_case:compile_fork_graph'

# The engine's ReturnStatement resolves its literal through the
# context FIRST (a case fact keyed by an outcome label would hijack
# the verdict — review finding, proven live). Compiled graphs
# therefore return outcomes under this reserved prefix, stripped
# after execution; fact keys and determinations may never carry it.
OUTCOME_PREFIX = '__outcome__:'
# 'determination' is the engine-transport key for the judge/jury
# input — never a case fact.
RESERVED_FACT_KEYS = frozenset({'determination'})

# advance/create are read-modify-write on shared rows and the server
# is multi-threaded — one lock per case name, one for creation.
_CASE_LOCKS = defaultdict(threading.Lock)
_CREATE_LOCK = threading.Lock()


class CourtCase(treeObject):
    """One case moving through a decision procedure — the persistent
    state BETWEEN fork-graph executions."""

    @treeObjectInit
    def __init__(self, name: str = '',
                 decision_procedure_name: str = '',
                 current_fork: str = '',
                 # 'in-progress' until an edge routes to a terminal;
                 # then the terminal label (e.g. 'ACQUITTAL').
                 status: str = CASE_IN_PROGRESS,
                 # The accumulated flat fact bag (ad hoc dict — the
                 # engine imposes no schema on it; verified).
                 context_json: str = '{}',
                 # Append-only audit trail: [{fork, criterion,
                 # determination, outcome, next, at}, ...]
                 execution_log_json: str = '[]',
                 adjudicator_type: str = 'judge',  # 'judge' | 'jury'
                 adjudicator_name: str = '',
                 jurisdiction_subject_name: str = '',
                 provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.decision_procedure_name = decision_procedure_name
        self.current_fork = current_fork
        self.status = status
        self.context_json = context_json
        self.execution_log_json = execution_log_json
        self.adjudicator_type = adjudicator_type
        self.adjudicator_name = adjudicator_name
        self.jurisdiction_subject_name = jurisdiction_subject_name
        self.provenance_id = provenance_id
        self.notes = notes


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


def create_court_case(manager, name, decision_procedure_name,
                      initial_context=None, adjudicator_type='judge',
                      adjudicator_name='',
                      jurisdiction_subject_name='', notes=''):
    """Open a case at the procedure's start edge (from_fork='')."""
    if not isinstance(name, str) or not name:
        return {'ok': False,
                'error': 'case name must be a non-empty string'}
    if name == 'create':
        return {'ok': False,
                'error': "a case may not be named 'create' — the "
                         'static create route shadows its report '
                         'endpoint'}
    if not isinstance(initial_context, (dict, type(None))):
        return {'ok': False,
                'error': 'initial_context must be a JSON object '
                         '(the flat case-fact bag)'}
    bad_keys = [k for k in (initial_context or {})
                if not isinstance(k, str) or k in RESERVED_FACT_KEYS
                or k.startswith(OUTCOME_PREFIX)]
    if bad_keys:
        return {'ok': False,
                'error': f'reserved/invalid fact keys: {bad_keys} — '
                         f"'determination' and '{OUTCOME_PREFIX}*' "
                         f'are engine transport, not case facts'}
    with _CREATE_LOCK:
        return _create_locked(manager, name, decision_procedure_name,
                              initial_context, adjudicator_type,
                              adjudicator_name,
                              jurisdiction_subject_name, notes)


def _create_locked(manager, name, decision_procedure_name,
                   initial_context, adjudicator_type,
                   adjudicator_name, jurisdiction_subject_name,
                   notes):
    if _by_name(manager, 'CourtCase').get(name) is not None:
        return {'ok': False,
                'error': f"a CourtCase named '{name}' already exists"}
    # The start edge is from_fork='' AND from_outcome='' — an edge
    # with only from_fork='' but a named outcome is a continuation
    # entry (e.g. a CONVICTION terminal feeding a sentencing phase),
    # not where a fresh case begins.
    start = next((e for e in _edges_for(manager,
                                        decision_procedure_name)
                  if not getattr(e, 'from_fork', '')
                  and not getattr(e, 'from_outcome', '')), None)
    if start is None or not getattr(start, 'to_fork', ''):
        return {'ok': False,
                'error': f"decision procedure "
                         f"'{decision_procedure_name}' has no start "
                         f"edge (from_fork='') pointing at a fork",
                'suggestion': {
                    'knob': 'DecisionProcedureEdge',
                    'action': "add an edge with from_fork='' and "
                              'to_fork=<first fork>'}}
    case = CourtCase(
        name=name,
        decision_procedure_name=decision_procedure_name,
        current_fork=getattr(start, 'to_fork', ''),
        status=CASE_IN_PROGRESS,
        context_json=json.dumps(initial_context or {}),
        execution_log_json='[]',
        adjudicator_type=adjudicator_type,
        adjudicator_name=adjudicator_name,
        jurisdiction_subject_name=jurisdiction_subject_name,
        notes=notes, manager=manager)
    # A real manager registers the row via treeObjectInit; in-memory
    # managers (selftests) need the explicit insert — guarded so a
    # registered row is never duplicated under a second key.
    table = manager.objectTables.setdefault('CourtCase', {})
    if not any(existing is case for existing in table.values()):
        table[name] = case
    persisted = _persist(manager, case)
    result = {'ok': True, 'case': case_report(manager, name)}
    if not persisted:
        result['persistWarning'] = (
            'the DB save FAILED — the case exists in memory only '
            'and will not survive a restart (check the backend log)')
    return result


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
