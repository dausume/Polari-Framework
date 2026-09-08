"""
@module testing.custom.app_benchmark

MEASURE an app under the standard budget (tcov-2): boot the backend
with POLARI_MODULES = the app's closure in a one-off container held to
the budget's cgroup limits (--cpus, --memory), on the host checkout,
sqlite, no Keycloak; record boot time to /api/health, peak RSS (docker
stats samples), class inits, OOM-kill, image + code size → an
AppBenchmark JSON under .generated/test-coverage/benchmarks/<app>.json
(the API ingests it as a row). A failed boot under the budget is the
honest answer "does not fit" — the plan then looks for nodes.

    python3 -m testing.custom.app_benchmark <app>|--all [--budget ram_mb:vcpus] [--image prf-backend:staging]
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

from testing.custom import app_hierarchy as H


def _sh(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _image_mb(image):
    r = _sh(['docker', 'image', 'inspect', '--format', '{{.Size}}', image])
    return round(int(r.stdout.strip() or 0) / 1e6, 1) if r.returncode == 0 else 0.0


def _code_mb(root, modules):
    total = 0
    for m in modules:
        d = os.path.join(root, 'modules', m)
        for dp, _, fs in os.walk(d):
            for f in fs:
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
    return round(total / 1e6, 1)


def benchmark(app, budget=None, image='prf-backend:staging', root=None, timeout=None):
    budget = budget or H.DEFAULT_BUDGET
    root = root or H._fw_root()
    graph, seeds, _ = H.load_inputs(root)
    apps = {a['name']: a for a in H.app_catalog(seeds, graph)}
    if app not in apps:
        return {'app': app, 'ok': None, 'error': 'unknown app (pol modules testplan apps)'}
    mods = apps[app]['closure']
    name = 'tcov-' + app.replace(':', '-')
    timeout = timeout or budget.get('boot_timeout_s', 900)
    _sh(['docker', 'rm', '-f', name])
    cmd = ['docker', 'run', '-d', '--name', name, '--cpus', str(budget['vcpus']), '--memory', '%dm' % int(budget['ram_mb']),
           '-u', '%d:%d' % (os.getuid(), os.getgid()), '-e', 'HOME=/tmp', '-e', 'DATABASE_PATH=/tmp/tcov.db',
           '-e', 'POLARI_LAZY_BOOT=off', '-e', 'POLARI_MESH_AUTOCONFIG=false', '-e', 'POLARI_MODULES=' + ','.join(mods),
           '-v', root + ':/app', '-w', '/app', '-p', '127.0.0.1::3000', '--entrypoint', 'python3', image, 'initLocalhostPolariServer.py']
    t0 = time.time()
    r = _sh(cmd)
    if r.returncode != 0:
        return {'app': app, 'ok': False, 'error': r.stderr.strip()[-300:], 'modules': mods}
    port = _sh(['docker', 'port', name, '3000']).stdout.strip().rsplit(':', 1)[-1]
    peak = 0.0
    health = 0
    boot = None
    oom = False
    while time.time() - t0 < timeout:
        st = _sh(['docker', 'stats', '--no-stream', '--format', '{{.MemUsage}}', name]).stdout.strip()
        try:
            val, unit = st.split('/')[0].strip().split('M')[0], st.split('/')[0].strip()
            mb = float(unit[:-3]) * (1024 if unit.endswith('GiB') else 1) if unit.endswith(('MiB', 'GiB')) else float(val)
            peak = max(peak, mb)
        except Exception:  # noqa: BLE001
            pass
        state = _sh(['docker', 'inspect', '--format', '{{.State.Running}} {{.State.OOMKilled}}', name]).stdout.split()
        if state and state[0] != 'true':
            oom = state[1] == 'true'
            break
        try:
            with urllib.request.urlopen('http://127.0.0.1:%s/api/health' % port, timeout=3) as resp:
                health = resp.status
                if health == 200 and boot is None:
                    boot = round(time.time() - t0, 1)
                    break
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    logs = _sh(['docker', 'logs', name], timeout=120).stdout + _sh(['docker', 'logs', name], timeout=120).stderr
    classes = logs.count('[DefInit]')
    tracebacks = logs.count('Traceback (most recent call last)')
    _sh(['docker', 'rm', '-f', name])
    ok = boot is not None and not oom and tracebacks == 0
    result = {'app': app, 'modules': mods, 'host': os.uname().nodename, 'budget': budget.get('name', 'standard'),
              'cpu_limit': budget['vcpus'], 'mem_limit_mb': budget['ram_mb'], 'boot_seconds': boot or round(time.time() - t0, 1),
              'peak_rss_mb': round(peak, 1), 'classes': classes, 'image_mb': _image_mb(image), 'code_mb': _code_mb(root, mods),
              'ok': ok, 'oom_killed': oom, 'health_http': health, 'tracebacks': tracebacks,
              'measured_at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'notes': '' if ok else ('OOM-killed under %dm' % budget['ram_mb'] if oom else 'no health within %ds' % timeout if boot is None else '%d traceback(s)' % tracebacks)}
    bdir = os.path.join(os.path.dirname(os.path.dirname(root)), '.generated', 'test-coverage', 'benchmarks')
    os.makedirs(bdir, exist_ok=True)
    json.dump(result, open(os.path.join(bdir, app.replace(':', '-') + '.json'), 'w'), indent=1)
    return result


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    budget = dict(H.DEFAULT_BUDGET)
    image = 'prf-backend:staging'
    targets = []
    i = 0
    while i < len(argv):
        if argv[i] == '--budget':
            ram, vcpus = argv[i + 1].split(':'); budget['ram_mb'] = float(ram); budget['vcpus'] = int(vcpus); i += 2
        elif argv[i] == '--image':
            image = argv[i + 1]; i += 2
        else:
            targets.append(argv[i]); i += 1
    if targets == ['--all']:
        graph, seeds, _ = H.load_inputs()
        targets = [a['name'] for a in H.largest_apps(H.app_catalog(seeds, graph), n=99)]
    for t in targets:
        r = benchmark(t, budget, image)
        print(json.dumps({k: r.get(k) for k in ('app', 'ok', 'boot_seconds', 'peak_rss_mb', 'classes', 'oom_killed', 'notes', 'error')}))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
