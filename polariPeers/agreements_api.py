"""
@cross-cutting
@module polariPeers.agreements_api
@tags @xc:bindings

Admission endpoints — the PeerAgreement flow (replaces the twin's shared
token; ruling in /MESH_CONVERGENCE_PLAN.md §5.2):

  POST /api/peers/join-request                — child asks to join
  GET  /api/peers/join-request/{agreement_id} — child polls; on approval
        the raw token is returned EXACTLY ONCE (fingerprint-gated), then
        cleared from the parent
  GET  /api/peers/agreements                  — list (the manager surface
        reads this: "device X asks to join as child")
  POST /api/peers/agreements/{agreement_id}/approve — mint per-child
        scoped token (hash stored), upsert the child's PeerNode
  POST /api/peers/agreements/{agreement_id}/deny
  POST /api/peers/agreements/{agreement_id}/revoke  — token invalid from
        here on; the child's PeerNode row is removed

Knobs-and-suggestions posture: a join request only ever SUGGESTS —
admission happens at the explicit approve knob. One convenience knob,
default OFF: POLARI_AUTO_APPROVE_SAME_ISLE=true auto-approves requesters
that mesh facts place on this instance's own isle (evidence-logged).

Token validation for /api/peers/register lives here too
(find_agreement_for_token) so peers_api stays thin.

@consumers
  - polariServer (route registration)
  - polariPeers.peers_api (register validates per-child tokens here)
  - polariPeers.join_flow (child side calls these endpoints)
@see /MESH_CONVERGENCE_PLAN.md §5.2, §7
"""

import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def token_hash(raw: str) -> str:
    return hashlib.sha256((raw or '').encode('utf-8')).hexdigest()


def agreement_rows(manager) -> List:
    return list((manager.objectTables.get('PeerAgreement', {}) or {}).values())


def find_agreement(manager, agreement_id: str):
    for a in agreement_rows(manager):
        if getattr(a, 'agreement_id', '') == agreement_id:
            return a
    return None


def find_agreement_for_token(manager, peer_name: str, raw_token: str):
    """The per-child register gate: an APPROVED inbound agreement whose
    token hash matches. Denied/revoked/pending agreements never match."""
    if not raw_token:
        return None
    h = token_hash(raw_token)
    for a in agreement_rows(manager):
        if (getattr(a, 'direction', '') == 'inbound'
                and getattr(a, 'status', '') == 'approved'
                and getattr(a, 'requester_name', '') == peer_name
                and getattr(a, 'token_hash', '')
                and getattr(a, 'token_hash', '') == h):
            return a
    return None


