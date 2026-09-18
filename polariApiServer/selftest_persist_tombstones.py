"""selftest_persist_tombstones — a delete is never undone by a flush that
started before it, and the tree path is found ONCE (ledger §51 addendum 3).

Two defects, one file.

**The resurrection.** `persistTree()` snapshots `objectTables` at the top,
spends 28-134 s serializing rows in Python, then writes that snapshot in
one DELETE+REPLACE transaction. A row deleted through CRUDE while the
serialization was running came BACK: the snapshot still held it. Observed
live twice (two throwaway AppPermissionProfiles, gone from the API and
from sqlite, present again after the next redeploy). Now every removal
leaves a tombstone (className, instanceId) and the write phase drops any
prepared row that is tombstoned AND still absent from the live table —
the live table being the truth, so an id re-created in the meantime is
written, not dropped.

**The serialization.** `_buildClassRows` asked `serializeTreePath` for
every row's `_branch_path`, and that is a FULL depth-first search of the
whole object tree, with `getBranchNode` re-walking from the root at every
step. ~96 % of rows are not in the tree, so those searches never
short-circuit: 42 297 210 recursive calls for 10 870 rows against a
3 900-node tree, 99.7 % of the flush. The tree does not move while the
flush serializes, so it is walked ONCE into an index. These checks pin
that the index gives the SAME answer as the live search, including for
duplicate-pointer nodes and repeated (class, identifiers) keys.

Run:  PYTHONPATH=.:modules python3 polariApiServer/selftest_persist_tombstones.py
"""

import os
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from objectTreeManagerDecorators import managerObject          # noqa: E402
from polariDBmanagement.managedDB import managedDatabase       # noqa: E402
from polariDataTyping.polyTyping import polyTypedObject        # noqa: E402

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


class treeObject:                                    # noqa: N801
    """Named exactly `treeObject`: getInstanceIdentifiers validates an
    instance by the NAME of its direct base class."""

    def __init__(self, rowId, name):
        self.id = rowId
        self.name = name


class Widget(treeObject):
    pass


class Gadget(treeObject):
    pass


# ------------------------------------------------------------- fixtures ---
def _manager(tmpdir, dbname, classes=('Widget', 'Gadget')):
    """A REAL managerObject (every method under test is the real one) with
    a real sqlite managedDatabase behind it."""
    mgr = managerObject.__new__(managerObject)
    typing = {}
    for className in tuple(classes) + ('managerObject',):
        pt = polyTypedObject.__new__(polyTypedObject)
        pt.__dict__.update({'className': className, 'manager': mgr,
                            'identifiers': ['id'], 'polyTypedVars': [],
                            'polyTypedVarsDict': {}})
        typing[className] = pt
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
                     '(id TEXT PRIMARY KEY, name TEXT, '
                     '_branch_path TEXT)')
    conn.commit()
    conn.close()
    mgr.db = db
    return mgr, db, path


def _rows(mgr, className, cls, n, prefix='w'):
    made = []
    for i in range(n):
        inst = cls(f'{prefix}{i}', f'name-{i}')
        mgr.objectTables[className][inst.id] = inst
        mgr.noteTreeMutation(className, inst.id)
        made.append(inst)
    return made


def _ids(path, className):
    conn = sqlite3.connect(path)
    got = sorted(r[0] for r in
                 conn.execute(f'SELECT id FROM "{className}"'))
    conn.close()
    return got


# ------------------------------------------------------- the bookkeeping ---
def test_bookkeeping(tmpdir):
    print('[the tombstone set and the generation counter]')
    mgr, _db, _path = _manager(tmpdir, 'book')
    start = mgr.treeGeneration()
    check('a fresh manager has no tombstones', mgr.currentTombstones() == set())

    _rows(mgr, 'Widget', Widget, 3)
    check('every create bumps the generation',
          mgr.treeGeneration() == start + 3, mgr.treeGeneration())

    gen = mgr.treeGeneration()
    mgr.noteTreeDeletion('Widget', 'w1')
    check('a delete bumps the generation too',
          mgr.treeGeneration() == gen + 1)
    check('and leaves a tombstone',
          ('Widget', 'w1') in mgr.currentTombstones(),
          mgr.currentTombstones())

    check('a tombstoned row still present in the live table is NOT dropped '
          '(the live table is the truth)',
          not mgr.rowIsTombstoned(mgr.currentTombstones(), 'Widget', 'w1'))
    del mgr.objectTables['Widget']['w1']
    check('once really gone from the live table it IS dropped',
          mgr.rowIsTombstoned(mgr.currentTombstones(), 'Widget', 'w1'))

    mgr.noteTreeMutation('Widget', 'w1')
    check('re-creating the same id CANCELS its tombstone',
          ('Widget', 'w1') not in mgr.currentTombstones(),
          mgr.currentTombstones())

    mgr.noteTreeDeletion('Widget', 'w2')
    mgr.noteTreeDeletion('Gadget', 'g9')
    mgr.clearTombstones({('Widget', 'w2')})
    check('clearTombstones drops ONLY what the flush honoured',
          mgr.currentTombstones() == {('Gadget', 'g9')},
          mgr.currentTombstones())


