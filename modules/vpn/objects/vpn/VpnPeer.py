"""
@module vpn.objects.vpn.VpnPeer

Row class VpnPeer of the vpn module — one class per file (design §7), split
from vpn_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
