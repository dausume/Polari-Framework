"""
@module testing.custom.app_hierarchy

The algorithm (tcov-1): modules → apps hierarchy, upstream lookup, the
largest apps by module closure, estimate-or-benchmark against a
StandardComputerBudget, and a greedy weighted set cover that picks the
smallest set of apps whose tests cover every module — then, for modules
no fitting app covers, whether other nodes (swarm / isle) or a large
host make them testable. Pure: takes plain dicts, runs on the host
(`pol modules testplan`) or inside the backend (the API); the only
inputs are the manifests, the app definitions, benchmarks and nodes.

Estimates are DECLARED constants (labelled) until a benchmark row for
the same app exists; a benchmark always wins. Constants are calibrated
from measured boots (2026-09-08: a 10-module sqlite boot, 677 classes,
health in ~10 s; the full 24-module staging on MariaDB: 744 MiB RSS).
"""
import json
import os
import subprocess

#: DECLARED estimate model — replaced per app by a benchmark row.
ESTIMATE = {
    'base_ram_mb': 300.0,        # the backend with core packages only (declared)
    'per_class_ram_mb': 0.45,    # 744 MiB @ ~1075 classes → ~0.41 MB/class above base (declared)
    'base_boot_s': 6.0,
    'per_class_boot_s': 0.02,    # sqlite boot: 677 classes in ~10 s (measured 2026-09-08)
    'image_mb': 966.0,           # prf-backend:staging (measured)
    'engine_image_mb': 2200.0,   # a heavy engine image (msci/cnt class) when an engine is 'image' kind
    'fidelity': 'declared',
}
DEFAULT_BUDGET = {'name': 'standard', 'cores': 2, 'vcpus': 4, 'ram_mb': 4096.0,
                  'disk_mb': 32768.0, 'boot_timeout_s': 900}


# ------------------------------------------------------------ the graph

def module_graph(manifests):
    """{module_id: {'requires': [...], 'classes': n, 'libraries_mb': x,
    'engines': [...], 'kind': app kind, 'package': pkg}} from the
    polari-app.json manifests (moduleService.manifests.all_manifests)."""
    g = {}
    for pkg, m in manifests.items():
        req = m.get('requires', {})
        libs = req.get('libraries', []) or []
        lib_mb = sum((l.get('bytes') or 0) for l in libs if isinstance(l, dict)) / 1e6
        g[m.get('id', pkg)] = {
            'package': pkg, 'requires': list(req.get('modules', []) or []),
            'classes': len(m.get('classes', []) or []), 'libraries_mb': round(lib_mb, 1),
            'engines': list(req.get('engines', []) or []), 'kind': (m.get('app') or {}).get('kind', 'library'),
            'core_required': bool(m.get('coreRequired')),
        }
    return g


def closure(module, graph, _seen=None):
    """The module plus everything it requires, transitively (known ids only)."""
    seen = _seen if _seen is not None else set()
    if module in seen or module not in graph:
        return seen
    seen.add(module)
    for dep in graph[module]['requires']:
        closure(dep, graph, seen)
    return seen


def app_catalog(seed_apps, graph, instances=None, include_singletons=True):
    """Every candidate 'app' with its module closure:
    - seeded apps (PolariAppDefinition rows / SEED_POLARI_APPS)
    - topology instances (name → assigned modules), kind 'instance'
    - module singletons `module:<id>` (the smallest app covering one module)
    Unknown module names (not a registry id) are kept aside, never silently dropped."""
    apps = []
    def entry(name, kind, modules):
        known = [m for m in modules if m in graph]
        unknown = [m for m in modules if m not in graph]
        cl = set()
        for m in known:
            closure(m, graph, cl)
        return {'name': name, 'kind': kind, 'modules': known, 'unknown': unknown,
                'closure': sorted(cl)}
    for a in seed_apps or []:
        mods = a.get('modules') if isinstance(a.get('modules'), list) else json.loads(a.get('modules_json', '[]') or '[]')
        apps.append(entry(a['name'], 'app', mods))
    for name, mods in (instances or {}).items():
        apps.append(entry('instance:' + name, 'instance', list(mods)))
    if include_singletons:
        for m in sorted(graph):
            apps.append(entry('module:' + m, 'module', [m]))
    return apps


def upstream_index(apps):
    """module → [app names whose CLOSURE contains it] (the 'look upstream')."""
    idx = {}
    for a in apps:
        for m in a['closure']:
            idx.setdefault(m, []).append(a['name'])
    return idx


def largest_apps(apps, n=10, kinds=('app', 'instance')):
    return sorted([a for a in apps if a['kind'] in kinds],
                  key=lambda a: (-len(a['closure']), a['name']))[:n]


# --------------------------------------------------------- estimates