def test_drop_prepared_rows(tmpdir):
    print('[_dropTombstonedRows filters prepared batches by the id column]')
    mgr, _db, _path = _manager(tmpdir, 'drop')
    _rows(mgr, 'Widget', Widget, 3)
    del mgr.objectTables['Widget']['w1']
    mgr.noteTreeDeletion('Widget', 'w1')
    prepared = [('Widget', ['id', 'name'],
                 [('w0', 'a'), ('w1', 'b'), ('w2', 'c')], '(core)')]
    out, honoured = mgr._dropTombstonedRows(prepared, mgr.currentTombstones())
    check('the deleted row is gone from the batch',
          [r[0] for r in out[0][2]] == ['w0', 'w2'], out[0][2])
    check('and it is reported as honoured',
          honoured == {('Widget', 'w1')}, honoured)

    noId = [('Widget', ['name'], [('a',), ('b',)], '(core)')]
    out2, honoured2 = mgr._dropTombstonedRows(noId, mgr.currentTombstones())
    check('a class with no id column is left ALONE, never guessed at',
          out2[0][2] == noId[0][2] and not honoured2)


# ------------------------------------------------- the defect, end to end ---
def test_delete_during_serialization_is_not_resurrected(tmpdir):
    print('[a delete landing AFTER the snapshot and BEFORE the write]')
    mgr, db, path = _manager(tmpdir, 'race')
    _rows(mgr, 'Widget', Widget, 4)
    mgr.persistTree()
    check('the four rows are on disk to start with',
          _ids(path, 'Widget') == ['w0', 'w1', 'w2', 'w3'],
          _ids(path, 'Widget'))

    # the delete lands while persistTree is serializing: prepareClassBatch
    # is exactly the slow phase, so we fire it from inside.
    realPrepare = db.prepareClassBatch
    fired = []

    def prepareThenDelete(className, instances, treePathIndex=None):
        out = realPrepare(className, instances,
                          treePathIndex=treePathIndex)
        if className == 'Widget' and not fired:
            fired.append(True)
            mgr.deleteTreeNode(className='Widget', nodePolariId='w2',
                               instancesDeleted=[], migratedInstances=[])
        return out

    db.__dict__['prepareClassBatch'] = prepareThenDelete
    mgr.persistTree()
    del db.__dict__['prepareClassBatch']

    check('the delete really did land mid-serialization', bool(fired))
    check('it is gone from the live tree',
          'w2' not in mgr.objectTables['Widget'])
    check('THE DEFECT: the flush did NOT write it back',
          _ids(path, 'Widget') == ['w0', 'w1', 'w3'],
          _ids(path, 'Widget'))
    check('the tombstone was cleared once the write committed',
          ('Widget', 'w2') not in mgr.currentTombstones(),
          mgr.currentTombstones())

    mgr.persistTree()
    check('and it stays gone on the next flush',
          _ids(path, 'Widget') == ['w0', 'w1', 'w3'],
          _ids(path, 'Widget'))


def test_create_during_serialization_is_never_lost(tmpdir):
    print('[a create landing mid-serialization is written now or next '
          'flush — never lost]')
    mgr, db, path = _manager(tmpdir, 'create')
    _rows(mgr, 'Widget', Widget, 2)
    mgr.persistTree()

    realPrepare = db.prepareClassBatch
    fired = []

    def prepareThenCreate(className, instances, treePathIndex=None):
        out = realPrepare(className, instances,
                          treePathIndex=treePathIndex)
        if className == 'Widget' and not fired:
            fired.append(True)
            inst = Widget('wLate', 'late arrival')
            mgr.objectTables['Widget'][inst.id] = inst
            mgr.noteTreeMutation('Widget', inst.id)
        return out

    db.__dict__['prepareClassBatch'] = prepareThenCreate
    mgr.persistTree()
    del db.__dict__['prepareClassBatch']

    onDisk = _ids(path, 'Widget')
    check('the row is either already written or still in the live tree',
          'wLate' in onDisk or 'wLate' in mgr.objectTables['Widget'],
          onDisk)
    mgr.persistTree()
    check('the NEXT flush has it on disk for certain',
          'wLate' in _ids(path, 'Widget'), _ids(path, 'Widget'))


