"""
Selftest for the vpn module (vpn-1, Polari side).

Run from polari-framework/:
    python3 -m vpn.selftest_vpn                    (container root)
    PYTHONPATH=.:modules python3 -m vpn.selftest_vpn   (host)

Fake manager (objectTables + idList, no DB, no falcon): the engine's
pure functions, the proposal validator, the acceptor + read surface
in-process, and the two-isle acceptance flow (vpn_demo). Pins the
handoff's selftest list: mesh conf carries N-1 peers, hub member
carries one, masquerade appears only with the exit knob (and an exit
kind), a Bridge Peer's subnet lands in the routes, no private key in
any row or export, a proposal never mutates rows until applied_by is
set, the `.vpn` option is absent without a gateway-kind app, plus the
catalog / page / no-code seed shapes.
"""

import json
import sys

from types import SimpleNamespace

from vpn import VPN_CLASSES, VPN_SEED_PAIRS
from vpn.vpn_api import VpnAPI
from vpn.vpn_catalog import SEED_VPN_CATALOG, vpn_install_plan
from vpn.vpn_constants import (
    GATEWAY_KINDS, KIND_INFO, KINDS, LABEL_BLIND, LABEL_SEES, LADDER,
    PROPOSAL_KINDS, label_for_kind,
)
from vpn.vpn_demo import run_demo
from vpn.vpn_engine import (
    PRIVATE_KEY_PLACEHOLDER, allocate_address, allocate_cidr,
    allocate_udp_port, federation_routes, forbidden_key_paths,
    is_key_shaped, opaque_public_key, peers_visible, private_key_lines,
    render_access_rules, render_bridge_client_ovpn,
    render_bridge_server_conf, render_link_conf,
)
from vpn.vpn_page import SEED_VPN_PAGE_DISPLAYS
from vpn.vpn_proposals import propose, validate_proposal
from vpn.vpn_seed import SEED_VPN_ANALYSES, SEED_VPN_SOLUTIONS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + str(extra)) if (extra and not cond) else ""}')


def manager():
    return SimpleNamespace(objectTables={}, idList=[], db=None)


def api_for(m):
    api = VpnAPI.__new__(VpnAPI)
    api.manager = m
    api.polServer = None
    return api


def _peer(name, kind, addr, carried=None, endpoint=''):
    return {'peer_name': name, 'kind': kind, 'public_key': opaque_public_key(),
            'address': addr, 'endpoint': endpoint,
            'carried_cidrs': carried or [], 'persistent_keepalive_s': 25}


# ---- 1. vocabulary ------------------------------------------------------
print('\n[1] vocabulary + labels')
check('ten kinds, five per line', len(KINDS) == 10
      and sum(1 for k in KINDS if KIND_INFO[k]['provider'] == 'link') == 5)
check('only the Link Relay is Blind',
      [k for k in KINDS if label_for_kind(k) == LABEL_BLIND]
      == ['vpn-link-relay'])
check('every hub / server / span / exit Sees traffic',
      all(label_for_kind(k) == LABEL_SEES for k in (
          'vpn-link-hub', 'vpn-link-exit', 'vpn-bridge-server',
          'vpn-bridge-span', 'vpn-bridge-exit')))
check('gateway kinds = the ones that make the .vpn rung',
      set(GATEWAY_KINDS) == {'vpn-link-gateway', 'vpn-link-hub',
                             'vpn-link-exit', 'vpn-bridge-server',
                             'vpn-bridge-span', 'vpn-bridge-exit'})
check('ladder has the .vpn rung after .arch',
      LADDER.index('.vpn') == LADDER.index('.arch') + 1)
check('descriptions name the engine, titles never do',
      all('WireGuard' not in KIND_INFO[k]['title']
          and 'OpenVPN' not in KIND_INFO[k]['title'] for k in KINDS)
      and all(('WireGuard' in KIND_INFO[k]['description'])
              == (KIND_INFO[k]['provider'] == 'link') for k in KINDS))

# ---- 2. engine: allocation ---------------------------------------------
print('\n[2] allocation from the ledger')
check('next free /24 skips used + docker pools',
      allocate_cidr(['10.60.1.0/24', '10.60.2.0/24', '172.20.0.0/16'])
      == '10.60.3.0/24')
