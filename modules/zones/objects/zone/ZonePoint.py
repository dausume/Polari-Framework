"""
@module zones.objects.zone.ZonePoint

Row class ZonePoint of the zones module — one class per file (design §7), split
from zone_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ZonePoint(treeObject):
    """One placed point, meters in zone-local space (y up)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        zone_name: str = '',
        index: int = 0,
        # POINT_KINDS entry.
        kind: str = 'ground',
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        # 'tracked' (live XR pose) | 'estimated' (desktop-authored).
        confidence: str = 'estimated',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.zone_name = zone_name
        self.index = index
        self.kind = kind
        self.x = x
        self.y = y
        self.z = z
        self.confidence = confidence
        self.notes = notes
