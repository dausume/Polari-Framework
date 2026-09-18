"""selftest_persist_atomic — a reader NEVER sees a half-written tree (ledger §51 addendum 2).

The defect this pins: `persistTree()` was DELETE+REPLACE per class with a
COMMIT per class, so for the whole ~60 s of a flush the file was partly
new and partly old, and a class on the row-by-row fallback path was
visibly EMPTY between its DELETE and its last INSERT. A container
booting inside that window read the short state (`[DB] Restoring 2
instances of AppPermissionProfile` when three existed) and its own boot
flush wrote the short state back. A concreted permission profile died
that way.

Now: every row is serialized OUTSIDE any transaction, the whole tree is
written inside ONE transaction, and a `polari_persist_state` marker —
committed before the transaction and cleared after it — lets another
process see a flush is in flight and decline to overwrite it.

Run:  PYTHONPATH=.:modules python3 polariDBmanagement/selftest_persist_atomic.py
"""

import os
import sqlite3
import sys
import tempfile
import threading
import time
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from polariDBmanagement.managedDB import managedDatabase as managedDB

PASS = FAIL = 0


def check(label, condition, extra=''):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label} {extra}')


class NoCache:
    def getTable(self, *a):
        return None

    def setTable(self, *a):
        pass

    def invalidateTable(self, *a):
        pass


class Row:
    def __init__(self, rowId, name):
        self.id = rowId
        self.name = name


def _db(tmpdir, name, tables):
    db = managedDB.__new__(managedDB)
    db.__dict__.update({
        'name': name, 'Path': tmpdir, 'isRemote': False,
        'tables': list(tables), 'manager': None, '_instanceScope': ''})
    path = os.path.join(tmpdir, name + '.db')
    conn = sqlite3.connect(path)
    for t in tables:
        conn.execute(f'CREATE TABLE IF NOT EXISTS "{t}" '
                     '(id TEXT PRIMARY KEY, name TEXT)')
    conn.commit()
    conn.close()
    return db, path


# ------------------------------------------------------------ the reader ---
def test_reader_never_sees_a_partial_table(tmpdir):
    print('[2000 rows persisted while a second thread reads the table]')
    db, path = _db(tmpdir, 'atomic', ['Widget'])
    rows = [Row(f'w{i}', f'name-{i}') for i in range(2000)]

    # a full table to start from, so "partial" is distinguishable from
    # "empty because nothing has been written yet"
    ok, written, failed, n = db.writePreparedBatches(
        [(c, cols, r) for (c, (cols, r)) in
         [('Widget', db.prepareClassBatch('Widget', rows)[1])]])
    check('the seed write landed', ok and n == 2000, f'{ok} {n}')

    counts = []
    stop = threading.Event()

    def reader():
        conn = sqlite3.connect(path)
        conn.execute('PRAGMA busy_timeout = 30000')
        while not stop.is_set():
            try:
                counts.append(
                    conn.execute('SELECT COUNT(*) FROM Widget')
                    .fetchone()[0])
            except Exception as e:                       # noqa: BLE001
                counts.append(f'ERR {e}')
            time.sleep(0.001)
        conn.close()

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    time.sleep(0.05)
    for _ in range(12):
        okW, _w, _f, _n = db.writePreparedBatches(
            [(c, cols, r) for (c, (cols, r)) in
             [('Widget', db.prepareClassBatch('Widget', rows)[1])]])
    stop.set()
    t.join(timeout=5)

    check('the reader actually sampled the table', len(counts) > 20,
          len(counts))
    errs = [c for c in counts if not isinstance(c, int)]
    check('no reader ever hit "database is locked"', not errs, errs[:2])
    bad = sorted({c for c in counts if isinstance(c, int)
                  and c not in (0, 2000)})
    check('the reader NEVER saw a count between 0 and full '
          '(this is the whole defect)', not bad, bad[:6])
    check('the reader never saw the table EMPTY either — the DELETE and '
          'the INSERTs commit together',
          0 not in counts, 'saw 0')


def test_serialization_is_outside_the_transaction(tmpdir):
    print('[the slow half runs with no lock held]')
    db, path = _db(tmpdir, 'split', ['Widget'])
    rows = [Row(f'w{i}', f'name-{i}') for i in range(500)]
    t0 = time.time()
    ok, payload, err = db.prepareClassBatch('Widget', rows)
    prep = time.time() - t0
    check('prepareClassBatch serializes the class', ok and len(payload[1]) == 500,
          f'{ok} {err}')

    # A reader holding the file open throughout must not be disturbed by
    # preparation at all — nothing is written until writePreparedBatches.
    conn = sqlite3.connect(path)
    before = conn.execute('SELECT COUNT(*) FROM Widget').fetchone()[0]
    check('preparing wrote nothing', before == 0, before)
    t0 = time.time()
    db.writePreparedBatches([('Widget', payload[0], payload[1])])
    write = time.time() - t0
    after = conn.execute('SELECT COUNT(*) FROM Widget').fetchone()[0]
    conn.close()
    check('the write landed all 500 rows', after == 500, after)
    print(f'     serialize {prep * 1000:.0f} ms, write+commit '
          f'{write * 1000:.0f} ms')


