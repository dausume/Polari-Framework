"""
@module cmod.objects.cmod.StructEdgeCheck

StructEdgeCheck - one class per file (design section 7); bss-3 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b "testing per edge").
"""
from objectTreeDecorators import treeObject, treeObjectInit


class StructEdgeCheck(treeObject):
    """What it is: ONE EXPECTATION ON AN EDGE BEYOND ITS NODE'S REQUIREMENTS: `timing` (the edge reaches its node within `bound_s` of its stimulus),
    `field-tolerance` (a field ends within `value` +/- `tolerance`) or `field-range` (within `value` = 'lo..hi'). A run that meets the requirements but
    fails a check is `checks-failed`: reached, not confirmable. A tolerance check needs a tolerance (refused in words without one).
    Related concepts: `StructEdge` (the parent), `StructNodeRequirement` (what defines the node), `StructNodeRun`.
    """

    plain_words = 'An edge check is an extra thing that must hold on the way to a situation - how fast it was reached, or how close a value landed.'

    @treeObjectInit
    def __init__(self, name: str = '', edge: str = '', kind: str = 'timing', field: str = '', value: str = '', tolerance: float = 0.0, bound_s: float = -1.0,
                 notes: str = '', manager=None):
        self.name = name            # '<edge>:<kind>:<field or timing>'
        self.edge = edge            # a StructEdge name
        self.kind = kind            # timing | field-tolerance | field-range
        self.field = field          # '' for timing
        self.value = value          # the centre ('25') or 'lo..hi'
        self.tolerance = tolerance  # field-tolerance: +/- this
        self.bound_s = bound_s      # timing: reached within this many seconds of the stimulus
        self.notes = notes
