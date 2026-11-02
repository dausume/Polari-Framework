"""
BenchConditions - one class per file (design section 7); cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "Thermal System and Thermal Solution").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BenchConditions(treeObject):
    """What it is: THE CONDITIONS A BENCH SOLUTION RUNS UNDER, as one reusable row several Bench Solutions can name: the ambient temperature range, the
    supply voltage and the years of aging to cover. Air is always 'open' for now (the user, 2026-11-01: Bench Solutions are simplified open-air
    simulations that prove the electronics before the embedding process); a clip-on heat sink or a breadboard fan is a part on the bench, not a
    condition. Every check reads its conditions from here, never from a typed number of its own.
    Related concepts: `BenchSolution` (names this row), board.custom.timing_drift (the clock band at a temperature).
    """

    plain_words = ('Bench conditions are the room the bench sits in: how cold and how hot it may get, the supply voltage, and how many years '
                   'of aging to allow for. The air is always open for now.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', air: str = 'open', ambient_min_c: float = 25.0, ambient_max_c: float = 25.0,
                 supply_v: float = 5.0, aging_years: float = 0.0, notes: str = '', manager=None):
        self.name = name                    # e.g. 'room-open-air'
        self.title = title
        self.air = air                      # open (the only value for now)
        self.ambient_min_c = ambient_min_c
        self.ambient_max_c = ambient_max_c
        self.supply_v = supply_v
        self.aging_years = aging_years
        self.notes = notes
