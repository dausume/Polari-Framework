"""
@module polariDBmanagement.sql_keyword_guard

THE SQL KEYWORD GUARD - protects the object database from names that are SQL keywords (2026-10-30, his ask: "a guard that safely protects and/or wraps
protected keywords so they can be used without breaking sql", "notated when it happens so when they come back out of sql it still is the same", "an
isolated piece of functionality that clearly indicates its purpose is to protect the database from keywords").

Why it exists: a row class's fields become column names. Before this guard the sqlite adapter wrote them unquoted, so a field named order, index, group,
default, commit, case, exists, when or where made CREATE TABLE fail and the class was never persisted - 31 classes in 15 modules, silently apart from one
boot log line.

What it does - and it is the ONLY place that does it:
  quote(name, dialect)   wraps ANY table / column name for the dialect (sqlite "x", MariaDB `x`) and doubles an embedded quote, so a keyword is legal
                         and a hostile name can never close the quoting. Every adapter's quoteIdent delegates here. Every name is wrapped, keyword or not:
                         the wrapping is SQL syntax only - the stored name is the name itself.
  is_keyword(name, dialect)   sqlite: asked of sqlite itself (an unquoted probe column - the engine is the authority); MariaDB: the published reserved-word
                         list (MARIADB_RESERVED, cited below).
  note(name, table, dialect)  NOTATES each keyword name the guard protected - which name, which table, which dialect, when - once per (table, name), in
                         guarded() and as one log line '[DB-KeywordGuard] ...'.
  check_roundtrip(table, declared, stored, dialect)   the promise that a guarded name comes back out of SQL THE SAME: the column names the database reports
                         for a table must equal the class's field names, exactly; a difference is noted as a broken round trip (never silently renamed).

MariaDB reserved words: "Reserved Words", MariaDB Knowledge Base, https://mariadb.com/kb/en/reserved-words/ (fetched 2026-10-30, page sha256
d17787601d47503fbf35885757d5ed2e08b63f60ea40394c5d77455fdeaf9eb0) - every word on the list, version-limited ones included (a superset only means a few
more notes; the wrapping happens either way).
"""
import datetime
import sqlite3
import threading

MARIADB_RESERVED = frozenset([
    'ACCESSIBLE', 'ADD', 'ALL', 'ALTER', 'ANALYZE', 'AND', 'AS', 'ASC', 'ASENSITIVE', 'BEFORE', 'BETWEEN', 'BIGINT', 'BINARY', 'BLOB', 'BOTH', 'BY',
    'CALL', 'CASCADE', 'CASE', 'CHANGE', 'CHAR', 'CHARACTER', 'CHECK', 'COLLATE', 'COLUMN', 'CONDITION', 'CONSTRAINT', 'CONTINUE', 'CONVERSION',
    'CONVERT', 'CREATE', 'CROSS', 'CURRENT_DATE', 'CURRENT_PATH', 'CURRENT_ROLE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP', 'CURRENT_USER', 'CURSOR',
    'DATABASES', 'DAY_HOUR', 'DAY_MICROSECOND', 'DAY_MINUTE', 'DAY_SECOND', 'DEC', 'DECIMAL', 'DECLARE', 'DEFAULT', 'DELAYED', 'DELETE',
    'DELETE_DOMAIN_ID', 'DESC', 'DESCRIBE', 'DETERMINISTIC', 'DISTINCT', 'DISTINCTROW', 'DIV', 'DOUBLE', 'DO_DOMAIN_IDS', 'DROP', 'DUAL', 'EACH',
    'ELSE', 'ELSEIF', 'ENCLOSED', 'ESCAPED', 'EXCEPT', 'EXISTS', 'EXIT', 'EXPLAIN', 'FALSE', 'FETCH', 'FLOAT', 'FLOAT4', 'FLOAT8', 'FOR', 'FORCE',
    'FOREIGN', 'FROM', 'FULLTEXT', 'GRANT', 'GROUP', 'HAVING', 'HIGH_PRIORITY', 'HOUR_MICROSECOND', 'HOUR_MINUTE', 'HOUR_SECOND', 'IF', 'IGNORE',
    'IGNORE_DOMAIN_IDS', 'IN', 'INDEX', 'INFILE', 'INNER', 'INOUT', 'INSENSITIVE', 'INSERT', 'INT', 'INT1', 'INT2', 'INT3', 'INT4', 'INT8',
    'INTEGER', 'INTERSECT', 'INTERVAL', 'INTO', 'IS', 'ITERATE', 'JOIN', 'KEY', 'KEYS', 'KILL', 'LEADING', 'LEAVE', 'LEFT', 'LIKE', 'LIMIT',
    'LINEAR', 'LINES', 'LOAD', 'LOCALTIME', 'LOCALTIMESTAMP', 'LOCK', 'LONG', 'LONGBLOB', 'LONGTEXT', 'LOOP', 'LOW_PRIORITY',
    'MASTER_DEMOTE_TO_REPLICA', 'MASTER_DEMOTE_TO_SLAVE', 'MASTER_SSL_VERIFY_SERVER_CERT', 'MATCH', 'MAXVALUE', 'MEDIUMBLOB', 'MEDIUMINT',
    'MEDIUMTEXT', 'MIDDLEINT', 'MINUTE_MICROSECOND', 'MINUTE_SECOND', 'MOD', 'MODIFIES', 'NATURAL', 'NOT', 'NO_WRITE_TO_BINLOG', 'NULL', 'NUMERIC',
    'OFFSET', 'ON', 'OPTIMIZE', 'OPTIONALLY', 'OR', 'ORDER', 'OUT', 'OUTER', 'OUTFILE', 'OVER', 'PAGE_CHECKSUM', 'PARSE_VCOL_EXPR', 'PARTITION',
    'PORTION', 'PRECISION', 'PRIMARY', 'PROCEDURE', 'PURGE', 'RANGE', 'READ', 'READS', 'READ_WRITE', 'REAL', 'RECURSIVE', 'REFERENCES',
    'REF_SYSTEM_ID', 'REGEXP', 'RELEASE', 'RENAME', 'REPEAT', 'REPLACE', 'REQUIRE', 'RESIGNAL', 'RESTRICT', 'RETURN', 'RETURNING', 'REVOKE', 'RIGHT',
    'RLIKE', 'ROWS', 'ROW_NUMBER', 'SCHEMAS', 'SECOND_MICROSECOND', 'SELECT', 'SENSITIVE', 'SEPARATOR', 'SET', 'SHOW', 'SIGNAL', 'SMALLINT',
    'SPATIAL', 'SPECIFIC', 'SQL', 'SQLEXCEPTION', 'SQLSTATE', 'SQLWARNING', 'SQL_AFTER_GTIDS', 'SQL_BEFORE_GTIDS', 'SQL_BIG_RESULT',
    'SQL_CALC_FOUND_ROWS', 'SQL_SMALL_RESULT', 'SSL', 'STARTING', 'STATS_AUTO_RECALC', 'STATS_PERSISTENT', 'STATS_SAMPLE_PAGES', 'STRAIGHT_JOIN',
    'TABLE', 'TERMINATED', 'THEN', 'TINYBLOB', 'TINYINT', 'TINYTEXT', 'TO', 'TO_DATE', 'TRAILING', 'TRIGGER', 'TRUE', 'UNDO', 'UNION', 'UNIQUE',
    'UNLOCK', 'UNSIGNED', 'UPDATE', 'USAGE', 'USE', 'USING', 'UTC_DATE', 'UTC_TIME', 'UTC_TIMESTAMP', 'VALUES', 'VARBINARY', 'VARCHAR',
    'VARCHARACTER', 'VARYING', 'VECTOR', 'WHEN', 'WHERE', 'WHILE', 'WITH', 'WRITE', 'XOR', 'YEAR_MONTH', 'ZEROFILL',
])

