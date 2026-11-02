"""
@module cmod.objects.cmod.StructNodeState

StructNodeState - one class per file (design section 7). Node kind 1 of 2 of a Bench Topology drawing (bss-5, BENCH_SOLUTION_SIM_PLAN.md section 5b).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from cmod.custom.topology_palette import palette


class StructNodeState(treeObject):
    """What it is: the `struct-node` NODE KIND, category **Bench Topology** - one `StructNode` drawn on the canvas: its name (a person's words), its
    requirements in one line, its confirmation state (the colour), its step and what set it, and the route to the Bench Solution view at this node
    ("see the bench here"). Authored: the drawing reads the rows through `cmod.custom.bench_topology_nocode` and writes back ONLY the title; the
    requirements, executions and edges change through the rows and the doors, so the drawing is never a second copy.
    Related concepts: `StructNode` (the row), `HardwareEventState` (the box between two nodes), `cmod.custom.bench_topology_nocode`.
    """

    plain_words = 'One situation of the bench, drawn: what the struct fields must be, whether it was reached, and how finely the simulation looked.'

    statePalette = palette('struct-node', 'Struct node', plain_words,
                           [('title', 'Name'), ('requirements', 'Requirements'), ('confirmation', 'Confirmed?'), ('step', 'Step'), ('kind', 'Kind'),
                            ('basis', 'Defined by'), ('runs', 'Runs'), ('bench_here', 'See the bench here')])

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', requirements: str = '', confirmation: str = '', step: str = '', kind: str = '', basis: str = '',
                 runs: str = '', bench_here: str = '', manager=None):
        self.name = name
        self.title = title
        self.requirements = requirements
        self.confirmation = confirmation
        self.step = step
        self.kind = kind
        self.basis = basis
        self.runs = runs
        self.bench_here = bench_here
