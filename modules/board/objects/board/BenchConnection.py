"""
BenchConnection - one class per file (design section 7); bob-2 (AI-Notes/plans/BENCH_BOARDS_PLAN.md section 4).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BenchConnection(treeObject):
    """What it is: ONE CONNECTION BETWEEN TWO FOOTHOLDS ON A BENCH - a wire or jumper from a dev board's header pin to a breadboard hole, a breadboard hole to
    a PCB connector pad, or MATED (a header pin pushed into a breadboard hole, a PCB connector onto a header). His ruling 2026-10-30: dev boards,
    breadboards and PCBs are equally Boards on the Bench, so a connection names a Board on the Bench (its id from board.custom.bench_boards) and a
    foothold on it - never a chip pin or a net, which belong to the board's definition. The bench's nets (board.custom.bench_nets) are the boards'
    own joins plus these rows; the electrical findings (two rails joined, a rail to ground, 5 V reaching a 3.3 V pin) are read off them.
    Related concepts: `BoardFoothold` (the two ends), `BenchBoard` / `Bench` (the boards), `BoardJumper` (the older breadboard-only jumper of a layout build).
    """

    @treeObjectInit
    def __init__(self, name: str = '', bench: str = '', from_board: str = '', from_foothold: str = '', to_board: str = '', to_foothold: str = '',
                 kind: str = 'wire', colour: str = '', label: str = '', notes: str = '', manager=None):
        self.name = name  # '<bench>:<from_board>:<from_foothold>-><to_board>:<to_foothold>'
        self.bench = bench
        self.from_board = from_board  # a Board-on-the-Bench id (boards_json#1, breadboards_json#2.1, a BenchBoard name)
        self.from_foothold = from_foothold  # J1:9, r17a, DIGITAL_L:7, P4:1
        self.to_board = to_board
        self.to_foothold = to_foothold
        self.kind = kind  # wire | jumper | mated
        self.colour = colour  # a wire colour name (electrodevice WIRE_COLOURS) or ''
        self.label = label
        self.notes = notes
