"""
@module isle_guestnet.objects.guestnet.GuestNetworkExposure

GuestNetworkExposure — one isle host a guest network may reach (a ledger row).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class GuestNetworkExposure(treeObject):
    """What it is: one deliberate hole in the guest network's isolation: an
    isle host/app (by isle address) that guests may reach, with who allowed
    it and why. No row, no reach — the UCI allow-list is rendered from
    exactly these rows.
    Related concepts: `GuestNetworkDefinition`, `AppVpnExposure` (the VPN
    arc's exposure ledger: same discipline), `IsleApp`.
    How it is derived: typed by an operator (`allowed_by`), never inferred.
    """

    @treeObjectInit
    def __init__(self, name: str = '', network: str = '', isle_host: str = '', app_name: str = '',
                 allowed_by: str = '', reason: str = '', enabled: bool = True, is_prior: bool = True):
        self.name = name
        self.network = network
        self.isle_host = isle_host
        self.app_name = app_name
        self.allowed_by = allowed_by
        self.reason = reason
        self.enabled = enabled
        self.is_prior = is_prior
