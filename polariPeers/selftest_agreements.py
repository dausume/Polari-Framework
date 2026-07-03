"""
Self-test for the PeerAgreement admission flow (mesh convergence Phase 1).

Run from polari-framework/:
    python3 -m polariPeers.selftest_agreements

Pure python — fake manager + fake falcon plumbing, both API halves
in-process; the child-side join_flow talks to the parent's AgreementsAPI
through a mocked HTTP layer, so the WHOLE bilateral flow runs.
"""

import json
import os
from types import SimpleNamespace

import polariPeers.agreements_api as agr_mod
import polariPeers.join_flow as jf_mod
import polariPeers.peers_api as peers_mod
from polariPeers.agreements_api import (
    AgreementsAPI, find_agreement_for_token, token_hash)
from polariPeers.peers_api import PeersAPI

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


class _Resp:
    def __init__(self):
        self.media, self.status = None, '200 OK'


def _req(body=None, params=None):
    return SimpleNamespace(media=body or {}, params=params or {})


def _manager():
    return SimpleNamespace(objectTables={'PeerAgreement': {}, 'PeerNode': {}},
                           db=None)


def _agreements_api(manager):
    api = AgreementsAPI.__new__(AgreementsAPI)  # bypass treeObjectInit
    api.manager = manager
    return api


def _peers_api(manager):
    api = PeersAPI.__new__(PeersAPI)
    api.manager = manager
    return api


def _stub_tree_classes():
    """PeerAgreement/PeerNode as plain namespaces (the real treeObject
    needs the full manager machinery; the flow, not the tree wiring, is
    under test). Instances self-insert into the fake objectTables."""
    import polariPeers.peer_agreement as pa_mod
    import polariPeers.peer_node as pn_mod
    real = (pa_mod.PeerAgreement, pn_mod.PeerNode)

    def fake_agreement(manager=None, **kw):
        defaults = dict(direction='inbound', requester_name='',
                        requester_base_url='', requester_fingerprint='',
                        requested_role='child', approver_name='',
                        approver_base_url='', status='pending',
                        scope='peer-basic', requested_at='', approved_by='',
                        approved_at='', revoked_at='', token_hash='',
                        token_pending_delivery='', token='')
        defaults.update(kw)
        inst = SimpleNamespace(**defaults)
        manager.objectTables['PeerAgreement'][inst.agreement_id] = inst
        return inst

    def fake_peer(manager=None, **kw):
        inst = SimpleNamespace(identity_json='{}', last_seen='', **kw)
        manager.objectTables['PeerNode'][inst.name] = inst
        return inst

    pa_mod.PeerAgreement = fake_agreement
    pn_mod.PeerNode = fake_peer
    return real


def _restore_tree_classes(real):
    import polariPeers.peer_agreement as pa_mod
    import polariPeers.peer_node as pn_mod
    pa_mod.PeerAgreement, pn_mod.PeerNode = real


