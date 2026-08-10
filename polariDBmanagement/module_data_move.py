"""
Move a module's TABLES between two instance databases.

`isle polari module move` relocates a module's LOADING — it rewrites
POLARI_MODULES on both instances and recreates the backends. The module's
DATA stayed behind in the origin's database. This is the missing half:
the module's tables move too, so the destination serves the same rows the
origin was serving.

Run it against two sqlite files (both instance volumes mounted):

    python3 -m polariDBmanagement.module_data_move \\
        --module gears --from /from/managerObject_DB.db \\
        --to /to/managerObject_DB.db [--apply] [--drop-source]

What belongs to a module is not guessed, and it is not always a whole
table. A module can own EITHER all the data of a class OR a named subset
of it, so there are two regimes and they move differently:

  WHOLE   the class is defined in the module's own package (the same rule
          module_gating.module_of_class uses). Every row is the module's.
          The table moves and is dropped from the source.

  SUBSET  the class belongs to core or another module, and this module
          contributes named rows to it — the `classRows` partitioning the
          module exporter describes, recorded in the module's bundle as
          objects: {Class: [rows keyed by name]}. Only those rows move,
          and only those rows are deleted from the source. The table
          itself is never dropped, because other modules' rows live in it.

Getting this wrong destroys data: treating a partitioned class as WHOLE
would carry other modules' rows to the destination and then drop them
from the source. A class with no table contributes nothing.

UNION, NOT OVERWRITE. A data instance belongs to strictly ONE module, but
several modules' datasets may reference the same instance — those
datasets define the UNION of the data. So a destination that already
holds some of these rows is not a conflict to refuse: it means another
module already pulled its share of the same set. Arriving rows are
therefore MERGED by identity (the `name` of the row within its class):
rows the destination lacks are inserted, rows it already has are left
alone. Installing the second module resolves the union rather than
duplicating it, and the operation is idempotent — running it twice adds
nothing the second time.

Safety properties, in order of importance:
  - the caller must quiesce first (stop the backends); this refuses to
    run against a database with an open WAL unless forced
  - existing destination rows are never overwritten or duplicated — a
    row already present is a merge, not a conflict
  - a table whose rows carry no identity cannot be merged, so it is only
    moved when the destination lacks it entirely; otherwise it is skipped
    and said so
  - the source is only removed after the destination is verified to hold
    every row that moved
  - --apply is required; the default is a dry run that reports the plan
"""

import argparse
import importlib
import json
import inspect
import os
import pkgutil
import sqlite3
import sys


def discover_module_classes(module_id, modules_path='/app/modules'):
    """Class names belonging to a module, by python package.

    Mirrors module_gating.module_of_class: a class belongs to the module
    whose top-level package it is defined in. selftest submodules are
    skipped — importing one runs it, and it calls SystemExit.
    """
    if modules_path and modules_path not in sys.path:
        sys.path.insert(0, modules_path)

    try:
        pkg = importlib.import_module(module_id)
    except Exception as e:
        raise RuntimeError(f'cannot import module package {module_id!r}: {e}')

    names = set()
    for sub in pkgutil.iter_modules(getattr(pkg, '__path__', [])):
        if sub.name.startswith('selftest'):
            continue
        try:
            mod = importlib.import_module(f'{module_id}.{sub.name}')
        except Exception:
            continue
        for obj in vars(mod).values():
            if (inspect.isclass(obj)
                    and (getattr(obj, '__module__', '') or '').split('.')[0]
                    == module_id):
                names.add(obj.__name__)
    return names


def _tables(conn):
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _schema_of(conn, table):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone()
    return row[0] if row else None


def _count(conn, table):
    return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def subset_rows_from_bundle(bundle):
    """{Class: {row name, ...}} the module contributes to classes it does
    not own outright — the exporter's `classRows` partitioning, as
    recorded in the module bundle's objects.

    Accepts a bundle dict or its JSON text; a module with no bundle
    simply has no subsets.
    """
    if not bundle:
        return {}
    if isinstance(bundle, str):
        try:
            bundle = json.loads(bundle)
        except ValueError:
            return {}
    objects = (bundle or {}).get('objects') or {}
    out = {}
    for cls, rows in objects.items():
        names = {str(r.get('name')) for r in rows
                 if isinstance(r, dict) and r.get('name') is not None}
        if names:
            out[cls] = names
    return out


def _columns(conn, table):
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def _count_named(conn, table, names):
    marks = ','.join('?' * len(names))
    return conn.execute(
        f'SELECT COUNT(*) FROM "{table}" WHERE "name" IN ({marks})',
        tuple(names)).fetchone()[0]


