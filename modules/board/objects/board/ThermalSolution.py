"""
ThermalSolution - one class per file (design section 7); bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5, "solution").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ThermalSolution(treeObject):
    """What it is: THE THERMAL CHOICES MADE for one bench: which `ThermalSystem` it follows and which `ThermalMitigation` rows it uses - possibly
    none, and "open air, nothing added" is still a Thermal Solution, chosen on purpose, so a Bench Solution without one is not whole. The parts that
    make the heat are not copied here: they are the Hardware Solution's parts with their pcb `PartThermalModel` rows, reached through the Bench
    Solution.
    Related concepts: `ThermalSystem` (its template), `ThermalMitigation`, `BenchSolution` (names it).
    """

    plain_words = ('A thermal solution is the decision about heat for one bench: which template it follows and which helpers, if any, are clipped '
                   'on. Deciding on none is still a decision.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', system: str = '', mitigations: str = '', notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.system = system            # a ThermalSystem name
        self.mitigations = mitigations  # comma-separated ThermalMitigation names; '' = open air, nothing added
        self.notes = notes
