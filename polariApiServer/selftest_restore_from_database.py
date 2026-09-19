"""
selftest_restore_from_database — THE OTHER RESTORE PATH (§66 addendum 5,
2026-09-19).

    PYTHONPATH=.:modules python3 polariApiServer/selftest_restore_from_database.py

§66e made `polariServer._restoreDefinitionInstances` MERGE instead of skip.
It left the main path — `objectTreeManagerDecorators.restoreFromDatabase` →
`_restoreTableRows` → `identifySeedDBIds` — untouched, on the belief that it
"skips by matching ids, so it looks sound". It does not skip by id, and it was
not sound. Two defects, both of them the same root cause as §66e: lazy boot
serves requests WHILE the restore walks the tree.

  1. **It crashed the admission worker.** `identifySeedDBIds` walked the LIVE
     `objectTables` dict. A request that creates a row of a class nobody had
     touched yet adds a KEY mid-walk, and python raises
     `RuntimeError: dictionary changed size during iteration` straight out of
     `restoreTables()`. Seen live on `polari-lean` on two consecutive boots —
     `[LazyBoot] islemesh FAILED: dictionary changed size during iteration`,
     then `polariapps`, which blocked `appstore` and `iso` behind it and left
     every `/api/apps/security/*` door answering 503. The same hazard sits on
     the inner loop, where an observer bumping a counter creates a SIBLING
     instance of the very class being fingerprinted.

  2. **It leaves a duplicate the merge then refused to fold.** At module
     admission `lazy_boot._admit` runs `restoreTables()` FIRST and
     `ensureDefinitionTables()` (the merge) second. The table restore has no
     name logic at all, so it happily inserts the persisted row beside a
     boot-time row of the same name; the merge then saw the persisted id
     already in `objectTables`, counted it "already restored" and moved on
     WITHOUT folding. Two rows for one subject — the §66d duplicate, arriving
     from the restore rather than from the observer. The fold now runs on that
     branch too.

What is NOT fixed here, and is deliberately left as a described hazard: the
seed FINGERPRINT itself (`identifySeedDBIds`, a >=60% property match) can
classify a persisted row that has DIVERGED from its boot-time twin — a
`confirmed` row beside a `suggested` one — as a re-created seed and drop it.
For a Definition class the merge puts it back; for a class outside
`defClassList` (`User`, `managedExecutable`, `isoSys`, every dynamic class)
nothing does. Changing a heuristic that every boot depends on is not this
slice's call. The demonstration of it lives in the scratchpad, not in the tree.

No server, no database, no network: a fake `db` answers `getAllInTable` the way
the real one does, and the REAL methods are bound to a double.
"""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'modules'))

PASSED, FAILED = [], []


def check(name, cond, detail=''):
    (PASSED if cond else FAILED).append(name if cond else f'{name} :: {detail}')


# ---- the doubles --------------------------------------------------------

COLUMNS = ['_branch_path', 'id', 'name', 'state', 'confirmed_by', 'count']


class Row:
    """A row shaped like the policy/decision rows: `name` is the dedup key,
    `state`/`confirmed_by` are a person's, `count` is an observation."""

    def __init__(self, manager=None, id='', name='', state='',
                 confirmed_by='', count=0, **_ignored):
        self.manager = manager
        self.id = id
        self.name = name
        self.state = state
        self.confirmed_by = confirmed_by
        self.count = int(count or 0)
        if manager is not None:
            manager.objectTables.setdefault(
                type(self).__name__, {})[id or name] = self


class Typing:
    def __init__(self, cls):
        self.cls = cls
        self.identifiers = ['id']

    def getCreateMethod(self):
        return self.cls

    def deserializeColumnValue(self, colName, value):
        return value


class FakeDb:
    """`onRead` is the REQUEST arriving mid-restore: the live stack's health
    probe, ct-9's traffic middleware, ct-8's converge-on-read."""

    def __init__(self, rows, onRead=None):
        self.rows = rows
        self.tables = list(rows)
        self.onRead = onRead
        self.reads = 0

    def getAllInTable(self, className):
        self.reads += 1
        if self.onRead is not None:
            self.onRead(self.reads, className)
        return COLUMNS, list(self.rows.get(className, []))


