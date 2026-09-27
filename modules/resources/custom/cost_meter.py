"""
@module resources.custom.cost_meter

WHAT A RUN COSTS (rc-1 — his rule 2026-09-26: "track how much all of these engines and modules are costing resource wise
both independently and collectively … the goal is to make it feasible to run this on as cheap of devices as possible even
if it takes a long time"). One meter, one shape, measured never estimated:

    Meter                 wraps a flow / selftest / boot in this process: wall seconds, CPU seconds (self + children),
                          peak RSS of this process and the peak RSS of any child (ngspice, gcc …) from rusage — the
                          numbers /usr/bin/time -v would print, inside the program
    docker_run_metered    runs ONE container synchronously (`docker run` WITHOUT --rm, with a cidfile) while a poller
                          reads its cgroup v2 `memory.peak` and `cpu.stat` every 0.25 s until it exits, then removes it:
                          the engine's own peak memory and CPU seconds — the cost an image-based engine has, which the
                          parent's rusage never sees (a container is not a child process)
    ENGINE_LOG            every metered engine call appends {engine, image, how, peak_rss_mb, cpu_s, wall_s}; a Meter
                          collects the calls made while it was open, so a flow's cost = host + its engines, stated apart
    image_size_mb         `docker image inspect` size of an image on this device (the pull footprint)

Remote workers report their own `cost` (rusage of the child they ran) in the /run answer; the ladder passes it through, so
a flow's engine costs are the same shape whether the engine ran here or on a worker. Nothing here guesses: a dimension that
could not be measured is absent, and the block says so.
"""
import json
import os
import resource
import subprocess
import threading
import time

ENGINE_LOG = []          # every metered engine call in this process (bounded)
_ENGINE_LOG_MAX = 2000
_IMAGE_SIZE_CACHE = {}
_KB = 1024.0


def _rss_mb(ru):
    return round(ru.ru_maxrss / _KB, 1)   # linux: ru_maxrss in kB


def image_size_mb(image):
    """The image's size on this device in MB ('' when it is not present here)."""
    if image in _IMAGE_SIZE_CACHE:
        return _IMAGE_SIZE_CACHE[image]
    out = ''
    try:
        p = subprocess.run(['docker', 'image', 'inspect', image, '--format', '{{.Size}}'], capture_output=True, text=True, timeout=20)
        if p.returncode == 0 and p.stdout.strip().isdigit():
            out = round(int(p.stdout.strip()) / (1024 * 1024), 1)
    except Exception:
        pass
    _IMAGE_SIZE_CACHE[image] = out
    return out


def _log(entry):
    ENGINE_LOG.append(entry)
    if len(ENGINE_LOG) > _ENGINE_LOG_MAX:
        del ENGINE_LOG[:len(ENGINE_LOG) - _ENGINE_LOG_MAX]


def record_engine_call(engine, how, where, cost=None, image=''):
    """Append one engine call's cost (from a worker's answer, or from docker_run_metered) so open Meters collect it."""
    e = {'engine': engine, 'how': how, 'where': where, 'image': image or '', 'at': time.time()}
    e.update({k: v for k, v in (cost or {}).items() if k in ('peak_rss_mb', 'cpu_s', 'wall_s', 'source')})
    _log(e)
    return e


def _cgroup_dir(cid):
    for cand in ('/sys/fs/cgroup/system.slice/docker-%s.scope' % cid, '/sys/fs/cgroup/docker/%s' % cid, '/sys/fs/cgroup/memory/docker/%s' % cid):
        if os.path.isdir(cand):
            return cand
    return ''


def docker_run_metered(cmd_prefix, image, argv, timeout=900, cwd=None, stdin=None):
    """`cmd_prefix` = ['docker', 'run', …options…] WITHOUT --rm; runs `image argv…` synchronously, polls the container's cgroup
    for memory.peak / cpu.stat until exit, removes the container. Returns (CompletedProcess-like, cost dict)."""
    import tempfile
    fd, cidfile = tempfile.mkstemp(prefix='polari-cid-'); os.close(fd); os.remove(cidfile)
    cmd = list(cmd_prefix) + ['--cidfile', cidfile, image] + list(argv)
    peak = {'mem': 0, 'cpu_usec': 0, 'cgroup': ''}
    stop = threading.Event()

    def poll():
        cid = ''
        while not stop.is_set():
            if not cid and os.path.exists(cidfile):
                try:
                    cid = open(cidfile).read().strip()
                except Exception:
                    cid = ''
            if cid:
                d = _cgroup_dir(cid)
                if d:
                    peak['cgroup'] = d
                    try:
                        peak['mem'] = max(peak['mem'], int(open(os.path.join(d, 'memory.peak')).read().strip()))
                    except Exception:
                        try:   # cgroup v1 fallback
                            peak['mem'] = max(peak['mem'], int(open(os.path.join(d, 'memory.max_usage_in_bytes')).read().strip()))
                        except Exception:
                            pass
                    try:
                        for line in open(os.path.join(d, 'cpu.stat')):
                            if line.startswith('usage_usec'):
                                peak['cpu_usec'] = max(peak['cpu_usec'], int(line.split()[1]))
                    except Exception:
                        pass
            stop.wait(0.25)

    t = threading.Thread(target=poll, daemon=True); t.start()
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, input=stdin)
    finally:
        wall = time.perf_counter() - t0
        stop.set(); t.join(timeout=2)
        try:
            cid = open(cidfile).read().strip() if os.path.exists(cidfile) else ''
            if cid:
                # one last read while the cgroup may still exist, then remove the container
                d = _cgroup_dir(cid)
                if d:
                    try:
                        peak['mem'] = max(peak['mem'], int(open(os.path.join(d, 'memory.peak')).read().strip()))
                    except Exception:
                        pass
                subprocess.run(['docker', 'rm', '-f', cid], capture_output=True, timeout=60)
            if os.path.exists(cidfile):
                os.remove(cidfile)
        except Exception:
            pass
    cost = {'wall_s': round(wall, 3), 'source': 'cgroup v2 memory.peak + cpu.stat, polled every 0.25 s while the container ran'}
    if peak['mem']:
        cost['peak_rss_mb'] = round(peak['mem'] / (1024 * 1024), 1)
    if peak['cpu_usec']:
        cost['cpu_s'] = round(peak['cpu_usec'] / 1e6, 3)
    if not peak['mem'] and not peak['cpu_usec']:
        cost['unmeasured'] = 'the container exited before its cgroup was read (a very short run) or the cgroup path is not the systemd docker scope on this device'
    return p, cost


