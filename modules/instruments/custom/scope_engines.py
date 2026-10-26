"""
@module instruments.custom.scope_engines

osc-5: THE ENGINES SEAM of the instruments module — where an emulated scope runs (the ladder of board.custom.board_engines, shortened: this
engine has an honest LOCAL rung by construction, the emulator being pure Python):
  1. SCOPE_ENGINES_URL set              → that worker, ALWAYS (unreachable = REFUSAL; a declared worker never silently degrades to local)
  2. the EngineProviderBinding row `scope` → that worker (the row `isle app deploy … --engine scope` writes; the catalog tile `scope-engines`);
                                           unreachable = refusal naming the row
  3. nothing declared                   → in-process (the emulator as a thread of the backend; its SCPI port is a loopback port) — unless the
                                           caller asked for `where='worker'`, which is then a refusal naming the knob, the tile and `pol dev deploy scope-engines`

    resolve(where='auto'|'worker'|'local') -> {'how': 'worker'|'local'|'refused', 'url', 'why', 'capability'?}
    capability(url) -> the worker's /capability dict or None
    post(url, path, body) / delete(url, path) -> the worker's JSON reply (raises WorkerRefused with the words on a non-2xx)
Outbound calls go through polariApiServer.outbound (the wrapper's own posture vocabulary) when it imports, plain urllib otherwise (a host tool context).
"""
import json
import os
import ssl
import urllib.error
import urllib.request

KNOB = 'SCOPE_ENGINES_URL'
ENGINE = 'scope'
TILE = 'scope-engines'
TIMEOUT_S = 10


class WorkerRefused(RuntimeError):
    pass


def knob_url():
    return os.environ.get(KNOB, '').strip().rstrip('/')


def binding_url():
    try:
        from topology.engine_metering import binding_url as _b
        return (_b(ENGINE) or '').rstrip('/')
    except Exception:  # noqa: BLE001 - the topology module may be absent (host tool context)
        return ''


def _request(method, url, body=None, timeout=TIMEOUT_S):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'} if data else {}, method=method)
    ctx = ssl._create_unverified_context()
    try:
        from polariApiServer import outbound
    except ImportError:
        outbound = None
    try:
        if outbound is not None:
            cm = outbound.http_request('engine', 'instruments', method, req, means='scope-engines', timeout=timeout, lib='urllib', context=ctx)
        else:
            cm = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        with cm as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            d = json.load(e)
        except ValueError:
            d = {}
        raise WorkerRefused(d.get('error') or ('%s %s -> HTTP %d' % (method, url, e.code)))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise WorkerRefused('%s %s unreachable: %s' % (method, url, e))


def capability(url):
    try:
        return _request('GET', url + '/capability')
    except WorkerRefused:
        return None


def post(url, path, body):
    return _request('POST', url + path, body)


def delete(url, path):
    return _request('DELETE', url + path)


def resolve(where='auto'):
    if where not in ('auto', 'worker', 'local'):
        return {'how': 'refused', 'url': '', 'why': "where is 'auto', 'worker' or 'local', not %r" % where}
    if where == 'local':
        return {'how': 'local', 'url': '', 'why': 'asked for in-process'}
    url = knob_url()
    if url:
        cap = capability(url)
        if cap is None:
            return {'how': 'refused', 'url': url, 'why': '%s=%s is set but the worker is unreachable - refusing (a declared worker never silently falls back)' % (KNOB, url)}
        return {'how': 'worker', 'url': url, 'why': 'knob %s' % KNOB, 'capability': cap}
    url = binding_url()
    if url:
        cap = capability(url)
        if cap is None:
            return {'how': 'refused', 'url': url, 'why': 'the EngineProviderBinding row %s names %s but it is unreachable - refusing (redeploy the %s app or clear the row)' % (ENGINE, url, TILE)}
        return {'how': 'worker', 'url': url, 'why': 'EngineProviderBinding %s' % ENGINE, 'capability': cap}
    if where == 'worker':
        return {'how': 'refused', 'url': '', 'why': 'no scope worker declared: set %s to a scope-engines worker, or deploy the catalog tile %s (`pol dev deploy %s`) '
                                                     'which writes the %s binding row' % (KNOB, TILE, TILE, ENGINE)}
    return {'how': 'local', 'url': '', 'why': 'no worker declared (no %s, no %s binding row): the emulator runs in this process' % (KNOB, ENGINE)}
