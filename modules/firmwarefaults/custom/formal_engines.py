"""
@module firmwarefaults.custom.formal_engines

THE FORMAL + STATIC TIER'S ENGINES SEAM (sc-2b; the Polari engines ladder of board.custom.board_engines /
computelod.custom.eda_engines): CBMC and cppcheck run in their OWN worker image `prf-formal-engines:trixie`
(polari-rf-node/prf-formal-engines/), never inside the framework process, never linked — CBMC's licence is BSD-4-clause
style (an advertising clause: GPL-incompatible to LINK, fine as a separate process; plan §2d). The module never assumes a
device (his rule 2026-09-24).

Resolution per engine, honest at every rung:
  1. FORMAL_ENGINES_URL set   → that worker, ALWAYS (unreachable or lacking the engine = REFUSAL; never a silent fallback)
  2. knob unset, binary local → the binary on the PATH (polari-cbmc-check / polari-cppcheck-run / cbmc / cppcheck)
  3. the image local          → `docker run` of FORMAL_ENGINES_IMAGE (default prf-formal-engines:trixie) on this docker
  4. nothing local            → the topology's LIVE provider for module `firmwarefaults.formal`
                                (`pol allocate firmwarefaults.formal <instance>`)
  5. nothing                  → a refusal naming the knob, the image and the provider module

sc-2c: Frama-C 33.0 + Mthread (LGPL-2.1, opam-built — Debian has no package) are in the SAME image (+185 MB: under the plan's
~1.5 GB fold-in line, so one image and one ladder): engines `mthread-check` (polari-mthread-check) and `frama-c`. The image
says what it carries in its label org.polari.engines; the local-image rung reads it, so an older prf-formal-engines image
built before sc-2c is never handed an Mthread run (it resolves onward — the topology, then a refusal naming the knob).

Input files keep RELATIVE paths (a model's include tree: stubs/avr/io.h), unlike the board engines' flat basenames.
    run(engine, args, files={relpath: bytes}, timeout) → {ok, how, where, returncode, stdout, stderr, files, cost}
"""
import base64
import json
import os
import resource
import shutil
import ssl
import subprocess
import tempfile
import time
import urllib.request

KNOB = 'FORMAL_ENGINES_URL'
IMAGE_KNOB = 'FORMAL_ENGINES_IMAGE'
DEFAULT_IMAGE = 'prf-formal-engines:trixie'
PROVIDER_MODULE = 'firmwarefaults.formal'
LOCAL_IMAGE = 'local-image'
REMOTE = 'remote'
#: engine → (binary, licence) — what prf-formal-engines/Dockerfile carries
ENGINES = {
    'cbmc-check': ('polari-cbmc-check', 'ours; drives cbmc 6.6.0 (Debian trixie) — BSD-4-clause style, a separate process'),
    'cppcheck-run': ('polari-cppcheck-run', 'ours; drives cppcheck 2.17.1 (Debian trixie) — GPL-3.0'),
    'cbmc': ('cbmc', 'BSD-4-clause style (diffblue/cbmc) — run, never linked'),
    'goto-cc': ('goto-cc', 'BSD-4-clause style (part of cbmc)'),
    'goto-instrument': ('goto-instrument', 'BSD-4-clause style (part of cbmc)'),
    'cppcheck': ('cppcheck', 'GPL-3.0 (danmar/cppcheck)'),
    # sc-2c: Frama-C 33.0 "Arsenic" via opam in the same image (no SMT prover wired; never Alt-Ergo's NC build)
    'mthread-check': ('polari-mthread-check', 'ours; drives frama-c 33.0 -eva -mthread (LGPL-2.1-only), a separate process'),
    'frama-c': ('frama-c', 'LGPL-2.1-only (Frama-C 33.0, CEA) — kernel + Eva + Mthread'),
}
#: what an image built BEFORE the org.polari.engines label (sc-2b) carries — no Mthread
PRE_LABEL_ENGINES = ('cbmc-check', 'cppcheck-run', 'cbmc', 'goto-cc', 'goto-instrument', 'cppcheck')
_LBL = {}
_CAP = {}
_IMG = {}
_TTL = 30.0


class FormalRefused(RuntimeError):
    pass


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def image_name():
    return os.environ.get(IMAGE_KNOB, '') or DEFAULT_IMAGE


