"""
@module vpn.custom.vpn_trust

The TRUST BRIDGE (vpn-3, Polari side): a VPN join request is a
PeerAgreement (the mesh-convergence consent record — never
auto-admitted) PLUS a VpnProposal that waits for that consent.

  POST /api/vpn/join-request  ->  PeerAgreement(pending, requested_role
      vpn-member | vpn-federation) + VpnProposal(status awaiting-consent,
      payload.agreement_id = <id>)
  approve (the existing /api/peers/agreements/{id}/approve knob)
      ->  the proposal becomes 'proposed' — it is now in the isle's inbox
          for `isle vpn apply`; the requester's join-status poll carries
          the scope 'vpn:<kind>:<network>@<device>' + the one-shot token
  deny  ->  the proposal is 'rejected' (never reached the isle)
  revoke->  every proposal of that agreement that was APPLIED gets a
            'revoke' proposal (target peer|link) so the isle tears the
            entry down; anything still waiting/proposed is rejected

D9 holds throughout: nothing here configures a VPN — approval only
moves a validated proposal into the inbox; the isle applies, and its
next push is what makes the mirror show the link/peer.

The agreement side is reached through polariPeers.agreements_api's
AGREEMENT_LISTENERS registry (registered by VpnAPI at construction).

@consumers
  - vpn.vpn_api (join-request route + the listener)
  - vpn.vpn_selftest
"""

import json
import uuid

from datetime import datetime, timezone

from vpn.vpn_basis import VpnProposal
from vpn.custom.vpn_constants import AGREEMENT_ROLES, PROPOSAL_STATUSES
from vpn.custom.vpn_proposals import mirror_view, proposal_row, validate_proposal


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', None) or {}
    return list((tables.get(class_name) or {}).values())


def _save(manager, row):
    db = getattr(manager, 'db', None)
    if db is None:
        return
    try:
        db.saveInstanceInDB(row)
    except Exception:  # noqa: BLE001
        pass


def _payload(row):
    try:
        return json.loads(getattr(row, 'payload_json', '{}') or '{}')
    except ValueError:
        return {}


def proposals_of_agreement(manager, agreement_id):
    return [r for r in _rows(manager, 'VpnProposal')
            if _payload(r).get('agreement_id') == agreement_id]


def file_join_request(manager, payload, save=None):
    """Validate the VPN half, then create the agreement + the waiting
    proposal. Returns (result dict, http status). `save` = a row
    persister (the API's), defaults to the manager's db."""
    save = save or (lambda row: _save(manager, row))
    p = dict(payload or {})
    device = str(p.pop('device', '') or '').strip()
    kind = str(p.pop('kind', '') or 'peer').strip()
    requester = str(p.pop('requester_name', '') or '').strip()
    base_url = str(p.pop('requester_base_url', '') or '').strip().rstrip('/')
    fingerprint = str(p.pop('fingerprint', '') or '').strip()
    p.pop('proposed_by', None)
    problems = []
    if kind not in AGREEMENT_ROLES:
        problems.append("kind must be 'peer' (a device asks to join) or "
                        "'link' (a remote isle asks to federate)")
    if not device:
        problems.append('device (the isle being asked) is required')
    if not (requester and base_url and fingerprint):
        problems.append('requester_name, requester_base_url and fingerprint '
                        'are required (the PeerAgreement identity)')
    if problems:
        return ({'ok': False, 'error': '; '.join(problems)}, '400 Bad Request')
    if kind == 'link' and not p.get('agreement_id'):
        # the consent row is being created right now — the validator's
        # "agreement required" rule is satisfied by construction
        p['agreement_id'] = 'pending'
    view = mirror_view(manager, device)
    vproblems, normalized = validate_proposal(kind, p, view)
    if vproblems:
        return ({'ok': False, 'error': 'Refused: ' + '; '.join(vproblems)},
                '400 Bad Request')
    # the consent record (the mesh-convergence ruling: never auto-admit)
    from polariPeers.peer_agreement import PeerAgreement
    existing = next(
        (a for a in _rows(manager, 'PeerAgreement')
         if getattr(a, 'direction', '') == 'inbound'
         and getattr(a, 'requester_name', '') == requester
         and getattr(a, 'requester_fingerprint', '') == fingerprint
         and getattr(a, 'status', '') == 'pending'
         and getattr(a, 'requested_role', '') == AGREEMENT_ROLES[kind]),
        None)
    if existing is not None:
        waiting = proposals_of_agreement(manager, existing.agreement_id)
        return ({'ok': True, 'agreement_id': existing.agreement_id,
                 'status': existing.status, 'already_pending': True,
                 'proposal': waiting[0].name if waiting else '',
                 'message': 'A join request from %s is already pending '
                            '(agreement %s).' % (requester,
                                                 existing.agreement_id)},
                '200 OK')
    agreement = PeerAgreement(
        agreement_id=uuid.uuid4().hex, direction='inbound',
        requester_name=requester, requester_base_url=base_url,
        requester_fingerprint=fingerprint,
        requested_role=AGREEMENT_ROLES[kind], status='pending',
        scope='vpn:%s:%s@%s' % (kind, normalized.get('network_name', ''),
                                 device),
        requested_at=_now_iso(), manager=manager)
    save(agreement)
    normalized['agreement_id'] = agreement.agreement_id
    normalized['requester_name'] = requester
    row_fields = proposal_row(
        device, kind, normalized,
        proposed_by='join-request:%s' % requester,
        note='awaiting consent — PeerAgreement %s (%s)'
             % (agreement.agreement_id, AGREEMENT_ROLES[kind]),
        is_mock=str(p.get('mock_network', '')).lower()
        in ('1', 'true', 'yes'))
    row_fields['status'] = 'awaiting-consent'
    row = VpnProposal(manager=manager, **row_fields)
    save(row)
    print('[vpn] SUGGESTION: "%s" asks to join %s@%s as %s — agreement %s '
          'pending. Knob: POST /api/peers/agreements/%s/approve (or /deny).'
          % (requester, normalized.get('network_name', ''), device,
             AGREEMENT_ROLES[kind], agreement.agreement_id,
             agreement.agreement_id), flush=True)
    return ({'ok': True, 'agreement_id': agreement.agreement_id,
             'status': 'pending', 'proposal': row.name,
             'proposal_status': row.status,
             'message': 'Join request filed: agreement %s is pending; the '
                        'proposal %s waits for consent. An operator approves '
                        'or denies on /api/peers/agreements/%s; approval '
                        'moves the proposal into %s\'s inbox for `isle vpn '
                        'apply`.' % (agreement.agreement_id, row.name,
                                     agreement.agreement_id, device)},
            '201 Created')


