"""selftest_persist_before_restore — THE PERSIST THAT BEAT THE RESTORE
(§66 addendum 6, 2026-09-19).

    PYTHONPATH=.:modules python3 polariApiServer/selftest_persist_before_restore.py

The live defect (round-5 live proof on `polari-lean`, reproduced twice). The DB
held TWO `InboundPolicy` rows at shutdown, both `confirmed` by an administrator.
The next boot logged

    [DB] Restoring 1 instances of InboundPolicy
    [DefRestore] InboundPolicy: merged 0 persisted rows, 0 boot-time rows folded,
                 1 already restored

and the one row that came back was THIS boot's `suggested` row with THIS boot's
count. `OutboundPolicy`, `SecurityDecision`, `PermissionObservation` and
`ObservationSession` all survived the very same restart.

**The mechanism, and it is not ct-9's.** `persistTree` is DELETE+REPLACE per
class: it rewrites a table from whatever `objectTables` holds. The swarm's
anonymous health probe hits `/api/health` seconds into a boot; ct-9's inbound
middleware writes one `suggested` row and schedules the 3-second debounce
(`persist_debounce.schedule_persist`); that flush lands BEFORE the security
module's admission (`lazy_boot._admit`: `restoreTables()` then
`ensureDefinitionTables()`) has read the table. So a table with two rows on disk
is replaced by one boot-time row, and the restore that follows finds nothing to
restore and nothing to merge. §66e taught the RESTORE to run beside an observer;
nothing had told the PERSIST to wait for the restore.

`OutboundPolicy` differs only in timing: nothing goes through the outbound
wrapper until an authenticated request reaches Keycloak, which is after
admission. Same class family, same exemption, same merge — the hazard is the
write ordering, not the class.

**The fix.** The manager now knows which classes it has read back
(`noteClassRestored`, set by both restore paths) and `persistTree` HOLDS BACK
any class whose DB table still holds rows this process has never read. The
bookkeeping arms only on a warm boot (`restoreFromDatabase`), so a fresh
database and every manager double behave exactly as before.

A REAL `managerObject` with a REAL `managedDatabase` over a temp sqlite file:
every method under test is the shipped one, and "the table on disk" is read back
with plain sqlite so no double can flatter the result.
"""

import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from objectTreeManagerDecorators import managerObject          # noqa: E402
from polariDBmanagement.managedDB import managedDatabase       # noqa: E402
from polariDataTyping.polyTyping import polyTypedObject        # noqa: E402

PASS = FAIL = 0

COLUMNS = ('id', 'name', 'state', 'confirmed_by', 'count')


def check(label, condition, extra=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label} {extra}')


class NoCache:
    """The restore reads a table and the persist rewrites it in the same
    process — a cached reading would hide exactly the bug under test."""

    def getTable(self, *a):
        return None

    def setTable(self, *a):
        pass

    def invalidateTable(self, *a):
        pass


class treeObject:                                    # noqa: N801
    """Named exactly `treeObject`: `getInstanceIdentifiers` validates an
    instance by the NAME of its direct base class."""

    def __init__(self, manager=None, id='', name='', state='',
                 confirmed_by='', count=0, **_ignored):
        self.manager = manager
        self.id = id
        self.name = name
        self.state = state
        self.confirmed_by = confirmed_by
        self.count = int(count or 0)
        # what `treeObjectInit` does for a real row: a constructed instance
        # registers itself, which is how the restore path gets its rows in.
        if manager is not None:
            manager.objectTables.setdefault(
                type(self).__name__, {})[id or name] = self


class InboundPolicy(treeObject):
    """The ct-9 row: `name` is the dedup key, `state`/`confirmed_by` are a
    person's ruling, `count` is the observation."""


class Typing:
    """Only what the two restore paths and the serializer ask of a typing
    object. Bound onto a real polyTypedObject so the persist path is real."""

    def __init__(self, className, cls):
        self.className = className
        self.cls = cls
        self.identifiers = ['id']

    def getCreateMethod(self):
        return self.cls

    def deserializeColumnValue(self, colName, value):
        return value


def _instance(mgr, className, **fields):
    row = InboundPolicy(manager=mgr, **fields)
    mgr.objectTables.setdefault(className, {})[row.id] = row
    return row


