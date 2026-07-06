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

    def __init__(self, dbName, dbDir=None):
        self.dbName = dbName
        self.dbDir = dbDir

    @property
    def dbFilePath(self):
        if self.dbDir:
            return os.path.join(self.dbDir, self.dbName + '.db')
        return self.dbName + '.db'

    def connect(self):
        return sqlite3.connect(self.dbFilePath)

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
