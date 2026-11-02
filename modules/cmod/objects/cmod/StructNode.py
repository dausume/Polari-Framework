"""
@module cmod.objects.cmod.StructNode

StructNode - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2 "Node").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNode(treeObject):
    """What it is: ONE NODE of a Bench Solution's Hardware Event topology - a named set of END-STATE REQUIREMENTS on the structs (the user, 2026-11-02:
    "only specific values or value ranges or sets that need to be met for something to be considered ending in that node's state"). The requirements
    are its `StructNodeRequirement` rows; the code expected to bring the structs there its `StructNodeExecution` rows; its measurable effects outside
    the structs its `StructNodeCollateral` rows (`collaterals` says none / declared / derived). Fields the node does not name are don't-care. `kind`
    root / flashed / boot are the fixed first chain (plugged in -> flash -> flashed -> init -> boot); every other node is `state`. The full Struct State
    a run has on arrival is the run's, not this row's.
    Related concepts: `StructEdge` (what reaches it), `StructNodePath` (how, from the root), board `BenchSolution`.
    """

    plain_words = ('A node is one named situation of the bench, defined by what certain struct fields must be - exactly this, within this range, or '
                   'one of these - for the bench to count as being there.')

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', bench_solution: str = '', kind: str = 'state', collaterals: str = 'none', basis: str = 'person',
                 notes: str = '', manager=None):
        self.name = name                      # '<bench_solution>:<slug>'
        self.title = title                    # a person's words ("light on"); '' shows the requirements instead
        self.bench_solution = bench_solution  # a BenchSolution name
        self.kind = kind                      # root | flashed | boot | state
        self.collaterals = collaterals        # none | declared | derived
        self.basis = basis                    # person | ai | proposed (bss-3, D-bss-10: a divergence's reached values, dashed and unnamed until accepted)
        self.notes = notes
