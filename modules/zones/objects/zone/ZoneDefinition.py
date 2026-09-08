"""
@module zones.objects.zone.ZoneDefinition

Row class ZoneDefinition of the zones module — one class per file (design §7), split
from zone_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ZoneDefinition(treeObject):
    """One captured 3D zone."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # Optional site membership + room label ('kitchen', 'garage').
        site_name: str = '',
        room_label: str = '',
        # ZONE_ROLES entry: 'room' = the containing space, 'selection'
        # = the packed sub-area.
        zone_role: str = 'selection',
        # For selections: which room zone contains this one.
        room_zone_name: str = '',
        # Selections are TIED to a specific simulation (Dustin: zones
        # do not stand on their own); rooms leave this '' — captured
        # reality is shared between simulations.
        simulation_ref: str = '',
        # CAPTURE_MODES entry.
        capture_mode: str = 'planar',
        capture_kind: str = 'desktop-authored',  # | 'ar-headset'
        # Which WebXR reference space captured it ('local-floor' |
        # 'unbounded' | '' for desktop) — accuracy evidence.
        reference_space: str = '',
        # What the zone-local origin anchors to in the real room.
        origin_note: str = '',
        # Calibration factor (known_length / measured_length).
        scale_correction: float = 1.0,
        status: str = 'capturing',
        captured_by: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.site_name = site_name
        self.room_label = room_label
        self.zone_role = zone_role
        self.room_zone_name = room_zone_name
        self.simulation_ref = simulation_ref
        self.capture_mode = capture_mode
        self.capture_kind = capture_kind
        self.reference_space = reference_space
        self.origin_note = origin_note
        self.scale_correction = scale_correction
        self.status = status
        self.captured_by = captured_by
        self.notes = notes
