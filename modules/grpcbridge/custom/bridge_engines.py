"""
@module grpcbridge.custom.bridge_engines

THE ENGINES SEAM of the hosted bridge (sim-2) - the same ladder shape as board.custom.board_engines.resolve_sessions. A hosted bridge is a WORKER-level door
(a detached JVM on the bridge-engines worker, prf-bridge-engines/), so a local binary or a local image never serves it. Ladder:

  1. BRIDGE_ENGINES_URL set   -> that worker, ALWAYS (unreachable, or lacking the bridges door = REFUSAL; a declared worker never silently degrades)
  2. the topology provider    -> module `grpcbridge.engines` (LIVE candidates only; `pol allocate grpcbridge.engines <instance>`)
  3. nothing                  -> refusal in words naming the knob, the image and the provider module
"""
import json
import os
import time

KNOB = 'BRIDGE_ENGINES_URL'
IMAGE = 'prf-bridge-engines:trixie'
PROVIDER_MODULE = 'grpcbridge.engines'
REMOTE = 'remote'
_CAP_CACHE = {}
_CAP_TTL_S = 30.0


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def topology_url():
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(PROVIDER_MODULE)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:  # noqa: BLE001 - no topology (a selftest, a host tool): the ladder moves on
        pass
    return ''


def remote_capability(url, timeout=5):
    now = time.time()
    cached = _CAP_CACHE.get(url)
    if cached and now - cached[0] < _CAP_TTL_S:
        return cached[1]
    cap = None
    try:
        from polariApiServer import outbound
        with outbound.http_request('engine', 'grpcbridge', 'GET', '%s/capability' % url, means='probe', timeout=timeout, lib='urllib') as response:
            cap = json.load(response)
    except Exception:  # noqa: BLE001
        cap = None
    _CAP_CACHE[url] = (now, cap)
    return cap


def forget(url=None):
    """Drop cached probes (a selftest that starts a fake worker, a person who just rolled the stack)."""
    if url:
        _CAP_CACHE.pop(url, None)
    else:
        _CAP_CACHE.clear()


def _hosts_bridges(cap):
    return bool(cap and (cap.get('bridges') or {}).get('available'))


def resolve():
    """{'how': 'remote'|'refused', 'where': worker url, 'why'}."""
    url = knob_url()
    if url:
        cap = remote_capability(url)
        if cap is None:
            return {'how': 'refused', 'where': url, 'why': '%s=%s is set but the worker is unreachable - refusing (a declared worker never silently falls back)' % (KNOB, url)}
        if not _hosts_bridges(cap):
            return {'how': 'refused', 'where': url, 'why': '%s=%s reached, but that worker does not host bridges (it needs the %s image: java + mvn - roll the '
                                                           'bridge-engines service)' % (KNOB, url, IMAGE)}
        return {'how': REMOTE, 'where': url, 'why': 'knob'}
    url = topology_url()
    if url and _hosts_bridges(remote_capability(url)):
        return {'how': REMOTE, 'where': url, 'why': 'topology provider %s' % PROVIDER_MODULE}
    return {'how': 'refused', 'where': '', 'why': 'no worker hosts bridges: set %s to a bridge-engines worker (image %s, polari-rf-node/prf-bridge-engines/), or `pol allocate %s '
                                                  '<instance>`; a hosted bridge is a worker-level door, so a local binary or image cannot serve it' % (KNOB, IMAGE, PROVIDER_MODULE)}


def placement():
    return {'knob': KNOB, 'knob_value': knob_url(), 'provider_module': PROVIDER_MODULE, 'image': IMAGE, 'resolved': resolve(),
            'ladder': ['%s (always, or refusal)' % KNOB, 'topology provider %s (live only)' % PROVIDER_MODULE, 'refusal']}
