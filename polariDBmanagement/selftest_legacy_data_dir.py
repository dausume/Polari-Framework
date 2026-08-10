"""
Selftest for the sqlite data-dir wiring + legacy migration.

Run from polari-framework/:
  python3 -m polariDBmanagement.selftest_legacy_data_dir

Covers the bug this fixes: DATABASE_PATH had no entry in the config
loader's env mapping, so every compose file's DATABASE_PATH=/data/... was
dead and the sqlite files went to ./data inside the container layer — a
container recreate (redeploy, or `isle polari module move`, which
recreates both backends) threw the instance's data away.

Drives the REAL migrate_legacy_data_dir against real files: the relocate
case, the refuse-to-clobber case, the not-relocated no-op, the empty-
legacy no-op, and that a failure mid-copy leaves the originals usable.
"""

import os
import tempfile

from polariDBmanagement.legacy_data_dir import migrate_legacy_data_dir

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _db(path, content):
    with open(path, 'w') as f:
        f.write(content)


def _quiet(*_a, **_k):
    pass


def main():
    # ---- the env override is actually wired ------------------------
    from config_loader import ConfigLoader
    check('database.sqlite.path maps to DATABASE_PATH',
          ConfigLoader.ENV_VAR_MAPPING.get('database.sqlite.path')
          == 'DATABASE_PATH',
          ConfigLoader.ENV_VAR_MAPPING.get('database.sqlite.path'))

    # ---- relocate: legacy DBs move into an empty volume ------------
    with tempfile.TemporaryDirectory() as tmp:
        legacy = os.path.join(tmp, 'app-data')
        volume = os.path.join(tmp, 'volume')
        os.makedirs(legacy)
        os.makedirs(volume)
        _db(os.path.join(legacy, 'managerObject_DB.db'), 'live-state')
        _db(os.path.join(legacy, 'other_DB.db'), 'more-state')
        _db(os.path.join(legacy, 'notes.txt'), 'not a database')

        moved = migrate_legacy_data_dir(volume, legacy, log=_quiet)
        check('both databases migrated', moved == 2, moved)
        check('content preserved',
              os.path.exists(os.path.join(volume, 'managerObject_DB.db'))
              and open(os.path.join(volume,
                                    'managerObject_DB.db')).read()
              == 'live-state')
        check('originals kept as *.migrated, not deleted',
              os.path.exists(os.path.join(legacy,
                                          'managerObject_DB.db.migrated'))
              and not os.path.exists(os.path.join(legacy,
                                                  'managerObject_DB.db')))
        check('non-database files left alone',
              os.path.exists(os.path.join(legacy, 'notes.txt'))
              and not os.path.exists(os.path.join(volume, 'notes.txt')))

    # ---- refuse to clobber: destination already has state ----------
    with tempfile.TemporaryDirectory() as tmp:
        legacy = os.path.join(tmp, 'app-data')
        volume = os.path.join(tmp, 'volume')
        os.makedirs(legacy)
        os.makedirs(volume)
        _db(os.path.join(legacy, 'managerObject_DB.db'), 'stale-legacy')
        _db(os.path.join(volume, 'managerObject_DB.db'), 'NEWER-state')

        moved = migrate_legacy_data_dir(volume, legacy, log=_quiet)
        check('populated destination is a no-op', moved == 0, moved)
        check('newer destination state NOT overwritten',
              open(os.path.join(volume,
                                'managerObject_DB.db')).read() == 'NEWER-state')
        check('legacy original untouched when destination populated',
              os.path.exists(os.path.join(legacy, 'managerObject_DB.db')))

    # ---- no-ops -----------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        legacy = os.path.join(tmp, 'app-data')
        os.makedirs(legacy)
        _db(os.path.join(legacy, 'managerObject_DB.db'), 'state')
        check('dbDir == legacy dir is a no-op',
              migrate_legacy_data_dir(legacy, legacy, log=_quiet) == 0)
        check('legacy file still there after the no-op',
              os.path.exists(os.path.join(legacy, 'managerObject_DB.db')))

        empty = os.path.join(tmp, 'empty-legacy')
        os.makedirs(empty)
        check('empty legacy dir is a no-op',
              migrate_legacy_data_dir(os.path.join(tmp, 'vol'), empty,
                                      log=_quiet) == 0)
        check('missing legacy dir is a no-op',
              migrate_legacy_data_dir(os.path.join(tmp, 'vol'),
                                      os.path.join(tmp, 'nope'),
                                      log=_quiet) == 0)

    # ---- a failure mid-copy must leave the originals usable ---------
    with tempfile.TemporaryDirectory() as tmp:
        legacy = os.path.join(tmp, 'app-data')
        os.makedirs(legacy)
        _db(os.path.join(legacy, 'managerObject_DB.db'), 'live-state')
        # destination path exists as a FILE, so makedirs/copy blows up
        blocked = os.path.join(tmp, 'blocked')
        _db(blocked, 'i am a file, not a directory')

        moved = migrate_legacy_data_dir(blocked, legacy, log=_quiet)
        check('failed migration reports nothing moved', moved == 0, moved)
        check('originals still in place after a failed migration',
              os.path.exists(os.path.join(legacy, 'managerObject_DB.db'))
              and open(os.path.join(legacy,
                                    'managerObject_DB.db')).read()
              == 'live-state')

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks '
          f'passed' + (f'; FAILURES: {failures}' if failures else ''))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