class Meter:
    """`with Meter('computelod.custom.lod3_devices') as m: …; m.as_dict()` — the cost of what ran inside, host and engines apart."""

    def __init__(self, label=''):
        self.label = label

    def __enter__(self):
        self.t0 = time.perf_counter()
        self.ru_self0 = resource.getrusage(resource.RUSAGE_SELF)
        self.ru_ch0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        self.log_start = len(ENGINE_LOG)
        return self

    def __exit__(self, *exc):
        self.wall = time.perf_counter() - self.t0
        s1 = resource.getrusage(resource.RUSAGE_SELF); c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        self.cpu_self = (s1.ru_utime - self.ru_self0.ru_utime) + (s1.ru_stime - self.ru_self0.ru_stime)
        self.cpu_children = (c1.ru_utime - self.ru_ch0.ru_utime) + (c1.ru_stime - self.ru_ch0.ru_stime)
        self.peak_self_mb = _rss_mb(s1)          # process-lifetime maximum (rusage cannot reset it — said so in the block)
        self.peak_children_mb = _rss_mb(c1)      # the largest child so far in this process's life
        self.engine_calls = list(ENGINE_LOG[self.log_start:])
        return False

    def as_dict(self):
        eng = self.engine_calls
        images = sorted({e['image'] for e in eng if e.get('image')})
        out = {'label': self.label, 'wall_s': round(self.wall, 3),
               'host': {'cpu_s_self': round(self.cpu_self, 3), 'cpu_s_children': round(self.cpu_children, 3), 'peak_rss_mb_self': self.peak_self_mb, 'peak_rss_mb_children': self.peak_children_mb,
                        'note': 'rusage: peak RSS is the process-lifetime maximum up to the end of this run (a lower bound for the run itself when the process did more before); children = subprocesses such as ngspice'},
               'engines': {'calls': len(eng), 'cpu_s': round(sum(float(e.get('cpu_s') or 0) for e in eng), 3), 'peak_rss_mb': max([float(e.get('peak_rss_mb') or 0) for e in eng] or [0]),
                           'by_engine': {}, 'images': {img: image_size_mb(img) for img in images}, 'unmeasured_calls': sum(1 for e in eng if not e.get('peak_rss_mb') and not e.get('cpu_s'))},
               'totals': {'cpu_s': round(self.cpu_self + self.cpu_children + sum(float(e.get('cpu_s') or 0) for e in eng), 3),
                          'peak_rss_mb_any_process': max([self.peak_self_mb, self.peak_children_mb] + [float(e.get('peak_rss_mb') or 0) for e in eng]),
                          'pull_mb_images': round(sum(float(image_size_mb(img) or 0) for img in images), 1),
                          'reading': 'peak_rss_mb_any_process is the memory ONE process needed at its worst (the flow runs its engines one at a time); cpu_s is the whole run\'s CPU time — on a slower device the wall time scales, the memory does not'}}
        for e in eng:
            b = out['engines']['by_engine'].setdefault(e['engine'], {'calls': 0, 'cpu_s': 0.0, 'peak_rss_mb': 0.0, 'how': e.get('how', ''), 'image': e.get('image', '')})
            b['calls'] += 1; b['cpu_s'] = round(b['cpu_s'] + float(e.get('cpu_s') or 0), 3); b['peak_rss_mb'] = max(b['peak_rss_mb'], float(e.get('peak_rss_mb') or 0))
        return out


def measure_command(argv, cwd=None, timeout=3600, env=None):
    """Run a command as a child and return its cost (wall, cpu, peak RSS of the child tree via rusage) — for selftests / boots."""
    c0 = resource.getrusage(resource.RUSAGE_CHILDREN); t0 = time.perf_counter()
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
    wall = time.perf_counter() - t0; c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    return p, {'wall_s': round(wall, 3), 'cpu_s': round((c1.ru_utime - c0.ru_utime) + (c1.ru_stime - c0.ru_stime), 3), 'peak_rss_mb': _rss_mb(c1), 'source': 'rusage(RUSAGE_CHILDREN) around the command'}