def test_one_bad_class_does_not_lose_the_others(tmpdir):
    print('[a class the batch refuses rolls back to ITS OWN rows only]')
    db, _path = _db(tmpdir, 'savepoint', ['Widget', 'Gadget'])
    good = db.prepareClassBatch('Widget', [Row('a', 'A'), Row('b', 'B')])[1]
    # a deliberately wrong column list for Gadget -> the executemany
    # inside its savepoint fails
    bad = (['id', 'name', 'nope'], [('x', 'X', 1)])
    ok, written, failed, n = db.writePreparedBatches([
        ('Widget', good[0], good[1]),
        ('Gadget', bad[0], bad[1]),
    ])
    check('the transaction still committed', ok, ok)
    check('the good class landed', 'Widget' in written and n == 2,
          f'{written} {n}')
    check('the bad class is reported for the row-by-row fallback',
          'Gadget' in failed, failed)
    conn = sqlite3.connect(os.path.join(_path))
    check('the good class really is on disk',
          conn.execute('SELECT COUNT(*) FROM Widget').fetchone()[0] == 2)
    conn.close()


# ------------------------------------------------------- the boot marker ---
def test_persist_marker(tmpdir):
    print('[polari_persist_state: another process cannot overwrite a flush]')
    db, _path = _db(tmpdir, 'marker', ['Widget'])
    check('no marker on a fresh DB', db.readPersistState() is None)
    db.ensurePersistStateTable()
    db.markPersistStarted()
    state = db.readPersistState()
    check('markPersistStarted publishes started_at with no finished_at',
          state and state['started_at'] and not state['finished_at'],
          state)
    check('our OWN pid never blocks our own flush',
          db.persistInProgress() is None)

    # pretend the row belongs to another live process
    conn = sqlite3.connect(os.path.join(tmpdir, 'marker.db'))
    conn.execute('UPDATE polari_persist_state SET pid = ?',
                 (os.getpid() + 100000,))
    conn.commit()
    conn.close()
    inFlight = db.persistInProgress()
    check("another process's unfinished flush IS reported",
          bool(inFlight), inFlight)

    db.markPersistFinished(classes=3, rows=42)
    check('a finished flush stops blocking',
          db.persistInProgress() is None)
    state = db.readPersistState()
    check('and the marker records what landed',
          state['classes'] == 3 and state['rows'] == 42, state)

    # an abandoned marker (process killed mid-flush) must age out
    conn = sqlite3.connect(os.path.join(tmpdir, 'marker.db'))
    conn.execute('UPDATE polari_persist_state SET pid = ?, '
                 'started_at = ?, finished_at = NULL',
                 (os.getpid() + 100000, time.time() - 10000))
    conn.commit()
    conn.close()
    check('a stale marker does not wedge every later flush',
          db.persistInProgress() is None)


def test_persist_tree_declines_during_another_flush(tmpdir):
    print('[persistTree DECLINES while another process is flushing]')
    from objectTreeManagerDecorators import managerObject
    db, _path = _db(tmpdir, 'decline', ['Widget'])
    db.ensurePersistStateTable()
    db.markPersistStarted()
    conn = sqlite3.connect(os.path.join(tmpdir, 'decline.db'))
    conn.execute('UPDATE polari_persist_state SET pid = ?',
                 (os.getpid() + 100000,))
    conn.commit()
    conn.close()

    calls = []
    db.prepareClassBatch = lambda *a, **k: (calls.append(a) or
                                            (False, None, 'x'))
    fake = types.SimpleNamespace(db=db, objectTables={
        'Widget': {'a': Row('a', 'A')}})
    for name in ('persistTree', '_persistTreeAtomic'):
        setattr(fake, name, getattr(managerObject, name).__get__(fake))
    fake.persistTree()
    check('the booting process wrote NOTHING back', not calls, calls)

    db.markPersistFinished()
    fake.persistTree()
    check('and it flushes normally once the other flush is done',
          bool(calls), calls)


def main():
    tmpdir = tempfile.mkdtemp(prefix='persist-atomic-selftest-')
    managedDB.cache = property(lambda self: NoCache())
    test_reader_never_sees_a_partial_table(tmpdir)
    test_serialization_is_outside_the_transaction(tmpdir)
    test_one_bad_class_does_not_lose_the_others(tmpdir)
    test_persist_marker(tmpdir)
    test_persist_tree_declines_during_another_flush(tmpdir)
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
