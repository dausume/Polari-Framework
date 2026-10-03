"""
@module firmwarefaults.objects.physical.ClockSkewFault

ClockSkewFault — one class per file (design §7): a FirmwareFault KIND of family `physical-trigger` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class ClockSkewFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: Two clocks disagree (resonator tolerance, temperature): baud rates and timeouts drift apart.
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'physical-trigger'
    plain_words = ('Clock skew: two devices count time at slightly different speeds, so their timing drifts apart.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'physical-trigger', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 ppm: float = 0.0,
                 manager=None):
        self._fault_fields(locals())
        self.ppm = ppm  # frequency error in parts per million
