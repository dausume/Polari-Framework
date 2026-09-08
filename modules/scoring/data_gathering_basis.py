"""
@cross-cutting
@module scoring.data_gathering_basis
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
  - scoring.term_competition_basis (comparability input)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/data_gathering/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from polariNoCode import graph_builder as gb
from polariNoCode import graph_compilers as gc
from scoring.worldview_elections_basis import _by_name, _rows

from scoring.objects.data_gathering._shared import ALL_PASSED, CREDIBILITY_DIRECTIONS, GATHERING_COMPILER_NAME, GATHERING_COMPILER_REF, GATHER_PREFIX, SEED_DATA_GATHERING_COMPILER, SOLUTION_STATUSES, STEP_KINDS, _assertions_for, _compiler_row, _equivalence_set, _flag_var, _persist, _solution_row, _step_node_name, compare_gathering_solutions, compile_gathering_solution, gathering_credibility_profile, parsed_steps, run_gathering_walkthrough  # noqa: F401
from scoring.objects.data_gathering.DataGatheringSolution import DataGatheringSolution  # noqa: F401
from scoring.objects.data_gathering.StepCredibilityAssertion import StepCredibilityAssertion  # noqa: F401

from scoring.worldview_elections_basis import _by_name, _rows

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
