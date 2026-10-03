"""
@module firmwarefaults.objects.physical.BitFlipFault

BitFlipFault — one class per file (design §7): a FirmwareFault KIND of family `physical-trigger` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class BitFlipFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: A stored bit changes by itself (radiation, marginal cells): a value, a pointer or a flag is wrong.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'physical-trigger'
    plain_words = ('A bit flip: one bit in memory changes on its own, for example from a cosmic ray.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'physical-trigger', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 upsets_per_bit_day: float = 0.0,
                 manager=None):
        self._fault_fields(locals())
        self.upsets_per_bit_day = upsets_per_bit_day  # upset rate per bit per day
