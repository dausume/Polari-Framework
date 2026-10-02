"""
@module firmwarefaults.objects.space_safety.StackOverflowFault

StackOverflowFault — one class per file (design §7): a FirmwareFault KIND of family `space-safety` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class StackOverflowFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: The stack grows into .bss/.data (deep calls plus an ISR frame at the worst moment): silent corruption.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'space-safety'
    plain_words = ('A stack overflow: the memory used for function calls grows too big and overwrites other data.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'space-safety', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 headroom_bytes: int = 0,
                 manager=None):
        self._fault_fields(locals())
        self.headroom_bytes = headroom_bytes  # bytes between the stack high-water and the end of .bss (measured)
