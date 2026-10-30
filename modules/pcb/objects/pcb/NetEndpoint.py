"""
@module pcb.objects.pcb.NetEndpoint

NetEndpoint — one class per file (design §7); kxc-2, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class NetEndpoint(treeObject):
    """What it is: ONE PIN ON A SCHEMATIC NET - which placed symbol (reference + unit + sheet instance path), which pin (number and name), its ERC
    electrical type from the library symbol (input, output, bidirectional, power_in, power_out, passive, open_collector, ...), where it sits on
    its sheet, and whether a no-connect flag marks it. The type is what later slices read to know which part DRIVES a net.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', net: str = '', ref: str = '', unit: str = '', pin: str = '', pin_name: str = '',
                 pintype: str = '', instance_path: str = '', x_mm: float = 0.0, y_mm: float = 0.0, no_connect: bool = False, notes: str = '',
                 manager=None):
        self.name = name  # board:ref:pin
        self.board = board
        self.net = net  # the SchematicNet's net
        self.ref = ref
        self.unit = unit  # A / B for a multi-unit part, '' otherwise
        self.pin = pin
        self.pin_name = pin_name
        self.pintype = pintype
        self.instance_path = instance_path
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.no_connect = no_connect
        self.notes = notes
