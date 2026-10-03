"""
@module firmwarefaults.objects.physical.MetastableInputFault

MetastableInputFault — one class per file (design §7): a FirmwareFault KIND of family `physical-trigger` (FIRMWARE_SCENARIO_PLAN.md §1).
"""
from objectTreeDecorators import treeObject, treeObjectInit
from firmwarefaults.objects.firmwarefaults.FirmwareFault import FirmwareFault


class MetastableInputFault(FirmwareFault, treeObject):   # treeObject named too: the manifest scan reads the bases (AST)
    """What it is: An asynchronous input sampled during its transition settles late or to either value (a flip-flop violation).
    Every row says which ASSUMPTION it breaks, what you would OBSERVE, which remedies (Techniques) restore the
    assumption, and where its rate comes from (a citation, a measured run, or `unverified` — never a silent guess).
    Related concepts: `FirmwareFault`, `Assumption`, `Technique`, `Scenario`.
    """

    LAYER = 'physical-trigger'
    plain_words = ('A metastable input: a signal that changes exactly when it is sampled can be read as neither 0 nor 1 for a moment.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = 'physical-trigger', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '',
                 mtbf_params_json: str = '{}',
                 manager=None):
        self._fault_fields(locals())
        self.mtbf_params_json = mtbf_params_json  # the MTBF parameters (tau, T0, clock and data rates) with their source