def test_recreated_id_is_not_dropped(tmpdir):
    print('[an id deleted and RE-created before the write is written]')
    mgr, db, path = _manager(tmpdir, 'recreate')
    _rows(mgr, 'Widget', Widget, 2)
    mgr.persistTree()

    realPrepare = db.prepareClassBatch
    fired = []

    def churn(className, instances, treePathIndex=None):
        out = realPrepare(className, instances,
                          treePathIndex=treePathIndex)
        if className == 'Widget' and not fired:
            fired.append(True)
            mgr.deleteTreeNode(className='Widget', nodePolariId='w1',
                               instancesDeleted=[], migratedInstances=[])
            back = Widget('w1', 'reborn')
            mgr.objectTables['Widget']['w1'] = back
            mgr.noteTreeMutation('Widget', 'w1')
        return out

    db.__dict__['prepareClassBatch'] = churn
    mgr.persistTree()
    del db.__dict__['prepareClassBatch']
    check('the re-created row survived the flush',
          'w1' in _ids(path, 'Widget'), _ids(path, 'Widget'))
    check('no tombstone is left standing against it',
          ('Widget', 'w1') not in mgr.currentTombstones())


def test_generation_reports_a_moving_tree(tmpdir):
    print('[the generation counter says whether the tree moved]')
    mgr, db, _path = _manager(tmpdir, 'gen')
    _rows(mgr, 'Widget', Widget, 2)
    before = mgr.treeGeneration()
    beforeRows = sum(len(t) for t in mgr.objectTables.values())
    mgr.persistTree()
    afterRows = sum(len(t) for t in mgr.objectTables.values())
    # a flush is not perfectly quiet: saveInstanceInDB/record_clean_save
    # BORN schema-stability rows are treeObjects too, and they count.
    check('a quiet flush bumps the generation ONLY for the rows the flush '
          'itself creates',
          mgr.treeGeneration() - before == afterRows - beforeRows,
          f'gen +{mgr.treeGeneration() - before}, '
          f'rows +{afterRows - beforeRows}')
    check('and a quiet flush leaves no tombstones behind',
          mgr.currentTombstones() == set(), mgr.currentTombstones())

    realPrepare = db.prepareClassBatch

    def churn(className, instances, treePathIndex=None):
        out = realPrepare(className, instances,
                          treePathIndex=treePathIndex)
        if className == 'Widget':
            mgr.noteTreeMutation('Widget', 'w0')
        return out

    db.__dict__['prepareClassBatch'] = churn
    mgr.persistTree()
    del db.__dict__['prepareClassBatch']
    check('a flush the tree moved under ends at a higher generation',
          mgr.treeGeneration() > before, mgr.treeGeneration())


def test_legacy_path_honours_tombstones(tmpdir):
    print('[the legacy per-class path drops tombstoned rows too]')
    mgr, db, path = _manager(tmpdir, 'legacy')
    _rows(mgr, 'Widget', Widget, 3)
    mgr.persistTree()

    # hide the atomic writer so persistTree takes the historical branch
    saved = managedDatabase.writePreparedBatches
    try:
        del managedDatabase.writePreparedBatches
        del mgr.objectTables['Widget']['w1']
        mgr.noteTreeDeletion('Widget', 'w1')
        check('persistTree really is on the legacy branch',
              not hasattr(db, 'writePreparedBatches'))
        mgr.persistTree()
    finally:
        managedDatabase.writePreparedBatches = saved
    check('the deleted row is not written back by the legacy path',
          _ids(path, 'Widget') == ['w0', 'w2'], _ids(path, 'Widget'))


# ------------------------------------------------ the tree-path index ---
def _tree(mgr):
    """root -> a, b ; a -> c ; plus a duplicate pointer to c under b, and
    a SECOND node carrying c's (class, identifiers) deeper down."""
    root = ('managerObject', (('id', 'mgr'),), mgr)
    a = Widget('a', 'A')
    b = Widget('b', 'B')
    c = Gadget('c', 'C')
    d = Gadget('c', 'C-elsewhere')        # same class AND identifiers
    ta = ('Widget', (('id', 'a'),), a)
    tb = ('Widget', (('id', 'b'),), b)
    tc = ('Gadget', (('id', 'c'),), c)
    td = ('Gadget', (('id', 'c'),), d)
    dup = ('Gadget', (('id', 'c'),), tuple([ta, tc]))
    mgr.objectTree = {root: {ta: {tc: {}}, tb: {dup: {}, td: {}}}}
    for inst in (a, b):
        mgr.objectTables['Widget'][inst.id] = inst
    mgr.objectTables['Gadget']['c'] = c
    return {'root': root, 'a': a, 'b': b, 'c': c, 'd': d,
            'ta': ta, 'tb': tb, 'tc': tc, 'td': td, 'dup': dup}


