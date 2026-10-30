"""
@module pcb.objects.pcb.PcbPad

PcbPad — one class per file (design §7); kxc-4, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PcbPad(treeObject):
    """What it is: ONE PAD of a footprint on an ingested board - number, type (thru_hole / smd / np_thru_hole / connect), shape, size, drill, the copper and
    mask layers it is on, its net, the ERC pin type and function KiCad copied from the schematic, and where it sits on the board (the footprint frame
    rotated, as pcbnew places it). What the single-Board view draws as footprints; a foothold is a pad of a connector or test point.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', number: str = '', pad_type: str = '', shape: str = '', x_mm: float = 0.0, y_mm: float = 0.0,
                 angle: float = 0.0, side: str = 'top', size_w_mm: float = 0.0, size_h_mm: float = 0.0, drill_mm: float = 0.0, drill_oval: bool = False,
                 layers_json: str = '[]', net: str = '', pintype: str = '', pinfunction: str = '', notes: str = '', manager=None):
        self.name = name
        self.board = board
        self.ref = ref
        self.number = number
        self.pad_type = pad_type
        self.shape = shape
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.angle = angle
        self.side = side
        self.size_w_mm = size_w_mm
        self.size_h_mm = size_h_mm
        self.drill_mm = drill_mm
        self.drill_oval = drill_oval
        self.layers_json = layers_json
        self.net = net
        self.pintype = pintype
        self.pinfunction = pinfunction
        self.notes = notes
