"""
@module board.objects.board.BoardConflict

BoardConflict — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardConflict(treeObject):
    """What it is: An ingested view disagreed with the rows (§2b): one row per (pin, field) — shown on /display/boards, NEVER
    auto-resolved (the rows stay as they were; a person edits the rows or the source of the view).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', view: str = '', view_kind: str = '', pin: str = '',
                 field: str = '', rows_value: str = '', view_value: str = '', state: str = 'open',
                 detected_at: str = '', notes: str = '', manager=None):
        self.name = name  # '<view>:<pin>:<field>'
        self.board = board
        self.view = view  # the BoardView name (direction in)
        self.view_kind = view_kind  # kicad | zephyr | esp-idf | bare-c
        self.pin = pin  # the canonical pin (or the view's own name for it)
        self.field = field
        self.rows_value = rows_value
        self.view_value = view_value
        self.state = state  # open | resolved (by a person)
        self.detected_at = detected_at
        self.notes = notes