check('address allocation skips taken, starts at .2',
      allocate_address('10.60.1.0/24', ['10.60.1.1/32', '10.60.1.2/32'])
      == '10.60.1.3/32')
check('gateway asks for .1', allocate_address('10.60.1.0/24', [], start=1)
      == '10.60.1.1/32')
check('udp port from the netledger window, skipping published',
      allocate_udp_port([{'port': 51820}, {'port': 51821}]) == 51822)
check('key shape check', is_key_shaped(opaque_public_key())
      and not is_key_shaped('short'))
check('forbidden keys found at any depth',
      forbidden_key_paths({'peers': [{'x': 1, 'PrivateKey': 'a'}],
                           'a': {'b': {'psk': 1}}})
      == ['peers[0].PrivateKey', 'a.b.psk'])

# ---- 3. engine: Link rendering -----------------------------------------
print('\n[3] Link rendering (mesh / hub / exit / bridge peer)')
net = {'network_name': 'arch', 'mode': 'mesh', 'cidr': '10.60.1.0/24',
       'listen_port': 51820, 'interface': 'wg-arch', 'mtu': 1420,
       'forward_allowed': False, 'masquerade': False}
peers = [_peer('a', 'vpn-link-gateway', '10.60.1.1/32', ['10.10.0.0/24']),
         _peer('b', 'vpn-link-node', '10.60.1.2/32'),
         _peer('c', 'vpn-link-node', '10.60.1.3/32'),
         _peer('d', 'vpn-link-node', '10.60.1.4/32')]
conf_a = render_link_conf(net, peers[0], peers)
check('mesh: conf carries N-1 peers', conf_a.count('[Peer]') == 3)
check('mesh: no PrivateKey value, placeholder present',
      not private_key_lines(conf_a) and PRIVATE_KEY_PLACEHOLDER in conf_a)
check('mesh: forwarding + masquerade commented OFF',
      'forwarding OFF' in conf_a and 'masquerade OFF' in conf_a
      and 'PostUp' not in conf_a)
hub_net = dict(net, mode='hub')
hub_peers = [_peer('hub', 'vpn-link-hub', '10.60.1.1/32', ['10.10.0.0/24']),
             _peer('m1', 'vpn-link-node', '10.60.1.2/32'),
             _peer('m2', 'vpn-link-node', '10.60.1.3/32')]
conf_m1 = render_link_conf(hub_net, hub_peers[1], hub_peers)
conf_hub = render_link_conf(hub_net, hub_peers[0], hub_peers)
check('hub: a member carries ONE peer (the hub)',
      conf_m1.count('[Peer]') == 1 and 'PublicKey = %s'
      % hub_peers[0]['public_key'] in conf_m1)
check('hub: the hub carries every member', conf_hub.count('[Peer]') == 2)
check('hub: member has no ListenPort', 'ListenPort' not in conf_m1)
check('masquerade absent on a hub with the knob OFF',
      'PostUp = nft' not in conf_hub and 'masquerade OFF' in conf_hub)
exit_net = dict(hub_net, masquerade=True, forward_allowed=True)
exit_peers = [_peer('exit', 'vpn-link-exit', '10.60.1.1/32')] + hub_peers[1:]
conf_exit = render_link_conf(exit_net, exit_peers[0], exit_peers)
check('exit knob ON + exit kind: masquerade PostUp + forward rendered',
      'masquerade' in conf_exit and 'PostUp = sysctl -w '
      'net.ipv4.ip_forward=1' in conf_exit
      and 'PostDown = nft delete table' in conf_exit)
conf_hub_knob = render_link_conf(exit_net, hub_peers[0], hub_peers)
check('exit knob ON but HUB kind (not exit): masquerade still absent',
      'PostUp = nft' not in conf_hub_knob and 'masquerade OFF' in conf_hub_knob)
conf_node_knob = render_link_conf(exit_net, exit_peers[1], exit_peers)
check('exit knob ON but NODE kind: no forward, no masquerade',
      'PostUp' not in conf_node_knob)
