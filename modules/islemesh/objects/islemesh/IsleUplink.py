"""
@module islemesh.objects.islemesh.IsleUplink

Row class IsleUplink of the islemesh module — one class per file (design §7), split
from islemesh_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IsleUplink(treeObject):
    """One isle uplink on one device (handoff §10: the uplink is an
    abstraction — cable or wifi). Link quality feeds placement."""

    @treeObjectInit
    def __init__(
        self,
        # Unique key: '<device>@<interface>' ('pol-core@eno1').
        name: str = '',
        device_name: str = '',
        interface: str = '',
        # UPLINK_KINDS entry.
        kind: str = 'ethernet',
        link_up: bool = False,
        # Link quality — 0.0 = unmeasured (never a fake number).
        latency_ms: float = 0.0,
        jitter_ms: float = 0.0,
        loss_pct: float = 0.0,
        measured_at: str = '',
        is_mock: bool = False,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.device_name = device_name
        self.interface = interface
        self.kind = kind
        self.link_up = link_up
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.loss_pct = loss_pct
        self.measured_at = measured_at
        self.is_mock = is_mock
        self.notes = notes
