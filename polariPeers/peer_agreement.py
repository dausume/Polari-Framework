"""
@cross-cutting
@module polariPeers.peer_agreement
@tags @xc:bindings

PeerAgreement — the durable, bilateral consent record for node admission
(Mesh Convergence ruling, Dustin 2026-07-03): a child is NEVER
auto-admitted; its join request becomes a pending agreement the parent
explicitly approves or denies. Approval mints a PER-CHILD, scoped,
REVOCABLE token — the parent stores only its hash; the raw token is
delivered to the requester exactly once over the join channel. Revoking
the agreement invalidates the token (no shared secret to rotate).

Both sides keep a row: the parent's is direction='inbound' (who asked,
who approved, when, scope, token hash); the child's is
direction='outbound' (which parent it joined + the raw token it must
present). Later, Keycloak federation replaces the token mechanics; the
agreement object remains the consent record.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - polariPeers.agreements_api (the admission endpoints)
  - polariPeers.join_flow (child-side flow)
@see /MESH_CONVERGENCE_PLAN.md (suite root) §5.2, §7
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PeerAgreement(treeObject):
    """One admission agreement. Identified by `agreement_id`."""

    @treeObjectInit
    def __init__(
        self,
        # Opaque unique id (uuid4 hex), minted when the request arrives.
        agreement_id: str = '',
        # 'inbound'  — this instance is the approver (parent side);
        # 'outbound' — this instance requested to join (child side).
        direction: str = 'inbound',
        # Requester identity as sent in the join request.
        requester_name: str = '',
        requester_base_url: str = '',
        # Instance fingerprint (persisted random id) — the requester must
        # present the same fingerprint when polling for the token.
        requester_fingerprint: str = '',
        requested_role: str = 'child',
        # Approver identity (filled on the outbound row from the parent's
        # ping identity; on the inbound row it is this instance).
        approver_name: str = '',
        approver_base_url: str = '',
        # 'pending' | 'approved' | 'denied' | 'revoked'
        status: str = 'pending',
        # What the token is good for — coarse capability scope string.
        scope: str = 'peer-basic',
        requested_at: str = '',
        # Who flipped the knob, and when (ISO timestamps).
        approved_by: str = '',
        approved_at: str = '',
        revoked_at: str = '',
        # PARENT side: sha256 of the minted token (never the raw token).
        token_hash: str = '',
        # PARENT side: raw token held ONLY until the requester's first
        # successful status poll delivers it, then cleared ('').
        token_pending_delivery: str = '',
        # CHILD side: the raw per-child token this instance presents to
        # the parent ('' on the parent's row).
        token: str = '',
        manager=None,
    ):
        self.agreement_id = agreement_id
        self.direction = direction
        self.requester_name = requester_name
        self.requester_base_url = requester_base_url
        self.requester_fingerprint = requester_fingerprint
        self.requested_role = requested_role
        self.approver_name = approver_name
        self.approver_base_url = approver_base_url
        self.status = status
        self.scope = scope
        self.requested_at = requested_at
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.revoked_at = revoked_at
        self.token_hash = token_hash
        self.token_pending_delivery = token_pending_delivery
        self.token = token
