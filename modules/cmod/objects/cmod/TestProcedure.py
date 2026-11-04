"""
@module cmod.objects.cmod.TestProcedure

TestProcedure - one class per file (design section 7); msv-0b (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 5b).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class TestProcedure(treeObject):
    """What it is: ONE FROZEN STEP-BY-STEP MANUAL TEST of a Bench Solution's built units, GENERATED from its topology (the fastest path to every
    node) and its measurement points - never written by hand. Frozen per build (hex sha256 + layout): a later build gets a new procedure. The user
    (2026-11-04): "generate step by step manual tests".
    Related concepts: `TestProcedureStep` (its steps), `TestSession` (a person working through it), `StructNode`, `MeasurementPoint`.
    """

    plain_words = ('The list of things to do and check, in order, to test a hand-built device against the simulation; worked out from the design, not typed.')

    @treeObjectInit
    def __init__(self, name: str = '', bench_solution: str = '', hex_sha256: str = '', layout: str = '', steps: int = 0, owed: str = '', at: str = '', notes: str = '', manager=None):
        self.name = name    # '<bench solution>-proc-<n>'
        self.bench_solution = bench_solution    # a BenchSolution name
        self.hex_sha256 = hex_sha256    # the build it is frozen for
        self.layout = layout    # the layout it is frozen for
        self.steps = steps    # how many steps
        self.owed = owed    # the words for what could not be generated (a node with no reached run has no points yet)
        self.at = at
        self.notes = notes
