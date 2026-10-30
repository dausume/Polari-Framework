"""
selftest_sql_keyword_guard - THE SQL KEYWORD GUARD (polariDBmanagement.sql_keyword_guard) protects the database from names that are SQL keywords.

  1. every row class (modules/**/objects/, read by AST - no imports) creates its table and saves a row through the sqlite adapter, whatever its field names
  2. the wrapping: any name wrapped for its dialect (sqlite "x", MariaDB `x`), an embedded quote doubled - a hostile name is just a column
  3. THE ROUND TRIP: every keyword field of every class goes in and comes back out of SQL under EXACTLY its own name with the value it went in with
  4. the notation: each protected keyword is noted once per table (guarded()), and a name that does not come back the same is reported (broken())
  5. end to end: the server's own persistence (managedDB.makeSQLiteTable / saveInstanceInDB / getAllInTable) round-trips a keyword-named object

Run from polari-framework/:  python3 -m polariDBmanagement.selftest_sql_keyword_guard
"""
import ast
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES = os.path.join(HERE, 'modules')
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:600]) if (extra and not cond) else ''))


def classes(root=MODULES):
    """-> [(file, class, [field names])] for every class with an __init__ under any objects/ directory."""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        if os.sep + 'objects' not in dirpath + os.sep or '__pycache__' in dirpath:
            continue
        for fn in files:
            if not fn.endswith('.py') or fn.startswith('_'):
                continue
            path = os.path.join(dirpath, fn)
            try:
                tree = ast.parse(open(path, encoding='utf-8').read())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in tree.body:
                init = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'), None) if isinstance(node, ast.ClassDef) else None
                if init is not None:
                    out.append((os.path.relpath(path, HERE), node.name, [a.arg for a in init.args.args + init.args.kwonlyargs if a.arg not in ('self', 'manager')]))
    return out


def main():
    from polariDBmanagement import sql_keyword_guard as KG
    from polariDBmanagement.sqlite_adapter import SqliteAdapter
    from polariDBmanagement.mariadb_adapter import MariaDBAdapter
    ad = SqliteAdapter('selftest', '/tmp')
    rows = classes()
    db = sqlite3.connect(':memory:')
    bad, keyword_fields, trips = [], [], []
    for path, cls, names in rows:
        defs = ['_branch_path TEXT', 'id TEXT PRIMARY KEY'] + ['%s TEXT' % n for n in names if n != 'id']
        table = 't_%s' % cls
        allc = ['id'] + [n for n in names if n != 'id']
        try:
            db.execute('CREATE TABLE IF NOT EXISTS %s (%s)' % (table, ', '.join(ad.translateColumnDefs(defs))))
            db.execute(ad.replaceSQL(table, allc), tuple('%s:%s' % (cls, c) for c in allc))
        except sqlite3.Error as e:
            bad.append('%s (%s): %s' % (cls, path, e))
            continue
        kws = [n for n in names if KG.is_keyword(n, 'sqlite')]
        if kws:
            keyword_fields += ['%s.%s' % (cls, n) for n in kws]
            cur = db.execute('SELECT * FROM %s' % table)
            got = dict(zip([d[0] for d in cur.description], cur.fetchone()))
            stored = ad.tableColumns(db, table)
            for n in kws:
                KG.note(n, table, 'sqlite', log=False)
                trips.append((cls, n, n in got and got[n] == '%s:%s' % (cls, n), KG.check_roundtrip(table, names, stored, 'sqlite')))
    check('every row class (%d) creates its table and saves a row through the sqlite adapter, whatever its field names' % len(rows), len(rows) > 100 and not bad, bad[:5])

    ma = MariaDBAdapter.__new__(MariaDBAdapter)
    hostile = 'x"); DROP TABLE g; --'
    try:
        db.execute('CREATE TABLE g (%s TEXT, %s TEXT)' % (ad.quoteIdent('where'), ad.quoteIdent(hostile)))
        db.execute('INSERT INTO g VALUES (?, ?)', ('w', 'h'))
        survived = [d[0] for d in db.execute('SELECT * FROM g').description] == ['where', hostile]
    except sqlite3.Error:
        survived = False
    check('THE WRAPPING: one place (sql_keyword_guard.quote) - sqlite "order", MariaDB `when`; an embedded quote doubled, so a hostile name is only a column '
          '(the table survives and the name reads back as itself); both adapters delegate to it',
          KG.quote('order') == '"order"' and KG.quote('a"b') == '"a""b"' and KG.quote('when', 'mariadb') == '`when`' and KG.quote('a`b', 'mariadb') == '`a``b`'
          and ad.quoteIdent('order') == '"order"' and ma.quoteIdent('when') == '`when`' and survived)
    check('THE ROUND TRIP: every keyword field of every class (%d) goes into SQL and comes back out under EXACTLY its own name with its value; the table\'s '
          'stored column names equal the declared ones' % len(trips), trips and all(ok and not br for _c, _n, ok, br in trips),
          [(c, n, br) for c, n, ok, br in trips if not ok or br][:5])
    noted = {(g['table'], g['name']) for g in KG.guarded()}
    KG.check_roundtrip('t_probe', ['order'], ['ordr'], 'sqlite')
    check('THE NOTATION: each protected keyword is noted once per table with how it was written (guarded(): %d), MariaDB words from its published list '
          '(%d words); a name that does not come back the same is reported, never silently renamed (broken())' % (len(noted), len(KG.MARIADB_RESERVED)),
          len(noted) == len(trips) and all(('t_%s' % c, n) in noted for c, n, _o, _b in trips) and KG.is_keyword('order') and not KG.is_keyword('title')
          and KG.is_keyword('precision', 'mariadb') and not KG.is_keyword('title', 'mariadb') and KG.broken()[-1]['names'] == ['order'], len(noted))
    import tempfile
    from polariDBmanagement.managedDB import managedDatabase as managedDB

    class KwRow:   # a row whose fields are keywords, persisted the way the server persists every object
        def __init__(self):
            self.id, self.name, self.order, self.when, self.index = 'r1', 'kept', '3', '2026-10-30T12:00:00+00:00', '7'

    with tempfile.TemporaryDirectory() as tmp:
        mdb = managedDB.__new__(managedDB)
        mdb.__dict__.update({'name': 'kwguard', 'Path': tmp, 'isRemote': False, 'tables': [], 'manager': None, '_instanceScope': ''})
        sqlite3.connect(os.path.join(tmp, 'kwguard.db')).close()
        mdb.makeSQLiteTable('KwRow', ['id TEXT PRIMARY KEY', 'name TEXT', 'order TEXT', 'when TEXT', 'index TEXT'])
        saved = mdb.saveInstanceInDB(KwRow())
        back = mdb.getAllInTable('KwRow')
    cols, data = back if isinstance(back, tuple) and len(back) == 2 else ([], [])
    vals = dict(zip(cols, data[0])) if data else {}   # getAllInTable -> (column names AS THE DATABASE REPORTS THEM, rows)
    check('END TO END through managedDB: a row with fields order / when / index is created, saved and read back by the server\'s own persistence with '
          'the same names and values; the guard noted all three for that table',
          saved and vals.get('order') == '3' and vals.get('when') == '2026-10-30T12:00:00+00:00' and vals.get('index') == '7'
          and {('KwRow', n) for n in ('order', 'when', 'index')} <= {(g['table'], g['name']) for g in KG.guarded()}, (saved, back))
    print('  (keyword fields the guard protects: %d - %s)' % (len(keyword_fields), ', '.join(sorted(keyword_fields))))
    print('\n%d/%d checks passed' % (sum(_results), len(_results)))
    return 0 if all(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
