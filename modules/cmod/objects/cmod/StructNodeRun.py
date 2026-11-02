"""
@module cmod.objects.cmod.StructNodeRun

StructNodeRun - one class per file (design section 7); bss-2 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md sections 3c and 6b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructNodeRun(treeObject):
    """What it is: ONE TEST OF ONE NODE - a deterministic twin run of the Firmware Solution's locked hex from reset (the root), along one path, the path's
    triggers applied as cycle-stamped stimuli, the node's required struct words watched. What is KEPT is the assessment (the user: "we do not want to
    record everything on the edges"): the outcome (reached | not-reached | diverged | blocked | refused), the finest step taken and the execution or
    collateral that asked for it, how long the last edge took to meet its requirements and what set that, the hex sha256, the engine, and the words. The
    per-edge detail is in `StructNodeRunEdge`, the per-signal assessment in `StructNodeRunSignal`; the traces themselves are not kept (3c).
    Related concepts: `StructNode`, `StructNodePath`, `StructNodeRunEdge`, `StructNodeRunSignal`, `StructNodeConfirmation` (bss-3).
    """

    plain_words = ('A node run is one try at reaching a situation on the simulated bench, from the moment the board is plugged in: did it get there, '
                   'how long did the last step take, and how finely did the simulation have to look.')

    @treeObjectInit
    def __init__(self, name: str = '', node: str = '', path: str = '', outcome: str = '', hex_sha256: str = '', engine: str = 'twin', step_s: float = -1.0,
                 step_set_by: str = '', duration_s: float = -1.0, duration_set_by: str = '', ran_at: str = '', words: str = '', manager=None):
        self.name = name                        # '<node>#run<n>'
        self.node = node                        # a StructNode name
        self.path = path                        # a StructNodePath name
        self.outcome = outcome                  # reached | not-reached | diverged | blocked | refused
        self.hex_sha256 = hex_sha256            # the locked firmware the run used
        self.engine = engine                    # twin (simavr through the engines seam); hardware (bss-3)
        self.step_s = step_s                    # the finest step the node asked for (section 3)
        self.step_set_by = step_set_by
        self.duration_s = duration_s            # stimulus -> requirements met, on the last edge
        self.duration_set_by = duration_set_by
        self.ran_at = ran_at
        self.words = words
