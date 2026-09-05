"""
@module vpn.vpn_demo

The two-isle ACCEPTANCE flow (handoff "Acceptance for vpn-1"), run
in-process against a VpnAPI: two Link networks on this box (two isles
simulated as two isles' pushes, every payload mock_network=true), one
federation proposal -> "applied" by the simulated isle side ->
mirrored rows show the link active; the `.vpn` exposure option
present only with the gateway app; a revoke -> the peer entry gone
within one render; zero private keys anywhere.

The simulated isle side does what the real `isle vpn apply` will do:
it reads the proposal, produces the NEXT push (peers + links +
proposals[applied]) — private keys are generated here only to be
thrown away (the public half rides the push, exactly as on a device).

Payload builders are pure; `run_demo(api)` orchestrates and returns a
step report the selftest and `POST /api/vpn/demo` / `pol vpn demo`
both read.

@consumers
  - vpn.vpn_api (POST /api/vpn/demo)
  - vpn.selftest_vpn
"""

import json

from vpn.vpn_constants import GATEWAY_ENGINE, LABEL_ENDPOINT
from vpn.vpn_engine import keygen, opaque_public_key, private_key_lines

ISLE_A, ISLE_B = 'isle-a', 'isle-b'
NET = 'arch-demo'
#: Each simulated isle's VLAN subnet (the OpenWRT 10.<vlan>.0.0/24).
#: isle-c is the control: a Link NODE (no gateway kind) — the `.vpn`
#: rung must be absent there.
ISLE_C = 'isle-c'
ISLE_SUBNET = {ISLE_A: '10.10.0.0/24', ISLE_B: '10.20.0.0/24',
               ISLE_C: '10.30.0.0/24'}
CIDR = {ISLE_A: '10.60.1.0/24', ISLE_B: '10.60.2.0/24',
        ISLE_C: '10.60.3.0/24'}
ENDPOINT = {ISLE_A: 'isle-a.example.net:51820',
            ISLE_B: 'isle-b.example.net:51821',
            ISLE_C: 'isle-c.example.net:51822'}
PORT = {ISLE_A: 51820, ISLE_B: 51821, ISLE_C: 51822}


def public_key():
    """A public key whose private half is discarded on the spot —
    the demo never holds one longer than this call."""
    try:
        _priv, pub = keygen()
        del _priv
        return pub
    except RuntimeError:
        return opaque_public_key()


def base_push(device, own_pub, extra_peers=(), links=(), exposures=(),
              proposals=(), kind='vpn-link-gateway'):
    """One isle's push: its network, its OWN gateway entry (the peer
    whose remote_device is the device itself), plus what the flow
    adds. mock_network=true on every payload — real pushes never
    carry it."""
    own = {'network_name': NET, 'peer_name': '%s-gw' % device,
           'kind': kind, 'public_key': own_pub,
           'address': CIDR[device].replace('.0/24', '.1/32'),
           'endpoint': ENDPOINT[device],
           'allowed_ips': [CIDR[device].replace('.0/24', '.1/32'),
                           ISLE_SUBNET[device]],
           'persistent_keepalive_s': 0, 'has_preshared': False,
           'status': 'active', 'remote_device': device}
    return {
        'device': device, 'mock_network': True, 'schema_version': '1',
        'app': {'name': 'isle-vpn', 'kind': kind, 'version': 'demo',
                'config_api': 'http://127.0.0.1:7443', 'status': 'up'},
        'networks': [{'network_name': NET, 'mode': 'mesh',
                      'cidr': CIDR[device], 'listen_port': PORT[device],
                      'interface': 'wg-arch', 'dns_suffix': '.vpn',
                      'mtu': 1420, 'forward_allowed': True,
                      'masquerade': False, 'status': 'up',
                      'notes': 'demo isle (mock)'}],
        'peers': [own] + list(extra_peers),
        'rules': [{'network_name': NET, 'name': 'members-to-apps',
                   'from_tag': 'members', 'to_target': ISLE_SUBNET[device],
                   'action': 'allow', 'ports': 'tcp:443', 'order': 0}],
        'links': list(links),
        'exposures': list(exposures),
        'proposals': list(proposals),
    }


