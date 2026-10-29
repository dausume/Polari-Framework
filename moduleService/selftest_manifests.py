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


def worker_contract(pkgs):
    """ea-0 (ELECTRONICS_APP_PLAN.md §1): engine `kind: worker` — vocabulary, catalog resolution, registrar piece,
    survival across regeneration."""
    import copy
    import types
    from islemesh.islemesh_catalog import resolve_worker_engines
    from moduleService.module_registrar import ModuleRegistrar, expected_from_manifest
    check('ea-0: engine kinds = system | python | worker', M.ENGINE_KINDS == ('system', 'python', 'worker'))
    used = {e.get('kind') for p in pkgs for e in ((M.load(p) or {}).get('requires') or {}).get('engines') or []}
    check('ea-0: every shipped manifest engine kind is in the vocabulary', used <= set(M.ENGINE_KINDS), str(used))
    good = {'name': 'board', 'kind': 'worker', 'tile': 'board-engines', 'placement': 'any-member'}
    usb = {'name': 'bridge', 'kind': 'worker', 'tile': 'bridge-engines', 'placement': 'with-usb-boards'}
    check('ea-0: a worker engine with tile + placement validates', M.engine_findings([good, usb]) == [])
    f = M.engine_findings([{'name': 'board', 'kind': 'worker'}])
    check('ea-0: a worker without a tile is refused, naming the tile', len(f) == 1 and '(tile)' in f[0], str(f))
    f = M.engine_findings([dict(good, placement='anywhere')])
    check('ea-0: an unknown placement is refused', len(f) == 1 and 'placement' in f[0], str(f))
    f = M.engine_findings([{'name': 'x', 'kind': 'container', 'probe': 'x'}])
    check('ea-0: an unknown engine kind is refused', len(f) == 1 and 'kind must be one of' in f[0], str(f))
    f = M.engine_findings([{'name': 'avr-gcc', 'kind': 'system', 'probe': 'avr-gcc', 'tile': 'board-engines'}])
    check('ea-0: tile on a system engine is refused', len(f) == 1 and 'belong to a worker' in f[0], str(f))
    m = copy.deepcopy(M.load('board'))
    m['requires']['engines'] = m['requires']['engines'] + [good]
    check('ea-0: a real manifest + a worker engine passes validate()', M.validate(m) == [], str(M.validate(m)))
    check('ea-0: worker_engines() lists only the worker entries', M.worker_engines(m) == [good])
    r = resolve_worker_engines([good, usb])
    check('ea-0: catalog resolves board -> board-engines (url, port, deploy step, binding key)',
          r[0]['ok'] and r[0]['url'] == 'https://board-engines.isle' and r[0]['port'] == 9830
          and r[0]['deploy'].startswith('isle app deploy board-engines ') and r[0]['deploy'].endswith('--engine board')
          and r[0]['binding'] == {'class': 'EngineProviderBinding', 'name': 'board'} and r[0]['bound'] is None, str(r[0]))
    check('ea-0: placement carried through (with-usb-boards on bridge; default any-member)',
          r[1]['ok'] and r[1]['placement'] == 'with-usb-boards'
          and resolve_worker_engines([{'name': 'pcb', 'kind': 'worker', 'tile': 'pcb-engines'}])[0]['placement'] == 'any-member')
    r = resolve_worker_engines([{'name': 'scope', 'kind': 'worker', 'tile': 'board-engines'},
                                {'name': 'x', 'kind': 'worker', 'tile': 'nope-engines'},
                                {'name': 'polari', 'kind': 'worker', 'tile': 'polari'}])
    check('ea-0: mismatched / missing / non-mesh-app tiles refuse with words',
          not any(x['ok'] for x in r) and "provides engine 'board', not 'scope'" in r[0]['refusal']
          and 'not in the isle catalog' in r[1]['refusal'] and 'not a mesh-app' in r[2]['refusal'] and r[0]['url'] == '',
          [x['refusal'] for x in r])
    r = resolve_worker_engines([good, usb], bindings={'board': 'https://board-engines.isle'})
    check('ea-0: live bindings mark bound / unbound', r[0]['bound'] is True and r[0]['bound_url'] and r[1]['bound'] is False)
    exp = expected_from_manifest('board', m, M.module_dir('board'))
    check('ea-0: registrar expects the worker piece', exp.get('workers') == {'engines': [{'name': 'board', 'tile': 'board-engines'}]},
          str(exp.get('workers')))
    row = types.SimpleNamespace(name='board', url='https://board-engines.isle')
    srv = types.SimpleNamespace(
        manager=types.SimpleNamespace(objectTypingDict={}, objectTables={'EngineProviderBinding': {'1': row}}),
        falconServer=types.SimpleNamespace(_router=types.SimpleNamespace(_roots=[])))
    reg = ModuleRegistrar(srv)
    reg._row('ea0probe')['expected'] = {'workers': {'engines': [{'name': 'board', 'tile': 'board-engines'},
                                                                 {'name': 'bridge', 'tile': 'bridge-engines'}]}}
    out = reg.verify('ea0probe')
    check('ea-0: registrar verify counts bound workers, names unbound ones, stays online',
          out['state'] == 'online' and out['confirmed'].get('workers') == {'count': 1, 'of': 2}
          and out['missing'].get('workers') == ['bridge (tile bridge-engines)'], str({k: out.get(k) for k in ('state', 'confirmed', 'missing')}))
    real_load = M.load
    try:
        M.load = lambda pkg: m if pkg == 'board' else real_load(pkg)
        fresh = M._preserve_hand_set('board', {'app': {}, 'requires': {'modules': [], 'engines': []}})
    finally:
        M.load = real_load
    check('ea-0: hand-set worker engines survive regeneration', M.worker_engines(fresh) == [good], str(fresh['requires']))


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
    # rtfix A: the hwnocode.Runtime gotcha (2026-10-04) — a class can be
    # correctly basis-exported and correctly named in FEATURE_IMPORT_BLOCKS
    # yet never make it into polariServer.py's literal defClassList, so
    # GET /<Class> 404s and its seed rows never land. Neither check above
    # (file resolution, manifest-vs-tables drift) catches this: both
    # compare the manifest's recorded 'imports' field against a FRESH
    # computation from the same FEATURE_IMPORT_BLOCKS table, so a name
    # missing from defClassList but consistently missing on both sides of
    # that comparison (as Runtime was) never shows up as drift.
    gaps = M.defclasslist_gaps(tables)
    check('every objects/ class is registered in polariServer.py defClassList',
          not gaps, str(gaps)[:400])
    ids = [M.load(p)['id'] for p in pkgs if M.load(p)]
    check('module ids are unique and match directory or registry', len(ids) == len(set(ids)))
    worker_contract(pkgs)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
