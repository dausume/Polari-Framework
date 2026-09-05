"""
Selftest for mp-3 lazy feature-module loading, dyn-1 form
(module_loading + the declarative tables that replaced the guarded
import blocks in polariApiServer/polariServer.py).

Run from polari-framework/:
    python3 -m moduleService.selftest_lazy_imports

The DRIFT GUARD half parses polariServer.py, feature_imports.py and
module_endpoints.py with ast and pins the invariants the
missing-module boot path AND live admission (dyn-2/4) depend on:
  - polariServer.py holds NO top-level feature imports any more —
    extending a module's imports means extending its
    FEATURE_IMPORT_BLOCKS entry, never re-inlining;
  - every FEATURE_IMPORT_BLOCKS entry is single-module (each import
    path's root package IS the entry's module name);
  - every import inside a module_endpoints constructor belongs to
    that constructor's module, and MODULE_ENDPOINT_CONSTRUCTORS maps
    exactly the construct_* functions defined;
  - every function-scope feature import left in polariServer.py sits
    under an ``if _feature_available('<that module>')`` gate.

The UNIT half exercises module_loading's semantics directly,
including the dyn-1 loader (import_feature_blocks) and the dyn-2/4
un-stub path (unstub_feature_module).
"""

import ast
import os

from moduleService.module_loading import (
    CORE_REQUIRED_MODULES, FEATURE_MODULES, FEATURE_REQUIRES,
    MISSING_FEATURE_MODULES, feature_available, feature_downloaded,
    feature_import_error, import_feature_blocks, missing_message,
    module_code_dir, stub_feature_symbols, unstub_feature_module,
)
from polariApiServer.feature_imports import FEATURE_IMPORT_BLOCKS

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra else ''))


def _pkg_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _parse(rel):
    return ast.parse(open(os.path.join(_pkg_dir(), rel)).read())


# Every module the table declares — the authoritative "feature" set
# for drift purposes (a superset of FEATURE_MODULES: registry-only
# modules like casting/composition/islemesh/pspp/video are extracted
# too, which the old guard could not see).
TABLE_MODULES = {m for m, _ in FEATURE_IMPORT_BLOCKS}


def _feature_root(node):
    if isinstance(node, ast.ImportFrom) and node.level == 0:
        root = (node.module or '').split('.')[0]
        return root if root in TABLE_MODULES else None
    return None


def _gate_names(test_node):
    names = set()
    for sub in ast.walk(test_node):
        if (isinstance(sub, ast.Call)
                and getattr(sub.func, 'id', '') == '_feature_available'
                and sub.args and isinstance(sub.args[0], ast.Constant)):
            names.add(sub.args[0].value)
    return names


