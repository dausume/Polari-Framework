"""
Selftest for shared-object-DB instance scoping (managedDB).

Run from polari-framework/:
  python3 -m polariDBmanagement.selftest_shared_db

Drives the REAL managedDB methods (bare instances, real sqlite
adapter on a temp file, cache off) as two Polari instances 'a' and
'b' sharing ONE database: table created once with the _instance_id
discriminator + composite PK, writes stamped, reads isolated,
identical ids never clobber across instances, deletes scoped, drop
refused (cleared for the caller only), legacy/unscoped mode
byte-identical to before, and the column-def transform + env-knob
parsing covered directly.
"""

import os
import tempfile
import types

from polariDBmanagement.managedDB import managedDatabase as managedDB

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


class Widget:
    def __init__(self, id, name, count):
        self.id, self.name, self.count = id, name, count


class Legacy:
    def __init__(self, id, name):
        self.id, self.name = id, name


class NoCache:
    def getTable(self, *a):
        return None

    def setTable(self, *a):
        pass

    def invalidateTable(self, *a):
        pass


def _db(tmpdir, scope):
    """A bare managedDB over the shared sqlite file, as one instance."""
    db = managedDB.__new__(managedDB)
    db.__dict__.update({
        'name': 'sharedtest', 'Path': tmpdir, 'isRemote': False,
        'tables': ['Widget'], 'manager': None,
        '_instanceScope': scope})
    from polariDBmanagement.db_adapter import make_adapter
    db.__dict__['_adapter'] = make_adapter(dbName='sharedtest',
                                           dbDir=tmpdir)
    # cache off: isolation must hold at the DB, not via cache keys
    managedDB.cache  # (property exists; bypass it)
    db.__dict__['_cache'] = None
    return db


def main():
    tmpdir = tempfile.mkdtemp(prefix='shared-db-selftest-')
    # sqlite adapter needs the db file to exist
    open(os.path.join(tmpdir, 'sharedtest.db'), 'a').close()

    # cache property is module-level (keydb) — force the no-op cache
    managedDB.cache = property(lambda self: NoCache())

    a = _db(tmpdir, 'a')
    b = _db(tmpdir, 'b')
    plain = _db(tmpdir, '')

    # --- column-def transform -------------------------------------------
    defs = a._scopeColumnDefs(['id text PRIMARY KEY', 'name TEXT',
                               'count INTEGER'])
    check('scoped defs: discriminator added + composite PK',
          '_instance_id TEXT' in defs
          and 'PRIMARY KEY (id, _instance_id)' in defs
          and not any('id text PRIMARY KEY' == d for d in defs))
    tbl_defs = a._scopeColumnDefs(['x TEXT', 'y TEXT',
                                   'PRIMARY KEY (x, y)'])
    check('scoped defs: table-level PK folded into the composite',
          'PRIMARY KEY (x, y, _instance_id)' in tbl_defs)
    check('unscoped defs: unchanged (byte-identical legacy path)',
          plain._scopeColumnDefs(['id text PRIMARY KEY'])
          == ['id text PRIMARY KEY'])

    # --- one shared table, not one per instance ---------------------------
    a.makeSQLiteTable('Widget', ['id text PRIMARY KEY', 'name TEXT',
                                 'count INTEGER'])
    b.makeSQLiteTable('Widget', ['id text PRIMARY KEY', 'name TEXT',
                                 'count INTEGER'])
    conn = a.adapter.connect()
    ntables = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND "
        "name='Widget'").fetchone()[0]
    cols = a.adapter.tableColumns(conn, 'Widget')
    conn.close()
    check('ONE table serves both instances (no per-instance copy)',
          ntables == 1)
    check('shared table carries _instance_id',
          '_instance_id' in cols)

    # --- scoped writes + isolated reads -------------------------------------
    a.saveInstanceInDB(Widget('w-1', 'alpha-widget', 1))
    a.saveInstanceInDB(Widget('w-2', 'alpha-only', 2))
    b.saveInstanceInDB(Widget('w-1', 'beta-widget', 10))  # same id!

    colsA, rowsA = a.getAllInTable('Widget')
    colsB, rowsB = b.getAllInTable('Widget')
    nameIdx = colsA.index('name')
    check('instance a reads ONLY its rows',
          len(rowsA) == 2 and all('alpha' in r[nameIdx] for r in rowsA))
    check('instance b reads ONLY its rows',
          len(rowsB) == 1 and rowsB[0][nameIdx] == 'beta-widget')
    check('same id in both instances: composite PK, no clobber',
          {r[nameIdx] for r in rowsA + rowsB}
          == {'alpha-widget', 'alpha-only', 'beta-widget'})

    # upsert semantics survive: a re-saves w-1 -> still 2 rows for a
    a.saveInstanceInDB(Widget('w-1', 'alpha-widget-v2', 1))
    colsA2, rowsA2 = a.getAllInTable('Widget')
    check('REPLACE upsert stays within the instance',
          len(rowsA2) == 2 and 'alpha-widget-v2'
          in {r[nameIdx] for r in rowsA2}
          and len(b.getAllInTable('Widget')[1]) == 1)

    # --- scoped deletes -------------------------------------------------------
    deleted = a.deleteRowsWhere('Widget', 'id', 'w-1')
    check('deleteRowsWhere: removes a\'s row, not b\'s same-id row',
          deleted == 1 and len(b.getAllInTable('Widget')[1]) == 1)
    b.deleteAllFromTable('Widget')
    check('deleteAllFromTable: clears only the caller\'s rows',
          len(b.getAllInTable('Widget')[1]) == 0
          and len(a.getAllInTable('Widget')[1]) == 1)

    # --- drop refusal ------------------------------------------------------------
    a.dropTable('Widget')
    conn = a.adapter.connect()
    still = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND "
        "name='Widget'").fetchone()[0]
    conn.close()
    check('dropTable in shared mode: table survives (rows cleared '
          'for caller only)', still == 1
          and len(a.getAllInTable('Widget')[1]) == 0)

    # --- legacy/unscoped mode unchanged -------------------------------------------
    plain.makeSQLiteTable('Legacy', ['id text PRIMARY KEY',
                                     'name TEXT'])
    plain.saveInstanceInDB(Legacy('L1', 'x'))
    colsL, rowsL = plain.getAllInTable('Legacy')
    check('unscoped mode: no discriminator column, plain behavior',
          '_instance_id' not in colsL and len(rowsL) == 1)
    # scoped reader over a legacy table: honest unscoped fallback
    colsF, rowsF = a.getAllInTable('Legacy')
    check('scoped read of a legacy table falls back honestly',
          len(rowsF) == 1)

    # --- env-knob parsing -----------------------------------------------------------
    env_db = managedDB.__new__(managedDB)
    env_db.__dict__.update({'name': 'x', 'Path': tmpdir})
    os.environ['POLARI_SHARED_OBJECT_DB'] = '1'
    os.environ['POLARI_INSTANCE_ID'] = 'inst-7'
    check('knob: POLARI_SHARED_OBJECT_DB + POLARI_INSTANCE_ID',
          env_db.instanceScope == 'inst-7')
    env_db2 = managedDB.__new__(managedDB)
    env_db2.__dict__.update({'name': 'x', 'Path': tmpdir})
    os.environ['POLARI_SHARED_OBJECT_DB'] = 'off'
    check('knob: off by default / non-truthy',
          env_db2.instanceScope == '')
    os.environ.pop('POLARI_SHARED_OBJECT_DB')
    os.environ.pop('POLARI_INSTANCE_ID')

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
