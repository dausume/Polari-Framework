"""test_derive - selftest_sweep.derive on a tiny fixture tree: one app per class, and the two ways a mention must NOT count.

    python3 tools/selftest_sweep/test_derive.py
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import derive  # noqa: E402

_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print('  [%s] %s%s' % ('PASS' if cond else 'FAIL', label, ('  ' + str(extra)[:300]) if (extra and not cond) else ''))


def _app(root, pkg, selftests, packaged=(), files=None):
    d = os.path.join(root, 'modules', pkg)
    os.makedirs(os.path.join(d, 'custom'), exist_ok=True)
    json.dump({'package': pkg, 'selftests': list(selftests), 'files': {'selftests': list(packaged)}}, open(os.path.join(d, 'polari-app.json'), 'w'))
    for rel, body in (files or {}).items():
        open(os.path.join(d, rel), 'w').write(body)


def run():
    root = tempfile.mkdtemp(prefix='sweep-fixture-')
    try:
        _app(root, 'alpha', ['alpha_selftest'], files={
            'alpha_selftest.py': 'from alpha.custom.selftest_parts import parts\nimport alpha.custom.selftest_more\n',
            'custom/selftest_parts.py': 'from alpha.custom import selftest_deep\n',      # transitive
            'custom/selftest_more.py': '', 'custom/selftest_deep.py': ''})
        _app(root, 'beta', ['beta_selftest'], packaged=['beta_shipped_selftest'], files={
            'beta_selftest.py': '# from beta.beta_comment_selftest import x   (a comment)\n"""docstring: beta.beta_doc_selftest"""\n',
            'beta_shipped_selftest.py': '', 'beta_comment_selftest.py': '', 'beta_doc_selftest.py': ''})
        _app(root, 'gamma', ['gamma_selftest', 'gamma_gone_selftest'], files={
            'gamma_selftest.py': "RUNNERS = ['gamma.gamma_table_selftest']\nimport importlib\nimportlib.import_module('gamma.gamma_dyn_selftest')\n",
            'gamma_table_selftest.py': '', 'gamma_dyn_selftest.py': ''})
        os.makedirs(os.path.join(root, 'modules', 'alpha', 'custom', 'upstream'))
        open(os.path.join(root, 'modules', 'alpha', 'custom', 'upstream', 'vendor_selftest.py'), 'w').write('')
        n, rows = derive.classify(root)
        cls = {m: c for _p, m, c in rows}
        check('three apps found', n == 3, n)
        check('a listed selftest is listed', cls.get('alpha.alpha_selftest') == 'listed', cls)
        check('a direct `from ... import` covers', cls.get('alpha.custom.selftest_parts') == 'covered', cls)
        check('a plain `import app.mod` covers', cls.get('alpha.custom.selftest_more') == 'covered', cls)
        check('coverage is transitive (`from app.custom import mod` inside a covered file)', cls.get('alpha.custom.selftest_deep') == 'covered', cls)
        check('upstream/ is never swept', not any('vendor' in m for m in cls), cls)
        check('shipped in files.selftests but run by nothing -> PACKAGED-UNRUN', cls.get('beta.beta_shipped_selftest') == 'PACKAGED-UNRUN', cls)
        check('a COMMENT mention does not cover -> UNLISTED', cls.get('beta.beta_comment_selftest') == 'UNLISTED', cls)
        check('a DOCSTRING mention does not cover -> UNLISTED', cls.get('beta.beta_doc_selftest') == 'UNLISTED', cls)
        check('a runner-table entry covers', cls.get('gamma.gamma_table_selftest') == 'covered', cls)
        check('importlib.import_module covers', cls.get('gamma.gamma_dyn_selftest') == 'covered', cls)
        check('a listed name with no file -> MISSING-FILE', cls.get('gamma.gamma_gone_selftest') == 'MISSING-FILE', cls)
        import io, contextlib
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = derive.main(['derive', root])
        swept = {line.split()[1] for line in out.getvalue().splitlines()}
        check('main exits 1 when there is a finding', rc == 1, rc)
        check('the sweep list runs the omissions too (PACKAGED-UNRUN, UNLISTED), never the covered ones',
              {'beta.beta_shipped_selftest', 'beta.beta_comment_selftest'} <= swept and 'alpha.custom.selftest_parts' not in swept, swept)
        _app(root, 'beta', ['beta_selftest', 'beta_shipped_selftest', 'beta_comment_selftest', 'beta_doc_selftest'])
        _app(root, 'gamma', ['gamma_selftest'])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = derive.main(['derive', root])
        check('main exits 0 once every file is listed or covered', rc == 0, rc)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    total, ok = len(_results), sum(_results)
    print('\n%d/%d checks passed' % (ok, total))
    return ok == total


if __name__ == '__main__':
    sys.exit(0 if run() else 1)