bridge_peer = _peer('yuno', 'vpn-bridge-peer', '10.60.1.9/32',
                    ['192.168.77.0/24'], endpoint='yuno.example:1194')
conf_with_bp = render_link_conf(net, peers[1], peers + [bridge_peer])
check("a Bridge Peer's subnet lands in AllowedIPs",
      'AllowedIPs = 10.60.1.9/32, 192.168.77.0/24' in conf_with_bp)
check('templated hooks only: no free shell reaches the conf',
      all(ln.startswith(('PostUp = sysctl', 'PostUp = nft',
                         'PostDown = sysctl', 'PostDown = nft'))
          for ln in conf_exit.splitlines()
          if ln.startswith(('PostUp', 'PostDown'))))

# federation routes
links = [{'gateway_peer': 'a', 'remote_cidrs': ['10.60.2.0/24',
                                                '10.20.0.0/24'],
          'status': 'active'},
         {'gateway_peer': 'b', 'remote_cidrs': ['10.99.0.0/24'],
          'status': 'pending'}]
check('federation routes: active links only',
      federation_routes(links) == {'a': ['10.60.2.0/24', '10.20.0.0/24']})
conf_b = render_link_conf(net, peers[1], peers, links)
check("active link's remote cidrs ride the gateway peer's AllowedIPs",
      '10.60.2.0/24' in conf_b and '10.20.0.0/24' in conf_b
      and '10.99.0.0/24' not in conf_b)
check('peers_visible never includes self',
      all(p['peer_name'] != 'a' for p in peers_visible(net, peers[0], peers)))

# ---- 4. engine: access rules + bridge refusals -------------------------
print('\n[4] access rules + Bridge honesty')
rules = [{'name': 'r1', 'from_tag': 'members', 'to_target': '10.10.0.0/24',
          'action': 'allow', 'ports': 'tcp:443,udp:53', 'order': 1},
         {'name': 'r0', 'from_tag': 'nobody', 'to_target': 'any',
          'action': 'deny', 'order': 0}]
nft = render_access_rules(net, rules, {'members': ['10.60.1.2/32']})
check('nftables: policy drop + established accept first',
      'policy drop' in nft and 'ct state established,related accept' in nft)
check('nftables: rule expands per port, ordered',
      'tcp dport 443 accept' in nft and 'udp dport 53 accept' in nft
      and nft.index('UNRESOLVED') < nft.index('tcp dport 443'))
check('nftables: unresolved tag is a comment, never silently dropped',
      '# UNRESOLVED rule r0' in nft)
srv = render_bridge_server_conf(dict(net, kind='vpn-bridge-server'))
cli = render_bridge_client_ovpn(net, bridge_peer)
check('Bridge server/client REFUSE honestly without step-ca',
      not srv['ok'] and 'step-ca' in srv['reason'] and not cli['ok'])
srv2 = render_bridge_server_conf(
    dict(net, kind='vpn-bridge-exit', masquerade=True),
    ca={'mode': 'step-ca', 'ca_cert_path': '/etc/isle-mesh/ca.crt'})
check('Bridge server renders with step-ca; keys are device PATHS, not '
      'contents', srv2['ok'] and 'key /etc/isle-mesh/vpn/arch/server.key'
      in srv2['text'] and 'redirect-gateway' in srv2['text']
      and 'BEGIN' not in srv2['text'])
srv3 = render_bridge_server_conf(
    dict(net, kind='vpn-bridge-server', masquerade=True),
    ca={'mode': 'step-ca', 'ca_cert_path': '/x'})
check('Bridge SERVER (not exit) never pushes redirect-gateway even with '
      'the knob', 'no redirect-gateway' in srv3['text'])

# ---- 5. proposals: validation against the mirror ------------------------
print('\n[5] proposals validate against the mirror, never mutate it')
m = manager()
api = api_for(m)


class _R:
    status = '200 OK'
    media = None


view0 = {'networks': {}, 'peers': {}, 'pools': [], 'ports': [],
         'gateway_present': False, 'all_cidrs': []}
