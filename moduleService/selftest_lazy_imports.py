"""
Selftest for mp-3 lazy feature-module loading (module_loading + the
guarded import blocks in polariApiServer/polariServer.py).

Run from polari-framework/:
    python3 -m moduleService.selftest_lazy_imports

The DRIFT GUARD half parses polariServer.py with ast and pins the
invariants the missing-module boot path depends on:
  - no top-level feature import sits outside a try/except guard;
  - every guard's stub tuple names EXACTLY the symbols its try
    block imports (someone adding an import must extend the stub);
  - every function-scope feature import sits under an
    ``if _feature_available('<that module>')`` gate (or the
    techtree backfill's availability check).

The UNIT half exercises module_loading's semantics directly.
"""

import ast
import os

from moduleService.module_loading import (
    CORE_REQUIRED_MODULES, FEATURE_MODULES, FEATURE_REQUIRES,
    feature_available, feature_downloaded, feature_import_error,
    missing_message, module_code_dir, stub_feature_symbols,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra else ''))


def _server_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'polariApiServer', 'polariServer.py')


def _feature_root(node):
    if isinstance(node, ast.ImportFrom) and node.level == 0:
        root = (node.module or '').split('.')[0]
        return root if root in FEATURE_MODULES else None
    return None


def _gate_names(test_node):
    """Module names passed to _feature_available in an if-test."""
    names = set()
    for sub in ast.walk(test_node):
        if (isinstance(sub, ast.Call)
                and getattr(sub.func, 'id', '') == '_feature_available'
                and sub.args and isinstance(sub.args[0], ast.Constant)):
            names.add(sub.args[0].value)
    return names


if __name__ == '__main__':
    print('== suite: drift guard over polariServer.py ==')
    tree = ast.parse(open(_server_path()).read())

    unguarded = [(_feature_root(n), n.lineno) for n in tree.body
                 if _feature_root(n)]
    check('no unguarded top-level feature imports',
          not unguarded, str(unguarded))

    plain = [a.name for n in ast.walk(tree)
             if isinstance(n, ast.Import) for a in n.names
             if a.name.split('.')[0] in FEATURE_MODULES]
    check('no plain "import <feature>" statements anywhere',
          not plain, str(plain))

    mismatches, mixed, guards = [], [], 0
    for node in tree.body:
        if not isinstance(node, ast.Try):
            continue
        imported, mods = [], set()
        for st in node.body:
            root = _feature_root(st)
            if root:
                mods.add(root)
                imported += [a.asname or a.name for a in st.names]
        if not mods:
            continue
        guards += 1
        if len(mods) > 1:
            mixed.append((node.lineno, mods))
        stubbed = None
        for h in node.handlers:
            for st in ast.walk(h):
                if (isinstance(st, ast.Call) and getattr(
                        st.func, 'id', '') == '_stub_missing_feature'):
                    stubbed = [ast.literal_eval(e)
                               for e in st.args[3].elts]
        if stubbed is None or set(imported) != set(stubbed):
            mismatches.append((node.lineno, sorted(mods)))
    check('found guarded feature-import blocks', guards >= 25,
          f'{guards} guards')
    check('every guard block is single-module', not mixed, str(mixed))
    check('every stub tuple matches its imports exactly',
          not mismatches, str(mismatches))

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

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    visit(item, frozenset())
        elif isinstance(node, ast.FunctionDef):
            visit(node, frozenset())
    check('every function-scope feature import is gated on its own '
          'module', not bad_gates, str(bad_gates))

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

    check('FEATURE_REQUIRES keys/values are known feature modules',
          all(k in FEATURE_MODULES and
              all(v in FEATURE_MODULES for v in vals)
              for k, vals in FEATURE_REQUIRES.items()))
    check('core-required movers are NOT in the lazy feature set',
          not (CORE_REQUIRED_MODULES & FEATURE_MODULES))

    failed = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failed)}/{len(_results)} checks '
          f'passed' + (f'; FAILED: {failed}' if failed else ''))
    raise SystemExit(1 if failed else 0)
