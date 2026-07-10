"""
@module simulationLocks.lease

The fencing-token mutation lease (xsim-2, design pillar 2): ONE
MutationLease singleton row on core polari; every mutating simulation
run acquires it at start; the token is a monotonic epoch int bumped on
every grant, so a crashed run's zombie worker holding epoch N is
refused after the lease was broken and re-issued as N+1 — refused
honestly, never silently.

TTL lapse makes the lease BREAKABLE, never auto-broken: break_lease is
an explicit act (queue head or admin knob) and EVERY break is a
LeaseBreakEvent row. Clock authority is this process's clock — core's
clock only, no skew games (remote validation arrives in xsim-4).
"""

from datetime import datetime, timezone
from typing import Dict, Optional

from objectTreeDecorators import treeObject, treeObjectInit

LEASE_NAME = 'mutation-lease'
DEFAULT_TTL_SECONDS = 120       # knob


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _age_seconds(stamp: str) -> float:
    try:
        then = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return float('inf')
    return (datetime.now(timezone.utc) - then).total_seconds()


class MutationLease(treeObject):
    """The mesh-wide single-writer lease. token = fencing epoch."""

    @treeObjectInit
    def __init__(self, name: str = LEASE_NAME, holder_run: str = '',
                 token: int = 0, acquired_at: str = '',
                 heartbeat_at: str = '',
                 ttl_seconds: int = DEFAULT_TTL_SECONDS,
                 status: str = 'free', notes: str = '', manager=None):
        self.name = name
        self.holder_run = holder_run
        self.token = token
        self.acquired_at = acquired_at
        self.heartbeat_at = heartbeat_at
        self.ttl_seconds = ttl_seconds
        self.status = status
        self.notes = notes


class LeaseBreakEvent(treeObject):
    """One row per break — a break is NEVER silent."""

    @treeObjectInit
    def __init__(self, name: str = '', broken_run: str = '',
                 token_epoch: int = 0, broken_by: str = '',
                 reason: str = '', forced: bool = False, at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.broken_run = broken_run
        self.token_epoch = token_epoch
        self.broken_by = broken_by
        self.reason = reason
        self.forced = forced
        self.at = at
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


def lease_row(manager) -> MutationLease:
    for row in _rows(manager, 'MutationLease'):
        if getattr(row, 'name', '') == LEASE_NAME:
            return row
    return MutationLease(manager=manager)


def is_breakable(lease) -> bool:
    return (lease.status == 'held'
            and _age_seconds(lease.heartbeat_at) > lease.ttl_seconds)


def lease_status(manager) -> Dict:
    lease = lease_row(manager)
    return {'status': lease.status, 'holderRun': lease.holder_run,
            'tokenEpoch': lease.token,
            'heartbeatAgeSeconds': (round(_age_seconds(
                lease.heartbeat_at), 1) if lease.status == 'held'
                else None),
            'ttlSeconds': lease.ttl_seconds,
            'breakable': is_breakable(lease)}


def acquire_lease(manager, run_id: str,
                  ttl_seconds: Optional[int] = None) -> Dict:
    """Grant the lease to run_id, bumping the fencing epoch. A held,
    non-expired lease refuses; an EXPIRED one still refuses — it is
    breakable, not broken (call break_lease first, evented)."""
    lease = lease_row(manager)
    if lease.status == 'held':
        return {'ok': False,
                'error': f"mutation lease held by run "
                         f"'{lease.holder_run}' (epoch {lease.token})",
                'breakable': is_breakable(lease),
                'suggestion': {
                    'knob': 'break_lease' if is_breakable(lease)
                            else 'the simulation queue',
                    'action': 'break the expired lease (evented) and '
                              'retry' if is_breakable(lease)
                              else 'wait in the queue — single-writer '
                                   'policy (directive 4)'}}
    lease.token += 1
    lease.holder_run = run_id
    lease.acquired_at = lease.heartbeat_at = _now()
    if ttl_seconds:
        lease.ttl_seconds = int(ttl_seconds)
    lease.status = 'held'
    _persist(manager, lease)
    return {'ok': True, 'token': lease.token,
            'ttlSeconds': lease.ttl_seconds}


def validate_token(manager, token: int) -> Dict:
    """Fencing check: EVERY lease-path write presents its token; only
    the current epoch of a HELD lease passes. Zombies are refused
    honestly, naming both epochs."""
    lease = lease_row(manager)
    if lease.status != 'held':
        return {'ok': False,
                'error': f'lease is {lease.status} — no run may '
                         f'mutate (presented epoch {token})'}
    if token != lease.token:
        return {'ok': False,
                'error': f'stale fencing token: presented epoch '
                         f'{token}, current epoch {lease.token} '
                         f"(held by run '{lease.holder_run}') — "
                         'zombie write refused'}
    return {'ok': True, 'holderRun': lease.holder_run}


def heartbeat_lease(manager, run_id: str, token: int) -> Dict:
    check = validate_token(manager, token)
    if not check['ok']:
        return check
    lease = lease_row(manager)
    if lease.holder_run != run_id:
        return {'ok': False,
                'error': f"heartbeat from '{run_id}' but the lease "
                         f"holder is '{lease.holder_run}'"}
    lease.heartbeat_at = _now()
    _persist(manager, lease)
    return {'ok': True}


def release_lease(manager, run_id: str, token: int) -> Dict:
    check = validate_token(manager, token)
    if not check['ok']:
        return check
    lease = lease_row(manager)
    if lease.holder_run != run_id:
        return {'ok': False,
                'error': f"release from '{run_id}' but the lease "
                         f"holder is '{lease.holder_run}'"}
    lease.status = 'free'
    lease.holder_run = ''
    _persist(manager, lease)
    return {'ok': True, 'releasedEpoch': token}


def break_lease(manager, broken_by: str, reason: str,
                force: bool = False) -> Dict:
    """Explicit break: allowed when the TTL lapsed (breakable) or
    force=True (the admin knob). Always evented, never silent."""
    lease = lease_row(manager)
    if lease.status != 'held':
        return {'ok': False, 'error': 'lease is not held — nothing '
                                      'to break'}
    if not is_breakable(lease) and not force:
        age = round(_age_seconds(lease.heartbeat_at), 1)
        return {'ok': False,
                'error': f'lease is live (heartbeat {age}s ago, TTL '
                         f'{lease.ttl_seconds}s) — not breakable',
                'suggestion': {'knob': 'force',
                               'action': 'admin force-break (evented) '
                                         'or wait for TTL lapse'}}
    event = LeaseBreakEvent(
        name=f'lease-break-epoch-{lease.token}',
        broken_run=lease.holder_run, token_epoch=lease.token,
        broken_by=broken_by, reason=reason, forced=bool(force),
        at=_now(), manager=manager)
    _persist(manager, event)
    lease.status = 'free'
    lease.holder_run = ''
    _persist(manager, lease)
    return {'ok': True, 'brokenEpoch': event.token_epoch,
            'brokenRun': event.broken_run, 'forced': event.forced}