def _manager(tmpdir, dbname, classes=('InboundPolicy',)):
    mgr = managerObject.__new__(managerObject)
    typing = {}
    for className in classes:
        typing[className] = Typing(className, InboundPolicy)
    pt = polyTypedObject.__new__(polyTypedObject)
    pt.__dict__.update({'className': 'managerObject', 'manager': mgr,
                        'identifiers': ['id'], 'polyTypedVars': [],
                        'polyTypedVarsDict': {}})
    typing['managerObject'] = pt
    mgr.__dict__.update({
        'objectTables': {c: {} for c in classes},
        'objectTyping': list(typing.values()),
        'objectTypingDict': typing,
        'objectTree': None, 'db': None, 'id': 'mgr', 'branch': None,
        'manager': None, 'idList': [], 'managedFiles': [],
    })
    db = managedDatabase.__new__(managedDatabase)
    db.__dict__.update({'name': dbname, 'Path': tmpdir, 'isRemote': False,
                        'tables': list(classes), 'manager': mgr,
                        '_instanceScope': ''})
    path = os.path.join(tmpdir, dbname + '.db')
    conn = sqlite3.connect(path)
    for className in classes:
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{className}" '
                     '(id TEXT PRIMARY KEY, name TEXT, state TEXT, '
                     'confirmed_by TEXT, count INTEGER, _branch_path TEXT)')
    conn.commit()
    conn.close()
    mgr.db = db
    return mgr, db, path


def _persist(path, className, rows):
    """What the PREVIOUS process left on disk."""
    conn = sqlite3.connect(path)
    for row in rows:
        conn.execute(f'INSERT OR REPLACE INTO "{className}" '
                     '(id, name, state, confirmed_by, count) '
                     'VALUES (?,?,?,?,?)', row)
    conn.commit()
    conn.close()


def _on_disk(path, className):
    conn = sqlite3.connect(path)
    got = sorted(conn.execute(
        f'SELECT id, name, state, confirmed_by, count FROM "{className}"'))
    conn.close()
    return got


def _shutdown_rows():
    """The two rows the live DB held at shutdown, both ruled on by
    demo-admin's `sub` — the ones the next boot lost."""
    return [('db-1', 'anonymous|anonymous', 'confirmed', 'sub-5cacba59', 43),
            ('db-2', 'origin|https://frontend.example', 'confirmed',
             'sub-5cacba59', 5)]


def _warm_boot(tmpdir, dbname):
    """A manager that has just opened an EXISTING database whose
    `InboundPolicy` table was DEFERRED to module admission (lazy boot), with
    the boot-time row ct-9 writes from the swarm's first health probe already
    in memory. Exactly the live shape."""
    mgr, db, path = _manager(tmpdir, dbname)
    _persist(path, 'InboundPolicy', _shutdown_rows())
    mgr.armRestoreTracking()            # what restoreFromDatabase does
    _instance(mgr, 'InboundPolicy', id='boot-1', name='anonymous|anonymous',
              state='suggested', confirmed_by='', count=1)
    return mgr, db, path


# ---- 1. the defect, reproduced -------------------------------------------

def test_the_flush_does_not_overwrite_an_unrestored_table(tmpdir):
    print('[the live defect: a debounce persist during lazy boot]')
    mgr, _db, path = _warm_boot(tmpdir, 'race')
    pending = mgr.classesPendingRestore(['InboundPolicy'])
    check('the manager knows this class is still owed a restore',
          pending == {'InboundPolicy'}, repr(pending))
    mgr.persistTree()
    on_disk = _on_disk(path, 'InboundPolicy')
    check('the two CONFIRMED rows are still on disk after the flush '
          '(before the fix this table held one `suggested` row)',
          [r[0] for r in on_disk] == ['db-1', 'db-2'], repr(on_disk))
    check('and both still carry the person who ruled on them',
          all(r[3] == 'sub-5cacba59' and r[2] == 'confirmed'
              for r in on_disk), repr(on_disk))
    check('the boot-time observation is not thrown away either — it stays in '
          'memory for the restore to fold',
          'boot-1' in mgr.objectTables['InboundPolicy'],
          repr(sorted(mgr.objectTables['InboundPolicy'])))


