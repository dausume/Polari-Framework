"""
@module simulationLocks.gate

The ONE gate every mutating simulation entry point wraps itself in
(strict policy, Dustin directive 4: assume ONE mutator, period —
model/scale executes count as sims and take short leases through this
same seam).

    with simulation_gate(manager, 'scale', name) as slot:
        if not slot['ok']:
            return <honest queued/refusal response from slot>
        ... run ...

- A valid ambient/tied run context (parent msim, nested solution
  engine, stage machinery) passes straight through presenting the
  PARENT's token — children never re-acquire.
- Otherwise the gate enqueues + acquires (head + free lease) or
  yields the honest queued state.
- Completion releases lease+locks atomically; an exception releases
  with outcome='failed' (generated objects quarantine) and re-raises.
"""

from contextlib import contextmanager
from typing import Dict, List, Optional

from accessControl.cause_context import pop_cause
from simulationLocks.lease import validate_token
from simulationLocks.run_context import current_run, pop_run, push_run
from simulationLocks.sim_queue import finish_run_slot, request_run_slot


@contextmanager
def simulation_gate(manager, sim_kind: str, sim_ref: str,
                    submitted_by: str = '',
                    manifest: Optional[List[Dict]] = None,
                    run_context: Optional[Dict] = None):
    """Yields a slot dict: {'ok': True, 'runContext', 'tied'} or the
    honest refusal/queued dict from request_run_slot."""
    tied = run_context or current_run()
    if tied and validate_token(manager,
                               tied.get('lease_token', 0)).get('ok'):
        yield {'ok': True, 'runContext': tied, 'tied': True}
        return
    if manager is None or not hasattr(manager, 'idList'):
        # A manager that cannot mint treeObject ids (unit-test stub)
        # cannot host queue/lease rows — pass through, honestly marked.
        yield {'ok': True, 'runContext': tied,
               'ungated': 'manager cannot host queue rows (no idList)'}
        return
    slot = request_run_slot(manager, sim_kind, sim_ref,
                            submitted_by=submitted_by,
                            manifest=manifest)
    if not slot.get('ok'):
        yield slot
        return
    token = push_run(slot['runContext'])
    # ct-0 (design §3, "simulations"): a `simulation` cause is pushed BESIDE
    # the run context, so every row the run writes is attributable to the run
    # that caused it. Child of the request/trigger that submitted the run, or
    # a root of kind `simulation` when nothing did. No-op outside dev posture.
    cause_token = push_cause_for_run(sim_kind, sim_ref)
    try:
        yield slot
    except Exception:
        pop_cause(cause_token)
        pop_run(token)
        finish_run_slot(manager, slot['runContext'], outcome='failed')
        raise
    else:
        pop_cause(cause_token)
        pop_run(token)
        finish_run_slot(manager, slot['runContext'], outcome='done')


def push_cause_for_run(sim_kind: str, sim_ref: str):
    """The `simulation` cause for one gated run (ct-0).

    A SOLUTION run already pushed its own `solution` cause in
    SolutionExecutionEngine.execute before reaching this gate; pushing a
    second node for the same run would put a phantom `simulation:solution:X`
    in the map. So that one case rides the cause it already has."""
    from accessControl.cause_context import child_or_root_cause, current_cause
    if sim_kind == 'solution':
        cause = current_cause()
        if cause and cause.get('entry_ref') == f'solution:{sim_ref}':
            return None
    return child_or_root_cause('simulation', f'{sim_kind}:{sim_ref}')


def gate_refusal_media(slot: Dict) -> Dict:
    """The consistent HTTP body for a queued/refused gate result."""
    return {k: v for k, v in slot.items() if k != 'ok'}
