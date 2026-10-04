"""
@module pcb.custom.pcb_engines

THE ENGINES SEAM of the PCB arc (pcb-0, PCB_FROM_SCRATCH_PLAN §0/§6/§7): KiCad is the RELAY ENGINE — `kicad-cli` checks (ERC,
DRC) and exports (Gerbers, drill, pos, BOM, netlist, SVG, STEP) — and this module never assumes a device (his rule 2026-09-24:
modules declare engines and resolve them through the ladder). The same ladder as board.custom.board_engines:

  1. PCB_ENGINES_URL set     → that worker, ALWAYS (unreachable or lacking kicad-cli = REFUSAL; a declared worker never
                               silently degrades to local)
  2. knob unset, local binary → `kicad-cli` on the PATH (a desktop KiCad — pcb-na's native app)
  3. the worker IMAGE local   → `docker run` of PCB_ENGINES_IMAGE (default prf-pcb-engines:trixie, polari-rf-node/prf-pcb-engines/)
  4. nothing local            → the topology's provider for module `pcb.engines` (LIVE candidates only; PROVIDER_PORTS
                               'prf-pcb-engines': 9860)
  5. nothing                  → a refusal naming the knob, the image and the provider module

run(args, files, source_date) runs ONE kicad-cli verb on the resolved rung: files keep their RELATIVE paths (a project's
footprints.pretty/…), outputs come back at theirs (gerbers/x-F_Cu.gtl). `source_date` freezes the clock the outputs stamp
(the worker runs kicad-cli under libfaketime; the image rung passes the same env; a local binary uses `faketime` when it is on
the PATH, else the run is marked NOT byte-stable) and every rung runs in the same directory (/tmp/pcb-job) — so the same
inputs give the same bytes wherever they ran. library(kind, lib, name) returns one official library entry + its file's sha256.
"""
import base64
import json
import os
import shutil
import ssl
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

KNOB = 'PCB_ENGINES_URL'
IMAGE_KNOB = 'PCB_ENGINES_IMAGE'
DEFAULT_IMAGE = 'prf-pcb-engines:trixie'
PROVIDER_MODULE = 'pcb.engines'
COMPOSE = 'docker-compose.pcb-engines.yml'
ENGINE = 'kicad-cli'
LICENCE = 'GPL-3.0+ (KiCad 9.0.2, Debian kicad 9.0.2+dfsg-1) — a separate process, never linked'
JOB_DIR = '/tmp/pcb-job'
FAKETIME_LIB = '/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1'
#: the frozen clock pcb-0's records use (the slice date) — any fixed value works; it is recorded on every export row
SOURCE_DATE = os.environ.get('POLARI_PCB_SOURCE_DATE', '2026-10-03 00:00:00')
LOCAL_IMAGE = 'local-image'
REMOTE = 'remote'
_CAP = {}
_TTL = 30.0


class EngineRefused(RuntimeError):
    pass


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def image_name():
    return os.environ.get(IMAGE_KNOB, '') or DEFAULT_IMAGE


def local_image():
    img = image_name()
    hit = _CAP.get(('img', img))
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    iid = ''
    if shutil.which('docker'):
        try:
            p = subprocess.run(['docker', 'image', 'inspect', img, '--format', '{{.Id}}'], capture_output=True, text=True, timeout=15)
            iid = p.stdout.strip() if p.returncode == 0 else ''
        except Exception:
            iid = ''
    _CAP[('img', img)] = (time.time(), iid)
    return iid


def local_binary():
    b = shutil.which(ENGINE)
    return b if b and os.access(b, os.X_OK) else None


def topology_url():
    try:
        from topology.provider_registry import resolve_provider
        r = resolve_provider(PROVIDER_MODULE)
        if r.get('ok'):
            return r['url'].rstrip('/')
    except Exception:
        pass
    return ''


def _get(url, timeout):
    from polariApiServer import outbound
    with outbound.http_request('engine', 'pcb', 'GET', url, means='probe', timeout=timeout, lib='urllib') as r:
        return json.load(r)


def capability(url, timeout=5):
    hit = _CAP.get(url)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    try:
        cap = _get('%s/capability' % url, timeout)
    except Exception:
        cap = None
    _CAP[url] = (time.time(), cap)
    return cap


def _has(cap):
    return bool(cap and (cap.get('engines') or {}).get(ENGINE, {}).get('available'))


def refusal():
    return ('no %s: %s unset, no kicad-cli on the PATH here, no %s image on this docker, no live %s provider — build the image '
            '(tar -C polari-rf-node/prf-pcb-engines -cf - . | ssh <device> docker build -t %s -, or docker compose -f polari-rf-node/%s '
            'build), set %s=http://<device>:9860, or `pol allocate %s <instance>`'
            % (ENGINE, KNOB, image_name(), PROVIDER_MODULE, DEFAULT_IMAGE, COMPOSE, KNOB, PROVIDER_MODULE))


