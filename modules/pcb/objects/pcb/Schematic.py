"""
@module pcb.objects.pcb.Schematic

Schematic — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Schematic(treeObject):
    """What it is: One SCHEMATIC (plan §2): the `.kicad_sch` file by sha256, its KiCad format version, the counts of what it
    holds (symbols, power symbols, wires, labels, junctions, no-connects), the board it belongs to and whether Polari WROTE
    it (D-pcb-1: rendered from rows) or INGESTED it.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', file: str = '', sha256: str = '', format_version: str = '',
                 generator: str = '', title: str = '', description: str = '', sheets: int = 0, symbols: int = 0, power_symbols: int = 0, wires: int = 0,
                 labels: int = 0, junctions: int = 0, no_connects: int = 0, origin: str = '', licence_notes: str = '',
                 notes: str = '', manager=None):
        self.name = name  # <board>
        self.board = board
        self.file = file
        self.sha256 = sha256
        self.format_version = format_version  # the (version …) of the file
        self.generator = generator
        self.title = title
        # see PcbBoard.description — same provenance rule (title block prose, else SOURCE.json; never invented).
        self.description = description
        self.sheets = sheets
        self.symbols = symbols  # placed symbols incl. power
        self.power_symbols = power_symbols
        self.wires = wires
        self.labels = labels
        self.junctions = junctions
        self.no_connects = no_connects
        self.origin = origin  # ingested | rendered
        self.licence_notes = licence_notes
        self.notes = notes
