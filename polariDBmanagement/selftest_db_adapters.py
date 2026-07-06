"""
Self-test for the DB adapter seam (MATERIALS_SCIENCE_MODULE_PLAN Track 3).

Covers, without needing a live MariaDB/KeyDB:
  - SqliteAdapter end-to-end against a temp file (create/list/columns/
    replace/upsert semantics)
  - MariaDBAdapter SQL generation (column-def translation incl. PRIMARY
    KEY VARCHAR mapping + composite PKs, REPLACE INTO, %s placeholders,
    backtick quoting) — connection-free
  - make_adapter dialect selection via DATABASE_TYPE
  - PolariCache no-op contract when CACHE_BACKEND=none, and full
    get/set/invalidate semantics against a fake redis client

Run from polari-framework/:
    python3 -m polariDBmanagement.selftest_db_adapters
"""

import os
import sys
import tempfile

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


def test_sqlite_adapter():
    print('[sqlite adapter]')
    from polariDBmanagement.sqlite_adapter import SqliteAdapter
    with tempfile.TemporaryDirectory() as tmp:
        adapter = SqliteAdapter(dbName='selftest_DB', dbDir=tmp)
        check('fresh db does not exist', not adapter.databaseExists())
        adapter.ensureDatabase()
        check('ensureDatabase creates file', adapter.databaseExists())

        conn = adapter.connect()
        cursor = conn.cursor()
        rows = adapter.translateColumnDefs(
            ['name TEXT PRIMARY KEY', 'count INTEGER', 'ratio REAL'])
        check('sqlite defs pass through unchanged',
              rows == ['name TEXT PRIMARY KEY', 'count INTEGER', 'ratio REAL'])
        cursor.execute('CREATE TABLE demo (' + ', '.join(rows) + ')')
        conn.commit()
        check('listTables sees demo', 'demo' in adapter.listTables(conn))
        check('tableColumns', adapter.tableColumns(conn, 'demo')
              == ['name', 'count', 'ratio'])
        check('tableColumnDefs types',
              adapter.tableColumnDefs(conn, 'demo')[1] == ('count', 'INTEGER'))
        check('tableExists true', adapter.tableExists(conn, 'demo'))
        check('tableExists false', not adapter.tableExists(conn, 'nope'))

        sql = adapter.replaceSQL('demo', ['name', 'count', 'ratio'])
        check('replaceSQL uses INSERT OR REPLACE + ?',
              sql.startswith('INSERT OR REPLACE INTO demo')
              and '?, ?, ?' in sql)
        cursor.execute(sql, ('a', 1, 0.5))
        cursor.execute(sql, ('a', 2, 0.7))  # same PK — upsert
        conn.commit()
        cursor.execute('SELECT count FROM demo WHERE name = ?', ('a',))
        check('upsert-by-pk keeps one row w/ latest value',
              cursor.fetchall() == [(2,)])
        check('quoteIdent double-quotes', adapter.quoteIdent('x') == '"x"')
        conn.close()


