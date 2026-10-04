"""
@module pcb.objects.pcb.Route

Route — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Route(treeObject):
    """What it is: The copper of ONE net, SUMMARISED (plan §2 `Track`/`Via`): segment count, vias, total length, the widths
    and layers used — ingested from the `.kicad_pcb`, never authored by Polari; every segment is not a row.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', net: str = '', segments: int = 0, vias: int = 0, length_mm: float = 0.0,
                 min_width_mm: float = 0.0, widths_json: str = '[]', layers_json: str = '[]', pads: int = 0, notes: str = '',
                 manager=None):
        self.name = name  # <board>:<net>
        self.board = board
        self.net = net
        self.segments = segments
        self.vias = vias
        self.length_mm = length_mm
        self.min_width_mm = min_width_mm
        self.widths_json = widths_json  # distinct widths (mm)
        self.layers_json = layers_json
        self.pads = pads  # pads on the net
        self.notes = notes
