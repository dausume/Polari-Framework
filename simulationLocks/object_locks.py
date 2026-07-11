"""
@module simulationLocks.object_locks

The run's working set (xsim-2, Dustin 2026-07-10): on top of the global
lease, a run holds WRITE locks on its declared read+write sets for its
whole duration, plus auto-locks on every object it generates.

- Selector granularity REUSES the overlap advisor's vocabulary —
  id | name | range | class-wide — so a 100k-object sweep is ONE
  class-wide/range lock row, not 100k rows (the advisor's write-set
  manifest IS the lock manifest; the advisor itself is xsim-5).
- Write locks only: anyone may READ; non-run writes get an honest
  refusal naming the run + queue position — refusal, not blocking, so
  under single-writer NO deadlock is possible anywhere.
- Undeclared objects touched mid-run get lazy escalation at first
  touch (tagged — feeds the advisor's accuracy back).
- Run FAILURE quarantines generated objects ('orphaned-by-run', an
  explicit cleanup/keep knob) — never silently deleted or adopted.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from objectTreeDecorators import treeObject, treeObjectInit

SELECTOR_KINDS = ('id', 'name', 'range', 'class-wide')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ObjectLockEntry(treeObject):
    """(authority, className, selector) → run + fencing epoch."""

    @treeObjectInit
    def __init__(self, name: str = '', run_id: str = '',
                 token_epoch: int = 0, authority: str = 'local',
                 class_name: str = '', selector_kind: str = 'id',
                 selector_value: str = '', tag: str = 'declared',
                 status: str = 'held', created_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.run_id = run_id
        self.token_epoch = token_epoch
        self.authority = authority
        self.class_name = class_name
        self.selector_kind = selector_kind     # SELECTOR_KINDS
        self.selector_value = selector_value   # id/name str; range JSON
        self.tag = tag             # declared | generated | escalated
        self.status = status       # held | released | quarantined
        self.created_at = created_at
        self.notes = notes


class LockBreakEvent(treeObject):
    """Admin lock break — evented, run notified via its blocked
    state (the run-side hook lands with the runner wiring)."""

    @treeObjectInit
    def __init__(self, name: str = '', lock_name: str = '',
                 run_id: str = '', broken_by: str = '',
                 reason: str = '', at: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.lock_name = lock_name
        self.run_id = run_id
        self.broken_by = broken_by
        self.reason = reason
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


def held_locks(manager) -> List[ObjectLockEntry]:
    return [lock for lock in _rows(manager, 'ObjectLockEntry')
            if getattr(lock, 'status', '') in ('held', 'quarantined')]


def _range_bounds(selector_value: str):
    try:
        bounds = json.loads(selector_value or '')
        return str(bounds['lo']), str(bounds['hi'])
    except (TypeError, ValueError, KeyError):
        return None


def selector_matches(lock, obj_id: str = '', obj_name: str = '') -> bool:
    """Does this lock cover the given object? Conservative: an
    undecidable comparison counts as covered (protects the run)."""
    kind = lock.selector_kind
    if kind == 'class-wide':
        return True
    if kind == 'id':
        return bool(obj_id) and lock.selector_value == obj_id
    if kind == 'name':
        return bool(obj_name) and lock.selector_value == obj_name
    if kind == 'range':
        bounds = _range_bounds(lock.selector_value)
        if bounds is None:
            return True     # unparseable range: conservative
        probe = obj_name or obj_id
        return bool(probe) and bounds[0] <= probe <= bounds[1]
    return True


def selectors_overlap(a_kind: str, a_value: str,
                      b_kind: str, b_value: str) -> bool:
    """Can the two selectors touch a common object? Conservative:
    incomparable kinds (id vs name) → True (cannot prove disjoint)."""
    if 'class-wide' in (a_kind, b_kind):
        return True
    if a_kind == b_kind and a_kind in ('id', 'name'):
        return a_value == b_value
    if a_kind == 'range' and b_kind == 'range':
        a_bounds, b_bounds = _range_bounds(a_value), _range_bounds(b_value)
        if a_bounds is None or b_bounds is None:
            return True
        return a_bounds[0] <= b_bounds[1] and b_bounds[0] <= a_bounds[1]
    if 'range' in (a_kind, b_kind):
        bounds = _range_bounds(a_value if a_kind == 'range' else b_value)
        probe = b_value if a_kind == 'range' else a_value
        if bounds is None:
            return True
        return bounds[0] <= probe <= bounds[1]
    return True     # id vs name: cannot prove disjoint


def _normalize_manifest_item(item: Dict) -> Optional[Dict]:
    class_name = str(item.get('className', '') or '')
    selector = item.get('selector') or {}
    kind = str(selector.get('kind', '') or '')
    if not class_name or kind not in SELECTOR_KINDS:
        return None
    return {'authority': str(item.get('authority', 'local') or 'local'),
            'className': class_name, 'kind': kind,
            'value': str(selector.get('value', '') or '')
            if kind != 'range' else json.dumps(selector.get('value'))
            if not isinstance(selector.get('value'), str)
            else selector.get('value')}


def acquire_manifest(manager, run_id: str, token_epoch: int,
                     manifest: List[Dict]) -> Dict:
    """Lock the run's declared working set at run start. Refuses on
    overlap with another run's held locks, naming both selectors —
    under single-writer this only trips against quarantined leftovers
    or an admin-frozen set, and the evidence names the culprit."""
    normalized = []
    for item in manifest or []:
        norm = _normalize_manifest_item(item)
        if norm is None:
            return {'ok': False,
                    'error': f'malformed manifest item: {item}',
                    'suggestion': {
                        'knob': 'manifest.selector.kind',
                        'action': f'one of {SELECTOR_KINDS}'}}
        normalized.append(norm)
    for norm in normalized:
        for lock in held_locks(manager):
            if lock.run_id == run_id:
                continue
            if (lock.class_name == norm['className']
                    and lock.authority == norm['authority']
                    and selectors_overlap(
                        lock.selector_kind, lock.selector_value,
                        norm['kind'], norm['value'])):
                return {'ok': False,
                        'error': f"lock overlap on {norm['className']}: "
                                 f"run '{lock.run_id}' holds "
                                 f'{lock.selector_kind}='
                                 f'{lock.selector_value} ({lock.status})',
                        'evidence': {'requested': norm,
                                     'held': lock.name},
                        'suggestion': {
                            'knob': 'break_lock / cleanup knob',
                            'action': 'release the quarantined set or '
                                      'wait for the holding run'}}
    entries = []
    for i, norm in enumerate(normalized):
        entry = ObjectLockEntry(
            name=f'{run_id}-lock-{i}-{norm["className"]}',
            run_id=run_id, token_epoch=token_epoch,
            authority=norm['authority'], class_name=norm['className'],
            selector_kind=norm['kind'], selector_value=norm['value'],
            tag='declared', status='held', created_at=_now(),
            manager=manager)
        _persist(manager, entry)
        entries.append(entry.name)
    return {'ok': True, 'locks': entries}


def lock_generated(manager, run_id: str, token_epoch: int,
                   class_name: str, obj_id: str) -> Dict:
    """Auto-lock a newly generated object, tagged with the run — the
    tag is the retention/cleanup lever ([[resource-aware-simulation]])."""
    entry = ObjectLockEntry(
        name=f'{run_id}-gen-{class_name}-{obj_id}',
        run_id=run_id, token_epoch=token_epoch, class_name=class_name,
        selector_kind='id', selector_value=str(obj_id), tag='generated',
        status='held', created_at=_now(), manager=manager)
    _persist(manager, entry)
    return {'ok': True, 'lock': entry.name}


def escalate_lock(manager, run_id: str, token_epoch: int,
                  class_name: str, obj_id: str = '',
                  obj_name: str = '') -> Dict:
    """Lazy escalation on an undeclared touch — noted so the overlap
    advisor (xsim-5) can learn the declared-set gap."""
    kind, value = ('id', obj_id) if obj_id else ('name', obj_name)
    entry = ObjectLockEntry(
        name=f'{run_id}-esc-{class_name}-{value}',
        run_id=run_id, token_epoch=token_epoch, class_name=class_name,
        selector_kind=kind, selector_value=str(value), tag='escalated',
        status='held', created_at=_now(),
        notes='undeclared touch — add to the definition\'s write set',
        manager=manager)
    _persist(manager, entry)
    return {'ok': True, 'lock': entry.name,
            'note': 'undeclared-touch (advisor evidence)'}


class _SweptLock:
    """A lock row read from the SHARED lock table (another instance's
    scope) — same duck shape as ObjectLockEntry for matching."""

    def __init__(self, fields: Dict):
        self.name = fields.get('name', '')
        self.run_id = fields.get('run_id', '')
        self.class_name = fields.get('class_name', '')
        self.selector_kind = fields.get('selector_kind', '')
        self.selector_value = fields.get('selector_value', '')
        self.status = fields.get('status', '')
        self.tag = fields.get('tag', '')


def _shared_locks(manager) -> List:
    """xsim-4: shared-DB instances share ONE lock table — the sweep
    that lets instance b refuse writes to rows locked by instance a's
    run. Honest no-op when sharing is off/unreadable."""
    db = getattr(manager, 'db', None)
    if db is None or not hasattr(db, 'getAllInTableAllScopes'):
        return []
    try:
        table = db.getAllInTableAllScopes('ObjectLockEntry')
    except Exception:
        return []
    if not (isinstance(table, dict) and table.get('ok')):
        return []
    local_names = {lock.name for lock in held_locks(manager)}
    swept = []
    for row in table.get('rows') or []:
        fields = dict(zip(table.get('columns') or [], row))
        lock = _SweptLock(fields)
        if lock.status in ('held', 'quarantined') \
                and lock.name not in local_names:
            swept.append(lock)
    return swept


def check_write(manager, class_name: str, obj_id: str = '',
                obj_name: str = '', run_id: str = '') -> Dict:
    """The enforcement seam (CRUDE PUT/POST/DELETE + saveInstanceInDB
    callers): allowed unless a lock held by ANOTHER run covers the
    object — including locks in the SHARED lock table placed by a
    peer instance's run. Refusals name the run and queue position."""
    for lock in held_locks(manager) + _shared_locks(manager):
        if lock.class_name != class_name or lock.run_id == run_id:
            continue
        if selector_matches(lock, obj_id=obj_id, obj_name=obj_name):
            position = None
            try:
                from simulationLocks.sim_queue import queue_position
                position = queue_position(manager, lock.run_id)
            except Exception:
                pass
            quarantined = lock.status == 'quarantined'
            return {'allowed': False,
                    'lockedBy': lock.run_id,
                    'queuePosition': position,
                    'quarantined': quarantined,
                    'error': f"{class_name} "
                             f"'{obj_name or obj_id}' is "
                             + (f"quarantined by failed run "
                                f"'{lock.run_id}' (orphaned-by-run)"
                                if quarantined else
                                f"write-locked by run '{lock.run_id}'"
                                + (f' (queue position {position})'
                                   if position is not None else '')),
                    'suggestion': {
                        'knob': 'cleanup knob (quarantined locks)'
                                if quarantined else 'the run / queue',
                        'action': 'keep or clean the orphaned set'
                                  if quarantined else
                                  'reads stay live; retry the write '
                                  'after the run releases'}}
    return {'allowed': True}


