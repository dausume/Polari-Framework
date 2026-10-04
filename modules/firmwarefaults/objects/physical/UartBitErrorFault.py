"""
@module firmwarefaults.objects.physical.UartBitErrorFault

UartBitErrorFault — one class per file (design §7): a FirmwareFault KIND of family `physical-trigger` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class UartBitErrorFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A bit on the serial line arrives flipped (noise, baud mismatch): the byte is wrong; framing errors set FE0.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'physical-trigger'
    plain_words = ('A UART bit error: one bit on the serial wire arrives wrong, so a byte is corrupted.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'physical-trigger', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 ber: float = 0.0,
                 manager=None):
        self._fault_fields(locals())
        self.ber = ber  # bit error rate (errors per bit)
