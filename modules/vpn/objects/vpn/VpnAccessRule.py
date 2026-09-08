"""
@module vpn.objects.vpn.VpnAccessRule

Row class VpnAccessRule of the vpn module — one class per file (design §7), split
from vpn_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
