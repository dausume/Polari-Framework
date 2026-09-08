"""
@module isle_relay.objects.relay.RelayNodeState

RelayNodeState — what the relay guest reports about its segment.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RelayNodeState(treeObject):
    """What it is: the twin of one relay segment: clients, leases, bytes per
    direction, and — when the Reticulum extension runs inside — the peers
    heard and the per-class relay counters (§5c-e), pushed by the guest.
    Related concepts: `RelayNodeDefinition`, `HardwareAppState`.
    How it is measured: the guest's DHCP leases + interface counters; the
    sidecar's /status inside the guest; every row carries `observed_at`.
    """

    @treeObjectInit
    def __init__(self, name: str = '', relay: str = '', clients: int = 0, rx_bytes: int = 0, tx_bytes: int = 0,
                 peers_heard: int = 0, class_counters_json: str = '{}', observed_at: str = '', is_mock: bool = False):
        self.name = name
        self.relay = relay
        self.clients = clients
        self.rx_bytes = rx_bytes
        self.tx_bytes = tx_bytes
        self.peers_heard = peers_heard
        self.class_counters_json = class_counters_json
        self.observed_at = observed_at
        self.is_mock = is_mock
