"""
@module scoring.court_case_basis

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
# sap-2c INDEX (design §7): the classes live one-per-file under objects/court_case/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import threading
from collections import defaultdict
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from polariNoCode import graph_builder as gb
from polariNoCode import graph_compilers as gc
from scoring.logic_fork_vote_basis import resolved_procedure_summary
from scoring.worldview_elections_basis import _by_name, _rows

from scoring.objects.court_case._shared import CASE_IN_PROGRESS, FORK_COMPILER_NAME, FORK_COMPILER_REF, OUTCOME_PREFIX, RESERVED_FACT_KEYS, UNRECOGNIZED, _CASE_LOCKS, _CREATE_LOCK, _advance_locked, _check_name, _compiler_row, _edges_for, _persist, _resolved_criterion, _ret_name, advance_case, case_report, compile_fork_graph, fork_outcomes  # noqa: F401
from scoring.objects.court_case.CourtCase import CourtCase  # noqa: F401

from scoring.worldview_elections_basis import _by_name, _rows
import json

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