def local_image():
    img = image_name()
    hit = _IMG.get(img)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    iid = ''
    if shutil.which('docker'):
        try:
            p = subprocess.run(['docker', 'image', 'inspect', img, '--format', '{{.Id}}'], capture_output=True, text=True, timeout=15)
            iid = p.stdout.strip() if p.returncode == 0 else ''
        except Exception:  # noqa: BLE001
            iid = ''
    _IMG[img] = (time.time(), iid)
    return iid


def image_engines():
    """The engines the local image says it carries (label org.polari.engines); an unlabelled image = the sc-2b set."""
    img, iid = image_name(), local_image()
    if not iid:
        return ()
    hit = _LBL.get(iid)
    if hit is not None:
        return hit
    eng = PRE_LABEL_ENGINES
    try:
        p = subprocess.run(['docker', 'image', 'inspect', img, '--format', '{{index .Config.Labels "org.polari.engines"}}'],
                           capture_output=True, text=True, timeout=15)
        lbl = p.stdout.strip() if p.returncode == 0 else ''
        if lbl and lbl != '<no value>':
            eng = tuple(lbl.split())
    except Exception:  # noqa: BLE001
        pass
    _LBL[iid] = eng
    return eng


def topology_url():
    try:
        from topology.provider_registry import resolve_provider
        r = resolve_provider(PROVIDER_MODULE)
        if r.get('ok'):
            return r['url'].rstrip('/')
    except Exception:  # noqa: BLE001
        pass
    return ''


def remote_capability(url, timeout=5):
    hit = _CAP.get(url)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    cap = None
    try:
        from polariApiServer import outbound
        with outbound.http_request('engine', 'formal', 'GET', '%s/capability' % url, means='probe', timeout=timeout, lib='urllib') as r:
            cap = json.load(r)
    except Exception:  # noqa: BLE001
        cap = None
    _CAP[url] = (time.time(), cap)
    return cap


def _has(cap, engine):
    return bool(cap and (cap.get('engines') or {}).get(engine, {}).get('available'))


def refusal_text(engine):
    return ('no %s: %s is unset, not on the PATH here, no %s image on this docker, no live %s provider — build it '
            '(docker compose -f polari-rf-node/docker-compose.formal-engines.yml build), set %s to a formal-engines worker, '
            'or `pol allocate %s <instance>`' % (engine, KNOB, image_name(), PROVIDER_MODULE, KNOB, PROVIDER_MODULE))


def resolve(engine):
    """{'how': remote | local-binary | local-image | refused, 'where', 'why'} for ONE engine — nothing is run."""
    if engine not in ENGINES:
        return {'how': 'refused', 'where': '', 'why': 'unknown engine %r — one of %s' % (engine, sorted(ENGINES))}
    url = knob_url()
    if url:
        cap = remote_capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'why': '%s=%s is set but the worker is unreachable — refusing (a declared worker never '
                                                          'silently falls back to local)' % (KNOB, url)}
        if not _has(cap, engine):
            return {'how': 'refused', 'where': url, 'why': '%s=%s reached but that worker lacks %s' % (KNOB, url, engine)}
        return {'how': REMOTE, 'where': url, 'why': 'knob %s' % KNOB}
    b = ENGINES[engine][0]
    for cand in (shutil.which(b), os.path.expanduser('~/.local/bin/%s' % b)):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return {'how': 'local-binary', 'where': cand, 'why': 'on this device'}
    if local_image() and engine in image_engines():
        return {'how': LOCAL_IMAGE, 'where': image_name(), 'why': 'the formal engines image on this device (%s)' % local_image()[:19]}
    turl = topology_url()
    if turl and _has(remote_capability(turl), engine):
        return {'how': REMOTE, 'where': turl, 'why': 'topology provider %s' % PROVIDER_MODULE}
    why = refusal_text(engine)
    if local_image() and engine not in image_engines():
        why += ' (the local %s predates %s — rebuild it)' % (image_name(), engine)
    return {'how': 'refused', 'where': '', 'why': why}


def placement():
    return {'knob': KNOB, 'knob_value': knob_url(), 'image': image_name(), 'image_present': bool(local_image()),
            'provider_module': PROVIDER_MODULE, 'engines': {e: resolve(e) for e in ('cbmc-check', 'cppcheck-run', 'mthread-check')},
            'ladder': ['%s (always, or refusal)' % KNOB, 'local binary', 'the local image %s (%s)' % (image_name(), IMAGE_KNOB),
                       'topology provider %s (live only)' % PROVIDER_MODULE, 'refusal naming %s' % KNOB]}