def test_index_matches_the_live_search(tmpdir):
    print('[buildTreePathIndex answers exactly what the full search does]')
    mgr, _db, _path = _manager(tmpdir, 'index')
    t = _tree(mgr)
    index = mgr.buildTreePathIndex()

    for label, inst in (('the manager at the root', mgr),
                        ('a node one level down', t['a']),
                        ('a node two levels down', t['c']),
                        ('the SECOND instance sharing a key', t['d'])):
        tup = mgr.getInstanceTuple(inst)
        live = mgr.getTuplePathInObjTree(tup)
        fast = mgr.treePathFromIndex(index, tup)
        check(f'{label}: the index agrees with the live search',
              live == fast, f'{live} != {fast}')

    stranger = Gadget('nope', 'not in the tree')
    tup = mgr.getInstanceTuple(stranger)
    check('a row that is NOT in the tree: both answer None',
          mgr.getTuplePathInObjTree(tup) is None
          and mgr.treePathFromIndex(index, tup) is None)

    check('a duplicate-pointer node is indexed by the path it points at',
          any(type(third) is tuple
              for third, _p in index[('Gadget', (('id', 'c'),))]),
          index[('Gadget', (('id', 'c'),))])
    check('one key can hold several occurrences, in traversal order',
          len(index[('Gadget', (('id', 'c'),))]) == 3,
          index[('Gadget', (('id', 'c'),))])
    check('a manager with no tree at all indexes to nothing',
          managerObject.buildTreePathIndex(
              __import__('types').SimpleNamespace(objectTree=None)) == {})


def test_serialized_branch_path_is_unchanged(tmpdir):
    print('[the _branch_path WRITTEN is byte-identical with and without '
          'the index]')
    mgr, db, _path = _manager(tmpdir, 'bytes')
    t = _tree(mgr)
    cols = ['id', 'name', '_branch_path']
    instances = [t['a'], t['b']]
    slow = db._buildClassRows('Widget', instances, cols)
    fast = db._buildClassRows('Widget', instances, cols,
                              treePathIndex=mgr.buildTreePathIndex())
    check('identical column list', slow[0] == fast[0], f'{slow[0]}')
    check('identical rows, _branch_path included', slow[1] == fast[1],
          f'{slow[1]} != {fast[1]}')
    check('and the path really was found (not None for both)',
          any(r[-1] for r in fast[1]), fast[1])


def test_index_is_built_once_per_flush(tmpdir):
    print('[one tree walk per flush, not one per row]')
    mgr, db, _path = _manager(tmpdir, 'once')
    _tree(mgr)
    _rows(mgr, 'Widget', Widget, 40, prefix='x')
    calls = []
    realSearch = mgr.getTuplePathInObjTree

    def counted(instanceTuple, traversalList=[]):
        if not traversalList:
            calls.append(instanceTuple[0])
        return realSearch(instanceTuple, traversalList)

    mgr.__dict__['getTuplePathInObjTree'] = counted
    t0 = time.time()
    mgr.persistTree()
    dt = time.time() - t0
    del mgr.__dict__['getTuplePathInObjTree']
    check('serializing 42 rows cost ZERO full tree searches '
          '(before: one per row)', not calls, calls[:4])
    print(f'     flush of 42 rows in {dt * 1000:.0f} ms')


def main():
    tmpdir = tempfile.mkdtemp(prefix='persist-tombstones-selftest-')
    managedDatabase.cache = property(lambda self: NoCache())
    test_bookkeeping(tmpdir)
    test_drop_prepared_rows(tmpdir)
    test_delete_during_serialization_is_not_resurrected(tmpdir)
    test_create_during_serialization_is_never_lost(tmpdir)
    test_recreated_id_is_not_dropped(tmpdir)
    test_generation_reports_a_moving_tree(tmpdir)
    test_legacy_path_honours_tombstones(tmpdir)
    test_index_matches_the_live_search(tmpdir)
    test_serialized_branch_path_is_unchanged(tmpdir)
    test_index_is_built_once_per_flush(tmpdir)
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
