"""
@module computelod.custom.eda_engines

THE ENGINES SEAM of the compute ladder — the Polari engines pattern, the same ladder cntfet (`cnt_remote`),
materialsScience (`engines.remote`) and the topology provider registry use, so the EDA tools run on WHATEVER
device the topology assigns and the core keeps the rows. Before this seam (2026-09-24) the lod scripts ran
`docker run polari-eda-tools:noble …` on the local machine directly — an assumption that circumvented the
pattern; this replaces every such call.

Resolution, per engine, honest at every rung:
  1. EDA_ENGINES_URL set          → that worker, ALWAYS (unreachable or lacking the engine = REFUSAL; a declared
                                    worker never silently degrades to local)
  2. knob unset, binary local     → the binary on the PATH (or the suite's ~/.local/bin wrappers)
  3. knob unset, image local      → `docker run` of the pinned image on THIS device (a local execution: the
                                    image is a way of having the binary, not a worker)
  4. nothing local                → the topology's provider for module `computelod.engines` (ModuleAssignment
                                    rows; LIVE candidates only; `pol allocate computelod.engines <instance>`)
  5. nothing                      → refusal naming BOTH knobs
`placement()` reports where each engine WOULD run before any dispatch; `/api/computelod/engines` serves it.

Execution is ARGV ONLY (engine + args, no shell), matching the worker's contract; a step's stdout can be
captured to a file in the work dir (`stdout_to`) — the pipelines the flows used to express with `> log` and
`| grep` live in Python now. The PDK (lod-3c) is a mounted read-only volume locally and the worker's own volume
remotely; `pdk=True` asks for it and refuses when absent.
"""
import base64
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request

KNOB = 'EDA_ENGINES_URL'
PROVIDER_MODULE = 'computelod.engines'
IMAGE = os.environ.get('POLARI_EDA_IMAGE') or os.environ.get('POLARI_COMPUTELOD_TOOLS_IMAGE', 'polari-eda-tools:noble')
STA_IMAGE = os.environ.get('POLARI_OPENSTA_IMAGE', 'openroad/opensta')   # the pre-seam way of having `sta`; still honoured locally
PDK_ROOT = os.environ.get('POLARI_PDK_ROOT') or os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')), 'polari-lod', 'pdk')
REMOTE = 'remote'
_ENGINE = 'eda'
#: engine name → binary (the worker's table, mirrored)
ENGINES = {
    'riscv-gcc': 'riscv64-unknown-elf-gcc', 'riscv-objdump': 'riscv64-unknown-elf-objdump',
    'yosys': 'yosys', 'iverilog': 'iverilog', 'vvp': 'vvp', 'verilator': 'verilator',
    'nextpnr-ice40': 'nextpnr-ice40', 'icepack': 'icepack', 'icetime': 'icetime',
    'sta': 'sta', 'magic': 'magic', 'netgen': 'netgen-lvs',
}
_CAP_CACHE = {}
_CAP_TTL_S = 30.0
_IMAGE_CACHE = {}


class EngineError(RuntimeError):
    pass


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def topology_url():
    """Rung 4: a LIVE provider from the topology rows, or ''."""
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(PROVIDER_MODULE)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:
        pass
    return ''


def remote_capability(url, timeout=5):
    now = time.time()
    cached = _CAP_CACHE.get(url)
    if cached and now - cached[0] < _CAP_TTL_S:
        return cached[1]
    cap = None
    try:
        try:
            from polariApiServer import outbound
            with outbound.http_request('engine', _ENGINE, 'GET', '%s/capability' % url, means='probe', timeout=timeout, lib='urllib') as response:
                cap = json.load(response)
        except ImportError:
            with urllib.request.urlopen('%s/capability' % url, timeout=timeout) as response:
                cap = json.load(response)
    except Exception:
        cap = None
    _CAP_CACHE[url] = (now, cap)
    return cap


def _has(cap, engine):
    return bool(cap and (cap.get('engines') or {}).get(engine, {}).get('available'))


