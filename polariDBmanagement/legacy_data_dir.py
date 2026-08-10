"""
One-time relocation of sqlite files out of the legacy ./data directory.

DATABASE_PATH was never wired into the config loader, so the configured
volume path was ignored and every instance wrote its <Class>_DB.db files
to ./data — inside the container's writable layer rather than the mounted
volume. Recreating a container (a redeploy, or `isle polari module move`,
which recreates both backends) therefore threw the data away.

With the env var honored, the configured directory now points at the
mounted volume. An instance that already has data would otherwise boot
against an empty volume and come up FRESH, silently abandoning it. This
moves the databases across once so the instance restores its real state.
"""

import glob
import os
import shutil

LEGACY_DIR = './data'
DB_GLOB = '*_DB.db'


def migrate_legacy_data_dir(dbDir, legacyDir=LEGACY_DIR, log=print):
    """Move legacy sqlite databases into dbDir. Returns the count moved.

    Deliberately conservative:
      - no-op when dbDir IS the legacy dir (not relocated)
      - no-op when the destination already holds databases, so it can
        never overwrite newer state
      - copies first and only then renames the originals aside, so a
        failure midway leaves the originals intact and usable
    """
    legacy = os.path.abspath(legacyDir)
    dest = os.path.abspath(dbDir)

    if dest == legacy or not os.path.isdir(legacy):
        return 0
    if glob.glob(os.path.join(dest, DB_GLOB)):
        return 0

    legacyDBs = glob.glob(os.path.join(legacy, DB_GLOB))
    if not legacyDBs:
        return 0

    log(f'[DB] Migrating {len(legacyDBs)} database file(s) from the legacy '
        f'data dir {legacy} -> {dest}')

    copied = []
    try:
        os.makedirs(dest, exist_ok=True)
        for src in legacyDBs:
            dst = os.path.join(dest, os.path.basename(src))
            shutil.copy2(src, dst)
            copied.append((src, dst))
    except Exception as e:
        # Roll the partial copy back. The originals are untouched, so the
        # instance still boots off them at the old path.
        log(f'[DB] Legacy migration FAILED ({e}) — leaving originals in place')
        for _src, dst in copied:
            try:
                os.remove(dst)
            except OSError:
                pass
        return 0

    for src, _dst in copied:
        try:
            os.rename(src, src + '.migrated')
        except OSError:
            pass

    log(f'[DB] Migrated {len(copied)} database file(s); originals kept as '
        f'*.migrated')
    return len(copied)
