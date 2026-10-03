"""
@module firmwarefaults.objects.space_safety.MissedDeadlineFault

MissedDeadlineFault — one class per file (design §7): a FirmwareFault KIND of family `space-safety` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class MissedDeadlineFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A periodic job finishes after its deadline (the loop or an ISR took too long; interrupts masked too long).
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'space-safety'
    plain_words = ('A missed deadline: something that must happen on time happens late.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'space-safety', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 deadline_cycles: int = 0,
                 manager=None):
        self._fault_fields(locals())
        self.deadline_cycles = deadline_cycles  # the deadline in CPU cycles
