"""
@module firmwarefaults.objects.physical.BrownoutMidWriteFault

BrownoutMidWriteFault — one class per file (design §7): a FirmwareFault KIND of family `physical-trigger` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class BrownoutMidWriteFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: The supply sags during a multi-step write (EEPROM, a record): the write stops half done.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'physical-trigger'
    plain_words = ('A brownout in the middle of a write: the power dips while something is being saved, leaving it half old and half new.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'physical-trigger', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 droop_v: float = 0.0,
                 droop_ms: float = 0.0,
                 bod_level_v: float = 0.0,
                 manager=None):
        self._fault_fields(locals())
        self.droop_v = droop_v  # supply droop in volts
        self.droop_ms = droop_ms  # droop duration in ms
        self.bod_level_v = bod_level_v  # the brown-out detector level (fuse) in volts