problems, norm = validate_proposal('network', {
    'network_name': 'arch', 'provider': 'link',
    'app_kind': 'vpn-link-gateway'}, view0)
check('network proposal: cidr + port allocated when blank',
      not problems and norm['cidr'] == '10.60.1.0/24'
      and norm['listen_port'] == 51820, problems)
problems, _ = validate_proposal('network', {
    'network_name': 'arch', 'provider': 'link', 'app_kind': 'vpn-link-node',
    'masquerade': True}, view0)
check('masquerade on a non-exit kind refused',
      any('exit kind' in p for p in problems))
problems, _ = validate_proposal('peer', {
    'network_name': 'arch', 'peer_name': 'p', 'public_key': 'x'}, view0)
check('peer on a missing network refused + bad key refused',
      any('no network' in p for p in problems)
      and any('44-char' in p for p in problems))
problems, _ = validate_proposal('exposure', {
    'network_name': 'arch', 'app_name': 'whoami'}, view0)
check('exposure refused without a gateway-kind app',
      any('.vpn rung is not available' in p for p in problems))
problems, _ = validate_proposal('link', {
    'network_name': 'arch', 'remote_device': 'b', 'remote_network': 'arch',
    'remote_gateway_public_key': opaque_public_key(),
    'remote_cidrs': '10.60.2.0/24'}, dict(view0, networks={
        'arch': {'cidr': '10.60.1.0/24', 'listen_port': 1, 'mode': 'mesh',
                 'provider': 'link', 'kind': 'vpn-link-gateway'}}))
check('link refused without an agreement id (consent)',
      any('agreement_id' in p for p in problems))
problems, _ = validate_proposal('peer', {
    'network_name': 'arch', 'peer_name': 'p',
    'public_key': opaque_public_key(), 'private_key': 'leak'}, view0)
check('key material in a proposal = refused outright',
      problems and problems[0].startswith('refused: key material'))
check('every proposal kind has a validator branch',
      all(validate_proposal(k, {}, view0)[0] for k in PROPOSAL_KINDS))
r = propose(m, device='isle-x', kind='network', network_name='arch',
            provider='link', app_kind='vpn-link-gateway', mock_network=True)
check('propose(): returns ONE row + message, writes nothing itself',
      r['ok'] and len(r['proposals']) == 1
      and r['proposals'][0]['status'] == 'proposed'
      and 'isle vpn apply' in r['message']
      and not m.objectTables.get('VpnProposal'))
resp = _R()
api.file_proposal({'device': 'isle-x', 'kind': 'network',
                   'network_name': 'arch', 'provider': 'link',
                   'app_kind': 'vpn-link-gateway', 'mock_network': True},
                  resp)
check('API files the proposal (201) and the mirror stays empty',
      resp.status.startswith('201')
      and len(m.objectTables.get('VpnProposal', {})) == 1
      and not m.objectTables.get('VpnNetwork'))
resp = _R()
api.file_proposal({'device': '', 'kind': 'network'}, resp)
check('API refuses a proposal without a device (400)',
      resp.status.startswith('400'))

# ---- 6. the two-isle acceptance flow ----------------------------------
print('\n[6] two-isle acceptance flow (vpn_demo)')
m2 = manager()
report = run_demo(api_for(m2))
for s in report['steps']:
    check('demo: ' + s['step'], s['pass'], s['detail'])
check('demo all_pass', report['all_pass'])

# ---- 7. seeds: catalog, page, no-code -----------------------------------
print('\n[7] seed shapes')
check('ten catalog entries, kind isle-vpn, gateway ones provide '
      'vpn-gateway', len(SEED_VPN_CATALOG) == 10
      and all(e['kind'] == 'isle-vpn' for e in SEED_VPN_CATALOG)
      and {e['name'] for e in SEED_VPN_CATALOG if e['provides_engine']}
      == set(GATEWAY_KINDS))
check('catalog never seeded is_mock',
      all(not e.get('is_mock') for e in SEED_VPN_CATALOG))
plan = vpn_install_plan(SEED_VPN_CATALOG[1])
check('install plan = isle vpn install <kind>, names the authority rule',
      plan['ok'] and plan['steps'] == ['isle vpn install vpn-link-gateway']
      and 'isle vpn apply' in plan['note'])
