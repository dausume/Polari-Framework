"""
@module zones.objects.zone.ZoneEstimateRecord

Row class ZoneEstimateRecord of the zones module — one class per file (design §7), split
from zone_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ZoneEstimateRecord(treeObject):
    """A persisted estimate verdict (area/volume + evidence)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        zone_name: str = '',
        # 'prism' | 'hull' | 'planar-triangle' | 'footprint-only'.
        model: str = '',
        ground_area_m2: float = 0.0,
        height_m: float = 0.0,
        volume_m3: float = 0.0,
        calibrated: bool = False,
        report_json: str = '{}',
        computed_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.zone_name = zone_name
        self.model = model
        self.ground_area_m2 = ground_area_m2
        self.height_m = height_m
        self.volume_m3 = volume_m3
        self.calibrated = calibrated
        self.report_json = report_json
        self.computed_at = computed_at
        self.notes = notes
