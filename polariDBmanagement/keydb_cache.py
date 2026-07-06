"""
KeyDB cache tier — read-through table cache for the object DB.

KeyDB speaks the redis protocol, so the standard `redis` client drives
it. The cache is a KNOB (`database.cache.backend`: none | keydb, env
CACHE_BACKEND; default none) and NEVER raises into the persistence
path: a failed connection disables it with one warning and every
operation degrades to a no-op / miss.

Consistency model (deliberately coarse but correct): whole-table
entries keyed `polari:table:<db>:<table>`, invalidated on ANY write to
that table (saveInstanceInDB / delete / drop / dynamic-class writes).
Values are JSON. TTL is a second safety net (default 300s,
database.cache.ttl_seconds).
"""

import json
import os


def _cfg(key, envVar, default):
    try:
        from config_loader import config
        value = config.get(key, None)
        if value is not None:
            return value
    except Exception:
        pass
    return os.environ.get(envVar, default)


class PolariCache:

    def __init__(self):
        backend = str(_cfg('database.cache.backend', 'CACHE_BACKEND', 'none')
                      or 'none').lower()
        self.enabled = backend == 'keydb'
        self.client = None
        self.ttl = int(_cfg('database.cache.ttl_seconds', 'CACHE_TTL_SECONDS', 300))
        if not self.enabled:
            return
        host = str(_cfg('database.cache.host', 'KEYDB_HOST', 'prf-keydb'))
        port = int(_cfg('database.cache.port', 'KEYDB_PORT', 6379))
        password = os.environ.get('KEYDB_PASSWORD', '') or None
        try:
            import redis
            self.client = redis.Redis(
                host=host, port=port, password=password,
                socket_connect_timeout=2, socket_timeout=2,
                decode_responses=True)
            self.client.ping()
            print(f'[Cache] KeyDB cache active at {host}:{port} '
                  f'(ttl={self.ttl}s)', flush=True)
        except Exception as e:
            print(f'[Cache] KeyDB unavailable at {host}:{port} — cache '
                  f'disabled ({e})', flush=True)
            self.enabled = False
            self.client = None

    @staticmethod
    def tableKey(dbName, tableName):
        return f'polari:table:{dbName}:{tableName}'

    def getTable(self, dbName, tableName):
        """Cached (columnNames, rows) for a table, or None on miss."""
        if not self.enabled:
            return None
        try:
            raw = self.client.get(self.tableKey(dbName, tableName))
            if raw is None:
                return None
            payload = json.loads(raw)
            return (payload['columns'],
                    [tuple(row) for row in payload['rows']])
        except Exception:
            return None

    def setTable(self, dbName, tableName, columnNames, rows):
        if not self.enabled:
            return
        try:
            payload = json.dumps(
                {'columns': list(columnNames),
                 'rows': [list(row) for row in rows]},
                default=str)
            self.client.set(self.tableKey(dbName, tableName), payload,
                            ex=self.ttl)
        except Exception:
            pass

    def invalidateTable(self, dbName, tableName):
        if not self.enabled:
            return
        try:
            self.client.delete(self.tableKey(dbName, tableName))
        except Exception:
            pass

    def ping(self):
        if not self.enabled:
            return False
        try:
            return bool(self.client.ping())
        except Exception:
            return False


_cache = None


def get_cache():
    """Process-wide cache singleton (config read once, at first use)."""
    global _cache
    if _cache is None:
        _cache = PolariCache()
    return _cache
