"""
@module suiteapps.objects.suiteapps.SuitePlacement

SuitePlacement — where each part of a suite would run, computed.
"""
from objectTreeDecorators import treeObject, treeObjectInit

PLACEMENT_VERDICTS = ('placed', 'needs-hardware-tier', 'needs-node', 'unplaceable')


class SuitePlacement(treeObject):
    """What it is: the computed answer for one part: which device takes it,
    why (a hardware-tier device with the ports the part needs, the core,
    the named node, the least-loaded fitting device), and what is missing
    when none can (`verdict`). Recomputed on demand; rows replace.
    Related concepts: `SuitePart`, `HardwareMapSnapshot` (tier readiness
    + ports), `PolariNodeMachine` / the coverage planner's nodes,
    `StandardComputerBudget`.
    How it is derived: `suiteapps.custom.placement.place` — pure rules
    over the rows.
    """

    @treeObjectInit
    def __init__(self, name: str = '', suite: str = '', part: str = '', device: str = '',
                 verdict: str = 'unplaceable', reason: str = '', computed_at: str = ''):
        self.name = name
        self.suite = suite
        self.part = part
        self.device = device
        self.verdict = verdict
        self.reason = reason
        self.computed_at = computed_at
