"""
@module board.custom.solution_rename_converge

The 2026-11-02 rename (BENCH_SOLUTION_SIM_PLAN D-bss-1: a System is a template, a Solution is a specific bound thing) moved two classes. Tables are named by
class, so an instance whose database still holds the OLD tables needs its rows brought across. This runs once per seed pass, in this order, and is idempotent
(a row whose name already exists in the new class is left as it is; a second run converges 0):

  1. the old `HardwareSolution` table's rows that have the cross-domain shape (a non-empty `cgraph` or `interface`) -> `HardwareNoCodeSolution` rows, same names
     (the hwnocode class was renamed from HardwareSolution; the name now belongs to the board class below).
  2. the table of the class renamed from HardwareSystem (its rows are the board's specific assemblies) -> `HardwareSolution` rows, same names.

NEVER deletes: the old tables and their rows stay where they are, and a row is copied with its id and every field the new class declares. The old table is
read by NAME through the managed DB (the class it belonged to is gone, so the restore pass skips that table as an unknown table). The same pattern as
the older BreadboardDefinition -> BenchBoard convergence, which is by name; unlike that one it also reads the stored rows, because these are user rows.

Known edge (said, not hidden): after the rename the restore pass loads the old cross-domain rows of the `HardwareSolution` table into the board class too
(same table name), where their cross-domain-only fields are dropped. They are converged from the DB copy read here, which still has every column.
"""
import inspect

OLD_SOLUTION = 'HardwareSolution'    # the table that held the cross-domain rows (renamed from HardwareSolution to HardwareNoCodeSolution)
NEW_CROSS = 'HardwareNoCodeSolution'
OLD_SYSTEM = 'HardwareSystem'        # the table that held the specific assemblies (renamed from HardwareSystem to HardwareSolution)
NEW_SOLUTION = 'HardwareSolution'    # the board class that took the name (renamed from HardwareSystem)
CROSS_MARKERS = ('cgraph', 'interface')
_SKIP_COLUMNS = ('_branch_path', '_instance_id')


def _table_names(db):
    return {(t[0] if isinstance(t, (tuple, list)) else t) for t in (getattr(db, 'tables', None) or [])}


def _read(manager, table):
    """[row dict, ...] of the stored table, or None when the table is not there. Reads only."""
    db = getattr(manager, 'db', None)
    if db is None or table not in _table_names(db):
        return None
    try:
        columns, rows = db.getAllInTable(table)
    except Exception as e:  # noqa: BLE001 - a table we cannot read is left alone
        print(f'[SolutionRename] could not read table {table}: {e}', flush=True)
        return None
    return [{c: v for c, v in zip(columns, r) if c not in _SKIP_COLUMNS} for r in rows]


def _class(manager, name):
    typing = (getattr(manager, 'objectTypingDict', None) or {}).get(name)
    return typing.getCreateMethod() if typing is not None else None


def _is_cross_domain(row):
    return any(str(row.get(k) or '').strip() for k in CROSS_MARKERS)


def _copy_rows(manager, rows, target):
    """Create a `target` row for every stored row whose name is not there yet; returns (converged, already_there)."""
    create = _class(manager, target)
    table = manager.objectTables.setdefault(target, {})
    have = {getattr(o, 'name', None) for o in table.values()}
    ids = {getattr(o, 'id', None) for o in table.values()}
    accepted = set(inspect.signature(create).parameters)
    done = there = 0
    for row in rows:
        name = row.get('name')
        if not name:
            continue
        if name in have:
            there += 1
            continue
        kwargs = {k: v for k, v in row.items() if k in accepted and v is not None and k != 'id'}
        if row.get('id') and row['id'] not in ids:
            kwargs['id'] = row['id']
        create(**kwargs, manager=manager)
        have.add(name)
        done += 1
    return done, there


def converge(manager):
    """Run both steps (in order). Returns {'cross_domain': n, 'hardware_solution': m} - the rows each step converged."""
    out = {'cross_domain': 0, 'hardware_solution': 0}
    if manager is None or getattr(manager, 'db', None) is None:
        return out
    steps = (('cross_domain', OLD_SOLUTION, NEW_CROSS, _is_cross_domain), ('hardware_solution', OLD_SYSTEM, NEW_SOLUTION, None))
    for key, old, new, keep in steps:
        if _class(manager, new) is None:
            continue  # the owning module is not admitted yet; the next seed pass does this step
        stored = _read(manager, old)
        if stored is None:
            continue
        rows = [r for r in stored if keep is None or keep(r)]
        done, there = _copy_rows(manager, rows, new)
        out[key] = done
        if key == 'cross_domain':
            # the restore pass loaded these same hardware no-code rows into the board class too (same table name): take those ghosts out of the
            # TREE only - their stored rows stay, and HardwareNoCodeSolution now holds them whole
            names = {r.get('name') for r in rows}
            table = manager.objectTables.get(NEW_SOLUTION, {}) or {}
            ghosts = [k for k, o in table.items() if getattr(o, 'name', None) in names]
            for k in ghosts:
                table.pop(k, None)
            if ghosts:
                print(f'[SolutionRename] {len(ghosts)} hardware no-code row(s) taken out of the {NEW_SOLUTION} tree (their stored rows are untouched)', flush=True)
        print(f'[SolutionRename] {old} -> {new}: {done} row(s) converged, {there} already there '
              f'({len(rows)} of {len(stored)} stored row(s) matched; the old table is left in place)', flush=True)
    return out
