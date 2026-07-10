"""
@module polariDBmanagement.migrate_shared_db

One-time (idempotent, re-runnable) migration of an existing
schema-per-instance object database into shared-DB shape, so several
Polari instances can share its tables (POLARI_SHARED_OBJECT_DB=1):

  per object table:
    1. ADD COLUMN `_instance_id` VARCHAR(64) NOT NULL DEFAULT '<owner>'
       — the DEFAULT stamps every EXISTING row as belonging to the
       instance that owned the schema (back-compat: an unscoped
       legacy writer keeps landing as that owner, never as nobody).
    2. re-key the primary key to composite (pk…, _instance_id) so a
       second instance can hold the same id without clobbering.

Internal tables (leading '_', e.g. _dynamic_class_registry) are
SKIPPED — dynamic-class definitions are schema-level, shared by
design. Tables without a primary key just gain the column.

Run inside a backend container against the target DB (env
DATABASE_TYPE/MARIADB_*):

  python3 -m polariDBmanagement.migrate_shared_db --owner a [--apply]

Without --apply it PLANS only (knobs-and-suggestions: destructive
DDL runs only on the explicit flag).
"""

import argparse
import sys


def survey(adapter, conn, database):
    """[(table, pk_cols, has_instance_id)] for every user table."""
    out = []
    with conn.cursor() as cur:
        cur.execute(
            'SELECT table_name FROM information_schema.tables '
            'WHERE table_schema = %s ORDER BY table_name', (database,))
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            cur.execute(
                'SELECT column_name FROM '
                'information_schema.key_column_usage WHERE '
                'table_schema = %s AND table_name = %s AND '
                'constraint_name = "PRIMARY" ORDER BY '
                'ordinal_position', (database, t))
            pk = [r[0] for r in cur.fetchall()]
            cur.execute(
                'SELECT COUNT(*) FROM information_schema.columns '
                'WHERE table_schema = %s AND table_name = %s AND '
                'column_name = "_instance_id"', (database, t))
            has_col = cur.fetchone()[0] > 0
            out.append((t, pk, has_col))
    return out


def plan(rows, owner):
    """[(table, [DDL…])] — empty DDL list = already migrated."""
    steps = []
    for table, pk, has_col in rows:
        if table.startswith('_'):
            steps.append((table, [], 'internal table — shared by '
                                     'design, skipped'))
            continue
        ddl = []
        if not has_col:
            ddl.append(f'ALTER TABLE `{table}` ADD COLUMN '
                       f'`_instance_id` VARCHAR(64) NOT NULL '
                       f"DEFAULT '{owner}'")
        if pk and '_instance_id' not in pk:
            cols = ', '.join(f'`{c}`' for c in pk + ['_instance_id'])
            ddl.append(f'ALTER TABLE `{table}` DROP PRIMARY KEY, '
                       f'ADD PRIMARY KEY ({cols})')
        note = ('no primary key — column only' if not pk and ddl
                else '' if ddl else 'already migrated')
        steps.append((table, ddl, note))
    return steps


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Migrate an object DB to shared-instance shape.')
    parser.add_argument('--owner', default='a',
                        help="instance id that owns the existing rows "
                             "(default 'a')")
    parser.add_argument('--apply', action='store_true',
                        help='execute the DDL (default: plan only)')
    args = parser.parse_args(argv)

    from polariDBmanagement.db_adapter import make_adapter
    adapter = make_adapter(dbName='migration', dbDir='/tmp')
    if adapter.dialect != 'mariadb':
        print('REFUSED: shared-DB migration is a MariaDB operation '
              '(sqlite cannot re-key primary keys in place; a sqlite '
              'DB is single-instance by nature). Set DATABASE_TYPE='
              'mariadb + MARIADB_* env.')
        return 2

    conn = adapter.connect()
    rows = survey(adapter, conn, adapter.database)
    steps = plan(rows, args.owner)
    todo = [(t, ddl) for t, ddl, _ in steps if ddl]
    done = sum(1 for _, ddl, note in steps if not ddl
               and note == 'already migrated')
    skipped = [t for t, ddl, note in steps if 'skipped' in note]
    print(f'{adapter.database}: {len(rows)} tables — {len(todo)} to '
          f'migrate, {done} already migrated, skipped: {skipped}')

    if not args.apply:
        for t, ddl in todo[:10]:
            for d in ddl:
                print(f'  PLAN {d}')
        if len(todo) > 10:
            print(f'  … and {sum(len(d) for _, d in todo[10:])} more '
                  'statements')
        print('\nDry run — re-run with --apply to execute.')
        conn.close()
        return 0

    failures = []
    with conn.cursor() as cur:
        for t, ddl in todo:
            for d in ddl:
                try:
                    cur.execute(d)
                    conn.commit()
                except Exception as e:
                    # 1071 key-too-long: wide multi-varchar PKs (e.g.
                    # managedExecutable name+extension+Path, 255*4*3
                    # bytes) blow the 3072-byte InnoDB key limit once
                    # _instance_id joins. Retry with 100-char PREFIX
                    # key parts on the varchar columns — uniqueness
                    # beyond char 100 of any part is pathological for
                    # these registry tables, and full column widths
                    # are preserved.
                    if '1071' in str(e) and 'ADD PRIMARY KEY' in d:
                        pk = [c for _, c, _ in
                              [(0, x.strip(' `'), 0) for x in
                               d.split('(', 1)[1].rstrip(')')
                               .split(',')]]
                        parts = []
                        for c in pk:
                            parts.append(f'`{c}`' if c == '_instance_id'
                                         else f'`{c}`(100)')
                        retry = (f'ALTER TABLE `{t}` DROP PRIMARY '
                                 f'KEY, ADD PRIMARY KEY '
                                 f'({", ".join(parts)})')
                        try:
                            cur.execute(retry)
                            conn.commit()
                            print(f'  RETRIED {t} with prefix key '
                                  'parts — ok')
                            continue
                        except Exception as e2:
                            e = e2
                    failures.append((t, d, str(e)))
                    print(f'  FAILED {t}: {e}')
    conn.close()
    migrated = len(todo) - len({t for t, _, _ in failures})
    print(f'APPLIED: {migrated}/{len(todo)} tables migrated'
          + (f'; {len(failures)} failures' if failures else ''))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
