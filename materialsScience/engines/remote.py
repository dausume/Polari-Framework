"""
@cross-cutting
@module materialsScience.engines.remote
@tags @xc:bindings

Delegation to the msci-engines worker (docker-compose.msci-engines.yml)
— the Debian container holding the compiled-extension science stack
(pyscf, pymatgen, sfepy) the Alpine backend image cannot pip.

Resolution ladder (top-7): the MSCI_ENGINES_URL knob ALWAYS wins when
set (e.g. http://prf-msci-engines:9500); unset, the topology's
provider registry resolves a LIVE provider from ModuleAssignment /
ModuleDependencyEdge rows (auto-pick among live providers only — it
never changes configuration). Nothing resolvable -> honest refusal
carrying both knobs. Never raises: unreachable workers degrade to
{'ok': False, suggestion}.
"""

import json
import os
import urllib.request


def engines_url():
    return os.environ.get('MSCI_ENGINES_URL', '').rstrip('/')


def _module_for_path(path):
    """Engine paths name their module: /dft/* -> materialsScience.dft.
    /darcy/* (aqp-3 hydraulics) rides the fem assignment — same worker,
    same scikit-fem stack."""
    seg = path.lstrip('/').split('/', 1)[0]
    if seg == 'darcy':
        return 'materialsScience.fem'
    return f'materialsScience.{seg}' if seg in ('dft', 'fem') else ''


def engines_url_for(path=''):
    """The ladder: env knob, then topology-resolved provider, else ''."""
    url = engines_url()
    if url:
        return url
    # non-module paths (/capability) ride the dft assignment — the
    # worker is ONE service providing both engine modules
    module = _module_for_path(path) or 'materialsScience.dft'
    try:
        from topology.provider_registry import resolve_provider
        resolved = resolve_provider(module)
        if resolved.get('ok'):
            return resolved['url'].rstrip('/')
    except Exception:
        pass  # registry absent/uninitialized -> fall through
    return ''


def unavailable_suggestion(evidence):
    return {
        'evidence': evidence,
        'knob': "MSCI_ENGINES_URL env var, or the topology's engines "
                'provider (ModuleAssignment rows)',
        'action': 'docker compose -p msci-engines -f '
                  'docker-compose.msci-engines.yml up -d --build, then set '
                  'MSCI_ENGINES_URL=http://prf-msci-engines:9500 on the '
                  'backend (both are on polari-link) — or keep the engines '
                  'instance running in the topology (pol topology diff; '
                  'pol allocate materialsScience.fem <instance>).',
    }


def remote_capability(timeout=5):
    """The worker's /capability report, or None when unset/unreachable."""
    url = engines_url_for('/capability')
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
    url = engines_url_for(path)
    if not url:
        return {'ok': False, 'error': 'no engines worker configured',
                'suggestion': unavailable_suggestion(
                    'MSCI_ENGINES_URL is unset on this backend and the '
                    'topology resolves no reachable provider.')}
    request = urllib.request.Request(
        f'{url}{path}', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except Exception as e:
        try:
            # falcon returns JSON bodies on 4xx/5xx — surface those
            body = json.load(e)   # HTTPError is file-like
            if isinstance(body, dict):
                return body
        except Exception:
            pass
        return {'ok': False, 'error': f'engines worker unreachable: {e}',
                'suggestion': unavailable_suggestion(
                    f'{url} did not answer: {e}')}
