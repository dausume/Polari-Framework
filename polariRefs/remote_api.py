"""
@module polariRefs.remote_api

xsim-6: rung 4 of the resolution ladder — the remote-API hop for
instances that do NOT share the object DB. Reads go to the owner's
/api/refs/resolve; writes go to the owner's /api/refs/apply-write
with the fencing token in headers; the OWNER validates the epoch
against core before applying (validate_epoch_for_owner below — local
lease table when this instance IS core / shares core's DB, HTTP to
POLARI_CORE_URL otherwise).

Peer addressing: PeerNode rows (name ↔ instance, base_url) are the
address book; the topology layer's provider URL is the future
refinement. Short timeouts, structured errors — a dead peer degrades
to an honest refusal naming the connection knob, never a hang or a
silent None (peers_api idiom).
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

REMOTE_HTTP_TIMEOUT_S = 6


def _http_json(method: str, url: str, body: Optional[Dict] = None,
               headers: Optional[Dict] = None) -> Dict[str, Any]:
    """Injectable transport (selftests monkeypatch this)."""
    data = json.dumps(body).encode('utf-8') if body is not None else None
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={'Content-Type': 'application/json',
                 'Accept': 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(
                request, timeout=REMOTE_HTTP_TIMEOUT_S) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode('utf-8'))
        except Exception:
            return {'_error': f'HTTP {e.code} from {url}'}
    except Exception as e:
        return {'_error': f'{type(e).__name__}: {e}'}


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {}) or {}
    return list(table.values()) if isinstance(table, dict) else list(table)


def peer_base_url(manager, target_instance: str) -> str:
    """The address book: a PeerNode whose name matches the instance
    ('b' or 'polari-b' forms)."""
    target = target_instance.strip().lower()
    for node in _rows(manager, 'PeerNode'):
        name = (getattr(node, 'name', '') or '').strip().lower()
        if name in (target, f'polari-{target}') \
                or name.replace('polari-', '') == target:
            return (getattr(node, 'base_url', '') or '').rstrip('/')
    return ''


def fetch_remote_api(manager, ref, target_instance: str) -> Dict:
    """Rung-4 read: ask the OWNER to resolve the ref locally (bare)
    and hand back its field dict."""
    base = peer_base_url(manager, target_instance)
    if not base:
        return {'ok': False, 'refusal': {
            'error': f"no PeerNode names instance '{target_instance}' "
                     '— rung 4 has no address',
            'rung': 'remote-api',
            'suggestion': {'knob': 'PeerNode (peer join flow)',
                           'action': f"enroll '{target_instance}' with "
                                     'its base_url'}}}
    bare = {'kind': 'objectRef', 'className': ref['className'],
            'name': ref['name'], 'id': ref['id']}
    reply = _http_json('POST', f'{base}/api/refs/resolve',
                       {'ref': bare})
    if reply.get('_error'):
        return {'ok': False, 'refusal': {
            'error': f"instance '{target_instance}' unreachable at "
                     f"{base}: {reply['_error']}",
            'rung': 'remote-api',
            'suggestion': {'knob': 'PeerNode.base_url / the peer',
                           'action': 'bring the owner back up or fix '
                                     'the address'}}}
    if not reply.get('ok'):
        return {'ok': False, 'refusal': {
            'error': f"owner '{target_instance}' refused the resolve: "
                     f"{(reply.get('refusal') or {}).get('error')}",
            'rung': 'remote-api',
            'ownerRefusal': reply.get('refusal')}}
    fields = reply.get('fields')
    if not isinstance(fields, dict):
        # the owner resolved a live tree object; its identifying
        # surface is still a read — hand back what it exposed
        fields = {'note': reply.get('note', '')}
    return {'ok': True, 'fields': fields,
            'provenance': {'rung': 'remote-api',
                           'owningInstance': target_instance,
                           'baseUrl': base,
                           'ownerProvenance': reply.get('provenance'),
                           'readOnly': 'writes go through '
                                       'apply-write under the lease'}}


def push_remote_write(manager, ref, fields: Dict, run_id: str,
                      token: int, target_instance: str) -> Dict:
    """Rung-4 write: POST the owner's apply-write with the fencing
    token in headers; the owner validates the epoch against core."""
    base = peer_base_url(manager, target_instance)
    if not base:
        return {'ok': False,
                'error': f"no PeerNode names instance "
                         f"'{target_instance}' — rung 4 has no address"}
    bare = {'kind': 'objectRef', 'className': ref['className'],
            'name': ref['name'], 'id': ref['id']}
    reply = _http_json('POST', f'{base}/api/refs/apply-write',
                       {'ref': bare, 'fields': fields},
                       headers={'X-Polari-Run-Id': run_id,
                                'X-Polari-Lease-Token': str(token)})
    if reply.get('_error'):
        return {'ok': False,
                'error': f"instance '{target_instance}' unreachable "
                         f"at {base}: {reply['_error']}"}
    return reply


def validate_epoch_for_owner(manager, token: int) -> Dict:
    """Owner-side epoch check: this instance validates a presented
    token against CORE — its own lease table when it is core (or
    shares core's DB), HTTP to POLARI_CORE_URL otherwise."""
    core_url = (os.environ.get('POLARI_CORE_URL') or '').rstrip('/')
    if not core_url:
        from simulationLocks.lease import validate_token
        return validate_token(manager, token)
    reply = _http_json('GET',
                       f'{core_url}/api/simulation-locks/lease')
    if reply.get('_error'):
        return {'ok': False,
                'error': f'core unreachable for epoch validation '
                         f"({core_url}): {reply['_error']} — refusing "
                         'the write rather than guessing'}
    if reply.get('status') != 'held':
        return {'ok': False,
                'error': f"core lease is {reply.get('status')} — no "
                         f'run may mutate (presented epoch {token})'}
    if int(reply.get('tokenEpoch') or 0) != int(token):
        return {'ok': False,
                'error': f'stale fencing token: presented epoch '
                         f"{token}, core epoch {reply.get('tokenEpoch')}"
                         f" (held by run '{reply.get('holderRun')}') — "
                         'zombie write refused'}
    return {'ok': True, 'holderRun': reply.get('holderRun', '')}