page = SEED_VPN_PAGE_DISPLAYS[0]
defn = json.loads(page['definition'])
kinds_used = {}
for row in defn['rows']:
    for item in row['items']:
        if item['type'] == 'form':
            kinds_used['form'] = kinds_used.get('form', 0) + 1
        else:
            name = item['componentProps']['componentName']
            kinds_used[name] = kinds_used.get(name, 0) + 1
check('page /display/vpn uses only tables, structured panels, forms — '
      'no api-json-panel, no custom component',
      page['pageRoute'] == 'vpn' and set(kinds_used)
      == {'class-rows-table', 'api-structured-panel', 'form'})
sol_names = {s['name'] for s in SEED_VPN_SOLUTIONS}
form_sols = {item['item']['linkedSolutionName']
             for row in defn['rows'] for item in row['items']
             if item['type'] == 'form'}
check('every form links a seeded vpn-propose-* solution',
      form_sols <= sol_names and len(form_sols) == 5)
check('one analysis (vpn-proposal) + six solutions, all FormSubscription '
      '-> Validate -> Message -> Write -> Refresh',
      len(SEED_VPN_ANALYSES) == 1 and len(SEED_VPN_SOLUTIONS) == 6
      and all([s['stateName'] for s in
               json.loads(x['definition'])['stateInstances']]
              == ['Start', 'Validate', 'Message', 'Write', 'Refresh']
              for x in SEED_VPN_SOLUTIONS))
check('seed pairs cover every class, no seeds (mirror + inbox only)',
      [p[1] for p in VPN_SEED_PAIRS] == VPN_CLASSES
      and all(p[2] == [] for p in VPN_SEED_PAIRS))
check('no class declares a private/preshared key field',
      all(f not in ('private_key', 'preshared_key')
          for cls in VPN_CLASSES
          for f in cls.__init__.__code__.co_varnames))

# ---- 8. vpn-3: the trust bridge -----------------------------------------
print('\n[8] trust bridge: join request -> PeerAgreement -> proposal inbox')
from polariPeers.agreements_api import AGREEMENT_LISTENERS, AgreementsAPI, notify_agreement
from vpn.vpn_trust import file_join_request, on_agreement_event, proposals_of_agreement
m3 = manager()
api3 = api_for(m3)
listener = api3.register_trust_bridge()
api_for(m3).register_trust_bridge()   # a second construction (boot cycles)
api_for(m3).register_trust_bridge()
check('listener registered ONCE across repeated endpoint constructions',
      AGREEMENT_LISTENERS.count(listener) == 1
      and listener is on_agreement_event)
# a network to join (mirror, mock)
sink = _R()
from vpn.vpn_demo import base_push, ISLE_A
api3.ingest(base_push(ISLE_A, opaque_public_key()), sink)
agr = AgreementsAPI.__new__(AgreementsAPI); agr.manager = m3
res, st = file_join_request(m3, {'device': ISLE_A, 'kind': 'peer',
                                 'network_name': 'arch-demo',
                                 'peer_name': 'phone-x', 'kind_': '',
                                 'public_key': opaque_public_key(),
                                 'requester_name': 'phone-x',
                                 'requester_base_url': 'http://phone-x:3000',
                                 'fingerprint': 'fp-x', 'mock_network': True})
check('join request -> 201 with agreement + waiting proposal',
      st.startswith('201') and res['ok'] and res['proposal_status']
      == 'awaiting-consent', res)
aid = res.get('agreement_id', '')
agreement = next(a for a in m3.objectTables['PeerAgreement'].values()
                 if a.agreement_id == aid)
check('agreement is pending, role vpn-member, scope names the network',
      agreement.status == 'pending' and agreement.requested_role == 'vpn-member'
      and agreement.scope == 'vpn:peer:arch-demo@isle-a', agreement.scope)
prow = proposals_of_agreement(m3, aid)[0]
check('proposal carries agreement_id, is NOT in the inbox yet',
      json.loads(prow.payload_json)['agreement_id'] == aid
      and prow.status == 'awaiting-consent')
