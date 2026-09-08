"""
@module vpn.objects.vpn.AppVpnExposure

Row class AppVpnExposure of the vpn module — one class per file (design §7), split
from vpn_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
