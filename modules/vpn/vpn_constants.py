"""
@cross-cutting
@module vpn.vpn_constants

Shared vocabulary for the VPN + federation arc (VPN_FEDERATION_PLAN
§7.5/§7.8, VPN_APP_KINDS.md): the two product lines under the
`isle-vpn` app family, the ten catalog kinds, the Blind / Sees-traffic
label every row carries, proposal + link statuses, the templated
hook toggles (never free shell), and the ingest payload keys.

Pure constants — NO framework imports (the islemesh_constants
discipline), so the engine and the selftest run stdlib-only.

Trademark rule (D12/D14): the family is `isle-vpn`; the engines are
named only in descriptions ("WireGuard-based" / "OpenVPN-based").

@consumers
  - vpn.* (basis, engine, api, catalog, page, demo, selftest)
  - polari-cli scripts/vpn.sh
"""

#: Ingest payload schema version (POST /api/islemesh/ingest/vpn).
SCHEMA_VERSION = '1'

#: The app family every kind belongs to.
APP_FAMILY = 'isle-vpn'

#: The two product lines (providers). 'link' drives WireGuard as a
#: separate program; 'bridge' drives OpenVPN the same way.
PROVIDERS = ('link', 'bridge')
PROVIDER_TITLES = {'link': 'Isle Link', 'bridge': 'Isle Bridge'}
PROVIDER_ENGINES = {'link': 'WireGuard-based', 'bridge': 'OpenVPN-based'}

#: The two labels (guide: on every row and on the isle-mesh matrix).
LABEL_BLIND = 'Blind'
LABEL_SEES = 'Sees traffic'
LABEL_ENDPOINT = ''  # a plain endpoint carries neither label

#: Catalog kinds (guide table, D14). Order = the guide's order.
#: Fields: provider, title, label, carries_subnet (isle subnet on the
#: tunnel), gateway (makes `.vpn` exposure available), relay (forwards
#: for others), exit (WAN masquerade knob applies), authority
#: (admits members), l2 (layer-2 span).
KIND_INFO = {
    'vpn-link-node': {
        'provider': 'link', 'title': 'Link Node', 'label': LABEL_ENDPOINT,
        'carries_subnet': False, 'gateway': False, 'relay': False,
        'exit': False, 'authority': False, 'l2': False,
        'description': 'Puts this device on a Link network with its '
                       'own address. Nothing behind it is shared. '
                       '(WireGuard-based)'},
    'vpn-link-gateway': {
        'provider': 'link', 'title': 'Link Gateway', 'label': LABEL_ENDPOINT,
        'carries_subnet': True, 'gateway': True, 'relay': False,
        'exit': False, 'authority': False, 'l2': False,
        'description': 'Puts this isle on a Link network and makes '
                       '.vpn exposure available for its apps. '
                       '(WireGuard-based)'},
    'vpn-link-relay': {
        'provider': 'link', 'title': 'Link Relay', 'label': LABEL_BLIND,
        'carries_subnet': False, 'gateway': False, 'relay': True,
        'exit': False, 'authority': False, 'l2': False,
        'description': 'Passes encrypted Link traffic between peers '
                       'that cannot reach each other. Holds no keys, '
                       'sees nothing. Safe on a rented box. '
                       '(WireGuard-based)'},
    'vpn-link-hub': {
        'provider': 'link', 'title': 'Link Hub', 'label': LABEL_SEES,
        'carries_subnet': True, 'gateway': True, 'relay': True,
        'exit': False, 'authority': True, 'l2': False,
        'description': 'A Link network\'s centre: admits members, '
                       'routes between them, can carry other isles\' '
                       'subnets. Own hardware only. (WireGuard-based)'},
    'vpn-link-exit': {
        'provider': 'link', 'title': 'Link Exit', 'label': LABEL_SEES,
        'carries_subnet': True, 'gateway': True, 'relay': True,
        'exit': True, 'authority': True, 'l2': False,
        'description': 'A Link Hub that also passes members\' internet '
                       'traffic out through its own connection. Off '
                       'unless you turn it on. (WireGuard-based)'},
    'vpn-bridge-client': {
        'provider': 'bridge', 'title': 'Bridge Client',
        'label': LABEL_ENDPOINT,
        'carries_subnet': False, 'gateway': False, 'relay': False,
        'exit': False, 'authority': False, 'l2': False,
        'description': 'Joins this device or isle to a Bridge server '
                       'with a certificate. Works over TCP/443 where '
                       'UDP is blocked. (OpenVPN-based)'},
    'vpn-bridge-server': {
        'provider': 'bridge', 'title': 'Bridge Server', 'label': LABEL_SEES,
        'carries_subnet': True, 'gateway': True, 'relay': True,
        'exit': False, 'authority': True, 'l2': False,
        'description': 'A certificate-issuing hub for Bridge clients, '
                       'with live per-client control and revocation. '
                       'Own hardware only. (OpenVPN-based)'},
    'vpn-bridge-span': {
        'provider': 'bridge', 'title': 'Bridge Span', 'label': LABEL_SEES,
        'carries_subnet': True, 'gateway': True, 'relay': True,
        'exit': False, 'authority': False, 'l2': True,
        'description': 'Stretches one isle\'s VLAN across sites at '
                       'layer 2, so two locations behave as one isle. '
                       '(OpenVPN-based)'},
    'vpn-bridge-exit': {
        'provider': 'bridge', 'title': 'Bridge Exit', 'label': LABEL_SEES,
        'carries_subnet': True, 'gateway': True, 'relay': True,
        'exit': True, 'authority': True, 'l2': False,
        'description': 'A Bridge Server that also passes clients\' '
                       'internet traffic out. Off unless you turn it '
                       'on. (OpenVPN-based)'},
    'vpn-bridge-peer': {
        'provider': 'bridge', 'title': 'Bridge Peer', 'label': LABEL_ENDPOINT,
        'carries_subnet': True, 'gateway': False, 'relay': False,
        'exit': False, 'authority': False, 'l2': False,
        'description': 'Connects an outside box that only speaks '
                       'OpenVPN (a YunoHost-class server, an existing '
                       'VPN) as a gateway peer. (OpenVPN-based)'},
}
KINDS = tuple(KIND_INFO)
LINK_KINDS = tuple(k for k in KINDS if KIND_INFO[k]['provider'] == 'link')
BRIDGE_KINDS = tuple(k for k in KINDS
                     if KIND_INFO[k]['provider'] == 'bridge')
