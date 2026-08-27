"""
@module cntfet.cnt_remote

dist-1/dist-4 (2026-08-26): delegation of the cntfet module's engine
subprocesses (OpenVAF, ngspice, OpenSTA, the kwant worker) to a
cnt-engines worker (polari-rf-node/cnt-engines, :9700) so the compute
runs on a swarm WORKER while this instance keeps the rows.

Resolution ladder — the same shape as materialsScience.engines.remote
and topology.provider_registry, honest at every rung:

  1. CNTFET_ENGINES_URL set  -> that worker, ALWAYS. Unreachable or
                                lacking the engine = REFUSAL (a
                                declared worker never silently
                                degrades to local — plan §3 dist-4).
  2. knob unset, engine local -> local binary (~/tools / PATH), the
                                pre-dist behaviour.
  3. knob unset, no local     -> the topology's provider for module
                                'cntfet.engines' (ModuleAssignment
                                rows; LIVE candidates only).
  4. nothing                  -> refusal naming BOTH knobs.

The capability endpoint reports WHERE each engine would run
(placement()) so the answer is visible before any dispatch.

Wire protocol = cnt_engines_service.py (JSON): /osdi/compile,
/ngspice/run, /sta/run, /kwant/run, /capability.

@consumers
  - cntfet.cnt_osdi (find_openvaf / find_ngspice / compile_osdi /
    run_ngspice)
  - cntfet.cnt_characterization (find_sta / run_sta)
  - cntfet.cnt_kwant (find_kwant_python / _run_worker)
  - cntfet.cnt_capability (placement)
"""

import json
import os
import time
import urllib.error
import urllib.request

KNOB = 'CNTFET_ENGINES_URL'
PROVIDER_MODULE = 'cntfet.engines'
REMOTE = 'remote'

_CAP_CACHE = {}
_CAP_TTL_S = 30.0


class RemoteError(RuntimeError):
    pass


def knob_url():
    return os.environ.get(KNOB, '').rstrip('/')


def topology_url():
    """Rung 3: a LIVE provider from the topology rows, or ''."""
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(PROVIDER_MODULE)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:
        pass
    return ''


def remote_capability(url, timeout=5):
    """The worker's /capability (TTL-cached), or None when unreachable."""
    now = time.time()
    cached = _CAP_CACHE.get(url)
    if cached and now - cached[0] < _CAP_TTL_S:
        return cached[1]
    try:
        with urllib.request.urlopen(f'{url}/capability',
                                    timeout=timeout) as response:
            cap = json.load(response)
    except Exception:
        cap = None
    _CAP_CACHE[url] = (now, cap)
    return cap


def _has(cap, engine):
    return bool(cap and cap.get('engines', {}).get(engine, {})
                .get('available'))


def resolve(engine, local_finder):
    """(path_or_REMOTE, detail) for one engine, walking the ladder.
    local_finder() returns (path, detail) or (None, why)."""
    url = knob_url()
    if url:
        cap = remote_capability(url)
        if cap is None:
            return None, (f'{KNOB}={url} is set but the worker is '
                          f'unreachable — refusing (a declared worker '
                          f'never silently falls back to local); '
                          f'pol swarm ps cnt-engines')
        if not _has(cap, engine):
            return None, (f'{KNOB}={url} reached but that worker lacks '
                          f'{engine}: {cap.get("engines", {}).get(engine)}')
        return REMOTE, f'remote {url} ({engine})'
    path, detail = local_finder()
    if path:
        return path, detail
    url = topology_url()
    if url and _has(remote_capability(url), engine):
        return REMOTE, f'remote {url} ({engine}, topology-resolved)'
    return None, (f'{detail}; no reachable cnt-engines worker either — '
                  f'set {KNOB}=http://<host>:9700 or place '
                  f'{PROVIDER_MODULE} on a live engines instance '
                  f'(pol allocate {PROVIDER_MODULE} <instance>)')


def active_url():
    """The URL a REMOTE resolution talks to (knob first)."""
    return knob_url() or topology_url()


def remote_post(path, payload, timeout=600):
    """POST JSON to the active worker. Transport failure raises
    RemoteError; the worker's own {'ok': False} passes through."""
    url = active_url()
    if not url:
        raise RemoteError(f'no cnt-engines worker resolvable ({KNOB} '
                          f'unset, no topology provider)')
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f'{url}{path}', data=data,
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            body = json.load(exc)
        except Exception:
            body = {'ok': False, 'error': f'HTTP {exc.code}'}
        body.setdefault('ok', False)
        body['httpStatus'] = exc.code
        return body
    except Exception as exc:
        raise RemoteError(f'{url}{path}: {exc}') from exc


def placement():
    """dist-4: WHERE each engine would run right now, as data."""
    from cntfet.cnt_osdi import find_ngspice, find_openvaf
    from cntfet.cnt_characterization import find_sta
    from cntfet.cnt_kwant import find_kwant_python
    out = {}
    for engine, finder in (('openvaf', find_openvaf),
                           ('ngspice', find_ngspice),
                           ('opensta', find_sta),
                           ('kwant', find_kwant_python)):
        path, detail = finder()
        if path == REMOTE:
            out[engine] = {'runsOn': 'remote', 'where': active_url(),
                           'detail': detail}
        elif path:
            out[engine] = {'runsOn': 'local', 'where': path,
                           'detail': detail}
        else:
            out[engine] = {'runsOn': 'refused', 'refusal': detail}
    return {'engines': out,
            'ladder': [f'{KNOB} knob wins (unreachable = refusal)',
                       'local binary', f'topology provider '
                       f'{PROVIDER_MODULE} (live only)', 'refusal'],
            'knob': knob_url() or None,
            'topologyProvider': topology_url() or None}