class _Sink:
    status = '200 OK'
    media = None


def run_demo(api):
    """The acceptance flow. Returns {'ok', 'all_pass', 'steps',
    'banner'} — every step carries pass + detail."""
    steps = []

    def step(label, passed, detail=''):
        steps.append({'step': label, 'pass': bool(passed),
                      'detail': detail})

    pub_a, pub_b = public_key(), public_key()

    # 1. two isles push their networks (two Link Gateways)
    for device, pub in ((ISLE_A, pub_a), (ISLE_B, pub_b)):
        sink = _Sink()
        api.ingest(base_push(device, pub), sink)
        step('%s push accepted (Link Gateway, mock)' % device,
             (sink.media or {}).get('ok'),
             json.dumps((sink.media or {}).get('counts')))
    # (only isle-a / isle-b: on a live instance the control isle-c's
    # row from an earlier demo run is DB-restored before its push)
    nets = [r for r in api._table('VpnNetwork').values()
            if getattr(r, 'network_name', '') == NET
            and getattr(r, 'device_name', '') in (ISLE_A, ISLE_B)]
    step('two networks mirrored', len(nets) == 2,
         ', '.join(sorted(getattr(n, 'name', '') for n in nets)))
    step('gateway label is a plain endpoint (Link Gateway sees only '
         'its own isle)', all(getattr(n, 'label', 'x') == LABEL_ENDPOINT
                              for n in nets))

    # 2. the .vpn rung: present with the gateway app, absent without
    opts_a = api.exposure_options(ISLE_A)
    step('.vpn option present on isle-a (gateway app installed)',
         '.vpn' in opts_a['options'], ', '.join(opts_a['options']))
    sink = _Sink()
    api.ingest(base_push(ISLE_C, public_key(), kind='vpn-link-node'), sink)
    opts_c = api.exposure_options(ISLE_C)
    step('.vpn option ABSENT on isle-c (Link Node — no gateway kind)',
         '.vpn' not in opts_c['options'], ', '.join(opts_c['options']))
    engines = [r for r in api._table('IsleEngine').values()
               if getattr(r, 'provides', '') == GATEWAY_ENGINE]
    step('vpn-gateway engine rows only for gateway isles',
         sorted(getattr(e, 'device_name', '') for e in engines)
         == [ISLE_A, ISLE_B])

    # 3. propose the federation link on isle-a (behind an agreement id)
    sink = _Sink()
    api.file_proposal({
        'device': ISLE_A, 'kind': 'link', 'network_name': NET,
        'remote_device': ISLE_B, 'remote_network': NET,
        'remote_gateway_public_key': pub_b,
        'remote_cidrs': [CIDR[ISLE_B], ISLE_SUBNET[ISLE_B]],
        'agreement_id': 'demo-agreement-ab', 'relay_kind': 'direct',
        'remote_endpoint': ENDPOINT[ISLE_B], 'proposed_by': 'demo',
        'mock_network': True}, sink)
    ok = (sink.media or {}).get('ok')
    pid = ((sink.media or {}).get('proposal') or {}).get('name', '')
    step('federation proposal filed on isle-a', ok and pid,
         (sink.media or {}).get('message') or (sink.media or {}).get('error'))
    links_before = [r for r in api._table('VpnFederationLink').values()]
    step('proposal did NOT touch the mirror (no link row yet)',
         not links_before)

    # 4. the simulated isle side applies it: next push carries the
    #    remote gateway as a peer + the link active + the proposal
    #    receipt with applied_by set
    remote_peer_b = {
        'network_name': NET, 'peer_name': '%s-gw' % ISLE_B,
        'kind': 'vpn-link-gateway', 'public_key': pub_b,
        'address': CIDR[ISLE_B].replace('.0/24', '.1/32'),
        'endpoint': ENDPOINT[ISLE_B],
        'allowed_ips': [CIDR[ISLE_B].replace('.0/24', '.1/32'),
                        CIDR[ISLE_B], ISLE_SUBNET[ISLE_B]],
        'persistent_keepalive_s': 25, 'has_preshared': False,
        'last_handshake': '2026-09-03T12:00:00+00:00',
        'rx_bytes': 1024, 'tx_bytes': 2048, 'status': 'active',
        'remote_device': ISLE_B}
    link_a = {'network_name': NET, 'remote_device': ISLE_B,
              'remote_network': NET, 'gateway_peer': '%s-gw' % ISLE_B,
              'remote_cidrs': [CIDR[ISLE_B], ISLE_SUBNET[ISLE_B]],
              'agreement_id': 'demo-agreement-ab', 'relay_kind': 'direct',
              'status': 'active', 'arch_name': 'demo.arch'}
    # an anonymous apply must be refused first (D9: an operator applies)
    sink = _Sink()
    api.ingest(base_push(ISLE_A, pub_a, extra_peers=[remote_peer_b],
                         links=[link_a],
                         proposals=[{'id': pid, 'status': 'applied',
                                     'applied_by': ''}]), sink)
    prow = next(r for r in api._table('VpnProposal').values()
                if getattr(r, 'name', '') == pid)
    step('anonymous apply refused (applied_by required); proposal still '
         'proposed', (sink.media or {}).get('proposal_errors')
         and getattr(prow, 'status', '') == 'proposed')
    sink = _Sink()
    api.ingest(base_push(ISLE_A, pub_a, extra_peers=[remote_peer_b],
                         links=[link_a],
                         proposals=[{'id': pid, 'status': 'applied',
                                     'applied_by': 'operator@isle-a',
                                     'note': 'applied via isle vpn apply'}]),
               sink)
    step('isle-a applied the proposal (applied_by set by the push)',
         getattr(prow, 'status', '') == 'applied'
         and getattr(prow, 'applied_by', '') == 'operator@isle-a')
    link_rows = [r for r in api._table('VpnFederationLink').values()
                 if getattr(r, 'device_name', '') == ISLE_A]
    step('mirrored link row ACTIVE on isle-a',
         len(link_rows) == 1 and getattr(link_rows[0], 'status', '')
         == 'active', getattr(link_rows[0], 'name', '') if link_rows else '')
    # isle-b's symmetric push (its own operator applied its half)
    remote_peer_a = dict(remote_peer_b, peer_name='%s-gw' % ISLE_A,
                         public_key=pub_a,
                         address=CIDR[ISLE_A].replace('.0/24', '.1/32'),
                         endpoint=ENDPOINT[ISLE_A],
                         allowed_ips=[CIDR[ISLE_A].replace('.0/24', '.1/32'),
                                      CIDR[ISLE_A], ISLE_SUBNET[ISLE_A]],
                         remote_device=ISLE_A)
    link_b = dict(link_a, remote_device=ISLE_A,
                  gateway_peer='%s-gw' % ISLE_A,
                  remote_cidrs=[CIDR[ISLE_A], ISLE_SUBNET[ISLE_A]])
    sink = _Sink()
    api.ingest(base_push(ISLE_B, pub_b, extra_peers=[remote_peer_a],
                         links=[link_b],
                         exposures=[{'app_name': 'whoami',
                                     'network_name': NET,
                                     'role': 'server', 'status': 'active'}]),
               sink)
    step('isle-b mirrored its half + a whoami.vpn exposure',
         (sink.media or {}).get('ok')
         and any(getattr(r, 'vpn_name', '') == 'whoami.vpn'
                 for r in api._table('AppVpnExposure').values()))

    # 5. render: isle-a's gateway conf carries isle-b's gateway with
    #    the federation routes; never a private key
    rendered = api.render(ISLE_A, NET, 'self')
    text = rendered.get('text', '')
    step('render for isle-a self: conf carries isle-b-gw peer with '
         'isle-b subnets', rendered.get('ok')
         and 'PublicKey = %s' % pub_b in text
         and ISLE_SUBNET[ISLE_B] in text and CIDR[ISLE_B] in text)
    step('render: forwarding ON (knob on, gateway relays? no -> stays '
         'commented) and masquerade OFF', 'masquerade OFF' in text
         and 'PostUp = nft' not in text)
    step('zero private keys in the render (placeholder only)',
         not private_key_lines(text) and '@@DEVICE_PRIVATE_KEY@@' in text)

    # 6. revoke: proposal -> isle-a applies -> peer gone within one push
    sink = _Sink()
    api.file_proposal({'device': ISLE_A, 'kind': 'revoke', 'target': 'link',
                       'name': link_rows[0].name if link_rows else '',
                       'network_name': NET, 'reason': 'demo revoke',
                       'proposed_by': 'demo', 'mock_network': True}, sink)
    rpid = ((sink.media or {}).get('proposal') or {}).get('name', '')
    step('revoke proposal filed', bool(rpid))
    sink = _Sink()
    api.ingest(base_push(ISLE_A, pub_a,
                         links=[dict(link_a, status='revoked')],
                         proposals=[{'id': rpid, 'status': 'applied',
                                     'applied_by': 'operator@isle-a'}]),
               sink)
    peers_a = [getattr(r, 'peer_name', '')
               for r in api._table('VpnPeer').values()
               if getattr(r, 'device_name', '') == ISLE_A]
    step('after revoke: isle-b-gw peer GONE from isle-a within one push',
         '%s-gw' % ISLE_B not in peers_a, ', '.join(peers_a))
    text2 = api.render(ISLE_A, NET, 'self').get('text', '')
    step('after revoke: render no longer carries isle-b', pub_b not in text2)
    link_after = [r for r in api._table('VpnFederationLink').values()
                  if getattr(r, 'device_name', '') == ISLE_A]
    step('link row now revoked', len(link_after) == 1
         and getattr(link_after[0], 'status', '') == 'revoked')

    # 7. the security gates
    sink = _Sink()
    api.ingest(dict(base_push(ISLE_A, pub_a),
                    peers=[{'network_name': NET, 'peer_name': 'leak',
                            'public_key': pub_a,
                            'private_key': 'AAAA' * 11}]), sink)
    step('a push carrying private_key is REFUSED whole',
         not (sink.media or {}).get('ok')
         and 'key material' in (sink.media or {}).get('error', ''))
    sink = _Sink()
    api.file_proposal({'device': ISLE_A, 'kind': 'peer', 'network_name': NET,
                       'peer_name': 'leaky', 'kind_': 'x',
                       'public_key': pub_b, 'preshared_key': 'nope',
                       'mock_network': True}, sink)
    step('a proposal carrying preshared_key is REFUSED',
         not (sink.media or {}).get('ok'))
    leaks = []
    for class_name in ('VpnNetwork', 'VpnPeer', 'VpnAccessRule',
                       'VpnFederationLink', 'AppVpnExposure',
                       'VpnProposal'):
        for row in api._table(class_name).values():
            for key, value in vars(row).items():
                if key.lower() in ('private_key', 'preshared_key') or (
                        isinstance(value, str)
                        and private_key_lines(value)):
                    leaks.append('%s.%s' % (class_name, key))
    step('zero private keys in any mirror or inbox row', not leaks,
         ', '.join(leaks))

    all_pass = all(s['pass'] for s in steps)
    return {'ok': True, 'all_pass': all_pass, 'steps': steps,
            'mock_network': True,
            'banner': 'MOCK NETWORK — the two-isle VPN demo (isle-a, '
                      'isle-b, isle-c) is simulated data'}
