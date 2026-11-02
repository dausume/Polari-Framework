"""
@module cmod.objects.cmod.StructNodeRunEdge

StructNodeRunEdge - one class per file (design section 7); bss-2 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 6b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodeRunEdge(treeObject):
    """What it is: ONE EDGE AS IT RAN in one `StructNodeRun`: the cycle its stimulus was applied (0 for the flash and init edges), the cycle its
    to-node's requirements were all met (-1 = never, within the guard), its duration, which executions were observed running (the twin's own
    function counters) and which were not, which collaterals were measured and how they came out against their bounds, and the divergence words when
    a required field landed outside its requirement. An edge that met its requirements is `met`; otherwise not-reached | diverged | skipped (an earlier
    edge failed).
    Related concepts: `StructNodeRun` (the parent), `StructEdge`, `StructNodeExecution`, `StructNodeCollateral`.
    """

    plain_words = 'One edge of a run says when its trigger was applied, when the bench arrived at the next situation, and what was seen on the way.'

    @treeObjectInit
    def __init__(self, name: str = '', run: str = '', edge: str = '', order: int = 1, outcome: str = '', stimulus_cycle: int = 0, met_cycle: int = -1,
                 duration_s: float = -1.0, executions: str = '', collaterals: str = '', words: str = '', manager=None):
        self.name = name                  # '<run>:<order>'
        self.run = run                    # a StructNodeRun name
        self.edge = edge                  # a StructEdge name
        self.order = order
        self.outcome = outcome            # met | not-reached | diverged | skipped
        self.stimulus_cycle = stimulus_cycle
        self.met_cycle = met_cycle
        self.duration_s = duration_s
        self.executions = executions      # 'atom: observed (n=3) ; atom: not observed ; atom: no symbol (inlined)'
        self.collaterals = collaterals    # 'pin-level PD6: high at cycle N (bound high: met) ; frame uno-1-bridge: 2 frames after'
        self.words = words