class FakeManager:
    """Only what the two restore paths touch. The real methods are bound on,
    so the code under test is the shipped code."""

    def __init__(self, db, classes):
        self.db = db
        self.objectTables = {}
        self.objectTypingDict = {name: Typing(cls)
                                 for name, cls in classes.items()}
        self.tombstoned = []
        from objectTreeManagerDecorators import managerObject
        self.identifySeedDBIds = (
            managerObject.identifySeedDBIds.__get__(self, type(self)))
        self._restoreTableRows = (
            managerObject._restoreTableRows.__get__(self, type(self)))

    def noteTreeDeletion(self, className, instanceId):
        self.tombstoned.append((className, instanceId))
        return 1


def persisted(rowId, name, state, by, count):
    return [None, rowId, name, state, by, count]


def server_with(manager):
    from polariApiServer.polariServer import polariServer
    obj = types.SimpleNamespace(manager=manager)
    for method in ('_restoreDefinitionInstances', '_mergeRestoredRows',
                   '_foldNameDuplicates', '_foldBootRow'):
        setattr(obj, method,
                getattr(polariServer, method).__get__(obj, type(obj)))
    return obj


def rows_of(manager, className):
    return list((manager.objectTables.get(className) or {}).values())


# ---- 1. the crash -------------------------------------------------------

def test_a_request_adding_a_CLASS_does_not_crash_the_restore():
    """The live failure: a request creates the first row of a class nobody
    had touched, so a KEY appears in objectTables while the fingerprint walks
    it. Before the fix this raised RuntimeError out of restoreTables() and
    failed the whole module admission."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='a', state='suggested', count=1)

    class Latecomer(Row):
        pass

    m.objectTypingDict['Latecomer'] = Typing(Latecomer)
    db.tables.append('Latecomer')
    db.rows['Latecomer'] = []
    # The request lands on the first table read — mid-walk, exactly as the
    # health probe did on polari-lean.
    db.onRead = lambda n, cls: (Latecomer(manager=m, id='req-1', name='new')
                                if n == 1 else None)
    try:
        seeds = m.identifySeedDBIds()
        crashed = ''
    except Exception as exc:                                   # noqa: BLE001
        seeds, crashed = None, f'{type(exc).__name__}: {exc}'
    check('a class created by a request mid-restore does not blow the '
          'fingerprint up', crashed == '', crashed)
    check('the walk still answered for the classes it did see',
          isinstance(seeds, dict), repr(seeds))


def test_a_request_adding_an_INSTANCE_does_not_crash_the_restore():
    """The same hazard one level in: an observer bumping a counter creates a
    sibling instance of the class being fingerprinted."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db, {'Row': Row})
    racer = Row(manager=m, id='boot-1', name='a', state='suggested', count=1)

    class Racing(Row):
        """Reading a column is where the inner loop spends its time, so that
        is where the sibling arrives."""
        _fired = False

        @property
        def state(self):
            if not Racing._fired:
                Racing._fired = True
                Row(manager=self.manager, id='req-2', name='b',
                    state='suggested', count=1)
            return self._state

        @state.setter
        def state(self, value):
            self._state = value

    racer.__class__ = Racing
    try:
        m.identifySeedDBIds()
        crashed = ''
    except Exception as exc:                                   # noqa: BLE001
        crashed = f'{type(exc).__name__}: {exc}'
    check('an instance created by a request mid-fingerprint does not blow '
          'the fingerprint up', crashed == '', crashed)


# ---- 2. what the path actually does with the persisted rows -------------

