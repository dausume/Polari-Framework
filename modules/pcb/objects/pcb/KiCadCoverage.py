"""
@module pcb.objects.pcb.KiCadCoverage

KiCadCoverage — one class per file (design §7); kxc-1, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class KiCadCoverage(treeObject):
    """What it is: WHAT THE INGEST UNDERSTOOD of one kind of element in one KiCad file — e.g. the 37 `symbol` elements of
    complex_hierarchy.kicad_sch became SchematicSymbol rows; its 120 `wire` elements are only counted until kxc-2 reads the
    connectivity. Every top-level element kind of every schematic and board file gets a row, so nothing is dropped silently:
    `handling` is typed (rows of `polari_class` hold it), summarised (rows hold an aggregate, e.g. Route per net), counted (the
    number only) or preserved (only the artifact's bytes keep it). `next_slice` names the kxc slice that types it.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', file: str = '', element: str = '', count: int = 0, handling: str = '',
                 polari_class: str = '', next_slice: str = '', notes: str = '', manager=None):
        self.name = name  # board:file:element
        self.board = board
        self.file = file  # the artifact path
        self.element = element  # the s-expression head (symbol, wire, footprint, segment, zone ...)
        self.count = count
        self.handling = handling  # typed | summarised | counted | preserved
        self.polari_class = polari_class  # the row class holding it ('' when counted / preserved)
        self.next_slice = next_slice  # kxc-2 .. kxc-6, '' when typed
        self.notes = notes
