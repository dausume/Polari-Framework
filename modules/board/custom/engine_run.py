"""
@module board.custom.engine_run

RUN one board engine wherever board_engines.resolve says (brd-1): a local binary in a scratch dir, the worker image
with `docker run` (the scratch dir mounted at /w, as this user; a flash maps the board's port in), or the remote worker's
POST /run (files round-trip). Argv only, never a shell. Every call returns what it cost (wall; CPU-s and peak RSS where
the rung can see them) — the cost rule.

    run(engine, args, files={name: bytes}, flash=False, devices=()) → {ok, how, where, returncode, stdout, stderr,
                                                                      files: {name: bytes}, cost}
"""
import base64
import json
import os
import resource
import shutil
import subprocess
import tempfile
import time
import urllib.request
import ssl

from board.custom import board_engines as be


class EngineRefused(RuntimeError):
    pass


def _collect(work, sent):
    out = {}
    for fn in sorted(os.listdir(work)):
        fp = os.path.join(work, fn)
        if fn not in sent and os.path.isfile(fp):
            out[fn] = open(fp, 'rb').read()
    return out


def _local(binary, args, files, timeout, prefix=None, cwd_in=None):
    work = tempfile.mkdtemp(prefix='polari-board-')
    try:
        for fn, data in files.items():
            open(os.path.join(work, os.path.basename(fn)), 'wb').write(data)
        argv = (prefix(work) if prefix else []) + [binary] + list(args)
        c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=work)
        c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cost = {'wall_s': round(time.perf_counter() - t0, 3)}
        if prefix is None:   # the child IS the engine: rusage sees it
            cost.update(cpu_s=round((c1.ru_utime - c0.ru_utime) + (c1.ru_stime - c0.ru_stime), 3), peak_rss_mb=round(c1.ru_maxrss / 1024.0, 1),
                        source='rusage(RUSAGE_CHILDREN) around the engine')
        else:
            cost['source'] = 'wall only: the engine ran inside docker (the worker /run measures CPU-s and peak RSS)'
        return {'ok': p.returncode == 0, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr,
                'files': _collect(work, {os.path.basename(f) for f in files}), 'cost': cost, 'argv': argv}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def docker_prefix(image, devices=()):
    """The `docker run` wrapper for the image rung (also what a DRY-RUN prints for a flash through the image)."""
    def pre(work):
        argv = ['docker', 'run', '--rm', '-u', '%d:%d' % (os.getuid(), os.getgid()), '-v', '%s:/w' % work, '-w', '/w']
        for host_dev, inner in devices:
            argv += ['--device', '%s:%s' % (host_dev, inner)]
            try:   # the dialout group of the HOST device, so a non-root user may open it
                argv += ['--group-add', str(os.stat(host_dev).st_gid)]
            except OSError:
                pass
        return argv + [image]
    return pre


def _remote(url, engine, args, files, timeout):
    body = json.dumps({'engine': engine, 'args': list(args), 'timeout': timeout,
                       'files_b64': {os.path.basename(k): base64.b64encode(v).decode() for k, v in files.items()}}).encode()
    req = urllib.request.Request('%s/run' % url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    ctx = ssl._create_unverified_context()
    t0 = time.perf_counter()
    from polariApiServer import outbound
    with outbound.http_request('engine', 'board', 'POST', req, means='run', timeout=timeout + 30, lib='urllib', context=ctx) as r:
        d = json.load(r)
    for k in ('stdout', 'stderr'):   # sc-2: a worker states each stream's length; a shorter one arrived cut — refuse it, never parse half
        if '%s_chars' % k in d and len(d.get(k) or '') != int(d['%s_chars' % k]):
            raise EngineRefused('%s from %s arrived cut: %d of %d characters' % (k, url, len(d.get(k) or ''), int(d['%s_chars' % k])))
    out = {k: v.encode() for k, v in (d.get('files') or {}).items()}
    out.update({k: base64.b64decode(v) for k, v in (d.get('files_b64') or {}).items()})
    cost = dict(d.get('cost') or {}, round_trip_s=round(time.perf_counter() - t0, 3))
    return {'ok': bool(d.get('ok')) and d.get('returncode') == 0, 'returncode': d.get('returncode'), 'stdout': d.get('stdout', ''),
            'stderr': d.get('stderr', '') or d.get('error', ''), 'files': out, 'cost': cost, 'argv': [engine] + list(args)}


def run(engine, args, files=None, flash=False, devices=(), timeout=300):
    """devices: [(host path, path inside the image)] — only for the image rung (a flash on this host)."""
    where = be.resolve(engine, flash=flash)
    files = files or {}
    if where['how'] == 'refused':
        raise EngineRefused(where['why'])
    binary = be.ENGINES[engine][0]
    if where['how'] == 'local-binary':
        res = _local(where['where'], args, files, timeout)
    elif where['how'] == be.LOCAL_IMAGE:
        res = _local(binary, args, files, timeout, prefix=docker_prefix(where['where'], devices))
    else:
        res = _remote(where['where'], engine, args, files, timeout)
    res.update(how=where['how'], where=where['where'])
    return res


def version(engine):
    """The version line of the engine that WOULD run (for the repro block); '' when refused."""
    args = {'avrdude': ['-?'], 'simavr': ['--help'], 'avr-twin': []}.get(engine, ['--version'])
    try:
        r = run(engine, args, timeout=60)
    except Exception:
        return ''
    text = (r.get('stdout') or '') + (r.get('stderr') or '')
    for line in text.splitlines():
        if engine == 'avrdude' and 'version' in line.lower():
            return line.strip()[:160]
        if engine != 'avrdude' and line.strip():
            return line.strip()[:160]
    return ''
