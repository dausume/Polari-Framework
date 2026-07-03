"""
@cross-cutting
@module polariPeers.join_flow
@tags @xc:bindings

Child-side admission flow (the other half of agreements_api): send a
join request to a would-be parent, poll for the decision, store the
delivered per-child token in this instance's OUTBOUND PeerAgreement row,
and register back with the parent using that token (bilateral consent —
the child's row records exactly which parent it joined).

The instance fingerprint lives at /app/data/instance_fingerprint
(random, persisted, created on first use) — it authenticates the status
poll so only the requester that asked can receive the token.

@consumers
  - polariPeers.role_autoconfig (child path drives this)
  - polariPeers.agreements_api (server half)
@see /MESH_CONVERGENCE_PLAN.md §5.2, §7
"""

import json
import os
import secrets
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from polariPeers.peers_api import (
    PEER_HTTP_TIMEOUT_S, _http_get_json, instance_identity)

_EPHEMERAL_FP = ''  # stable within the process when the file is unwritable


def instance_fingerprint() -> str:
    """This instance's persisted random fingerprint (created on first
    use). Falls back to a process-stable ephemeral one if the data dir
    is unwritable."""
    global _EPHEMERAL_FP
    path = os.environ.get('POLARI_FINGERPRINT_FILE',
                          '/app/data/instance_fingerprint')
    try:
        with open(path) as f:
            existing = f.read().strip()
        if existing:
            return existing
    except OSError:
        pass
    fresh = _EPHEMERAL_FP or secrets.token_hex(16)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(fresh)
    except OSError:
        _EPHEMERAL_FP = fresh
    return fresh


