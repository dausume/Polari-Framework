"""
@module vpn.vpn_page

The /display/vpn no-code page (vpn-1): the mirror tables, the
structured API panels (summary, kinds, matrix, the `.vpn` rung
option) and the PROPOSE forms — every one a configured
class-rows-table / api-structured-panel / form item (Dustin
2026-09-02: no raw JSON on screens, no new components).

Every form links a `vpn-propose-<kind>` SolutionDefinition
(vpn_seed): FormSubscription -> AnalysisCall vpn-proposal (validate
against the mirror; refusals come back as the message) ->
GenerateEvent VpnProposal (dedupe by name) -> refreshDisplay with the
message. Nothing on this page can configure a VPN — it fills the
isle's inbox.
"""

from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

_VPN = '/api/vpn'


def _form(item_id, index, segments, title, solution_name, variables,
          submit_label='Propose'):
    """A no-code FORM item (the mealplan_pages_seed shape, copied so
    this page does not import the whole meal-planning seed). Fields:
    (name, label, dataType, default, placeholder, required)."""
    return {'id': item_id, 'index': index, 'type': 'form',
            'rowSegmentsUsed': segments, 'gridColumnStart': None,
            'title': title, 'visible': True, 'collapsed': False,
            'cssClass': '', 'componentProps': {}, 'nestedRows': [],
            'item': {'boundClassName': '', 'formFields': [],
                     'linkedSolutionName': solution_name,
                     'formLayout': 'grid', 'submissionMode': 'button',
                     'submitLabel': submit_label, 'debounceDelayMs': 1500,
                     'extraVariables': [
                         {'variableName': n, 'displayName': label,
                          'dataType': dtype, 'defaultValue': default,
                          'placeholder': ph, 'required': req}
                         for n, label, dtype, default, ph, req in variables]}}


_DEVICE = ('device', 'Isle (device that applies it)', 'string', 'isle-a',
           'the isle hostname — see the networks table', True)
_NETWORK = ('network_name', 'Network', 'string', 'arch-demo',
            'a VpnNetwork on that isle', True)

