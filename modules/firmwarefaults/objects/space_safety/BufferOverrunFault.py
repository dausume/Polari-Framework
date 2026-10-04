"""
@module firmwarefaults.objects.space_safety.BufferOverrunFault

BufferOverrunFault — one class per file (design §7): a FirmwareFault KIND of family `space-safety` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class BufferOverrunFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A write past a buffer's bound (a ring index unmasked, a length unchecked).
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'space-safety'
    plain_words = ('A buffer overrun: data is written past the end of the space set aside for it.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'space-safety', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 buffer: str = '',
                 bound: int = 0,
                 manager=None):
        self._fault_fields(locals())
        self.buffer = buffer  # the buffer (symbol)
        self.bound = bound  # its size in elements
