"""
@module firmwarefaults.objects.concurrency.LostWakeupFault

LostWakeupFault — one class per file (design §7): a FirmwareFault KIND of family `concurrency` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class LostWakeupFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: The waker signals between the waiter's check and its sleep: the wakeup is lost and the waiter sleeps through it.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'concurrency'
    plain_words = ('A lost wakeup: the "go" signal arrives in the tiny gap before the other side starts listening, so it is missed.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'concurrency', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 manager=None):
        self._fault_fields(locals())
