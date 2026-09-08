"""
@module isle_relay.objects.relay.RelayNodeDefinition

RelayNodeDefinition — one relay segment an isle-relay guest serves.
"""
from objectTreeDecorators import treeObject, treeObjectInit

BEARERS = ('wifi-ap', 'wifi-sta', 'ethernet')


class RelayNodeDefinition(treeObject):
    """What it is: one relay segment — a VLAN + DHCP pool + (usually) a WiFi
    AP served by an isle-relay guest, FORWARDING into the isle zone so the
    isle extends across it; optionally the segment the Reticulum extension
    app uses as its bearer (RETICULUM plan §5c-e classes apply there).
    Related concepts: `HardwareAppDefinition` (`hardware_app` names the guest
    this segment runs on), `RelayNodeState` (the twin), `DeviceLink` (the
    WiFi adapter passed through), `RelayPolicy` (reticulum, later).
    How it is realised: `hardwareapps.custom.uci_profiles` profile `relay`
    renders the UCI script from these fields; the PSK is deploy-time input
    on the guest (`/etc/isle-mesh/<uci>.psk`), never a row.
    """

    @treeObjectInit
    def __init__(self, name: str = '', hardware_app: str = 'isle-relay', uci: str = 'relay',
                 vlan: int = 30, cidr: str = '10.30.0.0/24', bearer: str = 'wifi-ap',
                 ssid: str = 'isle-relay', radio: str = 'radio0', reticulum_bearer: bool = True,
                 reticulum_port: int = 4242, dhcp_start: int = 50, dhcp_limit: int = 200,
                 is_prior: bool = True, notes: str = ''):
        self.name = name
        self.hardware_app = hardware_app
        self.uci = uci
        self.vlan = vlan
        self.cidr = cidr
        self.bearer = bearer
        self.ssid = ssid
        self.radio = radio
        self.reticulum_bearer = reticulum_bearer
        self.reticulum_port = reticulum_port
        self.dhcp_start = dhcp_start
        self.dhcp_limit = dhcp_limit
        self.is_prior = is_prior
        self.notes = notes

    def uci_params(self):
        return {'uci': self.uci, 'vlan': self.vlan, 'cidr': self.cidr, 'ssid': self.ssid if self.bearer == 'wifi-ap' else '',
                'radio': self.radio, 'reticulum_port': self.reticulum_port, 'dhcp_start': self.dhcp_start, 'dhcp_limit': self.dhcp_limit}