def _local_binary(engine):
    b = ENGINES[engine]
    for cand in (shutil.which(b), os.path.expanduser('~/.local/bin/%s' % b), os.path.expanduser('~/tools/%s/bin/%s' % (b, b))):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def _docker_ok(image):
    if image in _IMAGE_CACHE:
        return _IMAGE_CACHE[image]
    try:
        ok = subprocess.run(['docker', 'image', 'inspect', image], capture_output=True, timeout=20).returncode == 0
    except Exception:
        ok = False
    _IMAGE_CACHE[image] = ok
    return ok


def _image_has(engine):
    key = (IMAGE, engine)
    if key in _IMAGE_CACHE:
        return _IMAGE_CACHE[key]
    ok = False
    if _docker_ok(IMAGE):
        try:
            ok = subprocess.run(['docker', 'run', '--rm', '--entrypoint', 'sh', IMAGE, '-c', 'command -v %s' % ENGINES[engine]], capture_output=True, timeout=60).returncode == 0
        except Exception:
            ok = False
    _IMAGE_CACHE[key] = ok
    return ok


def resolve(engine):
    """{'how': 'remote'|'local-binary'|'local-image'|'refused', 'where': url|path|image, 'why': str} for ONE engine."""
    if engine not in ENGINES:
        return {'how': 'refused', 'where': '', 'why': 'unknown engine %r — one of %s' % (engine, sorted(ENGINES))}
    url = knob_url()
    if url:
        cap = remote_capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'why': '%s=%s is set but the worker is unreachable — refusing (a declared worker never silently falls back to local)' % (KNOB, url)}
        if not _has(cap, engine):
            return {'how': 'refused', 'where': url, 'why': '%s=%s reached but that worker lacks %s' % (KNOB, url, engine)}
        return {'how': REMOTE, 'where': url, 'why': 'knob'}
    b = _local_binary(engine)
    if b:
        return {'how': 'local-binary', 'where': b, 'why': 'on this device'}
    if _image_has(engine):
        return {'how': 'local-image', 'where': IMAGE, 'why': 'the pinned image on this device'}
    if engine == 'sta' and _docker_ok(STA_IMAGE):
        return {'how': 'local-image', 'where': STA_IMAGE, 'why': 'the openroad/opensta image on this device (pre-seam)'}
    url = topology_url()
    if url and _has(remote_capability(url), engine):
        return {'how': REMOTE, 'where': url, 'why': 'topology provider %s' % PROVIDER_MODULE}
    return {'how': 'refused', 'where': '', 'why': 'no %s: not on the PATH, no %s image here, no live %s provider — set %s or `pol allocate %s <instance>`' % (
        engine, IMAGE, PROVIDER_MODULE, KNOB, PROVIDER_MODULE)}


def placement():
    """Where each engine WOULD run, before any dispatch (the capability endpoint's answer)."""
    return {'knob': KNOB, 'knob_value': knob_url(), 'provider_module': PROVIDER_MODULE, 'image': IMAGE, 'pdk_root_local': PDK_ROOT,
            'pdk_present_local': os.path.exists(os.path.join(PDK_ROOT, 'sky130A', 'libs.tech', 'magic', 'sky130A.tech')),
            'engines': {e: resolve(e) for e in ENGINES},
            'ladder': ['%s (always, or refusal)' % KNOB, 'local binary', 'local image %s' % IMAGE, 'topology provider %s (live only)' % PROVIDER_MODULE, 'refusal']}


