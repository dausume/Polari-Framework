"""
@module pcb.objects.pcb.SchematicSheet

SchematicSheet — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SchematicSheet(treeObject):
    """What it is: One SHEET of a Schematic: its path, page number, file and how many symbols it places.
    """

    @treeObjectInit
    def __init__(self, name: str = '', schematic: str = '', path: str = '', page: str = '', file: str = '', symbols: int = 0,
                 notes: str = '', manager=None):
        self.name = name  # <board>:<path>
        self.schematic = schematic
        self.path = path
        self.page = page
        self.file = file
        self.symbols = symbols
        self.notes = notes
