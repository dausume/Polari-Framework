"""
@module board.objects.board.BoardSimCost

BoardSimCost — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BoardSimCost(treeObject):
    """What it is: The MEASURED cost of one twin (plan §8a): rows per simulated device, bytes of state, cycles per
    second on a device class. One row per twin is the yardstick before another device is admitted to simulation.
    No row is seeded: a cost exists only once measured (brd-3).
    Related concepts: `BoardDefinition.twin`, resources.custom.cost_meter.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', twin: str = '', object_count: int = 0, state_bytes: int = 0,
                 cycles_per_s: float = 0.0, host_class: str = '', measured_at: str = '', method: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.board = board
        self.twin = twin
        self.object_count = object_count
        self.state_bytes = state_bytes
        self.cycles_per_s = cycles_per_s
        self.host_class = host_class
        self.measured_at = measured_at
        self.method = method
        self.notes = notes
