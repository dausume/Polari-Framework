"""
@cross-cutting
@module mathshapes.cad_remote
@tags @xc:bindings

Delegation to the cad-engines worker (docker-compose.cad-engines.yml) —
the Debian container holding trimesh + optional FreeCAD/OpenCASCADE the
Alpine backend image cannot pip. Mirrors materialsScience.engines.remote.

Resolution ladder: the CAD_ENGINES_URL knob ALWAYS wins when set (e.g.
http://prf-cad-engines:9600); unset, the topology provider registry
resolves a LIVE provider for the 'mathshapes.cad' module. Nothing
resolvable -> honest refusal carrying the knob. Never raises: an
unreachable worker degrades to {'ok': False, suggestion}.
"""

import json
import os
import urllib.request

_MODULE = 'mathshapes.cad'


def engines_url():
    return os.environ.get('CAD_ENGINES_URL', '').rstrip('/')


def engines_url_for():
    url = engines_url()
    if url:
        return url
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(_MODULE)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:
        pass
    return ''


def unavailable_suggestion(evidence):
    return {
        'evidence': evidence,
        'knob': "CAD_ENGINES_URL env var, or the topology's cad-engines "
                'provider (ModuleAssignment rows)',
        'action': 'docker compose -p cad-engines -f '
                  'docker-compose.cad-engines.yml up -d --build (add '
                  '--build-arg WITH_FREECAD=1 for FCStd/STEP), then set '
                  'CAD_ENGINES_URL=http://prf-cad-engines:9600 on the '
                  'backend (both on polari-link) — or deploy it to a swarm '
                  'worker device and allocate mathshapes.cad to it.',
    }


def remote_capability(timeout=5):
    """The worker's /capability, or None when unset/unreachable."""
    url = engines_url_for()
    if not url:
        return None
    try:
        with urllib.request.urlopen(f'{url}/capability',
                                    timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return None


def remote_post(path, payload, timeout=300):
    """POST JSON to the worker; {'ok': False, suggestion} when it can't."""
    url = engines_url_for()
    if not url:
        return {'ok': False, 'error': 'no cad-engines worker configured',
                'suggestion': unavailable_suggestion(
                    'CAD_ENGINES_URL is unset and the topology resolves no '
                    'reachable provider.')}
    request = urllib.request.Request(
        f'{url}{path}', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except Exception as e:
        try:
            body = json.load(e)
            if isinstance(body, dict):
                return body
        except Exception:
            pass
        return {'ok': False, 'error': f'cad-engines worker unreachable: {e}',
                'suggestion': unavailable_suggestion(
                    f'{url} did not answer: {e}')}