if __name__ == '__main__':
    print('== suite: drift guard over polariServer.py ==')
    server = _parse(os.path.join('polariApiServer', 'polariServer.py'))

    inlined = [(_feature_root(n), n.lineno) for n in server.body
               if _feature_root(n)]
    check('no top-level feature imports re-inlined in polariServer.py',
          not inlined, str(inlined))

    plain = [a.name for n in ast.walk(server)
             if isinstance(n, ast.Import) for a in n.names
             if a.name.split('.')[0] in TABLE_MODULES]
    check('no plain "import <feature>" statements anywhere',
          not plain, str(plain))

    # Function-scope imports must sit under a matching gate.
    bad_gates = []

    def visit(node, gates):
        for child in ast.iter_child_nodes(node):
            child_gates = gates
            if isinstance(child, ast.If):
                child_gates = gates | _gate_names(child.test)
            root = _feature_root(child)
            if root is not None and root not in gates:
                bad_gates.append((root, child.lineno))
            visit(child, child_gates)

    for node in server.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    visit(item, frozenset())
        elif isinstance(node, ast.FunctionDef):
            visit(node, frozenset())
    check('every function-scope feature import in polariServer.py is '
          'gated on its own module', not bad_gates, str(bad_gates))

    print('== suite: drift guard over feature_imports.py ==')
    check('table is non-trivial', len(FEATURE_IMPORT_BLOCKS) >= 40,
          f'{len(FEATURE_IMPORT_BLOCKS)} blocks')
    mixed = []
    for module, imports in FEATURE_IMPORT_BLOCKS:
        roots = {path.split('.')[0] for path, _ in imports}
        if roots != {module}:
            mixed.append((module, sorted(roots)))
    check('every block is single-module (paths root == module name)',
          not mixed, str(mixed))
    empty = [m for m, imports in FEATURE_IMPORT_BLOCKS
             if not imports or any(not syms for _, syms in imports)]
    check('no empty blocks / empty symbol tuples', not empty, str(empty))

    print('== suite: drift guard over module_endpoints.py ==')
    endpoints = _parse(os.path.join('polariApiServer',
                                    'module_endpoints.py'))
    ctor_fns = {n.name: n for n in endpoints.body
                if isinstance(n, ast.FunctionDef)
                and n.name.startswith('construct_')}
    stray = []
    for name, fn in ctor_fns.items():
        module = name[len('construct_'):-len('_endpoints')]
        for sub in ast.walk(fn):
            if isinstance(sub, ast.ImportFrom):
                root = (sub.module or '').split('.')[0]
                if root != module:
                    stray.append((name, sub.module, sub.lineno))
    check('every constructor imports only from its own module',
          not stray, str(stray))
    mapping = {}
    for n in endpoints.body:
        if (isinstance(n, ast.Assign)
                and getattr(n.targets[0], 'id', '')
                == 'MODULE_ENDPOINT_CONSTRUCTORS'):
            mapping = {k.value: getattr(v, 'id', '')
                       for k, v in zip(n.value.keys, n.value.values)}
    check('MODULE_ENDPOINT_CONSTRUCTORS maps exactly the defined '
          'constructors',
          set(mapping.values()) == set(ctor_fns)
          and all(f'construct_{m}_endpoints' == fn
                  for m, fn in mapping.items()),
          f'{len(mapping)} mapped / {len(ctor_fns)} defined')

    print('== suite: module_loading semantics ==')
    check('a present module resolves a code dir (moduleService test '
          'uses biomining, moved in mp-1)',
          (module_code_dir('biomining') or '').endswith(
              os.path.join('modules', 'biomining')))
    check('an absent module is not downloaded',
          not feature_downloaded('definitely-not-a-module'))
    check('feature_available False for absent code',
          not feature_available('definitely-not-a-module'))
    check('missing_message names the pol command',
          'pol modules get nutrition' in missing_message('nutrition'))

    ns = {}
    stub_feature_symbols(ns, 'ghostmod',
                         ('SEED_THINGS', 'ThingDefinition'))
    check('stub: SEED_* -> [], classes -> None',
          ns['SEED_THINGS'] == [] and ns['ThingDefinition'] is None)

    raised = False
    try:
        feature_import_error('biomining', ImportError('broken code'))
    except ImportError:
        raised = True
    check('downloaded-but-broken module stays a LOUD ImportError',
          raised)
    check('absent module import error returns (caller stubs)',
          feature_import_error('definitely-not-a-module',
                               ImportError('x')) is True)

    print('== suite: dyn-1 loader + dyn-2/4 un-stub ==')
    ns = {}
    fake_blocks = (
        ('moduleService',
         (('moduleService.module_loading', ('FEATURE_MODULES',)),)),
        ('ghostmod2',
         (('ghostmod2.things', ('SEED_GHOSTS', 'GhostDefinition')),)),
    )
    import_feature_blocks(ns, fake_blocks)
    check('loader: present block binds the real symbol',
          ns.get('FEATURE_MODULES') is FEATURE_MODULES)
    check('loader: absent block stubs (SEED_* -> [], class -> None) '
          'and records the module',
          ns.get('SEED_GHOSTS') == [] and ns.get('GhostDefinition') is None
          and 'ghostmod2' in MISSING_FEATURE_MODULES)
    MISSING_FEATURE_MODULES.pop('ghostmod2', None)

    unstubbed = {}
    unstub_feature_module(unstubbed, 'moduleService', fake_blocks)
    check('un-stub: rebinds real symbols from the same declaration',
          unstubbed.get('FEATURE_MODULES') is FEATURE_MODULES)
    raised = False
    try:
        unstub_feature_module({}, 'ghostmod2', fake_blocks)
    except ImportError:
        raised = True
    check('un-stub of still-absent code raises LOUDLY', raised)
    raised = False
    try:
        unstub_feature_module({}, 'never-declared', fake_blocks)
    except KeyError:
        raised = True
    check('un-stub of an undeclared module refuses (KeyError)', raised)

    check('FEATURE_REQUIRES keys/values are known feature modules',
          all(k in FEATURE_MODULES and
              all(v in FEATURE_MODULES for v in vals)
              for k, vals in FEATURE_REQUIRES.items()))
    check('core-required movers are NOT in the lazy feature set',
          not (CORE_REQUIRED_MODULES & FEATURE_MODULES))
    check('every FEATURE_MODULES entry polariServer imports appears '
          'in the table',
          not ({'scoring', 'aquaponics', 'gears', 'motors'}
               - TABLE_MODULES))

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
