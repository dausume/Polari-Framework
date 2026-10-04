"""
@module pcb.objects.pcb.Footprint

Footprint — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Footprint(treeObject):
    """What it is: A FOOTPRINT by KiCad library reference (plan §2): `Package_TO_SOT_THT:TO-92_Inline` — library nickname +
    name, source (kicad-official | project | ours), the library's version and the footprint FILE's sha256, its licence
    (official: CC-BY-SA-4.0 + the design exception — our boards and Gerbers are free of the share-alike, the libraries
    themselves stay CC-BY-SA), pad count and mount.
    """

    @treeObjectInit
    def __init__(self, name: str = '', lib: str = '', footprint: str = '', source: str = '', lib_version: str = '',
                 lib_sha256: str = '', licence: str = '', pad_count: int = 0, mount: str = '', description: str = '',
                 notes: str = '', manager=None):
        self.name = name  # lib:footprint
        self.lib = lib  # library nickname
        self.footprint = footprint  # footprint name
        self.source = source  # kicad-official | project | ours
        self.lib_version = lib_version  # kicad-footprints 9.0.2-1 | the project's .pretty
        self.lib_sha256 = lib_sha256  # sha256 of the .kicad_mod file (or the board file it is embedded in)
        self.licence = licence
        self.pad_count = pad_count
        self.mount = mount  # tht | smd (attr)
        self.description = description
        self.notes = notes
