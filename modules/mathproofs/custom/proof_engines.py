"""
@module mathproofs.custom.proof_engines

THE ENGINES SEAM of the proof tiers — the Polari engines ladder, exactly as `computelod.custom.eda_engines` (and
cntfet's `cnt_remote`, materialsScience's `engines.remote`): the Lean checker runs on WHATEVER device the topology
assigns and the core keeps the claim rows. No device is assumed anywhere (his rule, 2026-09-24).

Resolution for the one engine `lean`, honest at every rung:
  1. PROOF_ENGINES_URL set        → that worker, ALWAYS (unreachable or lacking lean = REFUSAL; a declared worker never
                                    silently degrades to local)
  2. knob unset, project local    → `lake` on the PATH AND a pinned project at POLARI_PROOF_PROJECT (the submodule's
                                    checkout with its .lake built) — a local execution through flows/check.sh
  3. knob unset, image local      → `docker run` of the pinned image on THIS device (a way of having the checker,
                                    not a worker)
  4. nothing local                → the topology's LIVE provider for module `mathproofs.engines`
                                    (`pol allocate mathproofs.engines <instance>`)
  5. nothing                      → refusal naming BOTH knobs
`placement()` answers before any dispatch; `GET /api/mathproofs/engines` serves it. `check(file, statement_hash,
timeout)` runs ONE theorem file wherever `resolve` says and returns the worker's shape either way.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

KNOB = 'PROOF_ENGINES_URL'
PROVIDER_MODULE = 'mathproofs.engines'
IMAGE = os.environ.get('POLARI_PROOF_IMAGE', 'polari-proof-tools:noble')
PROJECT = os.environ.get('POLARI_PROOF_PROJECT', '')   # a local checkout of polari-proof-tools with its .lake built
REMOTE = 'remote'
_ENGINE = 'proof'
_CAP_CACHE = {}
_CAP_TTL_S = 30.0
_IMAGE_CACHE = {}


class EngineError(RuntimeError):
    pass


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def topology_url():
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


def _has(cap):
    return bool(cap and (cap.get('engines') or {}).get('lean', {}).get('available'))


def _local_project():
    """A local checkout with `lake` available and the project built (a .lake dir) — rung 2."""
    if PROJECT and shutil.which('lake') and os.path.isfile(os.path.join(PROJECT, 'lean-toolchain')) and os.path.isdir(os.path.join(PROJECT, '.lake')):
        return PROJECT
    return None


def _image_ok():
    if IMAGE in _IMAGE_CACHE:
        return _IMAGE_CACHE[IMAGE]
    try:
        ok = subprocess.run(['docker', 'image', 'inspect', IMAGE], capture_output=True, timeout=20).returncode == 0
    except Exception:
        ok = False
    _IMAGE_CACHE[IMAGE] = ok
    return ok


def resolve():
    """{'how': 'remote'|'local-project'|'local-image'|'refused', 'where': url|path|image, 'why': str} for `lean`."""
    url = knob_url()
    if url:
        cap = remote_capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'why': '%s=%s is set but the worker is unreachable — refusing (a declared worker never silently falls back to local)' % (KNOB, url)}
        if not _has(cap):
            return {'how': 'refused', 'where': url, 'why': '%s=%s reached but that worker has no working lean' % (KNOB, url)}
        return {'how': REMOTE, 'where': url, 'why': 'knob'}
    p = _local_project()
    if p:
        return {'how': 'local-project', 'where': p, 'why': 'lake + the pinned project on this device (POLARI_PROOF_PROJECT)'}
    if _image_ok():
        return {'how': 'local-image', 'where': IMAGE, 'why': 'the pinned image on this device'}
    url = topology_url()
    if url and _has(remote_capability(url)):
        return {'how': REMOTE, 'where': url, 'why': 'topology provider %s' % PROVIDER_MODULE}
    return {'how': 'refused', 'where': '', 'why': 'no lean: no %s, no local project (POLARI_PROOF_PROJECT + lake), no %s image here, no live %s provider — set %s or `pol allocate %s <instance>`' % (
        KNOB, IMAGE, PROVIDER_MODULE, KNOB, PROVIDER_MODULE)}


def placement():
    r = resolve()
    cap = remote_capability(r['where']) if r['how'] == REMOTE else None
    return {'knob': KNOB, 'knob_value': knob_url(), 'provider_module': PROVIDER_MODULE, 'image': IMAGE, 'project_local': PROJECT, 'engines': {'lean': r},
            'pins': (cap or {}).get('pins') if cap else None, 'theorems': [t.get('file') for t in (cap or {}).get('theorems', [])] if cap else None,
            'ladder': ['%s (always, or refusal)' % KNOB, 'local project (POLARI_PROOF_PROJECT + lake)', 'local image %s' % IMAGE, 'topology provider %s (live only)' % PROVIDER_MODULE, 'refusal'],
            'policy': 'lean is never run automatically (plan §I.9): a person or the pipeline asks, within the claim\'s budget_s'}


def _post(url, payload, timeout):
    data = json.dumps(payload).encode()
    req = urllib.request.Request('%s/check' % url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
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


def _header(text):
    h = re.search(r'^POLARI_STATEMENT_HASH (\S+)', text, re.M)
    t = re.search(r'^POLARI_TERM (.*)$', text, re.M)
    return (h.group(1) if h else ''), (t.group(1).strip() if t else '')


def _parse_local(rc, out, err, rel, statement_hash, text, elapsed, timeout, how, where):
    m = re.search(r'^POLARI_PROOF (ok|error) (\S+)', out, re.M)
    pins = re.search(r'^POLARI_PINS lean=(\S*) mathlib=(\S*)', out, re.M)
    h, term = _header(text)
    verdict = 'timeout' if rc == 124 else ('proved' if (m and m.group(1) == 'ok' and rc == 0) else 'error')
    return {'ok': True, 'verdict': verdict, 'returncode': rc, 'stdout': out[-20000:], 'stderr': err[-20000:], 'file': rel, 'file_sha256': hashlib.sha256(text.encode()).hexdigest(), 'statement_hash_in_file': h, 'term_in_file': term,
            'hash_matches': bool(statement_hash) and statement_hash == h, 'pins': {'lean': pins.group(1) if pins else '', 'mathlib': pins.group(2) if pins else ''}, 'elapsed_s': elapsed, 'timeout_s': timeout, 'how': how, 'where': where}


def check(file, statement_hash, timeout=600):
    """Check ONE committed theorem file (a path inside theorems/) wherever `resolve` says. Returns the worker's shape
    (+ how/where). Raises EngineError on a refusal or an unreachable worker."""
    r = resolve()
    if r['how'] == 'refused':
        raise EngineError(r['why'])
    if file.startswith('/') or '..' in file or not file.endswith('.lean'):
        raise EngineError('a theorem file is a .lean path inside theorems/')
    if r['how'] == REMOTE:
        rep = _post(r['where'], {'file': file, 'statement_hash': statement_hash, 'timeout': timeout}, timeout + 60)
        if not rep.get('ok'):
            raise EngineError('worker refused: %s' % rep.get('error'))
        rep['how'] = REMOTE; rep['where'] = r['where']
        return rep
    t0 = time.time()
    if r['how'] == 'local-project':
        proj = r['where']; rel = os.path.join('theorems', file)
        text = open(os.path.join(proj, rel), errors='replace').read() if os.path.isfile(os.path.join(proj, rel)) else ''
        if not text:
            raise EngineError('no such theorem file %r in %s' % (file, proj))
        p = subprocess.run([os.path.join(proj, 'flows', 'check.sh'), rel, str(timeout)], capture_output=True, text=True, timeout=timeout + 30, cwd=proj, env=dict(os.environ, POLARI_PROOF_PROJECT=proj))
        return _parse_local(p.returncode, p.stdout or '', p.stderr or '', file, statement_hash, text, round(time.time() - t0, 3), timeout, 'local-project', proj)
    image = r['where']
    show = subprocess.run(['docker', 'run', '--rm', image, 'cat', 'theorems/' + file], capture_output=True, text=True, timeout=120)
    if show.returncode != 0:
        raise EngineError('no such theorem file %r in image %s' % (file, image))
    p = subprocess.run(['docker', 'run', '--rm', image, 'flows/check.sh', 'theorems/' + file, str(timeout)], capture_output=True, text=True, timeout=timeout + 60)
    return _parse_local(p.returncode, p.stdout or '', p.stderr or '', file, statement_hash, show.stdout, round(time.time() - t0, 3), timeout, 'local-image', image)
