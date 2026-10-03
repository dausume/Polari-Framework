"""
@module firmwarefaults.objects.concurrency.DeadlockFault

DeadlockFault — one class per file (design §7): a FirmwareFault KIND of family `concurrency` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class DeadlockFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A circular wait: each party holds a lock the next one needs. A LOGIC property — no physics is needed (plan §0).
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'concurrency'
    plain_words = ('A deadlock: two parts each hold something the other needs and both wait forever.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'concurrency', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 lock_cycle_json: str = '[]',
                 manager=None):
        self._fault_fields(locals())
        self.lock_cycle_json = lock_cycle_json  # the cycle in the wait-for graph, e.g. ["A", "B", "A"]