class AgreementsAPI(treeObject):
    """PeerAgreement admission endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/peers/agreements'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/peers/join-request', self, suffix='join_request')
            polServer.falconServer.add_route(
                '/api/peers/join-request/{agreement_id}', self,
                suffix='join_status')
            polServer.falconServer.add_route(
                '/api/peers/agreements', self, suffix='agreements')
            polServer.falconServer.add_route(
                '/api/peers/agreements/{agreement_id}/approve', self,
                suffix='approve')
            polServer.falconServer.add_route(
                '/api/peers/agreements/{agreement_id}/deny', self,
                suffix='deny')
            polServer.falconServer.add_route(
                '/api/peers/agreements/{agreement_id}/revoke', self,
                suffix='revoke')

    # ------------------------------------------------------------------
    # POST /api/peers/join-request — {name, baseUrl, fingerprint,
    # requestedRole} → a pending agreement (idempotent per
    # name+fingerprint while pending).
    # ------------------------------------------------------------------
    def on_post_join_request(self, request, response):
        try:
            body = request.media or {}
        except Exception:
            body = {}
        name = (body.get('name') or '').strip()
        base_url = (body.get('baseUrl') or '').strip().rstrip('/')
        fingerprint = (body.get('fingerprint') or '').strip()
        role = (body.get('requestedRole') or 'child').strip()
        if not name or not base_url or not fingerprint:
            response.status = falcon.HTTP_400
            response.media = {
                'success': False,
                'error': "'name', 'baseUrl' and 'fingerprint' are required."}
            return
        # Re-asking while a request is already pending returns the SAME
        # agreement (safe to retry); a denied/revoked requester may ask
        # again — that creates a fresh pending row for a fresh decision.
        existing = next(
            (a for a in agreement_rows(self.manager)
             if getattr(a, 'direction', '') == 'inbound'
             and getattr(a, 'requester_name', '') == name
             and getattr(a, 'requester_fingerprint', '') == fingerprint
             and getattr(a, 'status', '') in ('pending', 'approved')),
            None)
        if existing is not None:
            response.media = {'success': True, 'data': {
                'agreementId': existing.agreement_id,
                'status': existing.status}}
            response.status = falcon.HTTP_200
            return
        from polariPeers.peer_agreement import PeerAgreement
        agreement = PeerAgreement(
            agreement_id=uuid.uuid4().hex, direction='inbound',
            requester_name=name, requester_base_url=base_url,
            requester_fingerprint=fingerprint, requested_role=role,
            status='pending', requested_at=_now(), manager=self.manager)
        self._persist(agreement)
        print(f'[PeerAgreement] SUGGESTION: "{name}" ({base_url}) asks to '
              f'join as {role} — agreement {agreement.agreement_id} pending. '
              f'Knob: POST /api/peers/agreements/{agreement.agreement_id}'
              f'/approve (or /deny).', flush=True)
        auto = self._maybe_auto_approve(agreement)
        response.media = {'success': True, 'data': {
            'agreementId': agreement.agreement_id,
            'status': agreement.status,
            'autoApproved': auto}}
        response.status = falcon.HTTP_201

    def _maybe_auto_approve(self, agreement) -> bool:
        """Convenience knob, DEFAULT OFF: auto-approve requesters already
        on this instance's own isle (mesh-facts evidence required)."""
        if (os.environ.get('POLARI_AUTO_APPROVE_SAME_ISLE') or '').lower() \
                not in ('1', 'true', 'yes'):
            return False
        try:
            from polariPeers.mesh_facts import get_mesh_facts
            facts = get_mesh_facts()
        except Exception:
            return False
        if not facts.get('meshed'):
            return False
        req_host = agreement.requester_base_url.split('//')[-1] \
            .split(':')[0].split('/')[0]
        devices = {str(d).lower() for d in (facts.get('devices') or [])}
        if req_host.lower() not in devices:
            return False
        print(f'[PeerAgreement] auto-approving {agreement.agreement_id}: '
              f'POLARI_AUTO_APPROVE_SAME_ISLE=true and mesh facts list '
              f'"{req_host}" on isle "{facts.get("isleName", "?")}".',
              flush=True)
        self._approve(agreement, approved_by='auto:same-isle-knob')
        return True

    # ------------------------------------------------------------------
    # GET /api/peers/join-request/{id}?fingerprint=... — requester polls.
    # The raw token rides back exactly once.
    # ------------------------------------------------------------------
    def on_get_join_status(self, request, response, agreement_id):
        agreement = find_agreement(self.manager, agreement_id)
        if agreement is None or getattr(agreement, 'direction', '') != 'inbound':
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'No agreement "{agreement_id}" here.'}
            return
        fingerprint = (request.params.get('fingerprint') or '').strip()
        if fingerprint != getattr(agreement, 'requester_fingerprint', ''):
            response.status = falcon.HTTP_403
            response.media = {'success': False,
                              'error': 'Fingerprint mismatch.'}
            return
        data: Dict[str, Any] = {'agreementId': agreement_id,
                                'status': agreement.status,
                                'scope': getattr(agreement, 'scope', '')}
        if agreement.status == 'approved' and agreement.token_pending_delivery:
            data['token'] = agreement.token_pending_delivery
            agreement.token_pending_delivery = ''  # one-shot delivery
            self._persist(agreement)
        response.media = {'success': True, 'data': data}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/peers/agreements — the review surface.
    # ------------------------------------------------------------------
    def on_get_agreements(self, request, response):
        out = [{
            'agreementId': getattr(a, 'agreement_id', ''),
            'direction': getattr(a, 'direction', ''),
            'requesterName': getattr(a, 'requester_name', ''),
            'requesterBaseUrl': getattr(a, 'requester_base_url', ''),
            'requestedRole': getattr(a, 'requested_role', ''),
            'approverName': getattr(a, 'approver_name', ''),
            'status': getattr(a, 'status', ''),
            'scope': getattr(a, 'scope', ''),
            'requestedAt': getattr(a, 'requested_at', ''),
            'approvedBy': getattr(a, 'approved_by', ''),
            'approvedAt': getattr(a, 'approved_at', ''),
            'revokedAt': getattr(a, 'revoked_at', ''),
        } for a in agreement_rows(self.manager)]
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # The approve / deny / revoke knobs.
    # ------------------------------------------------------------------
    def on_post_approve(self, request, response, agreement_id):
        agreement = find_agreement(self.manager, agreement_id)
        if agreement is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'No agreement "{agreement_id}".'}
            return
        if agreement.status not in ('pending',):
            response.status = falcon.HTTP_409
            response.media = {
                'success': False,
                'error': f'Agreement is {agreement.status}, not pending. '
                         f'A revoked/denied requester must send a fresh '
                         f'join request.'}
            return
        try:
            body = request.media or {}
        except Exception:
            body = {}
        self._approve(agreement,
                      approved_by=(body.get('approvedBy') or 'operator'),
                      scope=(body.get('scope') or '').strip() or None)
        response.media = {'success': True, 'data': {
            'agreementId': agreement_id, 'status': agreement.status,
            'scope': agreement.scope,
            'note': ('Token minted; the requester receives it on its next '
                     'status poll. This instance stores only the hash.')}}
        response.status = falcon.HTTP_200

    def _approve(self, agreement, approved_by: str, scope: Optional[str] = None):
        raw = secrets.token_urlsafe(32)
        agreement.token_hash = token_hash(raw)
        agreement.token_pending_delivery = raw
        agreement.status = 'approved'
        agreement.approved_by = approved_by
        agreement.approved_at = _now()
        if scope:
            agreement.scope = scope
        from polariPeers.peers_api import instance_identity
        agreement.approver_name = instance_identity()['instanceName']
        self._persist(agreement)
        self._upsert_peer(agreement.requester_name,
                          agreement.requester_base_url)
        print(f'[PeerAgreement] approved {agreement.agreement_id} '
              f'("{agreement.requester_name}" as {agreement.requested_role}, '
              f'scope {agreement.scope}) by {approved_by}.', flush=True)

    def on_post_deny(self, request, response, agreement_id):
        agreement = find_agreement(self.manager, agreement_id)
        if agreement is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'No agreement "{agreement_id}".'}
            return
        agreement.status = 'denied'
        agreement.token_hash = ''
        agreement.token_pending_delivery = ''
        self._persist(agreement)
        response.media = {'success': True, 'data': {
            'agreementId': agreement_id, 'status': 'denied'}}
        response.status = falcon.HTTP_200

    def on_post_revoke(self, request, response, agreement_id):
        agreement = find_agreement(self.manager, agreement_id)
        if agreement is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False,
                              'error': f'No agreement "{agreement_id}".'}
            return
        agreement.status = 'revoked'
        agreement.token_hash = ''       # the token is invalid from here on
        agreement.token_pending_delivery = ''
        agreement.revoked_at = _now()
        self._persist(agreement)
        removed = self._remove_peer(agreement.requester_name)
        print(f'[PeerAgreement] revoked {agreement_id} '
              f'("{agreement.requester_name}"); peer row removed: {removed}.',
              flush=True)
        response.media = {'success': True, 'data': {
            'agreementId': agreement_id, 'status': 'revoked',
            'peerRemoved': removed}}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _upsert_peer(self, name: str, base_url: str) -> None:
        peers = self.manager.objectTables.get('PeerNode', {}) or {}
        peer = next((p for p in peers.values()
                     if getattr(p, 'name', '') == name), None)
        if peer is None:
            from polariPeers.peer_node import PeerNode
            peer = PeerNode(name=name, base_url=base_url, status='unknown',
                            manager=self.manager)
        else:
            peer.base_url = base_url
        self._persist(peer)

    def _remove_peer(self, name: str) -> bool:
        table = self.manager.objectTables.get('PeerNode', {}) or {}
        for key, p in list(table.items()):
            if getattr(p, 'name', '') == name:
                del table[key]
                db = getattr(self.manager, 'db', None)
                if db is not None:
                    try:
                        db.deleteRowsWhere('PeerNode', 'name', name)
                    except Exception:
                        pass
                return True
        return False

    def _persist(self, inst) -> None:
        db = getattr(self.manager, 'db', None)
        if db is not None:
            try:
                db.saveInstanceInDB(inst)
            except Exception:
                pass
