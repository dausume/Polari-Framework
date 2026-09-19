"""
selftest_restore_merge — THE RESTORE MERGE (§66e, 2026-09-19).

    PYTHONPATH=.:modules python3 polariApiServer/selftest_restore_merge.py

`polariServer._restoreDefinitionInstances` used to SKIP any class that already
had one instance in `objectTables`:

    [DefRestore] InboundPolicy: 1 instances already in objectTables, skipping

Lazy boot serves requests WHILE that runs, so one boot-time write — the ct-9
traffic middleware on the first request, ct-8's converge-on-read, any observer
at all — made every persisted row of that class unreachable. The rows were not
corrupted; they were simply never loaded, and the next persist wrote the
half-booted tree over them. Live on `polari-lean` 2026-09-19 a person's
`confirmed` traffic ruling vanished across a restart while the database still
held it. This is a CORE hazard: it applies to every class an observer can
touch during boot, not to the traffic rows alone.

So restore MERGES. The rule, and this file is the proof of it:

  * every persisted row is inserted;
  * a row already in memory with the SAME `id` IS that persisted row (an
    earlier pass restored it) and is left alone — which is what keeps repeat
    passes idempotent rather than doubling every counter;
  * a row in memory with the same `name` and a DIFFERENT id is a boot-time
    row: the persisted row wins every field, absorbs the boot-time row's
    count-like fields (`count`, `traces_opened`, `edges_written`,
    `journal_written`, `dropped`), and the boot-time row is deleted through
    `noteTreeDeletion` so a persist in flight cannot write it back;
  * a boot-time row whose name matches nothing in the database SURVIVES — it
    is a real observation nobody had persisted yet.

No server, no database, no network: the merge is driven with a fake `db`
returning rows as `getAllInTable` does, a manager double that records its
tombstones, and a plain row class.
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
    """A row class shaped like the policy/observation rows: a `name` that is
    the dedup key, fields a person owns, and a counter."""

    def __init__(self, manager=None, id='', name='', state='', confirmed_by='',
                 count=0, **_ignored):
        self.manager = manager
        self.id = id
        self.name = name
        self.state = state
        self.confirmed_by = confirmed_by
        self.count = int(count or 0)
        if manager is not None:
            manager.objectTables.setdefault(type(self).__name__, {})[id or name] = self


class Other(Row):
    pass


class FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.tables = list(rows)

    def getAllInTable(self, className):
        return COLUMNS, list(self.rows.get(className, []))


class FakeManager:
    def __init__(self, db):
        self.db = db
        self.objectTables = {}
        self.tombstoned = []

    def noteTreeDeletion(self, className, instanceId):
        self.tombstoned.append((className, instanceId))
        return 1


def persisted(rowId, name, state, by, count):
    return [None, rowId, name, state, by, count]


def server_with(manager):
    """A polariServer whose __init__ we never run — the merge only touches
    `self.manager`, so binding the real methods to a bare object proves the
    real code rather than a copy of it."""
    from polariApiServer.polariServer import polariServer
    obj = types.SimpleNamespace(manager=manager)
    obj._restoreDefinitionInstances = (
        polariServer._restoreDefinitionInstances.__get__(obj, type(obj)))
    obj._mergeRestoredRows = (
        polariServer._mergeRestoredRows.__get__(obj, type(obj)))
    obj._foldBootRow = polariServer._foldBootRow.__get__(obj, type(obj))
    return obj


def rows_of(manager, className):
    return list((manager.objectTables.get(className) or {}).values())


# ---- the checks ---------------------------------------------------------

def test_boot_row_folded_into_persisted():
    """The live case: a person's ruling is in the DB, a boot-time row of the
    same name is in memory, restore runs."""
    db = FakeDb({'Row': [persisted('db-1', 'anonymous|anonymous', 'confirmed',
                                   'sub-9', 14)]})
    m = FakeManager(db)
    Row(manager=m, id='boot-1', name='anonymous|anonymous', state='suggested',
        confirmed_by='', count=7)
    server_with(m)._restoreDefinitionInstances([Row])
    rows = rows_of(m, 'Row')
    check('one row survives, not two', len(rows) == 1,
          repr([(r.id, r.state, r.count) for r in rows]))
    if not rows:
        return
    row = rows[0]
    check('the PERSISTED row is the one that survives (its id)',
          row.id == 'db-1', row.id)
    check('the person\'s fields come from the database, never from the '
          'boot-time guess',
          row.state == 'confirmed' and row.confirmed_by == 'sub-9',
          f'{row.state}/{row.confirmed_by}')
    check('the counts are SUMMED — both halves really were observed',
          row.count == 21, row.count)
    check('the boot-time row is TOMBSTONED, so a persist in flight cannot '
          'write it back', ('Row', 'boot-1') in m.tombstoned,
          repr(m.tombstoned))


def test_new_boot_row_survives():
    """A boot-time observation nobody had persisted is a real observation."""
    db = FakeDb({'Row': [persisted('db-1', 'known', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db)
    Row(manager=m, id='boot-2', name='brand-new', state='suggested', count=3)
    server_with(m)._restoreDefinitionInstances([Row])
    byName = {r.name: r for r in rows_of(m, 'Row')}
    check('the restored row and the NEW boot-time row both exist',
          sorted(byName) == ['brand-new', 'known'], sorted(byName))
    check('the new boot-time row is untouched (nothing summed into it)',
          byName.get('brand-new') is not None
          and byName['brand-new'].count == 3 and byName['brand-new'].id == 'boot-2',
          repr([(r.id, r.name, r.count) for r in rows_of(m, 'Row')]))
    check('nothing was tombstoned', m.tombstoned == [], repr(m.tombstoned))


def test_plain_restore_unchanged():
    """A class nothing wrote during boot restores exactly as it always did."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5),
                         persisted('db-2', 'b', 'suggested', '', 2)]})
    m = FakeManager(db)
    server_with(m)._restoreDefinitionInstances([Row])
    rows = sorted(rows_of(m, 'Row'), key=lambda r: r.name)
    check('every persisted row is restored, with its own fields',
          [(r.name, r.state, r.count) for r in rows]
          == [('a', 'confirmed', 5), ('b', 'suggested', 2)],
          repr([(r.name, r.state, r.count) for r in rows]))
    check('nothing was tombstoned', m.tombstoned == [], repr(m.tombstoned))