def estimate(app, graph, benchmarks=None, profiles=None):
    """Resources for booting the app's closure. A benchmark row for the
    app (or for an identical closure) wins; else the declared model plus
    any ModuleResourceProfile mins (declared too)."""
    cl = app['closure']
    classes = sum(graph[m]['classes'] for m in cl)
    engines = []
    for m in cl:
        for e in graph[m]['engines']:
            engines.append({'module': m, **(e if isinstance(e, dict) else {'name': str(e)})})
    lib_mb = sum(graph[m]['libraries_mb'] for m in cl)
    ram = ESTIMATE['base_ram_mb'] + classes * ESTIMATE['per_class_ram_mb']
    disk = ESTIMATE['image_mb'] + lib_mb + sum(ESTIMATE['engine_image_mb'] for e in engines if e.get('kind') == 'image')
    boot = ESTIMATE['base_boot_s'] + classes * ESTIMATE['per_class_boot_s']
    threads = 1 + len({e['name'] for e in engines if e.get('kind') in ('system', 'image')})
    for m in cl:
        p = (profiles or {}).get(m)
        if p:
            ram = max(ram, float(p.get('min_ram_mb') or 0))
            disk = max(disk, float(p.get('min_disk_mb') or 0) + ESTIMATE['image_mb'])
            threads = max(threads, int(p.get('min_threads') or 1))
    est = {'classes': classes, 'ram_mb': round(ram, 1), 'disk_mb': round(disk, 1),
           'boot_s': round(boot, 1), 'threads': threads, 'engines': engines,
           'fidelity': 'declared'}
    b = (benchmarks or {}).get(app['name'])
    if b and b.get('ok') is not None:
        est.update({'ram_mb': float(b.get('peak_rss_mb') or est['ram_mb']),
                    'boot_s': float(b.get('boot_seconds') or est['boot_s']),
                    'disk_mb': float((b.get('image_mb') or 0) + (b.get('code_mb') or 0)) or est['disk_mb'],
                    'classes': int(b.get('classes') or classes),
                    'fidelity': 'benchmark', 'benchmark_ok': bool(b.get('ok')),
                    'oom_killed': bool(b.get('oom_killed'))})
    return est


def fits(est, budget):
    """(fits, reasons) against a StandardComputerBudget dict."""
    reasons = []
    if est.get('fidelity') == 'benchmark' and est.get('benchmark_ok') is False:
        reasons.append('benchmark under the budget FAILED' + (' (OOM-killed)' if est.get('oom_killed') else ''))
    if est['ram_mb'] > budget['ram_mb']:
        reasons.append('ram %.0f MB > budget %.0f MB' % (est['ram_mb'], budget['ram_mb']))
    if est['disk_mb'] > budget['disk_mb']:
        reasons.append('disk %.0f MB > budget %.0f MB' % (est['disk_mb'], budget['disk_mb']))
    if est['threads'] > budget['vcpus']:
        reasons.append('threads %d > vcpus %d' % (est['threads'], budget['vcpus']))
    if est['boot_s'] > budget.get('boot_timeout_s', 900):
        reasons.append('boot %.0f s > timeout %d s' % (est['boot_s'], budget.get('boot_timeout_s', 900)))
    return (not reasons), reasons


# ---------------------------------------------------------- the plan

def node_can_host(node, est):
    """A swarm/isle node (PolariNodeMachine-shaped dict) can host the app."""
    ram = float(node.get('total_ram_mb') or node.get('totalRamMb') or 0)
    cpus = int(node.get('logical_cpus') or node.get('logicalCpus') or 0)
    disk = float(node.get('free_disk_mb') or node.get('freeDiskMb') or 0)
    return ram >= est['ram_mb'] and cpus >= est['threads'] and (disk == 0 or disk >= est['disk_mb'])


