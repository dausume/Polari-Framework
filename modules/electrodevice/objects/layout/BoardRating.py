"""
@module electrodevice.objects.layout.BoardRating

Row class BoardRating of the electrodevice module (D-bob-3 2026-10-30) — one class per file (design §7). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardRating(treeObject):
    """What it is: THE VENDOR-RATED LIMITS OF ONE BOARD MODEL'S CONTACTS - the maximum rail voltage and current its maker rates it for, with the document
    that says so. -1 = not rated by any source read (never a typical value). A model with no row has no rating cited; a rail-less model says n/a.
    The bench reads it as the drive limit of a breadboard's tie points (board.custom.footholds.geometry). `name` = `board_model`.
    Related concepts: `BoardModel`, `BoardFoothold` (source_ma / sink_ma of a tie point).
    """

    plain_words = 'The most voltage and current a board\'s contacts are rated for by its maker - or that no rating is published.'

    @treeObjectInit
    def __init__(self, name: str = '', board_model: str = '', rail_voltage_max_v: float = -1.0, rail_current_max_a: float = -1.0, basis: str = '',
                 manager=None):
        self.name = name                              # = board_model
        self.board_model = board_model                # the BoardModel this rates
        self.rail_voltage_max_v = rail_voltage_max_v  # vendor-RATED maximum (V); -1 = not determined
        self.rail_current_max_a = rail_current_max_a  # vendor-RATED maximum (A); -1 = not determined
        self.basis = basis                            # the document that states it, or 'unverified (...)' / 'n/a (...)'