_LOCK = threading.Lock()
_GUARDED = {}      # (dialect, table, name) -> {'name', 'table', 'dialect', 'first_seen', 'quoted'}
_BROKEN = []       # round trips that did not come back the same
_SQLITE_CACHE = {}


def quote(name, dialect='sqlite'):
    """The one identifier wrapper. sqlite (and the ANSI default): "name"; MariaDB: `name`. An embedded quote character is doubled (the SQL escape)."""
    s = str(name)
    if dialect == 'mariadb':
        return '`%s`' % s.replace('`', '``')
    return '"%s"' % s.replace('"', '""')


def _sqlite_keyword(name):
    if name not in _SQLITE_CACHE:
        db = sqlite3.connect(':memory:')
        try:
            db.execute('CREATE TABLE probe (%s TEXT)' % name)
            _SQLITE_CACHE[name] = False
        except sqlite3.Error:
            _SQLITE_CACHE[name] = True
        finally:
            db.close()
    return _SQLITE_CACHE[name]


def is_keyword(name, dialect='sqlite'):
    """True when the bare name would break (sqlite: the engine refuses it unquoted) or is reserved (MariaDB: on the published list)."""
    s = str(name)
    if not s.isidentifier():
        return True   # not a plain identifier at all (a space, a quote, a hyphen): it needs the wrapping as much as a keyword does
    return s.upper() in MARIADB_RESERVED if dialect == 'mariadb' else _sqlite_keyword(s)


def note(name, table='', dialect='sqlite', log=True):
    """Record that the guard protected a keyword name (once per dialect / table / name). Returns True when the name IS a keyword."""
    if not is_keyword(name, dialect):
        return False
    key = (dialect, table, str(name))
    with _LOCK:
        if key in _GUARDED:
            return True
        _GUARDED[key] = {'name': str(name), 'table': table, 'dialect': dialect, 'quoted': quote(name, dialect),
                         'first_seen': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()}
    if log:
        print('[DB-KeywordGuard] %s.%s is an SQL keyword in %s: written as %s, stored and read back as %r' % (table or '?', name, dialect, quote(name, dialect), str(name)),
              flush=True)
    return True


def check_roundtrip(table, declared, stored, dialect='sqlite'):
    """The guarded names must come back out of SQL the same: every declared field that is a keyword must be a stored column under EXACTLY its own name.
    Returns the list of names that did not come back the same (noted in broken())."""
    have = set(stored)
    bad = [n for n in declared if is_keyword(n, dialect) and n not in have]
    if bad:
        with _LOCK:
            _BROKEN.append({'table': table, 'dialect': dialect, 'names': bad, 'stored': sorted(have)})
        print('[DB-KeywordGuard] ROUND TRIP BROKEN for %s (%s): %s not found under their own names in %s' % (table, dialect, bad, sorted(have)), flush=True)
    return bad


def guarded():
    """Every keyword name the guard protected in this process, as rows."""
    with _LOCK:
        return sorted(_GUARDED.values(), key=lambda r: (r['table'], r['name']))


def broken():
    with _LOCK:
        return list(_BROKEN)


def columns_of(defs):
    """The bare names of sqlite-affinity column defs ('order TEXT', 'id TEXT PRIMARY KEY'), table constraints skipped."""
    out = []
    for row in defs:
        parts = row.strip().split(None, 1)
        if len(parts) == 2 and parts[0].upper() not in ('PRIMARY', 'UNIQUE', 'FOREIGN', 'CHECK', 'CONSTRAINT'):
            out.append(parts[0].strip('`"'))
    return out
