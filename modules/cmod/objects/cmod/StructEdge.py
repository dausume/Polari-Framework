"""
@module cmod.objects.cmod.StructEdge

StructEdge - one class per file (design section 7); bss-1 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2 "Edge").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructEdge(treeObject):
    """What it is: ONE EDGE of the topology: from one `StructNode` to the next, and what moves it - `flash` (the fixed first edge), `init` (the second),
    `trigger` (a `HardwareEvent` starts it) or `cascade` (the previous node's change makes code run that produces the next). An edge ALWAYS ENDS when
    its to-node's requirements are all met at once, never by a clock (the guard only says "not reached"). The checks beyond the requirements, the runs
    and the confirmations come in bss-3.
    Related concepts: `StructNode` x2, `HardwareEvent` (when trigger), board `ConfigurationEvent` (the flash), `StructNodePath`.
    """

    plain_words = 'An edge is one move between two situations of the bench and what causes it - a press, a command, the code itself, or the flash.'

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', bench_solution: str = '', from_node: str = '', to_node: str = '', kind: str = 'trigger', event: str = '',
                 notes: str = '', manager=None):
        self.name = name                      # '<bench_solution>:<from-slug>-><to-slug>'
        self.title = title
        self.bench_solution = bench_solution  # a BenchSolution name
        self.from_node = from_node            # a StructNode name
        self.to_node = to_node                # a StructNode name
        self.kind = kind                      # flash | init | trigger | cascade
        self.event = event                    # a HardwareEvent name when kind == trigger, else ''
        self.notes = notes
