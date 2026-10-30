"""
DB adapter seam — one interface, per-dialect implementations.

The object-persistence layer (managedDB, boot restore/persist, dynamic
class tables) historically called sqlite3 directly. This module defines
the small dialect surface those call sites actually need, so the
backing store is a CONFIG choice (`database.type`: sqlite | mariadb,
env DATABASE_TYPE) instead of an assumption:

  - connect()                     DBAPI-2 connection (connect-per-call,
                                  matching the existing sqlite pattern)
  - ensureDatabase()/databaseExists()
  - listTables(conn) / tableColumns(conn, table)
  - translateColumnDefs(rowList)  sqlite-affinity column defs -> dialect
  - replaceSQL(table, cols)       INSERT OR REPLACE / REPLACE INTO
  - placeholder                   '?' vs '%s'

Implementations: sqlite_adapter.SqliteAdapter (today's behavior,
extracted) and mariadb_adapter.MariaDBAdapter. Pick via make_adapter().
"""

import os


class DBAdapter:
    """Dialect surface for the object-persistence layer."""

    dialect = 'abstract'
    #: DBAPI paramstyle token used when building parameterized SQL.
    placeholder = '?'
    #: Statement that opens an explicit write transaction. The
    #: whole-tree persist drives BEGIN/COMMIT itself so readers see the
    #: old tree or the new tree, never a half-written one (§51 addendum
    #: 2). Dialects that need a write lock taken UP FRONT say so here.
    beginTransactionSQL = 'BEGIN'

    def connect(self):
        raise NotImplementedError

    def ensureDatabase(self):
        """Create the database (file / schema) if it does not exist."""
        raise NotImplementedError

    def databaseExists(self):
        """True when the database exists AND holds at least one table."""
        raise NotImplementedError

    def listTables(self, conn):
        raise NotImplementedError

    def tableColumns(self, conn, tableName):
        """Column names of an existing table ([] when absent)."""
        raise NotImplementedError

    def tableColumnDefs(self, conn, tableName):
        """[(column name, declared type), ...] of an existing table."""
        raise NotImplementedError

    def translateColumnDefs(self, rowList):
        """Translate sqlite-affinity column definition strings (the
        format makeTypedTableFromAnalysis emits, e.g. 'name TEXT
        PRIMARY KEY' or 'PRIMARY KEY (a, b)') into this dialect.

        Every column NAME is quoted (2026-10-30): a field named after an SQL keyword (order, index, group, default, when, where ...) made the unquoted
        CREATE fail and the class was never persisted - 31 classes, found by polariDBmanagement.selftest_column_names."""
        import re
        out = []
        for row in rowList:
            stripped = row.strip()
            constraint = re.match(r'(?i)^PRIMARY KEY\s*\(([^)]*)\)', stripped)
            if constraint:
                out.append('PRIMARY KEY (%s)' % ', '.join(self.quoteIdent(c.strip().strip('`"')) for c in constraint.group(1).split(',')))
                continue
            parts = stripped.split(None, 1)
            if len(parts) < 2 or parts[0].upper() in ('PRIMARY', 'UNIQUE', 'FOREIGN', 'CHECK', 'CONSTRAINT'):
                out.append(stripped)
                continue
            out.append('%s %s' % (self.quoteIdent(parts[0].strip('`"')), parts[1]))
        return out

    def replaceSQL(self, tableName, columns):
        """Upsert-by-primary-key statement with placeholders."""
        ph = ', '.join([self.placeholder] * len(columns))
        cols = ', '.join(self.quoteIdent(c) for c in columns)
        return f'REPLACE INTO {tableName} ({cols}) VALUES({ph});'

    def addColumnSQL(self, tableName, colName, colType):
        return f'ALTER TABLE {tableName} ADD COLUMN {self.quoteIdent(colName)} {colType}'

    def modifyColumnSQL(self, tableName, colName, newType):
        """Widen an existing column's type (schema-stability OOPS
        adaptation). None = this dialect cannot alter column types
        in place (sqlite — its loose affinity rarely rejects data
        anyway; the caller falls back to value coercion)."""
        return None

    def quoteIdent(self, name):
        """Dialect identifier quoting (sqlite: "x", mariadb: `x`) - THE keyword guard: every table / column name that reaches SQL goes through here,
        so a field may be named order, index, when, where ... The wrapping itself is polariDBmanagement.sql_keyword_guard's (the one place it lives)."""
        from polariDBmanagement import sql_keyword_guard as KG
        return KG.quote(name, self.dialect)

    def tableExists(self, conn, tableName):
        return tableName in self.listTables(conn)


def make_adapter(dbName, dbDir=None):
    """Build the configured adapter for the named object database.

    `database.type` (env DATABASE_TYPE) picks the dialect; sqlite is the
    default and needs dbDir. MariaDB connection settings come from
    `database.mariadb.*` (env MARIADB_HOST/PORT/USER/DATABASE), password
    from env MARIADB_PASSWORD only — never YAML.
    """
    dbType = 'sqlite'
    try:
        from config_loader import config
        dbType = str(config.get('database.type', 'sqlite') or 'sqlite').lower()
    except Exception:
        dbType = str(os.environ.get('DATABASE_TYPE', 'sqlite') or 'sqlite').lower()

    if dbType == 'mariadb':
        from polariDBmanagement.mariadb_adapter import MariaDBAdapter
        return MariaDBAdapter(dbName=dbName)
    from polariDBmanagement.sqlite_adapter import SqliteAdapter
    return SqliteAdapter(dbName=dbName, dbDir=dbDir)