def on_agreement_event(manager, agreement, event, save=None):
    """The listener: react to approve / deny / revoke for agreements the
    bridge owns (requested_role vpn-*). Returns what changed."""
    save = save or (lambda row: _save(manager, row))
    role = getattr(agreement, 'requested_role', '')
    if role not in AGREEMENT_ROLES.values():
        return {'handled': False}
    aid = getattr(agreement, 'agreement_id', '')
    who = getattr(agreement, 'approved_by', '') or 'operator'
    changed, filed = [], []
    for row in proposals_of_agreement(manager, aid):
        status = getattr(row, 'status', '')
        if event == 'approved' and status == 'awaiting-consent':
            row.status = 'proposed'
            row.note = 'consent: agreement %s approved by %s at %s' % (
                aid, who, getattr(agreement, 'approved_at', ''))
            row.proposed_at = _now_iso()
            save(row)
            changed.append(row.name)
        elif event == 'denied' and status in ('awaiting-consent', 'proposed'):
            row.status = 'rejected'
            row.note = 'consent: agreement %s DENIED' % aid
            save(row)
            changed.append(row.name)
        elif event == 'revoked':
            if getattr(row, 'kind', '') == 'revoke':
                # a tear-down already filed for this agreement stays
                # in the inbox (it is what the revoke asks for)
                continue
            if status in ('awaiting-consent', 'proposed'):
                row.status = 'rejected'
                row.note = 'consent: agreement %s REVOKED before apply' % aid
                save(row)
                changed.append(row.name)
            elif status == 'applied' and getattr(row, 'kind', '') in (
                    'peer', 'link'):
                payload = _payload(row)
                kind = getattr(row, 'kind', '')
                target_name = (payload.get('peer_name') if kind == 'peer'
                               else '%s@%s->%s' % (
                                   payload.get('network_name', ''),
                                   getattr(row, 'device_name', ''),
                                   payload.get('remote_device', '')))
                already = [r for r in proposals_of_agreement(manager, aid)
                           if getattr(r, 'kind', '') == 'revoke'
                           and _payload(r).get('name') == target_name
                           and getattr(r, 'status', '') in ('proposed',
                                                            'applied')]
                if already:
                    continue  # idempotent: one tear-down per target
                normalized = {'target': kind, 'name': target_name,
                              'network_name': payload.get('network_name',
                                                          ''),
                              'reason': 'agreement %s revoked at %s' % (
                                  aid, getattr(agreement, 'revoked_at',
                                               '')),
                              'agreement_id': aid}
                fields = proposal_row(
                    getattr(row, 'device_name', ''), 'revoke', normalized,
                    proposed_by='consent-revoke:%s' % aid,
                    note='tear down %s %s — PeerAgreement %s revoked'
                         % (kind, target_name, aid),
                    is_mock=bool(getattr(row, 'is_mock', False)))
                new_row = VpnProposal(manager=manager, **fields)
                save(new_row)
                filed.append(new_row.name)
    assert all(getattr(r, 'status', '') in PROPOSAL_STATUSES
               for r in proposals_of_agreement(manager, aid))
    if changed or filed:
        print('[vpn] agreement %s %s: proposals %s -> %s; revoke proposals '
              'filed %s' % (aid, event, changed,
                            {'approved': 'proposed', 'denied': 'rejected',
                             'revoked': 'rejected'}[event], filed),
              flush=True)
    return {'handled': True, 'event': event, 'changed': changed,
            'revoke_proposals': filed}
