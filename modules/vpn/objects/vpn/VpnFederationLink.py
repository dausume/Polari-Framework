"""
@module vpn.objects.vpn.VpnFederationLink

Row class VpnFederationLink of the vpn module — one class per file (design §7), split
from vpn_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