def test_repeat_pass_is_idempotent():
    """`ensureDefinitionTables` runs several times over a lazy boot, so the
    merge runs several times too. A second pass must not re-insert the rows
    it restored on the first, and must not sum a counter into itself."""
    db = FakeDb({'Row': [persisted('db-1', 'a', 'confirmed', 'sub-9', 5)]})
    m = FakeManager(db)
    srv = server_with(m)
    srv._restoreDefinitionInstances([Row])
    srv._restoreDefinitionInstances([Row])
    srv._restoreDefinitionInstances([Row])
    rows = rows_of(m, 'Row')
    check('three passes leave ONE row with its original count (the id is how '
          '"already restored" is told from "a different row")',
          len(rows) == 1 and rows[0].count == 5 and rows[0].state == 'confirmed',
          repr([(r.id, r.count) for r in rows]))
    check('nothing was tombstoned by the repeat passes', m.tombstoned == [],
          repr(m.tombstoned))


def test_empty_and_missing_tables():
    db = FakeDb({'Row': []})
    m = FakeManager(db)
    Row(manager=m, id='boot-3', name='only-boot', state='suggested', count=4)
    server_with(m)._restoreDefinitionInstances([Row, Other])
    check('an empty DB table leaves the boot-time rows alone',
          [r.id for r in rows_of(m, 'Row')] == ['boot-3'],
          repr(rows_of(m, 'Row')))
    check('a class with no table at all is skipped, not an error',
          rows_of(m, 'Other') == [])


def test_multiple_boot_duplicates():
    """Two boot-time rows can share the name when two writers raced."""
    db = FakeDb({'Row': [persisted('db-1', 'dup', 'denied', 'sub-9', 10)]})
    m = FakeManager(db)
    Row(manager=m, id='boot-a', name='dup', state='suggested', count=3)
    Row(manager=m, id='boot-b', name='dup', state='suggested', count=4)
    server_with(m)._restoreDefinitionInstances([Row])
    rows = rows_of(m, 'Row')
    check('both boot-time duplicates fold into the persisted row',
          len(rows) == 1 and rows[0].id == 'db-1' and rows[0].count == 17
          and rows[0].state == 'denied',
          repr([(r.id, r.state, r.count) for r in rows]))
    check('both are tombstoned',
          sorted(m.tombstoned) == [('Row', 'boot-a'), ('Row', 'boot-b')],
          repr(m.tombstoned))


def test_fold_never_raises():
    """A boot-time row whose counter is nonsense must not take a boot down."""
    db = FakeDb({'Row': [persisted('db-1', 'x', 'confirmed', 'sub-9', 2)]})
    m = FakeManager(db)
    bad = Row(manager=m, id='boot-x', name='x', state='suggested', count=0)
    bad.count = 'not a number'
    server_with(m)._restoreDefinitionInstances([Row])
    rows = rows_of(m, 'Row')
    check('the persisted row still wins and keeps its own count',
          len(rows) == 1 and rows[0].id == 'db-1' and rows[0].count == 2,
          repr([(r.id, r.count) for r in rows]))


def main():
    for fn in (test_boot_row_folded_into_persisted, test_new_boot_row_survives,
               test_plain_restore_unchanged, test_repeat_pass_is_idempotent,
               test_empty_and_missing_tables, test_multiple_boot_duplicates,
               test_fold_never_raises):
        try:
            fn()
        except Exception as exc:      # noqa: BLE001
            FAILED.append(f'{fn.__name__} BLEW UP :: {type(exc).__name__}: {exc}')
    for line in FAILED:
        print('FAIL', line)
    total = len(PASSED) + len(FAILED)
    print(f'selftest_restore_merge: {len(PASSED)}/{total}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