def _post(url, payload, timeout):
    data = json.dumps(payload).encode()
    req = urllib.request.Request('%s/run' % url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        try:
            from polariApiServer import outbound
            with outbound.http_request('engine', _ENGINE, 'POST', req, timeout=timeout, lib='urllib') as response:
                return json.load(response)
        except ImportError:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            return json.load(exc)
        except Exception:
            raise EngineError('worker %s: HTTP %s' % (url, exc.code))
    except Exception as exc:
        raise EngineError('worker %s unreachable: %s' % (url, exc))


def _is_text(fp):
    try:
        with open(fp, 'rb') as fh:
            return b'\0' not in fh.read(4096)
    except Exception:
        return False


def run(engine, work, args, timeout=900, env=None, pdk=False, stdout_to=None, send=None, stdin=None):
    """Run ONE engine with argv `args` in `work` (cwd), wherever `resolve` says. Returns
    {'returncode', 'stdout', 'stderr', 'how', 'where'}; stdout also lands in work/<stdout_to> when asked.
    `send` limits which files travel to a remote worker (default: every file in work up to 64 MB)."""
    r = resolve(engine)
    if r['how'] == 'refused':
        raise EngineError(r['why'])
    if pdk and r['how'] != REMOTE and not os.path.exists(os.path.join(PDK_ROOT, 'sky130A', 'libs.tech', 'magic', 'sky130A.tech')):
        raise EngineError('engine %s needs the PDK and none is at %s (polari-eda-tools/fetch-pdk.sh, or POLARI_PDK_ROOT)' % (engine, PDK_ROOT))
    args = [str(a) for a in args]
    env = dict(env or {})
    if r['how'] == REMOTE:
        files, files_b64 = {}, {}
        names = send if send is not None else sorted(os.listdir(work))
        for fn in names:
            fp = os.path.join(work, fn)
            if not os.path.isfile(fp):
                continue
            if _is_text(fp):
                files[fn] = open(fp, errors='replace').read()
            else:
                files_b64[fn] = base64.b64encode(open(fp, 'rb').read()).decode()
        rep = _post(r['where'], {'engine': engine, 'args': args, 'files': files, 'files_b64': files_b64, 'env': env, 'timeout': timeout, 'stdin': stdin}, timeout + 60)
        if not rep.get('ok'):
            raise EngineError('worker refused %s: %s' % (engine, rep.get('error')))
        for fn, text in (rep.get('files') or {}).items():
            p = os.path.join(work, fn); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(text)
        for fn, b64 in (rep.get('files_b64') or {}).items():
            p = os.path.join(work, fn); os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'wb').write(base64.b64decode(b64))
        out = {'returncode': rep.get('returncode', -1), 'stdout': rep.get('stdout', ''), 'stderr': rep.get('stderr', ''), 'how': REMOTE, 'where': r['where']}
    elif r['how'] == 'local-binary':
        # the engine's view of the PDK is /pdk/…; a local binary sees the real root
        local_args = [PDK_ROOT + a[4:] if a.startswith('/pdk/') else a for a in args]
        full_env = dict(os.environ, PDK_ROOT=PDK_ROOT, **env)
        p = subprocess.run([r['where']] + local_args, capture_output=True, text=True, timeout=timeout, cwd=work, env=full_env, input=stdin)
        out = {'returncode': p.returncode, 'stdout': p.stdout or '', 'stderr': p.stderr or '', 'how': 'local-binary', 'where': r['where']}
    else:   # local image
        image = r['where']
        cmd = ['docker', 'run', '--rm'] + (['-i'] if stdin is not None else []) + ['-u', '%d:%d' % (os.getuid(), os.getgid()), '-e', 'HOME=/tmp', '-v', '%s:/w' % work, '-w', '/w']
        if pdk:
            cmd += ['-v', '%s:/pdk:ro' % PDK_ROOT, '-e', 'PDK_ROOT=/pdk']
        for k, v in env.items():
            cmd += ['-e', '%s=%s' % (k, v)]
        if image == STA_IMAGE:
            cmd += ['--entrypoint', '/OpenSTA/build/sta', image] + args
        else:
            cmd += [image, ENGINES[engine]] + args
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=work, input=stdin)
        out = {'returncode': p.returncode, 'stdout': p.stdout or '', 'stderr': p.stderr or '', 'how': 'local-image', 'where': image}
    if stdout_to:
        open(os.path.join(work, stdout_to), 'w').write(out['stdout'] + out['stderr'])
    return out


def pdk_path(rel):
    """A PDK path as the ENGINE sees it: '/pdk/<rel>' inside an image or on a worker, the local root for a local binary."""
    return '/pdk/' + rel.lstrip('/')


def pdk_local(rel):
    return os.path.join(PDK_ROOT, rel.lstrip('/'))
