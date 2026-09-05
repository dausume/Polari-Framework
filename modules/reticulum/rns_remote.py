"""
@cross-cutting
@module reticulum.rns_remote
@tags @xc:bindings

Resolution ladder for the pol-reticulum sidecar (ret-2). The FIFTH
walk of the *_remote ladder (cad_remote → recon_remote →
livekit_remote → here). The sidecar is its own container (plan §5k,
DECIDED row 16): it holds the RNS stack and the radio; THIS image
never imports RNS — that boundary is also the licence boundary
(RETICULUM_LICENCE_GATE.md: the stack is pinned to the last MIT
releases and lives only in the sidecar).

Knobs, each with its own honest refusal:

  RETICULUM_URL   server-side base (http://host:4285) of the sidecar's
                  status/control API; unset → topology resolves the
                  'reticulum.mesh' module's provider.

Never raises. Refusals carry evidence + knob + action.
"""

import json
import os
import urllib.request

_MODULE = 'reticulum.mesh'

#: The licence pins ARE facts about this deployment — surfaced by the
#: capability endpoint so nobody has to remember why the version is
#: old. Bump ONLY through a re-run of the licence gate.
STACK_PINS = {'rns': '0.9.4', 'lxmf': '0.6.3',
              'gate': 'RETICULUM_LICENCE_GATE.md'}


def server_url():
    url = os.environ.get('RETICULUM_URL', '').rstrip('/')
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
        'knob': "RETICULUM_URL (sidecar status API base) or the "
                "topology's reticulum provider (module "
                "'reticulum.mesh')",
        'action': 'pol compose reticulum up on the mesh host, then '
                  'set RETICULUM_URL=http://<host>:4285 on this '
                  'backend (or seed the topology provider).',
    }


def reachable(timeout=3):
    """Whether the resolved sidecar answers its /status probe. None
    when no URL resolves — absence of a knob is not a failure."""
    url = server_url()
    if not url:
        return None
    try:
        with urllib.request.urlopen(url + '/status',
                                    timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def sidecar_status(timeout=5):
    """The sidecar's own view (interfaces up, identity hash, peers
    heard) or an honest refusal. Facts come FROM the sidecar; rows
    hold what was declared — the split is fidelity."""
    url = server_url()
    if not url:
        return {'ok': False, 'error': 'no reticulum sidecar configured',
                'suggestion': unavailable_suggestion(
                    'RETICULUM_URL is unset and the topology resolves '
                    "no provider for 'reticulum.mesh'.")}
    try:
        with urllib.request.urlopen(url + '/status',
                                    timeout=timeout) as resp:
            body = json.load(resp)
            return {'ok': True, 'status': body if isinstance(body, dict)
                    else {}}
    except Exception as e:
        return {'ok': False,
                'error': f'reticulum sidecar did not answer /status: {e}',
                'suggestion': unavailable_suggestion(
                    f'{url} rejected or did not answer /status.')}
