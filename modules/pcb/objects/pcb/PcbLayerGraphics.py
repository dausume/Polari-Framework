"""
@module pcb.objects.pcb.PcbLayerGraphics

PcbLayerGraphics — one class per file (design §7); kxc-4, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PcbLayerGraphics(treeObject):
    """What it is: THE DRAWING ON ONE LAYER of an ingested board, by item kind - silkscreen, fab, courtyard, board edge, user layers; lines, arcs, circles,
    rectangles, polygons, texts - board-level and inside footprints together: how many and their bounding box. The silkscreen / fab part of the single-
    Board view (overlap checks come later).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', layer: str = '', item: str = '', count: int = 0, bbox_json: str = '[]', notes: str = '', manager=None):
        self.name = name
        self.board = board
        self.layer = layer
        self.item = item
        self.count = count
        self.bbox_json = bbox_json
        self.notes = notes