def _names_in(conn, table):
    return {r[0] for r in conn.execute(f'SELECT "name" FROM "{table}"')}


def _has_identity(conn, table):
    """Rows are merged by their `name` within a class. Without it, this
    module's rows cannot be told apart from anyone else's."""
    return 'name' in _columns(conn, table)


def plan_move(src_conn, dst_conn, class_names, subsets=None):
    """What would move: [(table, ownership, insert, merge, verdict)].

    ownership is 'whole' | 'subset'. `insert` is how many rows the
    destination lacks; `merge` is how many it already holds from the same
    set — those are the union overlap, left exactly as they are.

    A class named in BOTH places is treated as WHOLE: the module defines
    it, so the subset listing is redundant.
    """
    subsets = dict(subsets or {})
    for cls in class_names:
        subsets.pop(cls, None)

    src_tables = _tables(src_conn)
    dst_tables = _tables(dst_conn)
    plan = []

    def entry(table, ownership, owned_names):
        # No identity column: cannot merge, so only a destination that
        # lacks the table entirely can safely receive it.
        if not _has_identity(src_conn, table):
            if table in dst_tables:
                return (table, ownership, 0, 0,
                        'skip: rows carry no name — cannot merge into an '
                        'existing table')
            rows = _count(src_conn, table)
            return (table, ownership, rows, 0,
                    'move' if rows else 'skip: empty')

        if owned_names is None:                    # whole class
            owned = _names_in(src_conn, table)
        else:
            owned = owned_names & _names_in(src_conn, table)

        if not owned:
            return (table, ownership, 0, 0, 'skip: empty')

        present = (_names_in(dst_conn, table)
                   if table in dst_tables and _has_identity(dst_conn, table)
                   else set())
        merge = len(owned & present)
        insert = len(owned - present)
        if insert == 0:
            verdict = 'skip: destination already holds the whole set'
        elif merge:
            verdict = 'move'   # partial overlap — union resolves it
        else:
            verdict = 'move'
        return (table, ownership, insert, merge, verdict)

    for table in sorted(class_names & src_tables):
        plan.append(entry(table, 'whole', None))
    for table in sorted(set(subsets) & src_tables):
        plan.append(entry(table, 'subset', subsets[table]))
    return plan


def _owned_names(src_conn, table, ownership, subsets):
    if ownership == 'whole':
        return _names_in(src_conn, table)
    return subsets[table] & _names_in(src_conn, table)


def move_tables(src_conn, dst_conn, entries, subsets=None):
    """Merge every 'move' entry into the destination (union by identity).

    Returns [(table, ownership, owned_names_or_None, inserted, merged)].
    The destination table is created from the SOURCE's schema when
    absent, so the definition travels with the data.
    """
    subsets = subsets or {}
    moved = []
    for table, ownership, _insert, _merge, verdict in entries:
        if verdict != 'move':
            continue
        schema = _schema_of(src_conn, table)
        if not schema:
            raise RuntimeError(f'no schema for {table} in the source')
        if table not in _tables(dst_conn):
            dst_conn.execute(schema)

        cols = _columns(src_conn, table)
        collist = ','.join(f'"{c}"' for c in cols)
        marks = ','.join('?' * len(cols))

        if not _has_identity(src_conn, table):
            data = src_conn.execute(
                f'SELECT {collist} FROM "{table}"').fetchall()
            dst_conn.executemany(
                f'INSERT INTO "{table}" ({collist}) VALUES ({marks})', data)
            dst_conn.commit()
            moved.append((table, ownership, None, len(data), 0))
            continue

        owned = _owned_names(src_conn, table, ownership, subsets)
        present = _names_in(dst_conn, table)
        to_insert = sorted(owned - present)
        merged = len(owned & present)

        if to_insert:
            nmarks = ','.join('?' * len(to_insert))
            data = src_conn.execute(
                f'SELECT {collist} FROM "{table}" WHERE "name" IN ({nmarks})',
                tuple(to_insert)).fetchall()
            dst_conn.executemany(
                f'INSERT INTO "{table}" ({collist}) VALUES ({marks})', data)
        dst_conn.commit()

        # The union must now hold every owned row exactly once.
        after = _names_in(dst_conn, table)
        missing = owned - after
        if missing:
            raise RuntimeError(
                f'{table}: {len(missing)} owned row(s) missing after the '
                f'merge, e.g. {sorted(missing)[:3]}')
        dupes = _count(dst_conn, table) - len(after)
        if dupes:
            raise RuntimeError(f'{table}: merge produced {dupes} duplicate(s)')

        moved.append((table, ownership, owned, len(to_insert), merged))
    return moved


