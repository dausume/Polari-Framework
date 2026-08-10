"""
Selftest for moving a module's data between instance databases.

Run from polari-framework/:
  python3 -m polariDBmanagement.selftest_module_data_move

Drives the REAL plan/move/remove functions against real sqlite files, on
the two ownership regimes and the union rule:

  WHOLE   the module defines the class — every row is its own; the table
          moves and is dropped from the source.
  SUBSET  a class the module only contributes NAMED rows to; only those
          rows move and only those are deleted. The table is never
          dropped, because other modules' rows live in it.
  UNION   a row already at the destination is the same instance arriving
          from another module's dataset — merge it, never duplicate it,
          and stay idempotent when run twice.
"""

import json
import os
import sqlite3
import tempfile

from polariDBmanagement.module_data_move import (
    plan_move, move_tables, drop_from_source, subset_rows_from_bundle,
    _tables, _count, _names_in)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mk(path, spec):
    """spec: {table: (schema_sql, [rows])}"""
    c = sqlite3.connect(path)
    for table, (schema, rows) in spec.items():
        c.execute(schema)
        if rows:
            marks = ','.join('?' * len(rows[0]))
            c.executemany(f'INSERT INTO "{table}" VALUES ({marks})', rows)
    c.commit()
    return c


GEAR_SQL = ('CREATE TABLE "GearDefinition" '
            '(id INTEGER PRIMARY KEY, name TEXT, teeth INT)')
GEAR = (GEAR_SQL, [(1, 'g12', 12), (2, 'g24', 24), (3, 'g36', 36)])
TRAIN = ('CREATE TABLE "GearTrainDefinition" '
         '(id INTEGER PRIMARY KEY, name TEXT)', [(1, 'clock')])
OTHER = ('CREATE TABLE "CeramicSample" '
         '(id INTEGER PRIMARY KEY, name TEXT)', [(1, 'not-a-gear')])
# A class the module does NOT own: core holds it and modules contribute
# named rows to it.
SHARED_SQL = ('CREATE TABLE "MaterialDefinition" '
              '(id INTEGER PRIMARY KEY, name TEXT)')

CLASSES = {'GearDefinition', 'GearTrainDefinition', 'GearTypeDefinition'}


