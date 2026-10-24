"""
@module board.objects.board.BreadboardModel

BreadboardModel - one class per file (design section 7). bench-0 (MISSION_GENERIC_PLAN.md section 13.1): a breadboard one can add to a Bench.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BreadboardModel(treeObject):
    """What it is: ONE KIND OF BREADBOARD - its tie-point count, its terminal-strip rows, its power-rail holes, and whether the layout engine
    knows its geometry (DERIVED from the row and hole counts at the 2.54 mm pitch by `board.custom.pv_shapes.breadboard_geometry`, or
    `unverified` when only a vendor label is known - never a guessed dimension). The Breadboard selection panel lists these rows; the
    Mission search's Combine step places parts on the ones a Bench holds.
    Related concepts: `Bench` (which breadboards are on the table), `KitPart` (the kit's own breadboard), the layout engine
    (`electrodevice.custom.layout_core`).
    """

    plain_words = 'One kind of breadboard: how many tie points and rows it has, and whether its geometry is known well enough to draw and place on.'

    KINDS = ('half', 'full', 'mini', 'bus-strip', 'unverified')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', vendor: str = '', part_number: str = '', kind: str = 'unverified', tie_points: int = -1,
                 rows: int = -1, rail_holes: int = -1, rails: int = -1, width_mm: float = -1.0, height_mm: float = -1.0, geometry_known: bool = False,
                 basis: str = '', notes: str = '', manager=None):
        self.name = name                    # kebab-case, e.g. 'half-400', 'bud-bb-32650-w'
        self.title = title
        self.vendor = vendor
        self.part_number = part_number
        self.kind = kind                    # half | full | mini | bus-strip | unverified
        self.tie_points = tie_points        # -1 = undetermined
        self.rows = rows                    # terminal-strip rows (a-e / f-j columns per row); -1 = undetermined
        self.rail_holes = rail_holes        # holes per power rail; 0 = no rails; -1 = undetermined
        self.rails = rails                  # number of power rails; -1 = undetermined
        self.width_mm = width_mm            # DERIVED from the counts at 2.54 mm when geometry_known; -1 otherwise
        self.height_mm = height_mm
        self.geometry_known = geometry_known
        self.basis = basis                  # where the numbers come from
        self.notes = notes