def main():
    print('PeerAgreement admission flow — bilateral consent\n')
    os.environ.pop('POLARI_AUTO_APPROVE_SAME_ISLE', None)
    os.environ['POLARI_FINGERPRINT_FILE'] = '/tmp/selftest_fp'
    try:
        os.remove('/tmp/selftest_fp')
    except OSError:
        pass

    real = _stub_tree_classes()
    try:
        parent = _manager()
        api = _agreements_api(parent)

        # --- Join request creates a pending agreement -----------------
        resp = _Resp()
        api.on_post_join_request(_req({'name': 'polari-b',
                                       'baseUrl': 'http://b:3000',
                                       'fingerprint': 'fp-b'}), resp)
        d = resp.media['data']
        aid = d['agreementId']
        check('join request -> pending agreement (201)',
              resp.status.startswith('201') and d['status'] == 'pending'
              and aid)
        check('never auto-admitted (knob off)', d['autoApproved'] is False)

        resp = _Resp()
        api.on_post_join_request(_req({'name': 'polari-b',
                                       'baseUrl': 'http://b:3000',
                                       'fingerprint': 'fp-b'}), resp)
        check('re-request while pending is idempotent (same agreement)',
              resp.media['data']['agreementId'] == aid
              and resp.status.startswith('200'))

        resp = _Resp()
        api.on_post_join_request(_req({'name': 'x'}), resp)
        check('missing fields -> 400', resp.status.startswith('400'))

        # --- Poll before approval: pending, no token ------------------
        resp = _Resp()
        api.on_get_join_status(_req(params={'fingerprint': 'fp-b'}),
                               resp, aid)
        check('poll while pending: status only, no token',
              resp.media['data']['status'] == 'pending'
              and 'token' not in resp.media['data'])
        resp = _Resp()
        api.on_get_join_status(_req(params={'fingerprint': 'WRONG'}),
                               resp, aid)
        check('poll with wrong fingerprint -> 403',
              resp.status.startswith('403'))

        # --- Approve knob: mints token, parent keeps only the hash ----
        resp = _Resp()
        api.on_post_approve(_req({'approvedBy': 'dustin'}), resp, aid)
        agreement = parent.objectTables['PeerAgreement'][aid]
        check('approve mints token; status approved; audit trail',
              resp.media['data']['status'] == 'approved'
              and agreement.approved_by == 'dustin'
              and agreement.approved_at and agreement.token_hash)
        check('parent upserted the child PeerNode on approval',
              'polari-b' in parent.objectTables['PeerNode'])

        # --- One-shot token delivery ----------------------------------
        resp = _Resp()
        api.on_get_join_status(_req(params={'fingerprint': 'fp-b'}),
                               resp, aid)
        raw_token = resp.media['data'].get('token', '')
        check('first poll after approval delivers the raw token',
              bool(raw_token)
              and token_hash(raw_token) == agreement.token_hash)
        resp = _Resp()
        api.on_get_join_status(_req(params={'fingerprint': 'fp-b'}),
                               resp, aid)
        check('second poll: token is GONE (one-shot delivery)',
              'token' not in resp.media['data']
              and agreement.token_pending_delivery == '')

        # --- Register gate: per-child token > shared fallback ---------
        papi = _peers_api(parent)
        os.environ['POLARI_SHARED_TOKEN_FALLBACK'] = 'false'
        os.environ.pop('POLARI_PEER_TOKEN', None)
        resp = _Resp()
        papi.on_post_register(_req({'name': 'polari-b',
                                    'baseUrl': 'http://b:3000',
                                    'token': raw_token}), resp)
        check('register with per-child token succeeds (201)',
              resp.status.startswith('201'))
        resp = _Resp()
        papi.on_post_register(_req({'name': 'polari-b',
                                    'baseUrl': 'http://b:3000',
                                    'token': 'forged'}), resp)
        check('register with a bad token -> 403 pointing at join-request',
              resp.status.startswith('403')
              and 'join-request' in resp.media['error'])
        resp = _Resp()
        papi.on_post_register(_req({'name': 'polari-c',
                                    'baseUrl': 'http://c:3000',
                                    'token': raw_token}), resp)
        check("another peer can't reuse the token (per-child scope)",
              resp.status.startswith('403'))

        # --- Deprecated shared-token fallback knob --------------------
        os.environ['POLARI_SHARED_TOKEN_FALLBACK'] = 'true'
        os.environ['POLARI_PEER_TOKEN'] = 'legacy'
        resp = _Resp()
        papi.on_post_register(_req({'name': 'polari-legacy',
                                    'baseUrl': 'http://l:3000',
                                    'token': 'legacy'}), resp)
        check('shared token still registers while the fallback knob is on',
              resp.status.startswith('201'))
        os.environ['POLARI_SHARED_TOKEN_FALLBACK'] = 'false'
        resp = _Resp()
        papi.on_post_register(_req({'name': 'polari-legacy2',
                                    'baseUrl': 'http://l2:3000',
                                    'token': 'legacy'}), resp)
        check('fallback knob off -> shared token refused',
              resp.status.startswith('403'))
        os.environ.pop('POLARI_PEER_TOKEN', None)
        os.environ.pop('POLARI_SHARED_TOKEN_FALLBACK', None)

        # --- Revocation: token dies with the agreement ----------------
        resp = _Resp()
        api.on_post_revoke(_req(), resp, aid)
        check('revoke clears hash + removes the peer row',
              resp.media['data']['peerRemoved'] is True
              and agreement.status == 'revoked' and agreement.token_hash == '')
        check('revoked token no longer matches any agreement',
              find_agreement_for_token(parent, 'polari-b', raw_token) is None)
        resp = _Resp()
        api.on_post_approve(_req(), resp, aid)
        check('re-approving a revoked agreement -> 409 (fresh request needed)',
              resp.status.startswith('409'))

        # --- The whole child-side flow over mocked HTTP ----------------
        child = _manager()
        parent2 = _manager()
        api2 = _agreements_api(parent2)
        papi2 = _peers_api(parent2)

        def fake_post(url, body):
            resp = _Resp()
            if url.endswith('/api/peers/join-request'):
                api2.on_post_join_request(_req(body), resp)
            elif url.endswith('/api/peers/register'):
                papi2.on_post_register(_req(body), resp)
            else:
                return {'_error': f'unmocked POST {url}'}
            return resp.media

        def fake_get(url):
            if '/api/peers/join-request/' in url:
                resp = _Resp()
                aid2 = url.split('/join-request/')[1].split('?')[0]
                fp = url.split('fingerprint=')[1]
                api2.on_get_join_status(_req(params={'fingerprint': fp}),
                                        resp, aid2)
                return resp.media
            if url.endswith('/api/peers/ping'):
                return {'success': True,
                        'data': {'instanceName': 'polari-a',
                                 'framework': 'polari'}}
            return {'_error': f'unmocked GET {url}'}

        real_post, real_get_fn = jf_mod._http_post_json, jf_mod._http_get_json
        jf_mod._http_post_json = fake_post
        jf_mod._http_get_json = fake_get
        os.environ['POLARI_SHARED_TOKEN_FALLBACK'] = 'false'
        os.environ['POLARI_INSTANCE_NAME'] = 'polari-b'
        try:
            report = jf_mod.join_parent(child, 'http://a:3000',
                                        'http://b:3000')
            check('join_parent: pending on first pass (no approval yet)',
                  report['joined'] is False and report.get('status') == 'pending'
                  and report.get('agreementId'))
            resp = _Resp()
            api2.on_post_approve(_req({'approvedBy': 'dustin'}), resp,
                                 report['agreementId'])
            report2 = jf_mod.join_parent(child, 'http://a:3000',
                                         'http://b:3000')
            check('join_parent after approval: token received + registered',
                  report2['joined'] is True)
            outbound = next(iter(child.objectTables['PeerAgreement']
                                 .values()), None)
            check('child holds its OUTBOUND half (parent identity + token)',
                  outbound is not None and outbound.direction == 'outbound'
                  and outbound.approver_name == 'polari-a'
                  and outbound.token)
            report3 = jf_mod.join_parent(child, 'http://a:3000',
                                         'http://b:3000')
            check('re-running join is idempotent (reuses the agreement)',
                  report3['joined'] is True
                  and any('reusing' in e for e in report3['evidence']))

            # Revocation recovery: the parent revokes; the child's stored
            # token is refused, so it asks afresh (new pending agreement).
            resp = _Resp()
            api2.on_post_revoke(_req(), resp, report['agreementId'])
            report4 = jf_mod.join_parent(child, 'http://a:3000',
                                         'http://b:3000')
            check('after revocation: dead token dropped, fresh join request '
                  'sent (pending)',
                  report4['joined'] is False
                  and report4.get('status') == 'pending'
                  and report4.get('agreementId') != report['agreementId']
                  and outbound.status == 'revoked')
        finally:
            jf_mod._http_post_json = real_post
            jf_mod._http_get_json = real_get_fn
            os.environ.pop('POLARI_INSTANCE_NAME', None)
            os.environ.pop('POLARI_SHARED_TOKEN_FALLBACK', None)
    finally:
        _restore_tree_classes(real)

    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
