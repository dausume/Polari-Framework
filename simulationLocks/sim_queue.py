"""
@module simulationLocks.sim_queue

The queue of multiscale simulations on core polari (Dustin directive
6): persisted SimulationQueueEntry rows, honest states
(queued|running|done|failed|cancelled), FIFO with a priority knob.

There is no background runner thread today (all sim execution is
synchronous within its request) — the queue is pumped event-driven:
a finished run's release response SUGGESTS the pump knob
([[knobs-and-suggestions]]), and POST /api/simulation-queue/pump
starts the head via runner.py's dispatch when its kind supports a
direct call. The automated runner loop lands with the xsim-6
rehearsal.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from objectTreeDecorators import treeObject, treeObjectInit
from simulationLocks.lease import (
    acquire_lease, lease_row, lease_status, release_lease,
)
from simulationLocks.object_locks import acquire_manifest, release_for_run

QUEUE_STATES = ('queued', 'running', 'done', 'failed', 'cancelled')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulationQueueEntry(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', sim_kind: str = '',
                 sim_ref: str = '', state: str = 'queued',
                 position: int = 0, submitted_by: str = '',
                 priority: int = 0, run_id: str = '',
                 manifest_json: str = '[]', submitted_at: str = '',
                 started_at: str = '', finished_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.sim_kind = sim_kind      # msim-run|solution|search|model|scale
        self.sim_ref = sim_ref
        self.state = state
        self.position = position
        self.submitted_by = submitted_by
        self.priority = priority      # knob; default 0 = pure FIFO
        self.run_id = run_id
        self.manifest_json = manifest_json   # declared working set
        self.submitted_at = submitted_at
        self.started_at = started_at
        self.finished_at = finished_at
        self.notes = notes


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def _persist(manager, row):
    try:
        manager.db.saveInstanceInDB(row)
    except Exception:
        pass


def _entries(manager) -> List[SimulationQueueEntry]:
    return _rows(manager, 'SimulationQueueEntry')


def waiting_entries(manager) -> List[SimulationQueueEntry]:
    """Queued entries in start order: priority desc, then FIFO."""
    queued = [e for e in _entries(manager) if e.state == 'queued']
    return sorted(queued, key=lambda e: (-int(e.priority or 0),
                                         int(e.position or 0)))


def queue_position(manager, run_id: str) -> Optional[int]:
    """1-based position for a queued run; 0 = running now."""
    for entry in _entries(manager):
        if entry.run_id == run_id and entry.state == 'running':
            return 0
    for i, entry in enumerate(waiting_entries(manager)):
        if entry.run_id == run_id:
            return i + 1
    return None


def queue_list(manager) -> List[Dict]:
    order = {e.name: i + 1 for i, e in
             enumerate(waiting_entries(manager))}
    return [{'name': e.name, 'simKind': e.sim_kind, 'simRef': e.sim_ref,
             'state': e.state, 'position': order.get(e.name),
             'priority': e.priority, 'runId': e.run_id,
             'submittedBy': e.submitted_by,
             'submittedAt': e.submitted_at, 'startedAt': e.started_at,
             'finishedAt': e.finished_at, 'notes': e.notes}
            for e in sorted(_entries(manager),
                            key=lambda e: e.submitted_at or '')]


def _next_position(manager) -> int:
    return 1 + max([int(e.position or 0) for e in _entries(manager)]
                   or [0])


def start_entry(manager, entry) -> Dict:
    """Acquire lease + the entry's stored manifest locks and flip it to
    running. The shared start path for admission AND the pump."""
    granted = acquire_lease(manager, entry.run_id)
    if not granted['ok']:
        return granted
    try:
        manifest = json.loads(entry.manifest_json or '[]')
    except (TypeError, ValueError):
        manifest = []
    locked = acquire_manifest(manager, entry.run_id, granted['token'],
                              manifest)
    if not locked['ok']:
        release_lease(manager, entry.run_id, granted['token'])
        entry.state = 'failed'
        entry.finished_at = _now()
        entry.notes = f"lock refusal: {locked['error']}"
        _persist(manager, entry)
        return locked
    entry.state = 'running'
    entry.started_at = _now()
    _persist(manager, entry)
    return {'ok': True, 'entry': entry.name,
            'runContext': {'run_id': entry.run_id,
                           'lease_token': granted['token']},
            'locks': locked['locks']}


def request_run_slot(manager, sim_kind: str, sim_ref: str,
                     submitted_by: str = '', priority: int = 0,
                     manifest: Optional[List[Dict]] = None) -> Dict:
    """The single-writer admission point: enqueue, and START only if
    the lease is free and this entry is the queue head. Otherwise the
    entry stays queued (persisted — survives restart) and the caller
    gets an honest position, never a block.

    A RESUBMISSION of an already-queued (kind, ref) ADOPTS the queued
    entry instead of enqueuing a duplicate — that is how
    endpoint-started kinds re-enter and start when they reach the
    head (retry-as-start; without this, retries pile up behind their
    own first attempt and the queue wedges)."""
    entry = next((e for e in waiting_entries(manager)
                  if e.sim_kind == sim_kind and e.sim_ref == sim_ref),
                 None)
    if entry is not None and manifest:
        entry.manifest_json = json.dumps(manifest)
        _persist(manager, entry)
    if entry is None:
        entry = SimulationQueueEntry(
            name=f'q-{sim_kind}-{sim_ref}-{_next_position(manager)}',
            sim_kind=sim_kind, sim_ref=sim_ref, state='queued',
            position=_next_position(manager), submitted_by=submitted_by,
            priority=int(priority or 0),
            manifest_json=json.dumps(manifest or []),
            submitted_at=_now(), manager=manager)
        entry.run_id = f'run-{entry.id or entry.name}'
        _persist(manager, entry)
    head = waiting_entries(manager)
    if lease_row(manager).status == 'held' or not head \
            or head[0].name != entry.name:
        status = lease_status(manager)
        return {'ok': False, 'queued': True, 'entry': entry.name,
                'runId': entry.run_id,
                'position': queue_position(manager, entry.run_id),
                'holderRun': status['holderRun'],
                'error': f"single-writer policy: lease held by "
                         f"'{status['holderRun']}'" if
                         status['status'] == 'held' else
                         'single-writer policy: not at the queue head',
                'suggestion': {'knob': 'the simulation queue',
                               'action': 'wait; retry starts it when '
                                         'the lease frees (or POST '
                                         '/api/simulation-queue/pump)'}}
    started = start_entry(manager, entry)
    if not started.get('ok'):
        started.setdefault('queued', entry.state == 'queued')
        started.setdefault('entry', entry.name)
    return started


def finish_run_slot(manager, run_context: Dict,
                    outcome: str = 'done') -> Dict:
    """Release the working set ATOMICALLY with the lease (failure
    quarantines generated objects), close the queue entry, and
    surface the pump knob for the next head."""
    run_id = run_context.get('run_id', '')
    token = run_context.get('lease_token', 0)
    lock_result = release_for_run(
        manager, run_id, 'failed' if outcome == 'failed' else 'done')
    lease_result = release_lease(manager, run_id, token)
    for entry in _entries(manager):
        if entry.run_id == run_id and entry.state == 'running':
            entry.state = 'failed' if outcome == 'failed' else 'done'
            entry.finished_at = _now()
            _persist(manager, entry)
    head = waiting_entries(manager)
    return {'ok': lease_result.get('ok', False), 'outcome': outcome,
            'locks': lock_result,
            'nextHead': head[0].name if head else None,
            'suggestion': ({'knob': 'pump',
                            'action': 'POST /api/simulation-queue/pump '
                                      'to start the queue head'}
                           if head else None)}


def reconcile_after_restart(manager) -> Dict:
    """Restart recovery (edge-case ledger): a reloaded 'running' entry
    whose lease is NOT held is a crashed run — closed as failed with
    its generated objects quarantined, never silently resumed."""
    stale = []
    if lease_row(manager).status != 'held':
        for entry in _entries(manager):
            if entry.state == 'running':
                release_for_run(manager, entry.run_id, 'failed')
                entry.state = 'failed'
                entry.finished_at = _now()
                entry.notes = ('closed by restart reconciliation — '
                               'lease was not held')
                _persist(manager, entry)
                stale.append(entry.name)
    return {'ok': True, 'closedStale': stale,
            'queuedSurvivors': [e.name for e in
                                waiting_entries(manager)]}


def cancel_entry(manager, entry_name: str, by: str = '') -> Dict:
    """Cancel queued (plain) or RUNNING (breaks the lease — evented —
    and quarantines the run's generated objects: it did not finish)."""
    from simulationLocks.lease import break_lease
    for entry in _entries(manager):
        if entry.name != entry_name:
            continue
        if entry.state == 'queued':
            entry.state = 'cancelled'
            entry.finished_at = _now()
            _persist(manager, entry)
            return {'ok': True, 'state': 'cancelled'}
        if entry.state == 'running':
            broke = break_lease(manager, by or 'cancel',
                                f'cancel of running entry {entry_name}',
                                force=True)
            release_for_run(manager, entry.run_id, 'failed')
            entry.state = 'cancelled'
            entry.finished_at = _now()
            _persist(manager, entry)
            return {'ok': True, 'state': 'cancelled',
                    'leaseBreak': broke}
        return {'ok': False,
                'error': f"entry is {entry.state} — nothing to cancel"}
    return {'ok': False, 'error': f"no queue entry '{entry_name}'"}


def promote_entry(manager, entry_name: str) -> Dict:
    """Priority knob: move a queued entry to the front (starvation
    relief — edge-case ledger)."""
    for entry in _entries(manager):
        if entry.name == entry_name:
            if entry.state != 'queued':
                return {'ok': False,
                        'error': f'entry is {entry.state}, not queued'}
            top = max([int(e.priority or 0)
                       for e in waiting_entries(manager)] or [0])
            entry.priority = top + 1
            _persist(manager, entry)
            return {'ok': True, 'priority': entry.priority}
    return {'ok': False, 'error': f"no queue entry '{entry_name}'"}
