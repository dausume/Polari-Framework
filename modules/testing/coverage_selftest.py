"""testing.coverage_selftest — the hierarchy/set-cover algorithm on a
synthetic graph + the real manifests; the benchmark runner's parsing
is exercised without docker."""
import sys

from testing.custom import app_hierarchy as H

passed = total = 0


def check(label, cond, extra=''):
    global passed, total
    total += 1
    passed += bool(cond)
    print('  [%s] %s %s' % ('\033[0;32mPASS\033[0m' if cond else '\033[0;31mFAIL\033[0m', label, extra if not cond else ''))


def main():
    g = {'a': {'requires': ['b'], 'classes': 10, 'libraries_mb': 0, 'engines': [], 'kind': 'polari-app', 'package': 'a'},
         'b': {'requires': [], 'classes': 5, 'libraries_mb': 0, 'engines': [], 'kind': 'library', 'package': 'b'},
         'c': {'requires': [], 'classes': 20000, 'libraries_mb': 0, 'engines': [{'name': 'x', 'kind': 'system'}], 'kind': 'polari-app', 'package': 'c'},
         'd': {'requires': ['a'], 'classes': 3, 'libraries_mb': 0, 'engines': [], 'kind': 'polari-app', 'package': 'd'}}
    check('closure is transitive', H.closure('d', g) == {'d', 'a', 'b'})
    apps = H.app_catalog([{'name': 'big', 'modules': ['d', 'zzz']}, {'name': 'small', 'modules': ['b']}], g)
    big = next(a for a in apps if a['name'] == 'big')
    check('unknown module names are kept aside, not dropped', big['unknown'] == ['zzz'] and big['closure'] == ['a', 'b', 'd'])
    check('upstream index finds the containing apps', set(H.upstream_index(apps)['b']) >= {'big', 'small', 'module:b'})
    check('largest apps ranks by closure', H.largest_apps(apps)[0]['name'] == 'big')
    est = H.estimate(big, g)
    check('declared estimate is labelled', est['fidelity'] == 'declared' and est['classes'] == 18)
    huge = H.estimate(next(a for a in apps if a['name'] == 'module:c'), g)
    ok, why = H.fits(huge, H.DEFAULT_BUDGET)
    check('20000 classes does not fit the standard budget, reason named', not ok and 'ram' in why[0])
    b = {'big': {'ok': True, 'peak_rss_mb': 512, 'boot_seconds': 12, 'image_mb': 900, 'code_mb': 1, 'classes': 18, 'oom_killed': False}}
    check('a benchmark wins over the estimate', H.estimate(big, g, b)['fidelity'] == 'benchmark' and H.estimate(big, g, b)['ram_mb'] == 512)
    p = H.plan(apps, g, H.DEFAULT_BUDGET, b, None, [], None)
    check('set cover picks the big app and not the redundant small one', p['chosen'][0] == 'big' and 'small' not in p['chosen'])
    check('module c is uncovered with no nodes', p['modules']['c']['verdict'] == 'uncovered')
    node = {'name': 'bignode', 'logical_cpus': 32, 'total_ram_mb': 64000, 'free_disk_mb': 500000}
    p2 = H.plan(apps, g, H.DEFAULT_BUDGET, b, None, [node], None)
    check('a capable node makes it covered-distributed, node named', p2['modules']['c']['verdict'] == 'covered-distributed' and p2['modules']['c']['nodes'] == ['bignode'])
    p3 = H.plan(apps, g, H.DEFAULT_BUDGET, b, None, [], node)
    check('a large host makes it covered-large-host', p3['modules']['c']['verdict'] == 'covered-large-host')
    graph, seeds, bench = H.load_inputs()
    check('real manifests load into the graph', len(graph) >= 40)
    real = H.plan(H.app_catalog(seeds, graph), graph, H.DEFAULT_BUDGET, bench, None, [], None)
    check('the real plan covers every module one way or another (declared)', real['counts']['uncovered'] == 0, str(real['uncovered']))
    check('largest real app has a closure > its direct modules or equal', real['largest'][0]['closure'] >= 1)
    print('\n%d/%d checks passed' % (passed, total))
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
