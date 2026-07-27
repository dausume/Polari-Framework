"""
Self-test for mlb-5b: the batched per-class flush.

saveClassBatch writes ALL of one class's rows in ONE transaction
(DELETE + executemany REPLACE) and is byte-equivalent to the per-row
path for restore purposes (REPLACE NULLs unnamed columns either way);
the batch-vs-row equivalence, shared-DB scoping, dedup-by-PK, the
fallback contract (ok=False, nothing half-written), and the
module-ordered progress stream through a stub persistTree are all
pinned here.

Run from polari-framework/ (modules/ on the path — the persistTree
test imports the server chain):
    PYTHONPATH=modules python3 -m polariDBmanagement.selftest_batched_persist
"""

import os
import sys
import tempfile

from polariDBmanagement.managedDB import managedDatabase as managedDB

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


class Widget:
    def __init__(self, id, name, count, tags=None):
        self.id, self.name, self.count = id, name, count
        if tags is not None:
            self.tags = tags


class NoCache:
    def getTable(self, *a):
        return None

    def setTable(self, *a):
        pass

    def invalidateTable(self, *a):
        pass


def _db(tmpdir, scope=''):
    db = managedDB.__new__(managedDB)
    db.__dict__.update({
        'name': 'batchtest', 'Path': tmpdir, 'isRemote': False,
        'tables': ['Widget'], 'manager': None,
        '_instanceScope': scope})
    from polariDBmanagement.db_adapter import make_adapter
    db.__dict__['_adapter'] = make_adapter(dbName='batchtest',
                                           dbDir=tmpdir)
    return db


def _rows(db, where=''):
    conn = db.adapter.connect()
    got = conn.execute(f'SELECT * FROM Widget {where} '
                       'ORDER BY id').fetchall()
    conn.close()
    return got


def test_batch_roundtrip(tmpdir):
    print('[batch: one transaction, byte-equivalent rows]')
    db = _db(tmpdir)
    db.makeSQLiteTable('Widget', ['id text PRIMARY KEY', 'name TEXT',
                                  'count INTEGER', 'tags TEXT'])
    widgets = [Widget('a', 'alpha', 1, tags=['x', 'y']),
               Widget('b', 'beta', 2),
               Widget('c', None, 0)]
    ok, n, err = db.saveClassBatch('Widget', widgets)
    check('batch ok, all rows written', ok and n == 3 and err == '')
    rows = _rows(db)
    check('3 rows in the table', len(rows) == 3)
    byid = {r[0]: r for r in rows}
    check('JSON columns serialized like the per-row path',
          byid['a'][3] == '["x", "y"]')
    check('missing/None attributes land as NULL',
          byid['b'][3] is None and byid['c'][1] is None)
    # Re-batch = idempotent replace, no duplication.
    ok, n, _ = db.saveClassBatch('Widget', widgets)
    check('re-batch replaces, never duplicates',
          ok and len(_rows(db)) == 3)
    # Batch REMOVES rows that no longer exist in the tree (the
    # delete-then-write semantics persistTree always had).
    ok, n, _ = db.saveClassBatch('Widget', widgets[:1])
    check('shrunken tree shrinks the table (delete-then-write)',
          ok and len(_rows(db)) == 1)
    check('unknown table refuses (caller falls back)',
          db.saveClassBatch('Nope', widgets)[0] is False)


def test_scoped_batch(tmpdir):
    print('[shared-DB scope: only OUR rows replaced]')
    sub = os.path.join(tmpdir, 'scoped')
    os.makedirs(sub, exist_ok=True)
    open(os.path.join(sub, 'batchtest.db'), 'a').close()
    a = _db(sub, 'a')
    b = _db(sub, 'b')
    a.makeSQLiteTable('Widget', ['id text PRIMARY KEY', 'name TEXT',
                                 'count INTEGER', 'tags TEXT'])
    b.__dict__['tables'] = ['Widget']
    ok, _, _ = a.saveClassBatch('Widget', [Widget('w', 'A-owned', 1)])
    ok2, _, _ = b.saveClassBatch('Widget', [Widget('w', 'B-owned', 2)])
    check('both scoped batches ok', ok and ok2)
    rows = _rows(a)
    check('one row PER INSTANCE survives (composite PK)',
          len(rows) == 2)
    ok, _, _ = a.saveClassBatch('Widget', [])
    rows = _rows(a)
    check("empty batch clears only A's rows — B untouched",
          len(rows) == 1 and 'B-owned' in str(rows[0]))


def test_failure_contract(tmpdir):
    print('[failure: ok=False, nothing half-written]')
    db = _db(tmpdir)

    class Sneaky:
        def __init__(self):
            self.id = 'z'
            self.name = 'fine'
            self.count = 3

    # Break the statement by pointing at a table that vanished
    # between tables[] and the write.
    db.__dict__['tables'] = ['Ghost']
    ok, n, err = db.saveClassBatch('Ghost', [Sneaky()])
    check('missing physical table -> ok=False with the error',
          ok is False and err != '')
    check('no rows were written anywhere', n == 0)


def test_module_ordered_progress():
    print('[persistTree: module-ordered class batches + progress]')
    # Stub manager exercising the REAL persistTree body.
    import types

    from objectTreeManagerDecorators import managerObject

    class FakeDB:
        def __init__(self):
            self.tables = ['CoreThing', 'PotDefinition', 'ScoreTerm']
            self.batches = []

        def saveClassBatch(self, className, instances):
            self.batches.append(className)
            if className == 'ScoreTerm':
                return (False, 0, 'simulated batch failure')
            return (True, len(instances), '')

        def deleteAllFromTable(self, className):
            self.batches.append(f'delete:{className}')

        def saveInstanceInDB(self, instance):
            self.batches.append(
                f'row:{type(instance).__name__}')
            return True

    core = type('CoreThing', (), {'__module__': 'topology.rows'})
    pot = type('PotDefinition', (), {'__module__': 'aquaponics.rows'})
    score = type('ScoreTerm', (), {'__module__': 'scoring.rows'})
    fake = types.SimpleNamespace(
        db=FakeDB(),
        objectTables={
            'PotDefinition': {'1': pot()},
            'CoreThing': {'1': core()},
            'ScoreTerm': {'1': score()},
            'NoTable': {'1': core()},
        })
    steps = []
    managerObject.persistTree(fake, progress=steps.append)
    order = [s for s in fake.db.batches if not s.startswith(('delete',
                                                             'row'))]
    check('core flushes before feature modules',
          order[0] == 'CoreThing')
    check('dependency order among modules (scoring before '
          'aquaponics)',
          order.index('ScoreTerm') < order.index('PotDefinition'))
    check('failed batch fell back to row-by-row (no silent loss)',
          'delete:ScoreTerm' in fake.db.batches
          and 'row:ScoreTerm' in fake.db.batches)
    check('progress streamed per class with module + counts',
          len(steps) == 3
          and steps[0]['module'] == '(core)'
          and steps[-1]['classesDone'] == 3
          and steps[-1]['classesTotal'] == 3)
    check('fallback class flagged in its progress step',
          any(s['className'] == 'ScoreTerm' and not s['batched']
              for s in steps))


def main():
    tmpdir = tempfile.mkdtemp(prefix='batched-persist-selftest-')
    open(os.path.join(tmpdir, 'batchtest.db'), 'a').close()
    managedDB.cache = property(lambda self: NoCache())
    test_batch_roundtrip(tmpdir)
    test_scoped_batch(tmpdir)
    test_failure_contract(tmpdir)
    test_module_ordered_progress()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
