"""
@module isle_guestnet.objects.guestnet.GuestNetworkState

GuestNetworkState — what the guestnet guest reports.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class GuestNetworkState(treeObject):
    """What it is: the twin of one guest network: clients, leases, bytes,
    pushed by the guest; `observed_at` on every row.
    Related concepts: `GuestNetworkDefinition`, `HardwareAppState`.
    How it is measured: DHCP leases + interface counters on the guest.
    """

    @treeObjectInit
    def __init__(self, name: str = '', network: str = '', clients: int = 0, leases: int = 0,
                 rx_bytes: int = 0, tx_bytes: int = 0, observed_at: str = '', is_mock: bool = False):
        self.name = name
        self.network = network
        self.clients = clients
        self.leases = leases
        self.rx_bytes = rx_bytes
        self.tx_bytes = tx_bytes
        self.observed_at = observed_at
        self.is_mock = is_mock
