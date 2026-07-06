"""
@cross-cutting
@module materialsScience.engines.remote
@tags @xc:bindings

Delegation to the msci-engines worker (docker-compose.msci-engines.yml)
— the Debian container holding the compiled-extension science stack
(pyscf, pymatgen, sfepy) the Alpine backend image cannot pip.

One knob: MSCI_ENGINES_URL (e.g. http://prf-msci-engines:9500). Unset
means no remote — callers get an honest refusal carrying the exact knob.
Never raises: unreachable workers degrade to {'ok': False, suggestion}.
"""

import json
import os
import urllib.request


def engines_url():
    return os.environ.get('MSCI_ENGINES_URL', '').rstrip('/')


def unavailable_suggestion(evidence):
    return {
        'evidence': evidence,
        'knob': 'MSCI_ENGINES_URL env var + the msci-engines worker',
        'action': 'docker compose -p msci-engines -f '
                  'docker-compose.msci-engines.yml up -d --build, then set '
                  'MSCI_ENGINES_URL=http://prf-msci-engines:9500 on the '
                  'backend (both are on polari-link).',
    }


def remote_capability(timeout=5):
    """The worker's /capability report, or None when unset/unreachable."""
    url = engines_url()
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
    url = engines_url()
    if not url:
        return {'ok': False, 'error': 'no engines worker configured',
                'suggestion': unavailable_suggestion(
                    'MSCI_ENGINES_URL is unset on this backend.')}
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