def resolve():
    """{'how': remote|local-binary|local-image|refused, 'where', 'why'} — where kicad-cli WOULD run, before any dispatch."""
    url = knob_url()
    if url:
        cap = capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'why': '%s=%s is set but the worker is unreachable — refusing (a declared worker never '
                                                             'silently falls back to local)' % (KNOB, url)}
        if not _has(cap):
            return {'how': 'refused', 'where': url, 'why': '%s=%s reached but that worker lacks %s' % (KNOB, url, ENGINE)}
        return {'how': REMOTE, 'where': url, 'why': 'knob %s' % KNOB}
    b = local_binary()
    if b:
        return {'how': 'local-binary', 'where': b, 'why': 'on this device'}
    if local_image():
        return {'how': LOCAL_IMAGE, 'where': image_name(), 'why': 'the pcb engines image on this device (%s)' % local_image()[:19]}
    url = topology_url()
    if url and _has(capability(url)):
        return {'how': REMOTE, 'where': url, 'why': 'topology provider %s' % PROVIDER_MODULE}
    return {'how': 'refused', 'where': '', 'why': refusal()}


def placement():
    """GET /api/pcb/engines and `pol pcb engines`."""
    r = resolve()
    cap = capability(r['where']) if r['how'] == REMOTE else None
    return {'engine': ENGINE, 'licence': LICENCE, 'knob': KNOB, 'knob_value': knob_url(), 'image': image_name(), 'image_present': bool(local_image()),
            'provider_module': PROVIDER_MODULE, 'resolved': r, 'worker': cap,
            'ladder': ['%s (always, or refusal)' % KNOB, 'local kicad-cli', 'the local image %s (%s)' % (image_name(), IMAGE_KNOB),
                       'topology provider %s (live only)' % PROVIDER_MODULE, 'refusal']}


# ---------------------------------------------------------------- running one verb
def _write(work, files):
    for rel, data in files.items():
        rel = os.path.normpath(rel)
        if rel.startswith('..') or os.path.isabs(rel):
            raise EngineRefused('bad input path %r' % rel)
        fp = os.path.join(work, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, 'wb').write(data if isinstance(data, bytes) else data.encode())


def _collect(work, sent):
    out = {}
    for root, dirs, fns in os.walk(work):
        dirs.sort()
        for fn in sorted(fns):
            rel = os.path.relpath(os.path.join(root, fn), work)
            if rel not in sent:
                out[rel] = open(os.path.join(root, fn), 'rb').read()
    return out


def _out_dirs(work, args):
    for i, a in enumerate(args[:-1]):
        if a in ('-o', '--output') and args[i + 1].endswith('/'):
            os.makedirs(os.path.join(work, args[i + 1]), exist_ok=True)


