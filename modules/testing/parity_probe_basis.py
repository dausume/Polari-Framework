"""
The dialect-parity probe — one leg of substrate:dialect-parity.

Boots a manager WITH the database (hasDB=True) under whatever
DATABASE_TYPE the environment says, then exercises the exact seam
Dustin flagged in the dbcombo track: sqlite-affinity column defs as
the neutral interchange form, adapter-translated into the live
dialect (makeSQLiteTable -> translateColumnDefs), a real
saveInstanceInDB upsert, and a read-back. NOT vacuous — a leg that
never reached the DB reports created=False and the parity check
fails loudly. (The first draft of this check ran a hasDB=False
unittest file and "passed" identically on both dialects without
touching either — this probe replaces that.)

Run from polari-framework/ (the parity check runs it twice):
    DATABASE_TYPE=sqlite  python3 -m testing.parity_probe_basis
    DATABASE_TYPE=mariadb MARIADB_DATABASE=polari_objects_test \
        MARIADB_HOST=... python3 -m testing.parity_probe_basis

Prints one machine-readable line: PARITY_RESULT {json}.
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/parity_probe/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
import os
from objectTreeDecorators import treeObject, treeObjectInit

from testing.objects.parity_probe._shared import COLUMN_DEFS, TABLE  # noqa: F401
from testing.objects.parity_probe.Acct1ParityProbe import Acct1ParityProbe  # noqa: F401

import json

def main():
    from objectTreeManagerDecorators import managerObject
    manager = managerObject(hasDB=True)
    db = manager.db
    result = {'dialect': getattr(db.adapter, 'dialect', 'unknown'),
              'created': False, 'save_ok': False,
              'roundtrip': False, 'columns': []}
    if TABLE in (db.tables or []):
        db.dropTable(TABLE)
    db.makeSQLiteTable(tableName=TABLE, rowList=COLUMN_DEFS)
    result['created'] = TABLE in db.tables
    if result['created']:
        probe = Acct1ParityProbe(manager=manager, name='parity-1',
                                 count=7, ratio=2.5, note='acct1')
        result['save_ok'] = bool(db.saveInstanceInDB(probe))
        columns, rows = db.getAllInTable(TABLE)
        result['columns'] = sorted(
            c for c in columns
            if c not in ('_branch_path', '_instance_id'))
        for row in rows:
            record = dict(zip(columns, row))
            if (record.get('name') == 'parity-1'
                    and int(record.get('count') or 0) == 7
                    and abs(float(record.get('ratio') or 0)
                            - 2.5) < 1e-9
                    and record.get('note') == 'acct1'):
                result['roundtrip'] = True
        db.dropTable(TABLE)
    print('PARITY_RESULT ' + json.dumps(result), flush=True)
    ok = (result['created'] and result['save_ok']
          and result['roundtrip'])
    raise SystemExit(0 if ok else 1)
if __name__ == '__main__':
    main()
