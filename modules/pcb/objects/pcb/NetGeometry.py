"""
@module pcb.objects.pcb.NetGeometry

NetGeometry — one class per file (design §7); kxc-4, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class NetGeometry(treeObject):
    """What it is: THE COPPER OF ONE NET on an ingested board - its track segments [x1, y1, x2, y2, width, layer], arcs [start, mid, end, width, layer] and
    vias [x, y, size, drill, layers] as lists (one row per net, D-kxc-2 recommended: a routed board has tens of thousands of segments), its total routed
    length and the layers it uses. The 'circuits in the layers' of the single-Board view: where a net's current flows.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', net: str = '', segments_json: str = '[]', arcs_json: str = '[]', vias_json: str = '[]', segments: int = 0,
                 arcs: int = 0, vias: int = 0, length_mm: float = 0.0, layers_json: str = '[]', notes: str = '', manager=None):
        self.name = name
        self.board = board
        self.net = net
        self.segments_json = segments_json
        self.arcs_json = arcs_json
        self.vias_json = vias_json
        self.segments = segments
        self.arcs = arcs
        self.vias = vias
        self.length_mm = length_mm
        self.layers_json = layers_json
        self.notes = notes
