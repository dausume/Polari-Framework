"""
@module electrodevice.objects.layout.BreadboardLayout

Row class BreadboardLayout of the electrodevice module (D-bob-3 2026-10-30) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BreadboardLayout(treeObject):
    """What it is: THE STRIPS AND RAILS OF ONE BREADBOARD MODEL - the definition a breadboard is known by (definition kind geometry). `rows` numbered strips,
    each split by the centre trench into `holes_per_side` holes left (a-e) and right (f-j); `rails` power rails of `rail_holes` holes each, at `pitch_mm`.
    The tie-point count is DERIVED (rows x holes_per_side x 2 + rails x rail_holes) and must equal the sold count `tie_points` (400 half, 830 full);
    -1 anywhere = undetermined (the starter kit's breadboard until someone counts it). `name` = `board_model` (one layout per model).
    Related concepts: `BoardModel` (the model this lays out), `BoardOutline` (its cited size), the hole grammar (electrodevice.custom.board_family).
    """

    plain_words = 'How a breadboard is laid out: how many numbered strips, how many holes on each side of the trench, and how many holes along each power rail.'

    SIZES = ('half', 'full', 'mini', 'bus-strip', 'unverified')

    @treeObjectInit
    def __init__(self, name: str = '', board_model: str = '', size: str = 'unverified', rows: int = -1, holes_per_side: int = 5, rails: int = -1,
                 rail_holes: int = -1, pitch_mm: float = 2.54, tie_points: int = -1, basis: str = '', manager=None):
        self.name = name                      # = board_model
        self.board_model = board_model        # the BoardModel this lays out
        self.size = size                      # half | full | mini | bus-strip | unverified
        self.rows = rows                      # numbered strips (30 half, 63 full); -1 = undetermined
        self.holes_per_side = holes_per_side  # a-e left of the trench, f-j right: 5 each
        self.rails = rails                    # power rails (4 = a top and a bottom pair; 0 = none); -1 = undetermined
        self.rail_holes = rail_holes          # holes in EACH rail (25 half, 50 full); -1 = undetermined
        self.pitch_mm = pitch_mm              # 2.54 mm = 0.1 in, the standard grid of DIP parts
        self.tie_points = tie_points          # the SOLD count the derived count must reproduce; -1 = undetermined
        self.basis = basis                    # where the counts come from, in words