def available(engine='cbmc-check'):
    return resolve(engine)['how'] != 'refused'


def _write_tree(work, files):
    for rel, data in files.items():
        n = os.path.normpath(rel)
        if n.startswith('/') or n.startswith('..'):
            raise FormalRefused('bad input path %r' % rel)
        fp = os.path.join(work, n)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, 'wb').write(data if isinstance(data, bytes) else data.encode())


def _local(argv_head, args, files, timeout, docker=False):
    work = tempfile.mkdtemp(prefix='polari-formal-')
    try:
        _write_tree(work, files)
        argv = (['docker', 'run', '--rm', '-u', '%d:%d' % (os.getuid(), os.getgid()), '-v', '%s:/w' % work, '-w', '/w', image_name()]
                if docker else []) + [argv_head] + list(args)
        c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
        t0 = time.perf_counter()
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout + 30, cwd=work)
        c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
        cost = {'wall_s': round(time.perf_counter() - t0, 3)}
        if not docker:
            cost.update(cpu_s=round((c1.ru_utime - c0.ru_utime) + (c1.ru_stime - c0.ru_stime), 3), peak_rss_mb=round(c1.ru_maxrss / 1024.0, 1))
        else:
            cost['source'] = 'wall only from here: the engine ran inside docker (polari-cbmc-check measures each step with wait4)'
        sent = {os.path.normpath(k) for k in files}
        out = {fn: open(os.path.join(work, fn), 'rb').read() for fn in sorted(os.listdir(work))
               if fn not in sent and os.path.isfile(os.path.join(work, fn)) and not fn.endswith('.gb')}
        return {'ok': p.returncode == 0, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr, 'files': out, 'cost': cost, 'argv': argv}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _remote(url, engine, args, files, timeout):
    body = json.dumps({'engine': engine, 'args': list(args), 'timeout': timeout,
                       'files_b64': {k: base64.b64encode(v if isinstance(v, bytes) else v.encode()).decode() for k, v in files.items()}}).encode()
    req = urllib.request.Request('%s/run' % url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    t0 = time.perf_counter()
    from polariApiServer import outbound
    with outbound.http_request('engine', 'formal', 'POST', req, means='run', timeout=timeout + 60, lib='urllib', context=ssl._create_unverified_context()) as r:
        d = json.load(r)
    for k in ('stdout', 'stderr'):
        if '%s_chars' % k in d and len(d.get(k) or '') != int(d['%s_chars' % k]):
            raise FormalRefused('%s from %s arrived cut: %d of %d characters' % (k, url, len(d.get(k) or ''), int(d['%s_chars' % k])))
    out = {k: v.encode() for k, v in (d.get('files') or {}).items()}
    out.update({k: base64.b64decode(v) for k, v in (d.get('files_b64') or {}).items()})
    return {'ok': bool(d.get('ok')) and d.get('returncode') == 0, 'returncode': d.get('returncode'), 'stdout': d.get('stdout', ''),
            'stderr': d.get('stderr', '') or d.get('error', ''), 'files': out, 'cost': dict(d.get('cost') or {}, round_trip_s=round(time.perf_counter() - t0, 3)),
            'argv': [engine] + list(args)}


def run(engine, args, files=None, timeout=600):
    """Run ONE engine wherever resolve() says. Raises FormalRefused (the reason names FORMAL_ENGINES_URL)."""
    where = resolve(engine)
    if where['how'] == 'refused':
        raise FormalRefused(where['why'])
    files = files or {}
    if where['how'] == 'local-binary':
        res = _local(where['where'], args, files, timeout)
    elif where['how'] == LOCAL_IMAGE:
        res = _local(ENGINES[engine][0], args, files, timeout, docker=True)
    else:
        res = _remote(where['where'], engine, args, files, timeout)
    res.update(how=where['how'], where=where['where'])
    return res


def digest(engine='cbmc-check'):
    """What identifies the engine that ran: the image id on the image rung, else the binary path / worker URL."""
    w = resolve(engine)
    if w['how'] == LOCAL_IMAGE:
        return 'image %s %s' % (image_name(), local_image())
    return '%s %s' % (w['how'], w['where'])
