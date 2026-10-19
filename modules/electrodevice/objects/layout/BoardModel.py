"""
@module electrodevice.objects.layout.BoardModel

Row class BoardModel of the electrodevice module (lay-0) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardModel(treeObject):
    """What it is: the GEOMETRY of one kind of board, shared by every physical board of that kind (a `BenchBoard` is one physical board of a model).
    kind `breadboard`: a solderless breadboard — `rows` numbered strips, each split by the centre trench into holes a-e (left) and f-j (right) that are
    joined across the strip, plus four power rails (a top and a bottom pair, `+` and `-`) of `rail_holes` holes each. The tie-point count is DERIVED
    (rows x holes_per_side x 2 + 4 x rail_holes) and must equal `nominal_ties` (400 half, 830 full: the common industry layout; no datasheet read).
    kind `devboard`: a development board; its header pins are NOT stored here, they are the `BoardPin` rows (and the connector power labels) of
    `board_definition`. kinds `protoboard` and `pcb` are RESERVED: they have no geometry yet (`status` says so) and nothing is built for them.
    Related concepts: `BenchBoard` (a physical board of this model), `ComponentPlacement` / `BoardJumper` (what is plugged into it), the pin view (`BoardPin`).
    """

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = 'breadboard', size: str = '', rows: int = 0, holes_per_side: int = 5,
                 rail_holes: int = 0, pitch_mm: float = 2.54, nominal_ties: int = 0, board_definition: str = '',
                 status: str = 'built', source: str = '', description: str = '', manager=None):
        self.name = name
        self.kind = kind                      # breadboard | devboard | protoboard (reserved) | pcb (reserved)
        self.size = size                      # half | full (breadboards)
        self.rows = rows                      # numbered strips (30 half, 63 full)
        self.holes_per_side = holes_per_side  # a-e left of the trench, f-j right: 5 each
        self.rail_holes = rail_holes          # holes in EACH of the four power rails (25 half, 50 full)
        self.pitch_mm = pitch_mm              # hole pitch: 2.54 mm = 0.1 in, the standard grid of DIP parts
        self.nominal_ties = nominal_ties      # the sold tie-point count the geometry must reproduce (400 | 830)
        self.board_definition = board_definition   # devboard: the board whose BoardPin rows are the header pins
        self.status = status                  # built | reserved (no geometry yet)
        self.source = source                  # where the numbers come from, in words
        self.description = description
