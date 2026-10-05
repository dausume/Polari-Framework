"""
@module hwnocode.objects.hwnocode.SimRigTempDerived

SimRigTempDerived — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SimRigTempDerived(treeObject):
    """What it is: the small DERIVED class the backend half of `uno-temp-split` writes (HARDWARE_NOCODE_PLAN.md §4 h): per SimRigState
    row, the latest moving average of `temp_c` and the boolean `over_threshold` (average > `threshold_c`), decided by the engine's
    ConditionalChain and persisted by its StateChangeCommit — existing node kinds, no new engine arm. `samples` counts the frames
    seen (the ring cursor of `SimRigTempSample`).
    Related concepts: `SimRigTempSample`, grpcbridge `SimRigState`, `HardwareSolution` uno-temp-split.
    """

    plain_words = 'The derived temperature state is the server\'s running view of a board\'s temperature: its smoothed value and whether it is above the limit.'

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', temp_avg: float = 0.0, over_threshold: bool = False,
                 threshold_c: float = 25.0, window: int = 5, samples: int = 0, last_uptime_ms: int = 0, last_temp_c: float = 0.0,
                 updated_at: str = '', manager=None):
        self.name = name                # = the SimRigState row's name (uno-digital-twin)
        self.solution = solution
        self.temp_avg = temp_avg
        self.over_threshold = over_threshold
        self.threshold_c = threshold_c
        self.window = window
        self.samples = samples
        self.last_uptime_ms = last_uptime_ms
        self.last_temp_c = last_temp_c
        self.updated_at = updated_at
