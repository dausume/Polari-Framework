"""
@module firmwarefaults.objects.concurrency.StarvationFault

StarvationFault — one class per file (design §7): a FirmwareFault KIND of family `concurrency` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class StarvationFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A task or ISR never gets the CPU or the resource because others always win.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'concurrency'
    plain_words = ('Starvation: one part never gets its turn because others always go first.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'concurrency', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 manager=None):
        self._fault_fields(locals())
