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
        PRIMARY KEY' or 'PRIMARY KEY (a, b)') into this dialect."""
        return list(rowList)

    def replaceSQL(self, tableName, columns):
        """Upsert-by-primary-key statement with placeholders."""
        ph = ', '.join([self.placeholder] * len(columns))
        cols = ', '.join(columns)
        return f'REPLACE INTO {tableName} ({cols}) VALUES({ph});'

    def addColumnSQL(self, tableName, colName, colType):
        return f'ALTER TABLE {tableName} ADD COLUMN {colName} {colType}'

    def quoteIdent(self, name):
        """Dialect identifier quoting (sqlite: "x", mariadb: `x`)."""
        return f'"{name}"'

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