def test_table_restore_never_deletes_a_boot_time_row():
    """The path is additive: it constructs instances and sets columns on
    them. It never pops objectTables, never tombstones, never writes. So a
    boot-time row is never overwritten — it is left standing BESIDE the
    persisted one, which is the duplicate the merge has to clean up."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='a', state='suggested', count=1)
    m._restoreTableRows(['Row'])
    rows = {r.id: r for r in rows_of(m, 'Row')}
    check('the boot-time row is still there, untouched',
          'boot-1' in rows and rows['boot-1'].state == 'suggested',
          repr(sorted(rows)))
    check('nothing was tombstoned by the table restore', m.tombstoned == [],
          repr(m.tombstoned))


def test_admission_order_leaves_ONE_row_per_name():
    """`lazy_boot._admit` runs restoreTables() and THEN the merge. Run them in
    that order over a class a request already wrote during boot: the table
    restore inserts the persisted row beside the boot-time one, and the merge
    must fold the duplicate away even though the persisted id is already in
    the tree ("already restored")."""
    db = FakeDb({'Row': [persisted('db-1', 'anonymous|anonymous', 'confirmed',
                                   'sub-9', 14)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='anonymous|anonymous', state='suggested',
        confirmed_by='', count=7)
    m._restoreTableRows(['Row'])            # the path §66e did not touch
    before = len(rows_of(m, 'Row'))
    server_with(m)._restoreDefinitionInstances([Row])   # the merge
    rows = rows_of(m, 'Row')
    check('the table restore really does produce the duplicate (this is what '
          'the merge has to clean up)', before == 2, before)
    check('after the merge ONE row survives, not two', len(rows) == 1,
          repr([(r.id, r.state, r.count) for r in rows]))
    if not rows:
        return
    row = rows[0]
    check('it is the PERSISTED row, with the person\'s ruling intact',
          row.id == 'db-1' and row.state == 'confirmed'
          and row.confirmed_by == 'sub-9',
          f'{row.id}/{row.state}/{row.confirmed_by}')
    check('the boot-time observations are summed in, not thrown away',
          row.count == 21, row.count)
    check('the boot-time row is TOMBSTONED so a persist in flight cannot '
          'write it back', ('Row', 'boot-1') in m.tombstoned,
          repr(m.tombstoned))


def test_admission_order_is_idempotent():
    """The merge runs again on later passes. Nothing may be folded twice and
    no counter may be summed into itself."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 14)]})
    m = FakeManager(db, {'Row': Row})
    Row(manager=m, id='boot-1', name='a', state='suggested', count=7)
    m._restoreTableRows(['Row'])
    srv = server_with(m)
    srv._restoreDefinitionInstances([Row])
    srv._restoreDefinitionInstances([Row])
    srv._restoreDefinitionInstances([Row])
    rows = rows_of(m, 'Row')
    check('three merge passes leave one row with the count summed ONCE',
          len(rows) == 1 and rows[0].count == 21,
          repr([(r.id, r.count) for r in rows]))
    check('the boot-time row is tombstoned exactly once',
          m.tombstoned.count(('Row', 'boot-1')) == 1, repr(m.tombstoned))


def test_a_clean_boot_restores_exactly_as_before():
    """No boot-time writer: the two paths together must behave like the table
    restore always did — every row in, nothing folded, nothing tombstoned."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5),
                         persisted('db-2', 'b', 'suggested', '', 2)]})
    m = FakeManager(db, {'Row': Row})
    m._restoreTableRows(['Row'])
    server_with(m)._restoreDefinitionInstances([Row])
    rows = sorted(rows_of(m, 'Row'), key=lambda r: r.name)
    check('both persisted rows are restored with their own fields',
          [(r.id, r.name, r.state, r.count) for r in rows]
          == [('db-1', 'a', 'confirmed', 5), ('db-2', 'b', 'suggested', 2)],
          repr([(r.id, r.name, r.state, r.count) for r in rows]))
    check('nothing was tombstoned', m.tombstoned == [], repr(m.tombstoned))


def test_persist_bookkeeping_table_is_never_restored():
    """`polari_persist_state` holds "is a flush in flight", not objects. A
    restore that turned it into instances would resurrect bookkeeping as
    data."""
    db = FakeDb({'polari_persist_state': [persisted('p-1', 'flush', '', '', 0)],
                 'Row_variant': [persisted('v-1', 'v', '', '', 0)]})
    m = FakeManager(db, {'polari_persist_state': Row, 'Row_variant': Row})
    m._restoreTableRows(['polari_persist_state', 'Row_variant'])
    check('neither the persist marker nor a variant side table becomes an '
          'instance', m.objectTables == {}, repr(m.objectTables))


def main():
    for fn in (test_a_request_adding_a_CLASS_does_not_crash_the_restore,
               test_a_request_adding_an_INSTANCE_does_not_crash_the_restore,
               test_table_restore_never_deletes_a_boot_time_row,
               test_admission_order_leaves_ONE_row_per_name,
               test_admission_order_is_idempotent,
               test_a_clean_boot_restores_exactly_as_before,
               test_persist_bookkeeping_table_is_never_restored):
        try:
            fn()
        except Exception as exc:                               # noqa: BLE001
            FAILED.append(
                f'{fn.__name__} BLEW UP :: {type(exc).__name__}: {exc}')
    for line in FAILED:
        print('FAIL', line)
    total = len(PASSED) + len(FAILED)
    print(f'selftest_restore_from_database: {len(PASSED)}/{total}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
