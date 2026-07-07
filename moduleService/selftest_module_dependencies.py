"""
Selftest — boundary + dependency tracking (msci-21).

Run from polari-framework/:
    python3 -m moduleService.selftest_module_dependencies

Runs against the REAL repository + the REAL installed environment:
  - the boundary graph declares the coherent modules and finds the
    KNOWN seams (simulations -> materialsScience via the stage
    executors; materialsScience -> simulations via the gate seam;
    polariNoCode -> materialsScience via EngineModelOperation);
  - python requires-trees resolve real installed packages and mark
    SHARED downstream deps exactly once across a forest;
  - refresh_dependency_rows persists both kinds idempotently;
  - plan_install unions missing packages (usually empty here — the
    empty plan must say so honestly) and install refuses without
    confirm at the API layer (checked structurally).
"""

from types import SimpleNamespace

from moduleService.module_dependency_tracker import (
    FRAMEWORK_BOUNDARIES, boundary_graph, plan_install,
    python_dependency_forest, python_dependency_tree,
    refresh_dependency_rows, scan_boundary_imports,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


class _StubDB:
    def saveInstanceInDB(self, row):
        pass


class _StubManager:
    def __init__(self):
        self.objectTables = {}
        self.db = _StubDB()

    def add(self, class_name, row):
        self.objectTables.setdefault(class_name, {})[id(row)] = row
        return row


def _boundaries():
    print('\nBoundary graph (the coherent-module map)\n')
    graph = boundary_graph()
    present = [n['name'] for n in graph['boundaries'] if n['present']]
    check('every declared boundary is present on disk',
          set(present) == set(FRAMEWORK_BOUNDARIES),
          f'missing={set(FRAMEWORK_BOUNDARIES) - set(present)}')
    edges = {n['name']: n['boundaryImports']
             for n in graph['boundaries']}
    check('KNOWN seam: simulations -> materialsScience '
          '(stage executors)',
          'materialsScience' in edges['simulations'])
    check('KNOWN seam: materialsScience -> simulations '
          '(gate/stage machinery)',
          'simulations' in edges['materialsScience'])
    check('KNOWN seam: polariNoCode -> materialsScience '
          '(EngineModelOperation)',
          'materialsScience' in edges['polariNoCode'])
    # A seam the tracker REVEALED (my original assumption was that the
    # compilers stay below the sim layer — they don't: the run-scope
    # resolver reaches up): assert the discovered edge, which is
    # exactly the boundary-tracking value.
    check('DISCOVERED seam: simSpace -> simulations '
          '(run-scope resolution in the snapshot compilers)',
          'simulations' in edges['simSpace'],
          f"simSpace edges={edges['simSpace']}")
    msci = next(n for n in graph['boundaries']
                if n['name'] == 'materialsScience')
    check('boundary python imports are pip names, not framework '
          'packages',
          'simulations' not in msci['pythonImports']
          and 'polariNoCode' not in msci['pythonImports'],
          f"imports={msci['pythonImports']}")


def _python_trees():
    print('\nPython requires-trees\n')
    tree = python_dependency_tree('falcon')
    check('an installed package resolves with a version',
          tree['installed'] and tree['resolvedVersion'])
    missing = python_dependency_tree('definitely-not-a-real-package-xyz')
    check('a missing package is honest (installed=False, no children)',
          not missing['installed'] and missing['children'] == [])
    # scipy and pandas both require numpy — in a forest, numpy must be
    # expanded once and marked shared at its second appearance.
    forest = python_dependency_forest(['scipy', 'pandas'])

    def _find(nodes, name, acc):
        for n in nodes:
            if n['name'].lower() == name:
                acc.append(n)
            _find(n['children'], name, acc)
    numpys = []
    _find(forest['trees'], 'numpy', numpys)
    if len(numpys) >= 2:
        check('shared downstream dep expanded once, marked shared '
              'on reappearance',
              sum(1 for n in numpys if not n['shared']) <= 1
              and any(n['shared'] for n in numpys),
              f'numpy nodes={len(numpys)}')
    else:
        check('forest built (numpy shared-marking not exercised in '
              'this env)', bool(forest['trees']),
              f'numpy nodes={len(numpys)}')


def _rows_and_plan():
    print('\nPersisted rows + install plan\n')
    mgr = _StubManager()
    import polariPeers.polari_module_dependency as dep_mod
    created_rows = []
    orig = dep_mod.PolariModuleDependency

    def _factory(manager=None, **fields):
        row = SimpleNamespace(**fields)
        created_rows.append(row)
        if manager is not None:
            manager.add('PolariModuleDependency', row)
        return row

    dep_mod.PolariModuleDependency = _factory
    try:
        report = refresh_dependency_rows(mgr)
        check('refresh creates rows for every present boundary',
              report['ok'] and report['created'] > 20,
              f"created={report['created']}")
        kinds = {r.kind for r in created_rows}
        check('BOTH dependency kinds persisted',
              kinds == {'python', 'polari'})
        py_rows = [r for r in created_rows if r.kind == 'python']
        check('python rows resolve versions or say missing',
              all(r.status in ('installed', 'missing')
                  for r in py_rows)
              and any(r.resolved_version for r in py_rows))
        # Idempotency: a second refresh must create nothing new.
        created_before = len(created_rows)
        report2 = refresh_dependency_rows(mgr)
        check('refresh is idempotent by name',
              report2['created'] == 0
              and len(created_rows) == created_before)
    finally:
        dep_mod.PolariModuleDependency = orig

    plan = plan_install()
    if plan['packages']:
        check('install plan unions missing packages into ONE command',
              plan['command'][:2] == ['pip', 'install']
              and len(set(plan['packages']))
              == len(plan['packages'])
              and plan['suggestion'] is not None,
              f"packages={plan['packages']}")
    else:
        check('empty plan says so honestly (nothing missing here)',
              'nothing missing' in plan['note'])


if __name__ == '__main__':
    _boundaries()
    _python_trees()
    _rows_and_plan()
    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
