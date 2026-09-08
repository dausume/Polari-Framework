"""
@module isle_guestnet.objects.guestnet.GuestNetworkDefinition

GuestNetworkDefinition — one isolated guest network an isle-guestnet guest serves.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class GuestNetworkDefinition(treeObject):
    """What it is: a guest-only network: its own SSID, VLAN and DHCP pool on
    an isle-guestnet guest, REJECTING forwarding into the isle, client
    isolation on, internet via the WAN zone; the only isle hosts a guest may
    reach are the `GuestNetworkExposure` rows that name this network.
    Related concepts: `HardwareAppDefinition` (`hardware_app` = the guest),
    `GuestNetworkExposure`, `GuestNetworkState`, the VPN arc's rule that
    every exposure is a ledger row.
    How it is realised: `hardwareapps.custom.uci_profiles` profile `guestnet`
    renders the UCI script; the PSK is deploy-time input on the guest.
    """

    @treeObjectInit
    def __init__(self, name: str = '', hardware_app: str = 'isle-guestnet', uci: str = 'guest', vlan: int = 20,
                 cidr: str = '10.20.0.0/24', ssid: str = 'isle-guest', radio: str = 'radio0', client_isolation: bool = True,
                 internet: bool = True, dhcp_start: int = 50, dhcp_limit: int = 200, dhcp_leasetime: str = '4h',
                 is_prior: bool = True, notes: str = ''):
        self.name = name
        self.hardware_app = hardware_app
        self.uci = uci
        self.vlan = vlan
        self.cidr = cidr
        self.ssid = ssid
        self.radio = radio
        self.client_isolation = client_isolation
        self.internet = internet
        self.dhcp_start = dhcp_start
        self.dhcp_limit = dhcp_limit
        self.dhcp_leasetime = dhcp_leasetime
        self.is_prior = is_prior
        self.notes = notes

    def uci_params(self, allow_hosts=()):
        return {'uci': self.uci, 'vlan': self.vlan, 'cidr': self.cidr, 'ssid': self.ssid, 'radio': self.radio,
                'dhcp_start': self.dhcp_start, 'dhcp_limit': self.dhcp_limit, 'dhcp_leasetime': self.dhcp_leasetime,
                'allow_hosts': list(allow_hosts)}