def main():
    # ---- WHOLE: only the module's own classes move -------------------
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, 'a.db'), os.path.join(tmp, 'b.db')
        src = _mk(a, {'GearDefinition': GEAR, 'GearTrainDefinition': TRAIN,
                      'CeramicSample': OTHER})
        dst = _mk(b, {'CeramicSample': (OTHER[0], [])})

        entries = plan_move(src, dst, CLASSES)
        planned = {e[0] for e in entries}
        check('only the module\'s classes are planned',
              planned == {'GearDefinition', 'GearTrainDefinition'}, planned)
        check('a class with no table contributes nothing',
              'GearTypeDefinition' not in planned)

        moved = move_tables(src, dst, entries)
        check('both tables moved', len(moved) == 2, moved)
        check('rows arrived', _count(dst, 'GearDefinition') == 3)
        check('schema arrived (columns preserved)',
              [r[1] for r in dst.execute('PRAGMA table_info("GearDefinition")')]
              == ['id', 'name', 'teeth'])
        check('values arrived intact',
              dst.execute('SELECT teeth FROM "GearDefinition" ORDER BY id'
                          ).fetchall() == [(12,), (24,), (36,)])
        check('another module\'s table untouched at the destination',
              _count(dst, 'CeramicSample') == 0)
        check('another module\'s table stays in the source',
              'CeramicSample' in _tables(src))

        removed = drop_from_source(src, dst, moved)
        check('whole tables dropped from the source', len(removed) == 2
              and all('dropped' in r for r in removed), removed)
        check('source no longer has the module tables',
              not ({'GearDefinition', 'GearTrainDefinition'} & _tables(src)))

    # ---- SUBSET: a partitioned class moves only its named rows -------
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, 'a.db'), os.path.join(tmp, 'b.db')
        src = _mk(a, {'MaterialDefinition': (
            SHARED_SQL, [(1, 'steel'), (2, 'brass'), (3, 'kaolin')])})
        dst = _mk(b, {})
        subsets = {'MaterialDefinition': {'steel', 'brass'}}

        entries = plan_move(src, dst, set(), subsets)
        check('the partitioned class is planned as a subset',
              entries[0][1] == 'subset', entries)
        check('only the named rows are counted',
              entries[0][2] == 2, entries)

        moved = move_tables(src, dst, entries, subsets)
        check('only the named rows arrived',
              _names_in(dst, 'MaterialDefinition') == {'steel', 'brass'},
              _names_in(dst, 'MaterialDefinition'))

        removed = drop_from_source(src, dst, moved)
        check('the shared table is KEPT in the source',
              'MaterialDefinition' in _tables(src), removed)
        check('another module\'s row survives in the source',
              _names_in(src, 'MaterialDefinition') == {'kaolin'},
              _names_in(src, 'MaterialDefinition'))

    # ---- UNION: overlapping rows merge, never duplicate --------------
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, 'a.db'), os.path.join(tmp, 'b.db')
        src = _mk(a, {'MaterialDefinition': (
            SHARED_SQL, [(1, 'steel'), (2, 'brass')])})
        # the destination already pulled 'steel' as part of ANOTHER
        # module's dataset — the same instance, not a conflict
        dst = _mk(b, {'MaterialDefinition': (SHARED_SQL, [(7, 'steel')])})
        subsets = {'MaterialDefinition': {'steel', 'brass'}}

        entries = plan_move(src, dst, set(), subsets)
        check('overlap is reported as a merge, not a conflict',
              entries[0][4] == 'move' and entries[0][3] == 1
              and entries[0][2] == 1, entries)

        moved = move_tables(src, dst, entries, subsets)
        check('the union holds both rows',
              _names_in(dst, 'MaterialDefinition') == {'steel', 'brass'})
        check('the shared instance was NOT duplicated',
              _count(dst, 'MaterialDefinition') == 2,
              _count(dst, 'MaterialDefinition'))
        check('the pre-existing row was left as it was',
              dst.execute('SELECT id FROM "MaterialDefinition" '
                          'WHERE name = ?', ('steel',)).fetchone()[0] == 7)

        # idempotence: installing again resolves to the same union
        entries2 = plan_move(src, dst, set(), subsets)
        check('a second run has nothing left to insert',
              entries2[0][4] == 'skip: destination already holds the whole set',
              entries2)
        move_tables(src, dst, entries2, subsets)
        check('a second run does not duplicate anything',
              _count(dst, 'MaterialDefinition') == 2)

    # ---- an empty source is a no-op ----------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, 'a.db'), os.path.join(tmp, 'b.db')
        src = _mk(a, {'GearDefinition': (GEAR_SQL, [])})
        dst = _mk(b, {})
        entries = plan_move(src, dst, CLASSES)
        check('empty source table is skipped',
              entries[0][4] == 'skip: empty', entries)
        check('nothing moved', move_tables(src, dst, entries) == [])

    # ---- removal refuses when the destination lost rows --------------
    with tempfile.TemporaryDirectory() as tmp:
        a, b = os.path.join(tmp, 'a.db'), os.path.join(tmp, 'b.db')
        src = _mk(a, {'GearDefinition': GEAR})
        dst = _mk(b, {})
        moved = move_tables(src, dst, plan_move(src, dst, CLASSES))
        dst.execute('DELETE FROM "GearDefinition" WHERE name = ?', ('g12',))
        dst.commit()
        try:
            drop_from_source(src, dst, moved)
            check('removal refused when the destination lost rows', False,
                  'it removed anyway')
        except RuntimeError:
            check('removal refused when the destination lost rows', True)
            check('source survives the refusal',
                  _count(src, 'GearDefinition') == 3)

    # ---- the subset comes from the module bundle ---------------------
    bundle = json.dumps({'objects': {
        'MaterialDefinition': [{'name': 'steel'}, {'name': 'brass'}],
        'EmptyClass': [],
    }})
    got = subset_rows_from_bundle(bundle)
    check('bundle objects become the owned row names',
          got == {'MaterialDefinition': {'steel', 'brass'}}, got)
    check('a module with no bundle has no subsets',
          subset_rows_from_bundle(None) == {})

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
