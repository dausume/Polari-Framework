"""
@module vpn.vpn_basis

Object model for the VPN + federation arc (vpn-1, Polari side).

Authority split (VPN_FEDERATION_PLAN §7.3, D9): the isle-side
`isle-vpn` app is the control plane. These rows are its SHADOW (fed by
the isle's push to /api/islemesh/ingest/vpn — replace-per-device, the
islemesh acceptor rule) and its INBOX (VpnProposal rows a local
operator applies with `isle vpn apply`). Nothing reached remotely or
through a tunnel can alter a VPN; nothing here renders a private key.

Every row carries `provider` (link|bridge), `kind` (the guide's ten
ids) and the derived Blind / Sees-traffic `label`, plus `is_mock` (the
islemesh mock discipline: real pushes never set it).

@consumers
  - vpn.vpn_api (ingest + read + proposals)
  - polariServer defClassList (tables + CRUDE)
  - vpn.selftest_vpn
"""

from objectTreeDecorators import treeObject, treeObjectInit


class VpnNetwork(treeObject):
    """One VPN network as one isle's app reports it. Two isles on the
    same federation each hold their own row (name is per device)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<network>@<device>'.
        name: str = '',
        network_name: str = '',
        # The isle whose app reported this row (the authority).
        device_name: str = '',
        # PROVIDERS entry + the app KIND installed on that device.
        provider: str = 'link',
        kind: str = 'vpn-link-gateway',
        # Blind / Sees traffic / '' — derived from kind, never typed.
        label: str = '',
        # NETWORK_MODES entry.
        mode: str = 'mesh',
        # 10.60.<n>.0/24 from the address plan (D5).
        cidr: str = '',
        listen_port: int = 0,
        interface: str = 'wg-arch',
        dns_suffix: str = '.vpn',
        mtu: int = 1420,
        # The knobs (default off; rendered only when on — §3).
        forward_allowed: bool = False,
        masquerade: bool = False,
        # Whether this network's peers use a preshared layer
        # (the fact only — the key itself never leaves the device).
        preshared_default: bool = False,
        peer_count: int = 0,
        # Observed state as last pushed ('' | 'up' | 'down').
        status: str = '',
        last_pushed: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.network_name = network_name
        self.device_name = device_name
        self.provider = provider
        self.kind = kind
        self.label = label
        self.mode = mode
        self.cidr = cidr
        self.listen_port = listen_port
        self.interface = interface
        self.dns_suffix = dns_suffix
        self.mtu = mtu
        self.forward_allowed = forward_allowed
        self.masquerade = masquerade
        self.preshared_default = preshared_default
        self.peer_count = peer_count
        self.status = status
        self.last_pushed = last_pushed
        self.is_mock = is_mock
        self.notes = notes


class VpnPeer(treeObject):
    """One peer entry of one network on one device. PUBLIC KEY ONLY —
    the private key is made on the peer and never enters a row."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<network>@<device>/<peer>'.
        name: str = '',
        network_name: str = '',
        device_name: str = '',
        peer_name: str = '',
        provider: str = 'link',
        # The peer's own app kind (what it IS on its side).
        kind: str = 'vpn-link-node',
        label: str = '',
        public_key: str = '',
        # Tunnel address ('10.60.1.2/32').
        address: str = '',
        # 'host:port' or '' (a peer behind NAT with no fixed endpoint).
        endpoint: str = '',
        # JSON list of AllowedIPs (own /32 + carried subnets).
        allowed_ips_json: str = '[]',
        persistent_keepalive_s: int = 25,
        # The FACT that a preshared layer is set — never the key.
        has_preshared: bool = False,
        # Observed from the isle's `wg show` / management interface.
        last_handshake: str = '',
        rx_bytes: int = 0,
        tx_bytes: int = 0,
        # PEER_STATUSES entry.
        status: str = '',
        # Which device / isle this peer IS, when known ('' otherwise).
        remote_device: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.network_name = network_name
        self.device_name = device_name
        self.peer_name = peer_name
        self.provider = provider
        self.kind = kind
        self.label = label
        self.public_key = public_key
        self.address = address
        self.endpoint = endpoint
        self.allowed_ips_json = allowed_ips_json
        self.persistent_keepalive_s = persistent_keepalive_s
        self.has_preshared = has_preshared
        self.last_handshake = last_handshake
        self.rx_bytes = rx_bytes
        self.tx_bytes = tx_bytes
        self.status = status
        self.remote_device = remote_device
        self.is_mock = is_mock
        self.notes = notes