def test_mariadb_sqlgen():
    print('[mariadb adapter — SQL generation, connection-free]')
    os.environ['MARIADB_PASSWORD'] = 'unused'
    from polariDBmanagement.mariadb_adapter import MariaDBAdapter
    adapter = MariaDBAdapter(dbName='selftest_DB')

    rows = adapter.translateColumnDefs([
        'name TEXT PRIMARY KEY', 'count INTEGER', 'ratio REAL',
        'payload BLOB', 'score NUMERIC',
    ])
    check('PK TEXT -> VARCHAR(255)', rows[0] == 'name VARCHAR(255) PRIMARY KEY')
    check('INTEGER -> BIGINT', rows[1] == 'count BIGINT')
    check('REAL -> DOUBLE', rows[2] == 'ratio DOUBLE')
    check('BLOB -> LONGBLOB', rows[3] == 'payload LONGBLOB')
    check('NUMERIC -> DOUBLE', rows[4] == 'score DOUBLE')

    # sqlite's typeless NONE affinity (live-found on managerObject:
    # 'objectStore NONE' + 'id NONE PRIMARY KEY' failed on MariaDB 11)
    noneRows = adapter.translateColumnDefs(
        ['objectStore NONE', 'id NONE PRIMARY KEY'])
    check('NONE -> TEXT', noneRows[0] == 'objectStore TEXT')
    check('PK NONE -> VARCHAR(255)',
          noneRows[1] == 'id VARCHAR(255) PRIMARY KEY')

    composite = adapter.translateColumnDefs([
        '_branch_path TEXT', 'a TEXT', 'b TEXT', 'PRIMARY KEY (a, b)'])
    check('composite PK columns -> VARCHAR(255)',
          composite[1] == 'a VARCHAR(255)' and composite[2] == 'b VARCHAR(255)')
    check('table-level PK constraint preserved',
          composite[3] == 'PRIMARY KEY (a, b)')
    check('non-PK TEXT stays TEXT', composite[0] == '_branch_path TEXT')

    sql = adapter.replaceSQL('demo', ['a', 'b'])
    check('replaceSQL uses REPLACE INTO + %s',
          sql.startswith('REPLACE INTO demo') and '%s, %s' in sql)
    check('quoteIdent backticks', adapter.quoteIdent('x') == '`x`')
    check('placeholder %s', adapter.placeholder == '%s')


def test_factory():
    print('[make_adapter dialect selection]')
    from polariDBmanagement.db_adapter import make_adapter
    old = os.environ.get('DATABASE_TYPE')
    try:
        os.environ.pop('DATABASE_TYPE', None)
        _reload_config()
        check('default is sqlite',
              make_adapter('x_DB', '/tmp').dialect == 'sqlite')
        os.environ['DATABASE_TYPE'] = 'mariadb'
        _reload_config()
        check('DATABASE_TYPE=mariadb picks mariadb',
              make_adapter('x_DB', '/tmp').dialect == 'mariadb')
    finally:
        if old is None:
            os.environ.pop('DATABASE_TYPE', None)
        else:
            os.environ['DATABASE_TYPE'] = old
        _reload_config()


def _reload_config():
    """config_loader caches env at import; nudge it per-scenario."""
    try:
        import config_loader
        import importlib
        importlib.reload(config_loader)
    except Exception:
        pass


class _FakeRedis:
    def __init__(self):
        self.store = {}
    def get(self, k):
        return self.store.get(k)
    def set(self, k, v, ex=None):
        self.store[k] = v
    def delete(self, k):
        self.store.pop(k, None)
    def ping(self):
        return True


def test_cache():
    print('[keydb cache]')
    from polariDBmanagement.keydb_cache import PolariCache

    os.environ.pop('CACHE_BACKEND', None)
    _reload_config()
    cache = PolariCache()
    check('backend none -> disabled', not cache.enabled)
    check('disabled getTable is a miss',
          cache.getTable('db', 't') is None)
    cache.setTable('db', 't', ['a'], [(1,)])  # must be a silent no-op
    check('disabled ping False', cache.ping() is False)

    # Enabled path against a fake client (no live KeyDB needed)
    cache.enabled = True
    cache.client = _FakeRedis()
    cache.setTable('db', 't', ['a', 'b'], [(1, 'x'), (2, 'y')])
    got = cache.getTable('db', 't')
    check('round-trip columns', got[0] == ['a', 'b'])
    check('round-trip rows as tuples', got[1] == [(1, 'x'), (2, 'y')])
    cache.invalidateTable('db', 't')
    check('invalidate clears', cache.getTable('db', 't') is None)
    check('ping via client', cache.ping() is True)


def main():
    test_sqlite_adapter()
    test_mariadb_sqlgen()
    test_factory()
    test_cache()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
