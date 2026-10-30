"""
@module pcb.objects.pcb.PcbZone

PcbZone — one class per file (design §7); kxc-4, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PcbZone(treeObject):
    """What it is: ONE ZONE of an ingested board - a copper pour on a net, a keep-out, or a teardrop (KiCad's pad-to-track fillet) - its layers, outline
    polygon, outline area and the copper area it actually filled (the thermal view's spreading copper), its priority and thermal-relief settings.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', net: str = '', kind: str = 'copper', zone_name: str = '', layers_json: str = '[]', priority: int = 0,
                 outline_json: str = '[]', outline_area_mm2: float = 0.0, filled_area_mm2: float = 0.0, min_thickness_mm: float = 0.0, thermal_gap_mm: float
                 = 0.0, thermal_bridge_mm: float = 0.0, notes: str = '', manager=None):
        self.name = name
        self.board = board
        self.net = net
        self.kind = kind
        self.zone_name = zone_name
        self.layers_json = layers_json
        self.priority = priority
        self.outline_json = outline_json
        self.outline_area_mm2 = outline_area_mm2
        self.filled_area_mm2 = filled_area_mm2
        self.min_thickness_mm = min_thickness_mm
        self.thermal_gap_mm = thermal_gap_mm
        self.thermal_bridge_mm = thermal_bridge_mm
        self.notes = notes
