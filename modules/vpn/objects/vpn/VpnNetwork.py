"""
@module vpn.objects.vpn.VpnNetwork

Row class VpnNetwork of the vpn module — one class per file (design §7), split
from vpn_basis.py (sap-2c). The class docstring below is the explanation.
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
