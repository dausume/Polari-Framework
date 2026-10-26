"""
@module board.objects.board.Bench

Bench - one class per file (design section 7). bench-0 (MISSION_GENERIC_PLAN.md section 13.1, his asks 2026-10-24: "a dev/eval-board selection
component for adding dev and eval boards to a Bench" and "a Breadboard Selection Component for selecting and adding Breadboards to a bench").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Bench(treeObject):
    """What it is: ONE BENCH - the dev and eval boards and the breadboards a person has on the table, as ROWS a person adds and removes
    (the two selection panels on /display/bench). The Mission search's Inventory step reads the Bench as "what is on hand". Each board
    entry carries, beside the board, how it can be TESTED - simulated with real pins, simulated with stub pins, or HARDWARE ONLY (his rule:
    "If something can only be hardware tested that needs to be outlined very clearly") - worked out from the chips-and-levels ladder when the
    entry is added and again when it is listed. A seeded bench is converged only in its shape: what a person added is never overwritten.
    Related concepts: `ChipLadderEntry` (the chips and their emulators), `BreadboardModel` (the breadboards one can add), `KitPart` (the
    parts in the kit), `BoardInstance` (one physical board the host has seen on USB).
    """

    plain_words = ('The boards and breadboards on one bench, added by a person from two selection lists; each board says whether it can be '
                   'simulated or can only be tested on hardware.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', boards_json: str = '[]', breadboards_json: str = '[]', notes: str = '', source: str = '',
                 instruments_json: str = '[]', manager=None):
        self.name = name                        # kebab-case, e.g. 'home-bench'
        self.title = title
        self.boards_json = boards_json          # [{board, title, label, chip, family, section, testing, added, note}] - board = the ladder's board key
        self.breadboards_json = breadboards_json  # [{model, title, count, note}] - model = a BreadboardModel name
        self.notes = notes
        self.source = source
        self.instruments_json = instruments_json  # osc-0: [{model, count, note}] - model = an instruments.Instrument name; read and written ONLY by instruments.custom.catalog