class VpnAccessRule(treeObject):
    """One access rule of one network — rendered as nftables text the
    router applies (§7.4); AllowedIPs stay the transport's business."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<network>@<device>/rule/<n>'.
        name: str = '',
        network_name: str = '',
        device_name: str = '',
        provider: str = 'link',
        kind: str = '',
        label: str = '',
        # A peer tag ('gateway', 'members', 'isle-b') or a cidr.
        from_tag: str = '',
        # A peer tag or a cidr the rule targets.
        to_target: str = '',
        # RULE_ACTIONS entry.
        action: str = 'allow',
        # '' = any; else 'tcp:443,udp:53' style.
        ports: str = '',
        order: int = 0,
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.network_name = network_name
        self.device_name = device_name
        self.provider = provider
        self.kind = kind
        self.label = label
        self.from_tag = from_tag
        self.to_target = to_target
        self.action = action
        self.ports = ports
        self.order = order
        self.is_mock = is_mock
        self.notes = notes


class VpnFederationLink(treeObject):
    """One federation link: this device's network joined to a remote
    isle's network behind an approved PeerAgreement. Routes are
    exchanged as remote cidrs, never renumbered (D5)."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<network>@<device>-><remote_device>'.
        name: str = '',
        network_name: str = '',
        device_name: str = '',
        provider: str = 'link',
        kind: str = '',
        label: str = '',
        remote_device: str = '',
        remote_network: str = '',
        # The local peer entry that carries the remote side.
        gateway_peer: str = '',
        # JSON list of cidrs the remote side carries.
        remote_cidrs_json: str = '[]',
        # PeerAgreement.agreement_id — the consent record.
        agreement_id: str = '',
        # RELAY_KINDS entry (blind by default — D10).
        relay_kind: str = 'blind',
        # LINK_STATUSES entry.
        status: str = 'pending',
        # The shared name space both sides serve ('' = none yet).
        arch_name: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.network_name = network_name
        self.device_name = device_name
        self.provider = provider
        self.kind = kind
        self.label = label
        self.remote_device = remote_device
        self.remote_network = remote_network
        self.gateway_peer = gateway_peer
        self.remote_cidrs_json = remote_cidrs_json
        self.agreement_id = agreement_id
        self.relay_kind = relay_kind
        self.status = status
        self.arch_name = arch_name
        self.is_mock = is_mock
        self.notes = notes


class AppVpnExposure(treeObject):
    """The `.vpn` rung row (§7.2): one app of one isle reachable by
    the members of the network its gateway belongs to. Exists only
    where a gateway-kind app is installed; `.isle` never crosses."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<app>@<device>.vpn'.
        name: str = '',
        device_name: str = '',
        app_name: str = '',
        network_name: str = '',
        provider: str = 'link',
        kind: str = '',
        label: str = '',
        # The name members resolve ('<app>.vpn').
        vpn_name: str = '',
        # EXPOSURE_ROLES entry.
        role: str = 'server',
        # '' | 'active' | 'revoked'.
        status: str = 'active',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.app_name = app_name
        self.network_name = network_name
        self.provider = provider
        self.kind = kind
        self.label = label
        self.vpn_name = vpn_name
        self.role = role
        self.status = status
        self.is_mock = is_mock
        self.notes = notes


class VpnProposal(treeObject):
    """The inbox (D9): Polari PROPOSES a change; a local operator on
    the isle applies it (`isle vpn apply <id>`). A proposal never
    mutates the mirror rows — only the isle's next push does, and it
    flips this row's status with `applied_by` / `applied_at` set."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: the proposal id ('vp-<12 hex>').
        name: str = '',
        # The isle expected to apply it.
        device_name: str = '',
        # PROPOSAL_KINDS entry.
        kind: str = 'peer',
        provider: str = 'link',
        # The app kind the proposal is for (a guide id).
        app_kind: str = '',
        label: str = '',
        network_name: str = '',
        # The proposed change, validated at POST (no key material).
        payload_json: str = '{}',
        # PROPOSAL_STATUSES entry.
        status: str = 'proposed',
        proposed_by: str = '',
        proposed_at: str = '',
        # Set ONLY by the isle's push when an operator applied it.
        applied_by: str = '',
        applied_at: str = '',
        note: str = '',
        # Set by the no-code GenerateEvent node when a form made it.
        generated_by: str = '',
        is_mock: bool = False,
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.kind = kind
        self.provider = provider
        self.app_kind = app_kind
        self.label = label
        self.network_name = network_name
        self.payload_json = payload_json
        self.status = status
        self.proposed_by = proposed_by
        self.proposed_at = proposed_at
        self.applied_by = applied_by
        self.applied_at = applied_at
        self.note = note
        self.generated_by = generated_by
        self.is_mock = is_mock


#: Mirror classes the ingest replaces per device (the proposal inbox
#: is NOT among them — proposals are Polari-owned rows).
VPN_MIRROR_CLASSES = ('VpnNetwork', 'VpnPeer', 'VpnAccessRule',
                      'VpnFederationLink', 'AppVpnExposure')

VPN_CLASSES = [VpnNetwork, VpnPeer, VpnAccessRule, VpnFederationLink,
               AppVpnExposure, VpnProposal]
