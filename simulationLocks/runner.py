"""
@module simulationLocks.runner

The event-driven queue pump (xsim-2): lease free → start the head →
run it via direct dispatch when the kind supports one → release.
Called from POST /api/simulation-queue/pump (and suggested by every
finish response). Kinds without a direct dispatch ('msim-run',
'solution') start through their own endpoints — the pump reports that
honestly instead of guessing; the automated loop lands with xsim-6.
"""

from typing import Dict

from simulationLocks.lease import lease_row
from simulationLocks.run_context import pop_run, push_run
from simulationLocks.sim_queue import (
    finish_run_slot, reconcile_after_restart, start_entry,
    waiting_entries,
)


def _dispatch(manager, sim_kind: str, sim_ref: str) -> Dict:
    """Direct-callable kinds. Imports are lazy — the pump must load
    even when a module is absent."""
    if sim_kind == 'scale':
        from materialsScience.scale_execution import (
            execute_scale_definition,
        )
        return execute_scale_definition(manager, sim_ref)
    if sim_kind == 'model':
        from materialsScience.model_execution import execute_model
        return execute_model(manager, sim_ref)
    if sim_kind == 'search':
        from materialsScience.formulation_search_runner import (
            run_formulation_search,
        )
        return run_formulation_search(manager, sim_ref)
    return {'ok': False,
            'error': f"sim kind '{sim_kind}' has no direct dispatch — "
                     'it starts through its own endpoint',
            'suggestion': {'knob': 'the sim\'s own run endpoint',
                           'action': f"re-POST the {sim_kind} run for "
                                     f"'{sim_ref}'; the gate will "
                                     'admit it now'}}


def pump_queue(manager) -> Dict:
    """Start + run the queue head if the lease is free. One head per
    pump — honest single-step progress, never a hidden loop."""
    reconciled = reconcile_after_restart(manager)
    if lease_row(manager).status == 'held':
        return {'ok': False, 'error': 'lease is held — nothing to pump',
                'reconciled': reconciled}
    head = waiting_entries(manager)
    if not head:
        return {'ok': True, 'note': 'queue is empty',
                'reconciled': reconciled}
    entry = head[0]
    if entry.sim_kind in ('msim-run', 'solution'):
        return {'ok': False, 'entry': entry.name,
                **_dispatch(manager, entry.sim_kind, entry.sim_ref)}
    started = start_entry(manager, entry)
    if not started.get('ok'):
        return started
    token = push_run(started['runContext'])
    try:
        result = _dispatch(manager, entry.sim_kind, entry.sim_ref)
    except Exception as e:
        pop_run(token)
        finish_run_slot(manager, started['runContext'],
                        outcome='failed')
        return {'ok': False, 'entry': entry.name,
                'error': f'run raised: {e}', 'outcome': 'failed'}
    pop_run(token)
    outcome = 'done' if result.get('ok', True) else 'failed'
    finished = finish_run_slot(manager, started['runContext'],
                               outcome=outcome)
    return {'ok': result.get('ok', True), 'entry': entry.name,
            'result': result, 'finish': finished}