def plan(apps, graph, budget=None, benchmarks=None, profiles=None, nodes=None, host=None):
    """Greedy weighted set cover: among apps that FIT the budget, pick the
    one covering the most still-uncovered modules per estimated MB until
    nothing new is covered; then singletons for the rest; then the
    distributed / large-host verdicts for what remains."""
    budget = budget or DEFAULT_BUDGET
    nodes = nodes or []
    ests = {a['name']: estimate(a, graph, benchmarks, profiles) for a in apps}
    fit = {a['name']: fits(ests[a['name']], budget) for a in apps}
    universe = set(graph)
    uncovered = set(universe)
    chosen = []
    real_apps = [a for a in apps if a['kind'] in ('app', 'instance') and fit[a['name']][0] and a['closure']]
    while uncovered:
        best, best_gain = None, 0
        for a in real_apps:
            gain = len(uncovered & set(a['closure']))
            score = gain / max(1.0, ests[a['name']]['ram_mb'])
            if gain > 0 and (best is None or score > best_gain):
                best, best_gain = a, score
        if best is None:
            break
        chosen.append(best['name'])
        uncovered -= set(best['closure'])
    for a in apps:  # singletons for what the apps left
        if a['kind'] == 'module' and a['modules'] and a['modules'][0] in uncovered and fit[a['name']][0]:
            chosen.append(a['name'])
            uncovered -= set(a['closure'])
    up = upstream_index(apps)
    by_name = {a['name']: a for a in apps}
    modules = {}
    counts = {'covered-standard': 0, 'covered-distributed': 0, 'covered-large-host': 0, 'uncovered': 0}
    for m in sorted(universe):
        holders = [n for n in up.get(m, []) if n in chosen]
        rec = {'module': m, 'apps': [n for n in up.get(m, []) if by_name[n]['kind'] == 'app'],
               'upstream': up.get(m, []), 'best_app': '', 'verdict': 'uncovered', 'reason': '', 'nodes': []}
        if holders:
            rec['best_app'] = min(holders, key=lambda n: ests[n]['ram_mb'])
            rec['verdict'] = 'covered-standard'
            rec['reason'] = 'tested through %s (%s, %.0f MB est.)' % (rec['best_app'], ests[rec['best_app']]['fidelity'], ests[rec['best_app']]['ram_mb'])
        else:
            single = by_name.get('module:' + m)
            est = ests[single['name']] if single else None
            reasons = fit[single['name']][1] if single else ['no app contains it']
            capable = [n.get('name', '?') for n in nodes if est and node_can_host(n, est)]
            if capable:
                rec['verdict'] = 'covered-distributed'
                rec['best_app'] = single['name']
                rec['nodes'] = capable
                rec['reason'] = 'exceeds the standard budget (%s); nodes that can host it: %s' % ('; '.join(reasons), ', '.join(capable))
            elif host and est and node_can_host(host, est):
                rec['verdict'] = 'covered-large-host'
                rec['best_app'] = single['name']
                rec['reason'] = 'exceeds the standard budget (%s); this host (%s) is large enough' % ('; '.join(reasons), host.get('name', 'local'))
            else:
                rec['reason'] = 'exceeds the standard budget (%s); no node or host can take it' % '; '.join(reasons)
        counts[rec['verdict']] += 1
        modules[m] = rec
    return {
        'budget': budget, 'chosen': chosen,
        'apps': [{**a, 'estimate': ests[a['name']], 'fits': fit[a['name']][0], 'fit_reasons': fit[a['name']][1],
                  'chosen': a['name'] in chosen} for a in apps],
        'modules': modules, 'counts': counts, 'total_modules': len(universe),
        'uncovered': sorted(m for m, r in modules.items() if r['verdict'] == 'uncovered'),
        'largest': [{'name': a['name'], 'closure': len(a['closure']), 'estimate': ests[a['name']],
                     'fits': fit[a['name']][0]} for a in largest_apps(apps)],
        'nodes': nodes, 'host': host,
    }


# ------------------------------------------------ host-side inventory

def local_host():
    try:
        cpus = os.cpu_count() or 0
        mem = [l for l in open('/proc/meminfo') if l.startswith('MemTotal')][0].split()[1]
        st = os.statvfs('/')
        return {'name': os.uname().nodename, 'logical_cpus': cpus,
                'total_ram_mb': round(int(mem) / 1024, 0),
                'free_disk_mb': round(st.f_bavail * st.f_frsize / 1e6, 0), 'source': 'local'}
    except Exception:  # noqa: BLE001
        return {'name': 'local', 'logical_cpus': 0, 'total_ram_mb': 0, 'free_disk_mb': 0}


def _ssh_aliases():
    """hostname → ssh alias from pol-build/manifests/nodes.yml (the deploy
    targets): swarm hostnames (dustin-etts-mesh-core) are not the ssh
    aliases (isle-core), so specs come through the alias."""
    aliases = {}
    path = os.path.join(os.path.dirname(os.path.dirname(_fw_root())), 'pol-build', 'manifests', 'nodes.yml')
    try:
        import re
        for m in re.finditer(r'ssh:\s*([A-Za-z0-9_.-]+)', open(path).read()):
            alias = m.group(1)
            try:
                r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=4', alias, 'hostname'],
                                   capture_output=True, text=True, timeout=8)
                if r.returncode == 0 and r.stdout.strip():
                    aliases[r.stdout.strip()] = alias
            except Exception:  # noqa: BLE001
                pass
    except OSError:
        pass
    return aliases