def _local(argv_prefix, args, files, timeout, source_date, image=False):
    """A local binary (argv_prefix = [kicad-cli] or [faketime, date, kicad-cli]) or the image (docker run … image kicad-cli)."""
    base = tempfile.mkdtemp(prefix='polari-pcb-')
    work = os.path.join(base, 'pcb-job')
    os.makedirs(work)
    try:
        _write(work, files)
        _out_dirs(work, args)
        if image:
            env = ['-e', 'HOME=/tmp'] + (['-e', 'LD_PRELOAD=%s' % FAKETIME_LIB, '-e', 'FAKETIME=%s' % source_date, '-e', 'DONT_FAKE_MONOTONIC=1']
                                         if source_date else [])
            argv = ['docker', 'run', '--rm', '-u', '%d:%d' % (os.getuid(), os.getgid()), '-v', '%s:%s' % (work, JOB_DIR), '-w', JOB_DIR] + env + \
                   [image_name(), ENGINE] + list(args)
        else:
            argv = list(argv_prefix) + list(args)
        t0 = time.perf_counter()
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=work,
                           env=dict(os.environ, HOME=tempfile.gettempdir()) if not image else None)
        cost = {'wall_s': round(time.perf_counter() - t0, 3),
                'source': 'wall only: the engine ran inside docker' if image else 'wall of the local kicad-cli'}
        return {'ok': p.returncode == 0, 'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr,
                'files': _collect(work, {os.path.normpath(f) for f in files}), 'cost': cost, 'argv': argv}
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _remote(url, args, files, timeout, source_date):
    body = json.dumps({'engine': ENGINE, 'args': list(args), 'timeout': timeout, 'source_date': source_date,
                       'files_b64': {k: base64.b64encode(v if isinstance(v, bytes) else v.encode()).decode() for k, v in files.items()}}).encode()
    req = urllib.request.Request('%s/run' % url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    t0 = time.perf_counter()
    from polariApiServer import outbound
    with outbound.http_request('engine', 'pcb', 'POST', req, means='run', timeout=timeout + 30, lib='urllib',
                               context=ssl._create_unverified_context()) as r:
        d = json.load(r)
    for k in ('stdout', 'stderr'):
        if '%s_chars' % k in d and len(d.get(k) or '') != int(d['%s_chars' % k]):
            raise EngineRefused('%s from %s arrived cut: %d of %d characters' % (k, url, len(d.get(k) or ''), int(d['%s_chars' % k])))
    out = {k: v.encode() for k, v in (d.get('files') or {}).items()}
    out.update({k: base64.b64decode(v) for k, v in (d.get('files_b64') or {}).items()})
    return {'ok': bool(d.get('ok')) and d.get('returncode') == 0, 'returncode': d.get('returncode'), 'stdout': d.get('stdout', ''),
            'stderr': d.get('stderr', '') or d.get('error', ''), 'files': out, 'cost': dict(d.get('cost') or {}, round_trip_s=round(time.perf_counter() - t0, 3)),
            'argv': [ENGINE] + list(args)}


def run(args, files=None, source_date=SOURCE_DATE, timeout=600):
    """One kicad-cli verb wherever resolve() says → {ok, how, where, returncode, stdout, stderr, files: {rel: bytes}, cost, argv,
    source_date, byte_stable}. EngineRefused names why not."""
    where = resolve()
    if where['how'] == 'refused':
        raise EngineRefused(where['why'])
    files = files or {}
    stable = bool(source_date)
    if where['how'] == 'local-binary':
        ft = shutil.which('faketime') if source_date else None
        stable = bool(ft)
        res = _local(([ft, source_date] if ft else []) + [where['where']], args, files, timeout, source_date)
    elif where['how'] == LOCAL_IMAGE:
        res = _local(None, args, files, timeout, source_date, image=True)
    else:
        res = _remote(where['where'], args, files, timeout, source_date)
    res.update(how=where['how'], where=where['where'], source_date=source_date if stable else '', byte_stable=stable)
    return res


def version():
    """'kicad-cli 9.0.2 (dpkg kicad 9.0.2+dfsg-1)' from the worker's capability, else `kicad-cli version`; '' when refused."""
    r = resolve()
    if r['how'] == REMOTE:
        cap = capability(r['where']) or {}
        return ((cap.get('engines') or {}).get(ENGINE) or {}).get('version', '')
    try:
        res = run(['version'], source_date='')
        return 'kicad-cli %s' % res['stdout'].strip()
    except Exception:
        return ''


def libraries():
    """{kicad-symbols: {version, md5sums_sha256, files}, kicad-footprints: …} from the worker (remote rung only; '' elsewhere)."""
    r = resolve()
    if r['how'] == REMOTE:
        return (capability(r['where']) or {}).get('libraries') or {}
    return {}


def library(kind, lib, name):
    """One official library entry {text, lib_sha256, lib_version, lib_file} — the worker's GET /library on the remote rung; the
    local rungs read the installed library file (the local binary's /usr/share/kicad or the image's) and cut the entry here."""
    r = resolve()
    if r['how'] == 'refused':
        raise EngineRefused(r['why'])
    if r['how'] == REMOTE:
        q = urllib.parse.urlencode({'kind': kind, 'lib': lib, 'name': name})
        try:
            d = _get('%s/library?%s' % (r['where'], q), 30)
        except Exception as e:
            raise EngineRefused('%s/library refused %s %s:%s — %s' % (r['where'], kind, lib, name, e))
        return d
    path = ('/usr/share/kicad/symbols/%s.kicad_sym' % lib) if kind == 'symbol' else ('/usr/share/kicad/footprints/%s.pretty/%s.kicad_mod' % (lib, name))
    if r['how'] == LOCAL_IMAGE:
        p = subprocess.run(['docker', 'run', '--rm', image_name(), 'cat', path], capture_output=True, timeout=120)
        if p.returncode:
            raise EngineRefused('no %s %s:%s in %s (%s)' % (kind, lib, name, image_name(), path))
        data = p.stdout
    else:
        if not os.path.isfile(path):
            raise EngineRefused('no %s %s:%s in the local KiCad libraries (%s)' % (kind, lib, name, path))
        data = open(path, 'rb').read()
    import hashlib
    text = data.decode('utf-8')
    if kind == 'symbol':
        from pcb.custom import sexpr as S
        hit = [s for s in S.find(S.parse(text), 'symbol') if str(s[1]) == name]
        if not hit:
            raise EngineRefused('no symbol %s in %s' % (name, path))
        if S.find(hit[0], 'extends'):
            raise EngineRefused('symbol %s:%s is DERIVED (extends) — not flattened here' % (lib, name))
        text = S.write(hit[0])
    return {'ok': True, 'kind': kind, 'lib': lib, 'name': name, 'text': text, 'lib_file': path,
            'lib_sha256': hashlib.sha256(data).hexdigest(), 'lib_version': 'local %s' % r['where']}
