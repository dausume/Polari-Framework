"""
@module firmwarefaults.objects.concurrency.DoubleGiveFault

DoubleGiveFault — one class per file (design §7): a FirmwareFault KIND of family `concurrency` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class DoubleGiveFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A semaphore or flag given twice for one event (an ISR re-entering, a ringing edge): the consumer runs twice.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'concurrency'
    plain_words = ('A double give: one event is signalled twice, so the work it should trigger happens twice.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'concurrency', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 manager=None):
        self._fault_fields(locals())