def drop_from_source(src_conn, dst_conn, moved):
    """Remove the moved content from the source, re-verifying first.

    Verification is repeated here rather than trusted from the merge
    step: this is the only irreversible action in the process.

    A WHOLE table is dropped. A SUBSET only has ITS OWN rows deleted —
    the table stays, because other modules' rows live in it.
    """
    removed = []
    for table, ownership, owned, _inserted, _merged in moved:
        if owned is None:
            # no identity column; verified by count instead
            if _count(dst_conn, table) < _count(src_conn, table):
                raise RuntimeError(
                    f'refusing to remove {table}: destination has fewer rows')
        else:
            missing = owned - _names_in(dst_conn, table)
            if missing:
                raise RuntimeError(
                    f'refusing to remove {table}: destination is missing '
                    f'{len(missing)} owned row(s)')

        if ownership == 'whole':
            src_conn.execute(f'DROP TABLE "{table}"')
            removed.append(f'{table} (table dropped)')
        else:
            names = tuple(sorted(owned))
            marks = ','.join('?' * len(names))
            src_conn.execute(
                f'DELETE FROM "{table}" WHERE "name" IN ({marks})', names)
            removed.append(
                f'{table} ({len(names)} rows deleted, table kept)')
    src_conn.commit()
    return removed


def _bundle_for_module(src_conn, module_id, bundle_path=None):
    """The module's bundle JSON — an explicit file, else the PolariModule
    row the instance already stores. Absent bundle = no partitioned
    classes, which is the common single-owner case.
    """
    if bundle_path:
        with open(bundle_path) as f:
            return f.read()
    if 'PolariModule' not in _tables(src_conn):
        return None
    if 'bundle_json' not in _columns(src_conn, 'PolariModule'):
        return None
    row = src_conn.execute(
        'SELECT bundle_json FROM "PolariModule" WHERE "name" = ?',
        (module_id,)).fetchone()
    return row[0] if row else None


def _warn_if_hot(path, force):
    """A -wal alongside the file means a writer may still be attached."""
    if os.path.exists(path + '-wal') and not force:
        raise SystemExit(
            f'ERROR {path} has an open WAL — quiesce the instance (stop its '
            f'backend) before moving data, or pass --force')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--module', required=True)
    ap.add_argument('--from', dest='src', required=True)
    ap.add_argument('--to', dest='dst', required=True)
    ap.add_argument('--modules-path', default='/app/modules')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--drop-source', action='store_true',
                    help='after a verified copy, drop the tables from the '
                         'source so this is a MOVE rather than a copy')
    ap.add_argument('--bundle', help='path to the module bundle JSON; '
                    'defaults to the PolariModule row in the source DB')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args(argv)

    if not os.path.exists(args.src):
        raise SystemExit(f'ERROR no such source database: {args.src}')
    _warn_if_hot(args.src, args.force)

    # The destination legitimately may not exist yet: an instance that has
    # never persisted anything has no database file until its first boot.
    # Creating it here lets a module move into a fresh instance.
    if not os.path.exists(args.dst):
        os.makedirs(os.path.dirname(args.dst) or '.', exist_ok=True)
        sqlite3.connect(args.dst).close()
        print(f'created destination database {args.dst}')
    else:
        _warn_if_hot(args.dst, args.force)

    classes = discover_module_classes(args.module, args.modules_path)

    src = sqlite3.connect(args.src)
    dst = sqlite3.connect(args.dst)

    subsets = subset_rows_from_bundle(
        _bundle_for_module(src, args.module, args.bundle))
    print(f'module {args.module}: {len(classes)} wholly-owned class(es), '
          f'{len(subsets)} partitioned class(es)')

    entries = plan_move(src, dst, classes, subsets)

    if not entries:
        print('NOTHING no tables for this module in the source database')
        return 0

    for table, ownership, insert, merge, verdict in entries:
        print(f'  {table:<28} {ownership:<7} insert={insert:<6} '
              f'merge={merge:<6} {verdict}')

    movable = [e for e in entries if e[4] == 'move']
    if not args.apply:
        print(f'\ndry run — {len(movable)} item(s) would move; '
              f'rerun with --apply')
        return 0
    if not movable:
        print('\nnothing to move')
        return 0

    moved = move_tables(src, dst, entries, subsets)
    print(f'\nMERGED {len(moved)} item(s): '
          f'{sum(m[3] for m in moved)} row(s) inserted, '
          f'{sum(m[4] for m in moved)} already present (union overlap)')

    if args.drop_source:
        removed = drop_from_source(src, dst, moved)
        for line in removed:
            print(f'REMOVED from source: {line}')
    else:
        print('source left intact (pass --drop-source to make it a move)')

    src.close()
    dst.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
