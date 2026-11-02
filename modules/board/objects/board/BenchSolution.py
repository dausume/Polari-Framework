"""
BenchSolution - one class per file (design section 7); cfg-0 (AI-Notes/plans/CATOM_CONFIG_PLAN.md "Systems and Solutions").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class BenchSolution(treeObject):
    """What it is: ONE BENCH SOLUTION - everything on one bench bound as a whole and simulated as a whole. The user's rule (2026-11-01): a System is a
    baseline template with choices still open; a Solution is the finalized, specific result. So this row holds NO facts of its own beyond its name: it
    REFERENCES the Bench (what is on the table), the Hardware Solution, the Firmware Solution, the Thermal Solution (none exist yet: '' until the
    thermal phase) and the BenchConditions it runs under (always open air for now). Every catom configuration's verdict is worked out in one Bench
    Solution, because only here are the peers, the boards and the conditions bound together.
    Related concepts: `Bench`, `BenchConditions`, hwnocode `HardwareSolution`, cmod `FirmwareSolution`, cmod `ConfigOptionGrade` (judged here).
    """

    plain_words = ('A bench solution is one finished setup on a bench - these boards, this firmware, these conditions - tied together so the whole '
                   'thing can be simulated at once.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', bench: str = '', hardware_solution: str = '', firmware_solution: str = '',
                 thermal_solution: str = '', conditions: str = '', notes: str = '', manager=None):
        self.name = name                            # kebab-case, e.g. 'uno-light-on-home-bench'
        self.title = title
        self.bench = bench                          # a Bench name
        self.hardware_solution = hardware_solution  # a HardwareSolution name
        self.firmware_solution = firmware_solution  # a FirmwareSolution name
        self.thermal_solution = thermal_solution    # '' until the Thermal Solution exists (D-cfg-9)
        self.conditions = conditions                # a BenchConditions name
        self.notes = notes
