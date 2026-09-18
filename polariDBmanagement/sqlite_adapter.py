"""
SQLite implementation of the DBAdapter seam — today's behavior, extracted.

One file-backed database per manager (<Class>_DB.db under the data dir),
connect-per-call, sqlite affinities used as-is.
"""

import os
import sqlite3

from polariDBmanagement.db_adapter import DBAdapter


class SqliteAdapter(DBAdapter):

    dialect = 'sqlite'
    placeholder = '?'
    #: IMMEDIATE takes the write lock at BEGIN rather than on the first
    #: write, so the whole-tree persist either gets the file or fails
    #: fast — it can never get half way and then lose a lock race.
    beginTransactionSQL = 'BEGIN IMMEDIATE'

    def __init__(self, dbName, dbDir=None):
        self.dbName = dbName
        self.dbDir = dbDir

    @staticmethod
    def _busyTimeoutMs():
        """How long a reader waits for a writer before giving up.

        §51 addendum 2: the persist now holds ONE transaction over the
        whole tree, so a concurrent reader (a booting container sharing
        the volume) must WAIT for it instead of erroring out with
        'database is locked'. The write window is a fraction of a
        second — 30 s is a large margin. Knob:
        POLARI_SQLITE_BUSY_TIMEOUT_MS."""
        raw = os.environ.get('POLARI_SQLITE_BUSY_TIMEOUT_MS', '')
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            return 30000

    @property
    def dbFilePath(self):
        if self.dbDir:
            return os.path.join(self.dbDir, self.dbName + '.db')
        return self.dbName + '.db'

    def connect(self):
        conn = sqlite3.connect(self.dbFilePath)
        try:
            conn.execute('PRAGMA busy_timeout = %d'
                         % self._busyTimeoutMs())
        except Exception:
            pass
        return conn

    def ensureDatabase(self):
        if self.dbDir:
            os.makedirs(self.dbDir, exist_ok=True)
        conn = sqlite3.connect(self.dbFilePath)
        conn.close()

    def databaseExists(self):
        return os.path.exists(self.dbFilePath)

    def listTables(self, conn):
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def tableColumns(self, conn, tableName):
        cursor = conn.cursor()
        cursor.execute(f'PRAGMA table_info({tableName})')
        return [col[1] for col in cursor.fetchall()]

    def tableColumnDefs(self, conn, tableName):
        cursor = conn.cursor()
        cursor.execute(f'PRAGMA table_info("{tableName}")')
        return [(col[1], col[2]) for col in cursor.fetchall()]

    def replaceSQL(self, tableName, columns):
        ph = ', '.join([self.placeholder] * len(columns))
        cols = ', '.join(columns)
        return f'INSERT OR REPLACE INTO {tableName} ({cols}) VALUES({ph});'
