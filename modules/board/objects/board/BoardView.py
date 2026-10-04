"""
@module board.objects.board.BoardView

BoardView — one class per file (design §7); brd-bo, THE BOARD OBJECT.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardView(treeObject):
    """What it is: One rendered (out) or ingested (in) view of a board (§2b "generate out, ingest in, both by hash"): its kind, path,
    sha256, and the board sha (the rows' canonical hash) at that moment. A refused render is a row too (refused + why).
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', kind: str = '', direction: str = 'out', path: str = '',
                 sha256: str = '', board_sha: str = '', refused: bool = False, refusal: str = '', conflicts: int = 0,
                 fields_carried: str = '', at: str = '', notes: str = '', manager=None):
        self.name = name  # '<board>:<kind>:<direction>:<sha12>'
        self.board = board
        self.kind = kind  # kicad | zephyr | esp-idf | bare-c
        self.direction = direction  # out | in
        self.path = path
        self.sha256 = sha256  # of the view file(s)
        self.board_sha = board_sha  # the rows at that moment
        self.refused = refused
        self.refusal = refusal
        self.conflicts = conflicts  # in: the BoardConflict rows it wrote
        self.fields_carried = fields_carried  # which BoardPin fields this kind carries
        self.at = at
        self.notes = notes