def test_the_restore_then_sees_everything_the_db_held(tmpdir):
    print('[and the restore that follows finds both rows, not one]')
    mgr, _db, path = _warm_boot(tmpdir, 'restore')
    mgr.persistTree()
    mgr._restoreTableRows(['InboundPolicy'])
    rows = mgr.objectTables['InboundPolicy']
    check('the table restore loads BOTH persisted rows',
          {'db-1', 'db-2'} <= set(rows), repr(sorted(rows)))
    confirmed = [r for r in rows.values() if r.state == 'confirmed']
    check('the administrator\'s two rulings are back in the tree',
          len(confirmed) == 2,
          repr([(r.id, r.state) for r in rows.values()]))
    check('the count on the restored row is the PERSISTED one (43), not this '
          'boot\'s probe count',
          rows['db-1'].count == 43, rows['db-1'].count)


def test_the_hold_is_released_by_the_restore(tmpdir):
    print('[the hold is a wait, not a refusal]')
    mgr, _db, path = _warm_boot(tmpdir, 'release')
    mgr._restoreTableRows(['InboundPolicy'])
    check('once the class is restored nothing is pending any more',
          mgr.classesPendingRestore(['InboundPolicy']) == set(),
          repr(mgr.classesPendingRestore(['InboundPolicy'])))
    mgr.persistTree()
    on_disk = _on_disk(path, 'InboundPolicy')
    check('so the very next flush writes the whole tree, boot-time row '
          'included', [r[0] for r in on_disk] == ['boot-1', 'db-1', 'db-2'],
          repr(on_disk))
    check('the rulings are written back exactly as they were read',
          sorted(r for r in on_disk if r[2] == 'confirmed')
          == sorted(_shutdown_rows()[:1] + _shutdown_rows()[1:]),
          repr(on_disk))


def test_the_whole_live_sequence(tmpdir):
    print('[the live sequence end to end: confirm, restart, probe, flush, '
          'restore, flush]')
    mgr, _db, path = _warm_boot(tmpdir, 'sequence')
    for _probe in range(4):             # the health probe keeps arriving
        mgr.objectTables['InboundPolicy']['boot-1'].count += 1
        mgr.persistTree()
    mgr._restoreTableRows(['InboundPolicy'])
    mgr.persistTree()
    on_disk = {r[1]: r for r in _on_disk(path, 'InboundPolicy')}
    check('the confirmed `anonymous|anonymous` ruling survived the restart',
          on_disk.get('anonymous|anonymous', ('', '', '', '', 0))[2]
          == 'confirmed', repr(on_disk.get('anonymous|anonymous')))
    check('the second inbound row was not deleted outright '
          '(the live proof lost it entirely)',
          'origin|https://frontend.example' in on_disk, repr(sorted(on_disk)))


# ---- 2. the bounds -------------------------------------------------------

def test_a_fresh_database_is_never_held_back(tmpdir):
    print('[the bound: a fresh instance persists exactly as it always did]')
    mgr, _db, path = _manager(tmpdir, 'fresh')
    _instance(mgr, 'InboundPolicy', id='new-1', name='anonymous|anonymous',
              state='suggested', count=1)
    check('tracking is not armed on a database nobody restored',
          not mgr.restoreTrackingArmed())
    check('so nothing is pending, whatever the table holds',
          mgr.classesPendingRestore(['InboundPolicy']) == set())
    mgr.persistTree()
    check('and the row reaches the database on the first flush',
          [r[0] for r in _on_disk(path, 'InboundPolicy')] == ['new-1'],
          repr(_on_disk(path, 'InboundPolicy')))


def test_an_empty_table_is_not_held_back(tmpdir):
    print('[the bound: an empty table has nothing to lose]')
    mgr, _db, path = _manager(tmpdir, 'empty')
    mgr.armRestoreTracking()
    _instance(mgr, 'InboundPolicy', id='boot-1', name='anonymous|anonymous',
              state='suggested', count=1)
    check('an unrestored class whose table is EMPTY is not pending',
          mgr.classesPendingRestore(['InboundPolicy']) == set())
    check('and it is marked restored, so the check is paid for once',
          'InboundPolicy' in mgr.restoredClasses())
    mgr.persistTree()
    check('the boot-time row persists normally',
          [r[0] for r in _on_disk(path, 'InboundPolicy')] == ['boot-1'],
          repr(_on_disk(path, 'InboundPolicy')))


def test_an_unreadable_table_is_held_back(tmpdir):
    print('[the bound: not knowing what is on disk is not a licence to '
          'replace it]')
    mgr, _db, path = _manager(tmpdir, 'unreadable')
    mgr.armRestoreTracking()
    _instance(mgr, 'InboundPolicy', id='boot-1', name='anonymous|anonymous',
              state='suggested', count=1)
    conn = sqlite3.connect(path)
    conn.execute('DROP TABLE "InboundPolicy"')     # the table db.tables claims
    conn.commit()
    conn.close()
    check('a table that cannot be read stays pending',
          mgr.classesPendingRestore(['InboundPolicy']) == {'InboundPolicy'})


