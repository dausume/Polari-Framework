"""
@module electrodevice.objects.layout.BoardOutline

Row class BoardOutline of the electrodevice module (D-bob-3 2026-10-30) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardOutline(treeObject):
    """What it is: A CITED PHYSICAL OUTLINE OF ONE BOARD MODEL - width x height in mm as a vendor states it, and whether the drawing derived from the model's
    own definition fits it (`drawable`). Only a STATED outline is a row: a breadboard with no row has its outline derived from its `BreadboardLayout` on
    read (board.custom.pv_shapes.breadboard_geometry) and is drawable. When the derived drawing disagrees with the stated outline by more than the
    tolerance, `drawable` is False and `basis` says by how much - the board is listed but never drawn or placed on with guessed margins.
    `name` = `board_model` (one outline per model).
    Related concepts: `BoardModel`, `BreadboardLayout` (what the derived drawing comes from).
    """

    plain_words = 'How big a board really is, as its maker states it, and whether our drawing of it matches closely enough to place parts on.'

    @treeObjectInit
    def __init__(self, name: str = '', board_model: str = '', width_mm: float = -1.0, height_mm: float = -1.0, drawable: bool = False,
                 basis: str = '', manager=None):
        self.name = name                # = board_model
        self.board_model = board_model  # the BoardModel this outlines
        self.width_mm = width_mm        # stated; -1 = undetermined
        self.height_mm = height_mm
        self.drawable = drawable        # the derived drawing fits the stated outline within tolerance
        self.basis = basis              # the citation, and the comparison with the derived drawing
