"""
@module firmwarefaults.objects.concurrency.TornReadFault

TornReadFault — one class per file (design §7): a FirmwareFault KIND of family `concurrency` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class TornReadFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A multi-byte value shared with an ISR read in several instructions: an interrupt between them makes the reader combine bytes from two different values (g_ms 0x000000FF read as 0x000001FF = 511).
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'concurrency'
    plain_words = ('A torn read: a number made of several bytes is read one byte at a time, and an interrupt changes it halfway, so the reader gets half the old number and half the new one.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'concurrency', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 width_bytes: int = 0,
                 read_order: str = '',
                 manager=None):
        self._fault_fields(locals())
        self.width_bytes = width_bytes  # bytes in the shared value (g_ms: 4 — four `lds`)
        self.read_order = read_order  # the order the bytes are loaded (lo→hi on avr-gcc)
