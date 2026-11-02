"""board_solution_rename_selftest — the 2026-11-02 rename (D-bss-1): the old HardwareSolution table's cross-domain rows -> HardwareNoCodeSolution, and the table of the class
renamed from HardwareSystem -> HardwareSolution, by name, never deleting, idempotent. A fake manager holds old-shaped stored rows; nothing else is needed.

Run from polari-framework/:  PYTHONPATH=.:modules python3 -m board.board_solution_rename_selftest
"""
import contextlib
import io

COLS_OLD_SOLUTION = ['id', 'name', 'title', 'cgraph', 'interface', 'firmware_runtime', 'solution', '_branch_path']
COLS_OLD_SYSTEM = ['id', 'name', 'title', 'stage', 'participants_json', 'notes', '_branch_path']


class _Typing:
    def __init__(self, cls):
        self.cls = cls

    def getCreateMethod(self):
        return self.cls


class _DB:
    def __init__(self, stored):
        self.stored = stored                      # {table: (columns, [row tuples])}
        self.tables = list(stored) + ['SomethingElse']
        self.reads = []

    def getAllInTable(self, name):
        self.reads.append(name)
        cols, rows = self.stored[name]
        return cols, tuple(rows)


class _Manager:
    def __init__(self, db, classes):
        self.db = db
        self.objectTables = {}
        self.objectTypingDict = {n: _Typing(c) for n, c in classes.items()}


def _names(m, cls):
    return sorted(getattr(o, 'name', '') for o in (m.objectTables.get(cls) or {}).values())


def run_solution_rename(check):
    from board.board_basis import HardwareSolution
    from board.custom import solution_rename_converge as SRC
    from hwnocode.objects.hwnocode.HardwareNoCodeSolution import HardwareNoCodeSolution
    OLD_SYSTEM = SRC.OLD_SYSTEM
    stored = {
        'HardwareSolution': (COLS_OLD_SOLUTION, [
            ('id-a', 'uno-temp-split', 'Temp split', 'uno-sim-rig-graph', 'uno-iface', 'bare-c', 'canvas-a', None),
            ('id-b', 'uno-button-clock', 'Button clock', 'button-graph', '', 'bare-c', 'canvas-b', None),
            ('id-c', 'iface-only', 'Iface only', '', 'some-binding', 'bare-c', '', None),
            ('id-d', 'a-board-row', 'No cross-domain fields', '', '', '', '', None)]),
        OLD_SYSTEM: (COLS_OLD_SYSTEM, [  # the table of the class renamed from HardwareSystem
            ('id-s1', 'uno-light-system', 'UNO light', 'S1-breadboard', '[{"role": "u1"}]', 'kept', None),
            ('id-s2', 'my-own-assembly', 'Mine', 'S2-protoboard', '[]', 'user row', None)]),
    }
    db = _DB(stored)
    m = _Manager(db, {'HardwareNoCodeSolution': HardwareNoCodeSolution, 'HardwareSolution': HardwareSolution})
    with contextlib.redirect_stdout(io.StringIO()) as log:
        first = SRC.converge(m)
    check('rename: step 1 converges the 3 cross-domain-shaped rows (cgraph or interface) and leaves the board-shaped one', first['cross_domain'] == 3
          and _names(m, 'HardwareNoCodeSolution') == ['iface-only', 'uno-button-clock', 'uno-temp-split'], str(first))
    row = next(o for o in m.objectTables['HardwareNoCodeSolution'].values() if o.name == 'uno-temp-split')
    check('rename: a converged row keeps its id and every field the new class declares (cgraph, interface, firmware_runtime, solution, title)',
          (row.id, row.cgraph, row.interface, row.firmware_runtime, row.solution, row.title) == ('id-a', 'uno-sim-rig-graph', 'uno-iface', 'bare-c', 'canvas-a', 'Temp split'))
    check('rename: step 2 converges the 2 rows of the old system table into HardwareSolution, same names',
          first['hardware_solution'] == 2 and _names(m, 'HardwareSolution') == ['my-own-assembly', 'uno-light-system'], str(first))
    r2 = next(o for o in m.objectTables['HardwareSolution'].values() if o.name == 'uno-light-system')
    check('rename: the system row keeps id + stage + participants_json + notes', (r2.id, r2.stage, r2.participants_json, r2.notes) == ('id-s1', 'S1-breadboard', '[{"role": "u1"}]', 'kept'))
    text = log.getvalue()
    check('rename: one log line per step says how many rows converged', '3 row(s) converged' in text and '2 row(s) converged' in text, text.strip().splitlines()[-1] if text.strip() else '')
    with contextlib.redirect_stdout(io.StringIO()):
        second = SRC.converge(m)
    check('rename: a second run changes nothing (0 + 0, no new rows)', second == {'cross_domain': 0, 'hardware_solution': 0}
          and len(m.objectTables['HardwareNoCodeSolution']) == 3 and len(m.objectTables['HardwareSolution']) == 2, str(second))
    check('rename: the stored tables are untouched (read only: the DB double has no write path, rows unchanged)',
          len(stored['HardwareSolution'][1]) == 4 and len(stored[OLD_SYSTEM][1]) == 2 and set(db.reads) == {'HardwareSolution', OLD_SYSTEM})
    m2 = _Manager(_DB(stored), {'HardwareSolution': HardwareSolution})   # hwnocode not admitted yet: step 1 waits, step 2 still runs
    with contextlib.redirect_stdout(io.StringIO()):
        third = SRC.converge(m2)
    check('rename: with the hwnocode class not admitted yet, step 1 is deferred (0) and step 2 still converges', third == {'cross_domain': 0, 'hardware_solution': 2}, str(third))
    m3 = _Manager(_DB({}), {'HardwareNoCodeSolution': HardwareNoCodeSolution, 'HardwareSolution': HardwareSolution})
    check('rename: a fresh database (no old tables) converges nothing and says nothing', SRC.converge(m3) == {'cross_domain': 0, 'hardware_solution': 0})


if __name__ == '__main__':
    import sys
    results = []

    def _check(label, cond, extra=''):
        results.append(bool(cond))
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra))
    run_solution_rename(_check)
    print('%d/%d passed' % (sum(results), len(results)))
    sys.exit(0 if all(results) else 1)