SEED_VPN_PAGE_DISPLAYS = [
    _page(
        'vpn-home', 'vpn',
        'Isle VPN (isle-vpn: Isle Link = WireGuard-based, Isle Bridge = '
        'OpenVPN-based): the MIRROR of each isle\'s VPN app (networks, '
        'peers with public keys only, access rules, federation links, '
        '.vpn exposures) and the PROPOSAL inbox a local operator applies '
        'with `isle vpn apply`. Blind / Sees-traffic on every row. '
        'Nothing here configures a VPN — the isle side is the authority.',
        'VpnNetwork',
        [
            _row(0, [
                _sapi('vpn-summary', 0, 6,
                      'VPN summary (mock banner lives here)', _VPN),
                _sapi('vpn-kinds', 1, 6,
                      'The ten app kinds — Link when both ends run '
                      'ours, Bridge when joining a network or an '
                      'OpenVPN-only box',
                      _VPN + '/kinds', pick='kinds'),
            ]),
            _row(1, [
                _table('vpn-networks', 0, 6, 'Networks (per isle)',
                       'VpnNetwork',
                       columns='network_name,device_name,provider,kind,'
                               'label,mode,cidr,listen_port,interface,'
                               'forward_allowed,masquerade,peer_count,'
                               'status,is_mock'),
                _table('vpn-peers', 1, 6,
                       'Peers (public keys only — private keys never '
                       'leave the device)', 'VpnPeer',
                       columns='peer_name,network_name,device_name,kind,'
                               'label,public_key,address,endpoint,'
                               'allowed_ips_json,has_preshared,'
                               'last_handshake,status,remote_device,'
                               'is_mock'),
            ]),
            _row(2, [
                _table('vpn-links', 0, 6,
                       'Federation links (exist only behind an approved '
                       'PeerAgreement; die with revocation)',
                       'VpnFederationLink',
                       columns='network_name,device_name,remote_device,'
                               'remote_network,gateway_peer,'
                               'remote_cidrs_json,agreement_id,'
                               'relay_kind,status,is_mock'),
                _table('vpn-exposures', 1, 6,
                       '.vpn exposures (the rung; only where a '
                       'gateway-kind app is installed)',
                       'AppVpnExposure',
                       columns='vpn_name,app_name,network_name,'
                               'device_name,kind,label,role,status,'
                               'is_mock'),
            ]),
            _row(3, [
                _table('vpn-rules', 0, 5,
                       'Access rules (rendered as nftables text the '
                       'router applies)', 'VpnAccessRule',
                       columns='name,network_name,device_name,from_tag,'
                               'to_target,action,ports,order,is_mock'),
                _table('vpn-proposals', 1, 7,
                       'Proposals — the isle\'s inbox (status flips only '
                       'when the isle reports applied_by)',
                       'VpnProposal',
                       columns='name,device_name,kind,app_kind,label,'
                               'network_name,status,proposed_by,'
                               'proposed_at,applied_by,applied_at,note'),
            ]),
            _row(4, [
                _form('vpn-propose-peer', 0, 6,
                      'Propose a peer (its public key only)',
                      'vpn-propose-peer', [
                          _DEVICE, _NETWORK,
                          ('peer_name', 'Peer name', 'string', '',
                           'slug, e.g. phone-dustin', True),
                          ('kind', 'Kind', 'string', 'vpn-link-node',
                           'one of the ten kinds (see the kinds panel)',
                           True),
                          ('public_key', 'Public key', 'string', '',
                           '44-char base64 from `wg pubkey` on the peer',
                           True),
                          ('endpoint', 'Endpoint', 'string', '',
                           'host:port, blank if behind NAT', False),
                          ('carried_cidrs', 'Carried subnets', 'string',
                           '', 'csv of cidrs a gateway/peer carries',
                           False),
                      ]),
                _form('vpn-propose-link', 1, 6,
                      'Propose a federation link (needs an approved '
                      'PeerAgreement id)',
                      'vpn-propose-link', [
                          _DEVICE, _NETWORK,
                          ('remote_device', 'Remote isle', 'string',
                           'isle-b', 'the other isle\'s hostname', True),
                          ('remote_network', 'Remote network', 'string',
                           'arch-demo', '', True),
                          ('remote_gateway_public_key',
                           'Remote gateway public key', 'string', '',
                           '44-char base64', True),
                          ('remote_cidrs', 'Remote subnets', 'string',
                           '', 'csv of cidrs the remote gateway carries',
                           True),
                          ('agreement_id', 'PeerAgreement id', 'string',
                           '', 'the approved agreement (consent)', True),
                          ('relay_kind', 'Relay', 'string', 'blind',
                           'direct | blind (default) | routing', False),
                          ('remote_endpoint', 'Remote endpoint', 'string',
                           '', 'host:port', False),
                      ]),
            ]),
            _row(5, [
                _form('vpn-propose-network', 0, 4,
                      'Propose a network', 'vpn-propose-network', [
                          _DEVICE,
                          ('network_name', 'Network name', 'string', '',
                           'slug', True),
                          ('provider', 'Provider', 'string', 'link',
                           'link | bridge', True),
                          ('app_kind', 'App kind', 'string',
                           'vpn-link-gateway', 'one of the ten kinds',
                           True),
                          ('mode', 'Mode', 'string', 'mesh',
                           'mesh | hub | p2p', False),
                          ('cidr', 'CIDR', 'string', '',
                           'blank = next free 10.60.n.0/24', False),
                          ('listen_port', 'UDP port', 'number', 0,
                           '0 = next free from the ledger', False),
                          ('forward_allowed', 'Forwarding knob',
                           'boolean', False, '', False),
                          ('masquerade', 'Exit (masquerade) knob',
                           'boolean', False, 'exit kinds only', False),
                      ]),
                _form('vpn-propose-exposure', 1, 4,
                      'Propose a .vpn exposure (gateway-kind app '
                      'required)', 'vpn-propose-exposure', [
                          _DEVICE, _NETWORK,
                          ('app_name', 'App', 'string', '',
                           'an isle app name', True),
                          ('role', 'Role', 'string', 'server',
                           'server | user | observer | relay-only',
                           False),
                      ]),
                _form('vpn-propose-revoke', 2, 4,
                      'Propose a revoke', 'vpn-propose-revoke', [
                          _DEVICE,
                          ('target', 'Target', 'string', 'peer',
                           'peer | link | exposure', True),
                          ('name', 'Name', 'string', '',
                           'peer name / link name / vpn name', True),
                          ('network_name', 'Network', 'string', '',
                           '', False),
                          ('reason', 'Reason', 'string', '', '', False),
                      ]),
            ]),
            _row(6, [
                _sapi('vpn-matrix', 0, 7,
                      'Per-isle matrix: kind, Blind / Sees traffic, '
                      'networks, .vpn names',
                      _VPN + '/matrix', pick='matrix'),
                _sapi('vpn-exposure-options', 1, 5,
                      'Exposure rungs on isle-a (.vpn present only '
                      'with a gateway-kind app)',
                      _VPN + '/exposure-options?device=isle-a'),
            ]),
        ]),
]