def _http_post_json(url: str, body: Dict[str, Any]) -> Dict[str, Any]:
    try:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode('utf-8'),
            headers={'Content-Type': 'application/json',
                     'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=PEER_HTTP_TIMEOUT_S) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as exc:
        return {'_error': f'{type(exc).__name__}: {exc}'}


def send_join_request(parent_base_url: str, my_base_url: str,
                      requested_role: str = 'child') -> Dict[str, Any]:
    """POST the join request. Returns {'agreementId', 'status'} or
    {'_error': ...}."""
    ident = instance_identity()
    payload = {
        'name': ident['instanceName'],
        'baseUrl': my_base_url,
        'fingerprint': instance_fingerprint(),
        'requestedRole': requested_role,
    }
    result = _http_post_json(
        f'{parent_base_url.rstrip("/")}/api/peers/join-request', payload)
    if '_error' in result:
        return result
    return result.get('data') or {'_error': 'empty response'}


def poll_join_status(parent_base_url: str, agreement_id: str) -> Dict[str, Any]:
    """One status poll. On approval the parent delivers the raw token
    exactly once — the caller must store it immediately."""
    url = (f'{parent_base_url.rstrip("/")}/api/peers/join-request/'
           f'{agreement_id}?fingerprint={instance_fingerprint()}')
    result = _http_get_json(url)
    if '_error' in result:
        return result
    return result.get('data') or {'_error': 'empty response'}


def record_outbound_agreement(manager, agreement_id: str,
                              parent_base_url: str, token: str,
                              scope: str, status: str = 'approved'):
    """Store/refresh this instance's OUTBOUND agreement row (its half of
    the bilateral record): which parent, what scope, the raw token."""
    table = manager.objectTables.get('PeerAgreement', {}) or {}
    row = next((a for a in table.values()
                if getattr(a, 'agreement_id', '') == agreement_id), None)
    parent_ping = _http_get_json(
        f'{parent_base_url.rstrip("/")}/api/peers/ping')
    parent_name = ((parent_ping.get('data') or {}).get('instanceName')
                   if '_error' not in parent_ping else '') or ''
    ident = instance_identity()
    if row is None:
        from polariPeers.peer_agreement import PeerAgreement
        row = PeerAgreement(
            agreement_id=agreement_id, direction='outbound',
            requester_name=ident['instanceName'],
            requester_fingerprint=instance_fingerprint(),
            manager=manager)
    row.status = status
    row.scope = scope
    row.token = token
    row.approver_name = parent_name
    row.approver_base_url = parent_base_url.rstrip('/')
    row.approved_at = datetime.now(timezone.utc).isoformat()
    db = getattr(manager, 'db', None)
    if db is not None:
        try:
            db.saveInstanceInDB(row)
        except Exception:
            pass
    # The child's half of the pairing: the parent becomes a known peer.
    if parent_name:
        peers = manager.objectTables.get('PeerNode', {}) or {}
        peer = next((p for p in peers.values()
                     if getattr(p, 'name', '') == parent_name), None)
        if peer is None:
            from polariPeers.peer_node import PeerNode
            peer = PeerNode(name=parent_name,
                            base_url=parent_base_url.rstrip('/'),
                            status='unknown', manager=manager)
        else:
            peer.base_url = parent_base_url.rstrip('/')
        if db is not None:
            try:
                db.saveInstanceInDB(peer)
            except Exception:
                pass
    return row


def register_with_parent(parent_base_url: str, my_base_url: str,
                         token: str) -> Dict[str, Any]:
    """Register this instance on the parent using the per-child token
    (the same /api/peers/register the twin used, minus the shared
    secret)."""
    ident = instance_identity()
    return _http_post_json(
        f'{parent_base_url.rstrip("/")}/api/peers/register',
        {'name': ident['instanceName'], 'baseUrl': my_base_url,
         'token': token})


def join_parent(manager, parent_base_url: str, my_base_url: str,
                max_polls: int = 1) -> Dict[str, Any]:
    """The whole child-side flow: request → poll (bounded) → store token
    + outbound agreement → register. Returns a report dict; 'joined' is
    True only after a successful register. Idempotent: an already-stored
    approved outbound agreement for this parent short-circuits to
    register."""
    report: Dict[str, Any] = {'parent': parent_base_url, 'joined': False,
                              'evidence': []}
    existing = next(
        (a for a in (manager.objectTables.get('PeerAgreement', {}) or {})
         .values()
         if getattr(a, 'direction', '') == 'outbound'
         and getattr(a, 'approver_base_url', '') == parent_base_url.rstrip('/')
         and getattr(a, 'status', '') == 'approved'
         and getattr(a, 'token', '')),
        None)
    if existing is not None:
        report['evidence'].append(
            f'outbound agreement {existing.agreement_id} already approved — '
            f'reusing its token')
        result = register_with_parent(parent_base_url, my_base_url,
                                      existing.token)
        if '_error' not in result and bool(result.get('success')):
            report['joined'] = True
            report['register'] = result
            return report
        # The parent refused the stored token — it was revoked (or the
        # parent reset). Mark our half revoked and ask afresh.
        existing.status = 'revoked'
        existing.token = ''
        db = getattr(manager, 'db', None)
        if db is not None:
            try:
                db.saveInstanceInDB(existing)
            except Exception:
                pass
        report['evidence'].append(
            'stored token refused by the parent — marking the outbound '
            'agreement revoked and sending a fresh join request')
    asked = send_join_request(parent_base_url, my_base_url)
    if '_error' in asked:
        report['evidence'].append(f'join request failed: {asked["_error"]}')
        return report
    agreement_id = asked.get('agreementId', '')
    report['agreementId'] = agreement_id
    report['evidence'].append(
        f'join request accepted as agreement {agreement_id} '
        f'(status {asked.get("status")})')
    for _ in range(max(1, max_polls)):
        polled = poll_join_status(parent_base_url, agreement_id)
        if '_error' in polled:
            report['evidence'].append(f'poll failed: {polled["_error"]}')
            return report
        status = polled.get('status', '')
        if status == 'approved' and polled.get('token'):
            record_outbound_agreement(
                manager, agreement_id, parent_base_url,
                polled['token'], polled.get('scope', ''))
            report['evidence'].append('approved — token received + stored')
            result = register_with_parent(parent_base_url, my_base_url,
                                          polled['token'])
            report['joined'] = ('_error' not in result
                                and bool(result.get('success')))
            report['register'] = result
            return report
        if status in ('denied', 'revoked'):
            report['evidence'].append(f'agreement {status} by the parent')
            return report
    report['status'] = 'pending'
    report['evidence'].append(
        'still pending — the parent has not approved yet (re-run to poll '
        'again; the request is durable)')
    return report