#: Kinds whose presence on a device makes the `.vpn` rung available
#: (§7.2: "an installed VPN app of gateway kind").
GATEWAY_KINDS = tuple(k for k in KINDS if KIND_INFO[k]['gateway'])
#: The engine name a gateway-kind app provides (IsleCatalogEntry
#: `provides_engine` idiom; the IsleEngine row the isle pushes).
GATEWAY_ENGINE = 'vpn-gateway'

#: Network modes. mesh = every peer carries every other; hub = members
#: carry the hub only; p2p = exactly two peers.
NETWORK_MODES = ('mesh', 'hub', 'p2p')

#: Per-peer observed status (from the isle's `wg show` / management
#: interface; '' = never reported).
PEER_STATUSES = ('', 'active', 'stale', 'never')

#: Federation link statuses (a link exists only behind an approved
#: PeerAgreement; revoke tears the peer entry down).
LINK_STATUSES = ('pending', 'active', 'revoked')

#: How a federation link crosses: direct (the gateways reach each
#: other), blind (through a Link Relay — the D10 default), routing
#: (through a hub that is a peer of both sides and sees plaintext).
RELAY_KINDS = ('direct', 'blind', 'routing')

#: Proposal lifecycle (D9): Polari proposes, a local operator applies
#: on the isle. Only the isle's push flips proposed -> applied|rejected.
PROPOSAL_STATUSES = ('proposed', 'applied', 'rejected')

#: What a proposal can ask for. 'revoke' names a peer or link to drop.
PROPOSAL_KINDS = ('network', 'peer', 'rule', 'link', 'exposure',
                  'revoke')

#: Access-rule actions (rendered as nftables text the router applies).
RULE_ACTIONS = ('allow', 'deny')

#: `.vpn` exposure roles (the ladder's row shape: our role toward
#: the app across that rung).
EXPOSURE_ROLES = ('server', 'user', 'observer', 'relay-only')

#: The templated PostUp/PostDown toggles (D11 — never free shell).
#: Each is a named knob; the engine renders the fixed command text.
HOOK_TOGGLES = ('forward', 'masquerade', 'route-add')

#: The exposure ladder with the `.vpn` rung in place (§7.2).
LADDER = ('.isle', '.arch', '.vpn', '.mesh', 'web')

#: Payload keys that must NEVER appear anywhere in an ingest or a
#: proposal: the acceptor refuses the whole payload if one does
#: (private material is made on the device and never leaves it).
FORBIDDEN_KEYS = ('private_key', 'privatekey', 'preshared_key',
                  'presharedkey', 'psk', 'tls_key', 'ca_key',
                  'client_key', 'server_key')

#: Address plan (D5): one /24 per network from 10.60.0.0/16.
ADDRESS_PLAN_PREFIX = '10.60'
DEFAULT_MTU = 1420
DEFAULT_KEEPALIVE_S = 25
DEFAULT_DNS_SUFFIX = '.vpn'
DEFAULT_INTERFACE = 'wg-arch'
#: UDP port window handed to the islemesh netledger's free_port scan.
UDP_PORT_LO = 51820
UDP_PORT_HI = 51900


def label_for_kind(kind):
    """The Blind / Sees-traffic label for a kind ('' for a plain
    endpoint). Unknown kind -> ''."""
    return KIND_INFO.get(kind, {}).get('label', '')


def provider_for_kind(kind):
    return KIND_INFO.get(kind, {}).get('provider', '')


def is_gateway_kind(kind):
    return kind in GATEWAY_KINDS
