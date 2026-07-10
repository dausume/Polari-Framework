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
    try:
        yield slot
    except Exception:
        pop_run(token)
        finish_run_slot(manager, slot['runContext'], outcome='failed')
        raise
    else:
        pop_run(token)
        finish_run_slot(manager, slot['runContext'], outcome='done')


def gate_refusal_media(slot: Dict) -> Dict:
    """The consistent HTTP body for a queued/refused gate result."""
    return {k: v for k, v in slot.items() if k != 'ok'}