res2, st2 = file_join_request(m3, {'device': ISLE_A, 'kind': 'peer',
                                   'network_name': 'arch-demo',
                                   'peer_name': 'phone-x2',
                                   'public_key': opaque_public_key(),
                                   'requester_name': 'phone-x',
                                   'requester_base_url': 'http://phone-x:3000',
                                   'fingerprint': 'fp-x'})
check('re-asking while pending returns the SAME agreement (idempotent)',
      st2.startswith('200') and res2.get('already_pending')
      and res2['agreement_id'] == aid)
bad, stb = file_join_request(m3, {'device': ISLE_A, 'kind': 'peer',
                                  'network_name': 'nope', 'peer_name': 'p',
                                  'public_key': 'x', 'requester_name': 'r',
                                  'requester_base_url': 'u', 'fingerprint': 'f'})
check('a join request that fails VPN validation makes NO agreement',
      stb.startswith('400') and len(m3.objectTables['PeerAgreement']) == 1)
before_networks = len(m3.objectTables.get('VpnNetwork', {}))
agr._approve(agreement, approved_by='operator@test')
check('approve -> proposal moves into the inbox (proposed), mirror untouched',
      prow.status == 'proposed' and 'approved by operator@test' in prow.note
      and len(m3.objectTables.get('VpnNetwork', {})) == before_networks)
# the isle applies it (push with the proposal receipt)
sink = _R()
api3.ingest(dict(base_push(ISLE_A, opaque_public_key()),
                 proposals=[{'id': prow.name, 'status': 'applied',
                             'applied_by': 'operator@isle-a'}]), sink)
check('isle applies -> proposal applied', prow.status == 'applied')
agreement.status = 'revoked'; agreement.revoked_at = '2026-09-03T15:00:00+00:00'
notify_agreement(m3, agreement, 'revoked')
revokes = [r for r in m3.objectTables['VpnProposal'].values()
           if r.kind == 'revoke']
check('revoke -> exactly ONE revoke proposal for the applied peer, in the '
      'inbox (proposed)',
      len(revokes) == 1 and json.loads(revokes[0].payload_json)['name']
      == 'phone-x' and revokes[0].status == 'proposed', [r.note for r in revokes])
notify_agreement(m3, agreement, 'revoked')   # a second revoke event
revokes2 = [r for r in m3.objectTables['VpnProposal'].values()
            if r.kind == 'revoke']
check('a repeated revoke event files nothing new and keeps the tear-down '
      'proposed', len(revokes2) == 1 and revokes2[0].status == 'proposed')
# deny path on a fresh federation request
resl, stl = file_join_request(m3, {'device': ISLE_A, 'kind': 'link',
                                   'network_name': 'arch-demo',
                                   'remote_device': 'isle-z',
                                   'remote_network': 'arch-demo',
                                   'remote_gateway_public_key': opaque_public_key(),
                                   'remote_cidrs': '10.60.9.0/24',
                                   'requester_name': 'isle-z',
                                   'requester_base_url': 'http://isle-z:3000',
                                   'fingerprint': 'fp-z'})
check('federation join request -> vpn-federation agreement + waiting link '
      'proposal', stl.startswith('201') and resl['ok'], resl)
agr_z = next(a for a in m3.objectTables['PeerAgreement'].values()
             if a.agreement_id == resl['agreement_id'])
check('federation role', agr_z.requested_role == 'vpn-federation')
agr_z.status = 'denied'
notify_agreement(m3, agr_z, 'denied')
lrow = proposals_of_agreement(m3, resl['agreement_id'])[0]
check('deny -> the waiting proposal is rejected, never reached the isle',
      lrow.status == 'rejected' and 'DENIED' in lrow.note)
check('a non-vpn agreement is ignored by the bridge',
      on_agreement_event(m3, SimpleNamespace(requested_role='child',
                                             agreement_id='x'),
                         'approved') == {'handled': False})
AGREEMENT_LISTENERS.remove(listener)

passed, total = sum(results), len(results)
print(f'\n{passed}/{total} checks passed')
sys.exit(0 if passed == total else 1)
