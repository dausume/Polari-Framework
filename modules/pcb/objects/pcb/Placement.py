"""
@module pcb.objects.pcb.Placement

Placement — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Placement(treeObject):
    """What it is: Where a footprint sits (plan §2): reference → x, y (mm), rotation, side — INGESTED from the `.kicad_pcb`
    a person saved, never authored by Polari (D-pcb-2: a person places and routes).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', value: str = '', footprint: str = '', part: str = '',
                 x_mm: float = 0.0, y_mm: float = 0.0, rotation: float = 0.0, side: str = '', attr: str = '', pads: int = 0,
                 notes: str = '', manager=None):
        self.name = name  # <board>:<ref>
        self.board = board
        self.ref = ref
        self.value = value
        self.footprint = footprint  # Footprint row
        self.part = part  # Part row
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.rotation = rotation  # degrees
        self.side = side  # front | back
        self.attr = attr  # through_hole | smd | …
        self.pads = pads
        self.notes = notes