def swarm_nodes(ssh_specs=True, timeout=6):
    """Other docker swarm nodes reachable from here (never this host),
    with specs over ssh through the nodes.yml alias for that hostname."""
    out = []
    aliases = _ssh_aliases() if ssh_specs else {}
    try:
        res = subprocess.run(['docker', 'node', 'ls', '--format', '{{.Hostname}}\t{{.Status}}\t{{.Availability}}\t{{.Self}}'],
                             capture_output=True, text=True, timeout=timeout)
        for line in res.stdout.splitlines():
            host, status, avail, self_ = (line.split('\t') + ['', '', '', ''])[:4]
            if self_ == 'true' or status != 'Ready' or avail != 'Active':
                continue
            node = {'name': host, 'kind': 'swarm', 'status': status, 'logical_cpus': 0, 'total_ram_mb': 0, 'free_disk_mb': 0}
            if ssh_specs:
                try:
                    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=4', aliases.get(host, host),
                                        "nproc; grep MemTotal /proc/meminfo | awk '{print $2}'; df -Pm / | tail -1 | awk '{print $4}'"],
                                       capture_output=True, text=True, timeout=timeout)
                    vals = r.stdout.split()
                    if len(vals) >= 3:
                        node.update({'logical_cpus': int(vals[0]), 'total_ram_mb': round(int(vals[1]) / 1024),
                                     'free_disk_mb': int(vals[2]), 'source': 'ssh:' + aliases.get(host, host), 'ssh': aliases.get(host, '')})
                except Exception:  # noqa: BLE001
                    node['source'] = 'no ssh alias by hostname — specs unknown'
            out.append(node)
    except Exception as e:  # noqa: BLE001
        return [{'name': 'swarm', 'error': str(e)[:120]}]
    return out


def _fw_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def load_inputs(root=None):
    """Manifests + seeded apps + benchmark files from the checkout."""
    import sys
    root = root or _fw_root()
    sys.path[:0] = [root, os.path.join(root, 'modules')]
    from moduleService import manifests as M
    graph = module_graph(M.all_manifests())
    try:
        from polariapps.apps_seed import SEED_POLARI_APPS
        seeds = [{'name': a['name'], 'modules': json.loads(a.get('modules_json', '[]') or '[]')} for a in SEED_POLARI_APPS]
    except Exception:  # noqa: BLE001
        seeds = []
    bdir = os.path.join(os.path.dirname(os.path.dirname(root)), '.generated', 'test-coverage', 'benchmarks')
    benchmarks = {}
    if os.path.isdir(bdir):
        for fn in os.listdir(bdir):
            if fn.endswith('.json'):
                try:
                    b = json.load(open(os.path.join(bdir, fn)))
                    benchmarks[b['app']] = b
                except Exception:  # noqa: BLE001
                    pass
    return graph, seeds, benchmarks


def main(argv):
    verb = argv[0] if argv else 'plan'
    graph, seeds, benchmarks = load_inputs()
    apps = app_catalog(seeds, graph)
    if verb == 'apps':
        for a in largest_apps(apps, n=len(apps), kinds=('app', 'instance')):
            e = estimate(a, graph, benchmarks)
            ok, why = fits(e, DEFAULT_BUDGET)
            print('%-28s %2d direct %2d closure  %5.0f MB %4.0f s %s%s' % (a['name'], len(a['modules']), len(a['closure']), e['ram_mb'], e['boot_s'], 'FITS' if ok else 'TOO BIG', ('  unknown: ' + ','.join(a['unknown'])) if a['unknown'] else ''))
        return 0
    nodes = swarm_nodes() if verb in ('plan', 'nodes') else []
    if verb == 'nodes':
        print('host:', local_host())
        for n in nodes:
            print('node:', n)
        return 0
    p = plan(apps, graph, DEFAULT_BUDGET, benchmarks, None, nodes, local_host())
    if verb == 'json':
        print(json.dumps(p, indent=1))
        return 0
    print('budget %(name)s: %(cores)s cores / %(vcpus)s vcpus / %(ram_mb).0f MB RAM / %(disk_mb).0f MB disk' % p['budget'])
    print('chosen apps (%d): %s' % (len(p['chosen']), ', '.join(p['chosen'])))
    print('modules: %s of %d' % (', '.join('%s %d' % kv for kv in p['counts'].items()), p['total_modules']))
    for m, r in p['modules'].items():
        if r['verdict'] != 'covered-standard':
            print('  %-20s %-20s %s' % (m, r['verdict'], r['reason'][:110]))
    print('largest apps:', ', '.join('%s(%d)' % (a['name'], a['closure']) for a in p['largest'][:6]))
    print('nodes:', ', '.join('%s(%s cpu/%s MB)' % (n['name'], n.get('logical_cpus'), n.get('total_ram_mb')) for n in nodes) or 'none')
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
