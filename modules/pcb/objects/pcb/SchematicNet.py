"""
@module pcb.objects.pcb.SchematicNet

SchematicNet — one class per file (design §7); kxc-2, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SchematicNet(treeObject):
    """What it is: ONE ELECTRICAL NET of a schematic, worked out by Polari from the file itself (pins, wires, junctions, labels, power symbols, the
    sheet hierarchy - pcb.custom.kicad_connect), never copied from KiCad's netlist: KiCad's own export is the cross-check (`kicad_check`). Its
    pins are NetEndpoint rows. `scope` global (a power symbol / global label names it), sheet (a local or hierarchical label, named with its sheet
    path), unnamed (named the way KiCad names it, Net-(R1-Pad2)). `aliases_json` = the other names on the same net.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', net: str = '', scope: str = '', endpoints: int = 0, aliases_json: str = '[]',
                 pintypes_json: str = '{}', kicad_check: str = '', notes: str = '', manager=None):
        self.name = name  # board:net
        self.board = board
        self.net = net
        self.scope = scope  # global | sheet | unnamed
        self.endpoints = endpoints
        self.aliases_json = aliases_json
        self.pintypes_json = pintypes_json  # {pintype: count} - the ERC types on the net (power_in, output, passive ...)
        self.kicad_check = kicad_check  # '' | same | differs: ... (when KiCad's own netlist was compared)
        self.notes = notes
