"""
@module vpn.objects.vpn.VpnProposal

Row class VpnProposal of the vpn module — one class per file (design §7), split
from vpn_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class VpnProposal(treeObject):
    """The inbox (D9): Polari PROPOSES a change; a local operator on
    the isle applies it (`isle vpn apply <id>`). A proposal never
    mutates the mirror rows — only the isle's next push does, and it
    flips this row's status with `applied_by` / `applied_at` set."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: the proposal id ('vp-<12 hex>').
        name: str = '',
        # The isle expected to apply it.
        device_name: str = '',
        # PROPOSAL_KINDS entry.
        kind: str = 'peer',
        provider: str = 'link',
        # The app kind the proposal is for (a guide id).
        app_kind: str = '',
        label: str = '',
        network_name: str = '',
        # The proposed change, validated at POST (no key material).
        payload_json: str = '{}',
        # PROPOSAL_STATUSES entry.
        status: str = 'proposed',
        proposed_by: str = '',
        proposed_at: str = '',
        # Set ONLY by the isle's push when an operator applied it.
        applied_by: str = '',
        applied_at: str = '',
        note: str = '',
        # Set by the no-code GenerateEvent node when a form made it.
        generated_by: str = '',
        is_mock: bool = False,
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.kind = kind
        self.provider = provider
        self.app_kind = app_kind
        self.label = label
        self.network_name = network_name
        self.payload_json = payload_json
        self.status = status
        self.proposed_by = proposed_by
        self.proposed_at = proposed_at
        self.applied_by = applied_by
        self.applied_at = applied_at
        self.note = note
        self.generated_by = generated_by
        self.is_mock = is_mock