def release_for_run(manager, run_id: str, outcome: str = 'done') -> Dict:
    """Completion releases the whole set atomically with the lease;
    FAILURE quarantines generated objects instead — never silently
    deleted, never silently adopted."""
    released, quarantined = [], []
    for lock in _rows(manager, 'ObjectLockEntry'):
        if lock.run_id != run_id or lock.status != 'held':
            continue
        if outcome == 'failed' and lock.tag == 'generated':
            lock.status = 'quarantined'
            lock.notes = ('orphaned-by-run — keep or clean via the '
                          'cleanup knob')
            quarantined.append(lock.name)
        else:
            lock.status = 'released'
            released.append(lock.name)
        _persist(manager, lock)
    return {'ok': True, 'released': released,
            'quarantined': quarantined}


def break_lock(manager, lock_name: str, broken_by: str,
               reason: str) -> Dict:
    """Admin break knob for a single lock — always evented."""
    for lock in _rows(manager, 'ObjectLockEntry'):
        if lock.name == lock_name and lock.status in ('held',
                                                      'quarantined'):
            event = LockBreakEvent(
                name=f'lock-break-{lock_name}', lock_name=lock_name,
                run_id=lock.run_id, broken_by=broken_by, reason=reason,
                at=_now(), manager=manager)
            _persist(manager, event)
            lock.status = 'released'
            _persist(manager, lock)
            return {'ok': True, 'broken': lock_name,
                    'run': lock.run_id}
    return {'ok': False,
            'error': f"no held/quarantined lock named '{lock_name}'"}
