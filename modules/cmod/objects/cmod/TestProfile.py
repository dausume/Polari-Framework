"""
@module cmod.objects.cmod.TestProfile

TestProfile - one class per file (design section 7); bss-3 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 3b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestProfile(treeObject):
    """What it is: ONE NAMED ANSWER TO "WHAT DO WE WATCH" during a node test - its `TestProfileItem` rows: struct fields (watched by address), pins (read
    from the wire) and timings. The user (2026-11-02): "we should have a way to define a TestProfile manually." `basis` manual = composed by a person;
    derived = the node's own requirements and collaterals (what a run uses when no profile is named; never stored as rows); suggested = proposed from
    the node's checks, shown, never applied silently. A profile is reusable across nodes and Bench Solutions with the same structs; an item a node
    cannot reach is refused in words when the profile is named on a run.
    Related concepts: `TestProfileItem`, `StructNodeRun` (names the profile it ran with), `StructNodeRequirement` / `StructNodeCollateral` (the derived default).
    """

    plain_words = 'A test profile is a named list of what to keep an eye on during a test: which fields, which pins, which timings.'

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', bench_solution: str = '', basis: str = 'manual', notes: str = '', manager=None):
        self.name = name
        self.title = title
        self.bench_solution = bench_solution  # '' when shared across Bench Solutions
        self.basis = basis                    # manual | suggested
        self.notes = notes
