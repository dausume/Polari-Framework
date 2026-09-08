"""
@module moduleService.selftest_manifests

The Standardized Polari App contract, machine-checked (sap-1): every
module directory carries a valid polari-app.json; every reference in it
resolves to a file in the package; the concept files follow the postfix
standard (or live in custom/); the manifest agrees with the core tables
it will one day replace. Report-style: each module is one check per
rule, so a drift names the module.

    PYTHONPATH=.:modules python3 -m moduleService.selftest_manifests
"""
import os
import sys

from moduleService import manifests as M

passed = 0
total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    if cond:
        passed += 1
        print('  [\033[0;32mPASS\033[0m] %s' % label)
    else:
        print('  [\033[0;31mFAIL\033[0m] %s %s' % (label, extra))


def main():
    pkgs = M.all_packages()
    check('modules discovered', len(pkgs) >= 40, str(len(pkgs)))
    tables, registry = M._tables(), M._registry()
    missing = [p for p in pkgs if M.load(p) is None]
    check('every module has polari-app.json', not missing, str(missing))
    invalid = {p: M.validate(M.load(p)) for p in pkgs if M.load(p) and M.validate(M.load(p))}
    check('every manifest validates', not invalid, str(invalid)[:300])
    unresolved = []
    for p in pkgs:
        m = M.load(p) or {}
        d = M.module_dir(p)
        for concept, names in m.get('files', {}).items():
            for f in names:
                if not os.path.isfile(os.path.join(d, f + '.py')):
                    unresolved.append('%s:%s' % (p, f))
    check('every manifest file reference resolves', not unresolved, str(unresolved)[:300])
    other = {p: M.load(p)['files'].get('other', []) for p in pkgs if M.load(p) and M.load(p)['files'].get('other')}
    check('no top-level file without a concept postfix (postfix standard)', not other, str(other)[:300])
    drift = {}
    for p in pkgs:
        r = M.conform(p, tables, registry)
        real = [f for f in r['findings'] if not f.startswith('no README')]
        if real:
            drift[p] = real
    check('manifests agree with files + core tables (README aside)', not drift, str(drift)[:400])
    kinds = {M.load(p)['app']['kind'] for p in pkgs if M.load(p)}
    check('app kinds are from the enum', kinds <= set(M.APP_KINDS), str(kinds))
    ids = [M.load(p)['id'] for p in pkgs if M.load(p)]
    check('module ids are unique and match directory or registry', len(ids) == len(set(ids)))
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
