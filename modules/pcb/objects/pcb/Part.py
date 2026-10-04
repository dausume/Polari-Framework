"""
@module pcb.objects.pcb.Part

Part — one class per file (design §7); pcb-0, the PCB arc (AI-Notes/plans/PCB_FROM_SCRATCH_PLAN.md §2).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Part(treeObject):
    """What it is: One PART of a board — a BOM line (plan §2): what is bought and soldered. Value, manufacturer + MPN where
    a source names them, package, mount (tht | smd), the KiCad `symbol` and `footprint` it uses (Symbol / Footprint rows),
    the reference designators that use it, and its provenance (the register row / a BoardDefinition for modules and boards,
    a kit part, or the ingested project). Lifecycle (active / NRND / EOL) only as cited — '' means no source says.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', value: str = '', manufacturer: str = '', mpn: str = '',
                 package: str = '', mount: str = '', symbol: str = '', footprint: str = '', refs_json: str = '[]', qty: int = 0,
                 device_definition: str = '', lifecycle: str = '', lifecycle_source: str = '', datasheet: str = '',
                 provenance: str = '', licence_notes: str = '', undetermined: str = '', notes: str = '', manager=None):
        self.name = name  # '<board>:<group key>'
        self.board = board  # the PcbBoard or Schematic board name
        self.value = value  # as on the symbol (1.5K, 10uF, TMP36GT9Z)
        self.manufacturer = manufacturer  # '' = no source names one
        self.mpn = mpn  # '' = no source names one
        self.package = package  # TO-92, DIP-28, Radial D10 …
        self.mount = mount  # tht | smd | '' (from the footprint's attr)
        self.symbol = symbol  # Symbol row name (lib:symbol)
        self.footprint = footprint  # Footprint row name (lib:footprint)
        self.refs_json = refs_json  # the reference designators, sorted
        self.qty = qty  # len(refs)
        self.device_definition = device_definition  # a BoardDefinition name for a module/board part
        self.lifecycle = lifecycle  # active | nrnd | eol | '' (only as cited)
        self.lifecycle_source = lifecycle_source
        self.datasheet = datasheet  # document + revision, or a DatasheetFact name
        self.provenance = provenance  # ingested:<file sha> | register:<row> | kit:<project> | ours
        self.licence_notes = licence_notes  # the design files' licence and its source (a caveat when it rests on a statement)
        self.undetermined = undetermined  # what no source settled
        self.notes = notes
