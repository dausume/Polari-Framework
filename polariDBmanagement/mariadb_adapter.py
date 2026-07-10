"""
MariaDB implementation of the DBAdapter seam (PyMySQL).

The object DB becomes a MariaDB schema (default `polari_objects`,
`database.mariadb.database` / env MARIADB_DATABASE). Column definitions
arrive in sqlite-affinity form from makeTypedTableFromAnalysis and are
translated here:

  - PRIMARY KEY text columns -> VARCHAR(255) (MariaDB cannot index
    unbounded TEXT), including columns named by a table-level
    `PRIMARY KEY (a, b)` constraint
  - TEXT -> TEXT, NUMERIC/REAL -> DOUBLE, INTEGER -> BIGINT,
    BLOB -> LONGBLOB

Connection settings: database.mariadb.host/port/user/database (env
MARIADB_HOST/MARIADB_PORT/MARIADB_USER/MARIADB_DATABASE); the password
comes from env MARIADB_PASSWORD only.
"""

import os
import re

from polariDBmanagement.db_adapter import DBAdapter

_AFFINITY_MAP = {
    'TEXT': 'TEXT',
    'NUMERIC': 'DOUBLE',
    'REAL': 'DOUBLE',
    'INTEGER': 'BIGINT',
    'BLOB': 'LONGBLOB',
    # sqlite's typeless affinity (columns whose analysis found no
    # dominant type) — MariaDB has no equivalent; store as TEXT.
    'NONE': 'TEXT',
}


def _cfg(key, envVar, default):
    try:
        from config_loader import config
        value = config.get(key, None)
        if value is not None:
            return value
    except Exception:
        pass
    return os.environ.get(envVar, default)


class MariaDBAdapter(DBAdapter):

    dialect = 'mariadb'
    placeholder = '%s'

    def __init__(self, dbName=None):
        # dbName (e.g. managerObject_DB) is kept for logs; the schema
        # name is a deployment setting so one MariaDB can host several
        # named Polari instances.
        self.dbName = dbName
        self.host = str(_cfg('database.mariadb.host', 'MARIADB_HOST', 'prf-mariadb'))
        self.port = int(_cfg('database.mariadb.port', 'MARIADB_PORT', 3306))
        self.user = str(_cfg('database.mariadb.user', 'MARIADB_USER', 'polari'))
        self.database = str(_cfg(
            'database.mariadb.database', 'MARIADB_DATABASE', 'polari_objects'))
        self.password = os.environ.get('MARIADB_PASSWORD', '')

    def _connectRaw(self, withDatabase=True):
        import pymysql
        kwargs = dict(host=self.host, port=self.port, user=self.user,
                      password=self.password, autocommit=False,
                      charset='utf8mb4')
        if withDatabase:
            kwargs['database'] = self.database
        return pymysql.connect(**kwargs)

    def connect(self):
        return self._connectRaw(withDatabase=True)

    def ensureDatabase(self):
        conn = self._connectRaw(withDatabase=False)
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f'CREATE DATABASE IF NOT EXISTS {self.database} '
                    'CHARACTER SET utf8mb4')
            conn.commit()
        finally:
            conn.close()

    def databaseExists(self):
        """True when the schema exists AND already holds tables — a bare
        schema (fresh volume) must take the fresh-boot path so tables
        get created and seeds run."""
        try:
            conn = self._connectRaw(withDatabase=False)
        except Exception as e:
            print(f'[DB] MariaDB unreachable at {self.host}:{self.port}: {e}',
                  flush=True)
            raise
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    'SELECT COUNT(*) FROM information_schema.tables '
                    'WHERE table_schema = %s', (self.database,))
                (count,) = cursor.fetchone()
            return count > 0
        finally:
            conn.close()

    def listTables(self, conn):
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT table_name FROM information_schema.tables '
                'WHERE table_schema = %s ORDER BY table_name',
                (self.database,))
            return [row[0] for row in cursor.fetchall()]

    def tableColumns(self, conn, tableName):
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT column_name FROM information_schema.columns '
                'WHERE table_schema = %s AND table_name = %s '
                'ORDER BY ordinal_position', (self.database, tableName))
            return [row[0] for row in cursor.fetchall()]

    def replaceSQL(self, tableName, columns):
        # Backtick every identifier — column names sqlite tolerates are
        # MariaDB reserved words ('precision' live-found on SimVariable).
        ph = ', '.join([self.placeholder] * len(columns))
        cols = ', '.join(self.quoteIdent(c) for c in columns)
        return (f'REPLACE INTO {self.quoteIdent(tableName)} ({cols}) '
                f'VALUES({ph});')

    def addColumnSQL(self, tableName, colName, colType):
        return (f'ALTER TABLE {self.quoteIdent(tableName)} ADD COLUMN '
                f'{self.quoteIdent(colName)} {colType}')

    def modifyColumnSQL(self, tableName, colName, newType):
        return (f'ALTER TABLE {self.quoteIdent(tableName)} MODIFY '
                f'COLUMN {self.quoteIdent(colName)} {newType}')

    def tableColumnDefs(self, conn, tableName):
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT column_name, data_type FROM '
                'information_schema.columns WHERE table_schema = %s AND '
                'table_name = %s ORDER BY ordinal_position',
                (self.database, tableName))
            return [(row[0], row[1]) for row in cursor.fetchall()]

    def quoteIdent(self, name):
        return f'`{name}`'

    def translateColumnDefs(self, rowList):
        # Pass 1: find every primary-key column name (inline suffix or
        # table-level constraint) — those become VARCHAR(255).
        pkColumns = set()
        for row in rowList:
            stripped = row.strip()
            constraint = re.match(r'(?i)^PRIMARY KEY\s*\(([^)]*)\)', stripped)
            if constraint:
                pkColumns.update(
                    c.strip() for c in constraint.group(1).split(','))
                continue
            if re.search(r'(?i)\bPRIMARY KEY\b', stripped):
                pkColumns.add(stripped.split()[0])

        translated = []
        for row in rowList:
            stripped = row.strip()
            constraint = re.match(r'(?i)^PRIMARY KEY\s*\(([^)]*)\)', stripped)
            if constraint:
                cols = ', '.join(self.quoteIdent(c.strip())
                                 for c in constraint.group(1).split(','))
                translated.append(f'PRIMARY KEY ({cols})')
                continue
            parts = stripped.split()
            if len(parts) < 2:
                translated.append(stripped)
                continue
            colName, colType = parts[0], parts[1].upper()
            rest = ' '.join(parts[2:])
            if colName in pkColumns and colType in ('TEXT', 'BLOB', 'NONE'):
                colType = 'VARCHAR(255)'
            else:
                colType = _AFFINITY_MAP.get(colType, colType)
            # Backtick the name — sqlite-legal names can be MariaDB
            # reserved words ('precision' live-found on SimVariable).
            translated.append(f'{self.quoteIdent(colName)} {colType}'
                              f'{(" " + rest) if rest else ""}')
        return translated