def test_a_class_with_no_table_at_all_is_not_pending(tmpdir):
    print('[the bound: a class the database has never heard of]')
    mgr, _db, _path = _manager(tmpdir, 'notable')
    mgr.armRestoreTracking()
    mgr.objectTables['Latecomer'] = {}
    check('a class with no DB table is not pending — there is nothing to read '
          'back', mgr.classesPendingRestore(['Latecomer']) == set())
    check('and it is marked restored rather than re-checked every flush',
          'Latecomer' in mgr.restoredClasses())


def test_the_restore_paths_mark_their_decisions(tmpdir):
    print('[what counts as "restored": a decision, not only a load]')
    mgr, db, path = _manager(tmpdir, 'decisions')
    mgr.armRestoreTracking()
    _persist(path, 'InboundPolicy', _shutdown_rows())
    db.tables.append('Orphan')                     # a table with no class
    mgr._restoreTableRows(['InboundPolicy', 'Orphan'])
    check('a table that was read is restored',
          'InboundPolicy' in mgr.restoredClasses())
    check('a table with no known class is NOT marked restored — its rows are '
          'read later by the definition merge',
          'Orphan' not in mgr.restoredClasses(),
          repr(sorted(mgr.restoredClasses())))


def test_a_pending_class_does_not_block_the_others(tmpdir):
    print('[one held-back class never stalls the rest of the tree]')
    mgr, db, path = _manager(tmpdir, 'others',
                             classes=('InboundPolicy', 'OutboundPolicy'))
    mgr.armRestoreTracking()
    _persist(path, 'InboundPolicy', _shutdown_rows())
    _instance(mgr, 'InboundPolicy', id='boot-1', name='anonymous|anonymous',
              state='suggested', count=1)
    out = InboundPolicy(manager=mgr, id='out-1', name='keycloak|Polari|rest',
                        state='confirmed', confirmed_by='sub-5cacba59',
                        count=12)
    mgr.objectTables['OutboundPolicy']['out-1'] = out
    mgr.persistTree()
    check('the unrestored class is held back',
          [r[0] for r in _on_disk(path, 'InboundPolicy')] == ['db-1', 'db-2'],
          repr(_on_disk(path, 'InboundPolicy')))
    check('the class with nothing persisted is written as usual',
          [r[0] for r in _on_disk(path, 'OutboundPolicy')] == ['out-1'],
          repr(_on_disk(path, 'OutboundPolicy')))


def test_tombstones_are_not_cleared_for_a_held_back_class(tmpdir):
    print('[a held-back class keeps its tombstones for the flush that does '
          'write it]')
    mgr, _db, path = _warm_boot(tmpdir, 'tombs')
    mgr.objectTables['InboundPolicy'].pop('boot-1')
    mgr.noteTreeDeletion('InboundPolicy', 'boot-1')
    mgr.persistTree()
    check('the tombstone survives a flush that never rewrote the table',
          ('InboundPolicy', 'boot-1') in mgr.currentTombstones(),
          repr(mgr.currentTombstones()))


def main():
    tests = (test_the_flush_does_not_overwrite_an_unrestored_table,
             test_the_restore_then_sees_everything_the_db_held,
             test_the_hold_is_released_by_the_restore,
             test_the_whole_live_sequence,
             test_a_fresh_database_is_never_held_back,
             test_an_empty_table_is_not_held_back,
             test_an_unreadable_table_is_held_back,
             test_a_class_with_no_table_at_all_is_not_pending,
             test_the_restore_paths_mark_their_decisions,
             test_a_pending_class_does_not_block_the_others,
             test_tombstones_are_not_cleared_for_a_held_back_class)
    managedDatabase.cache = property(lambda self: NoCache())
    with tempfile.TemporaryDirectory() as tmpdir:
        for fn in tests:
            try:
                fn(tmpdir)
            except Exception as exc:                           # noqa: BLE001
                global FAIL
                FAIL += 1
                print(f'  FAIL: {fn.__name__} BLEW UP :: '
                      f'{type(exc).__name__}: {exc}')
                import traceback
                traceback.print_exc()
    print(f'\nselftest_persist_before_restore: {PASS}/{PASS + FAIL}')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
