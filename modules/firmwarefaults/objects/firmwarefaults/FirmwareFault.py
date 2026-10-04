"""
@module firmwarefaults.objects.firmwarefaults.FirmwareFault

FirmwareFault — one class per file (design §7): the BASE of every fault kind (FIRMWARE_SCENARIO_PLAN.md §1; his ruling
2026-10-02: fault kinds are OBJECTS, one class per kind, so a run attaches to an object and not to a label).
"""
from objectTreeDecorators import treeObject, treeObjectInit

#: the fields every kind carries (a kind adds its own beside them)
BASE_FIELDS = ('name', 'description', 'layer', 'assumption_broken', 'observable', 'primitives_json', 'remedies_json', 'rate', 'rate_unit',
               'rate_source', 'needs_rtos', 'forcing_status', 'provenance', 'notes')
LAYERS = ('concurrency', 'physical-trigger', 'space-safety')


class FirmwareFault(treeObject):
    """What it is: A KIND of firmware fault — the base every kind class extends (TornReadFault, DeadlockFault,
    UartBitErrorFault, StackOverflowFault, …). The layer says which analysis it belongs to: `concurrency` (a logic
    property of an interleaving — can it happen at all?), `physical-trigger` (physics breaks an assumption and exposes a
    latent bug; the RATE comes from physics) or `space-safety` (space pressure is a cause: a smaller buffer is where a
    race lands). Rows live in the kind classes; this class's own table stays empty unless a fault fits no kind yet.
    Related concepts: `Assumption` (what it breaks), `Technique` (what restores it), `Scenario` (how it is forced).
    """

    LAYER = ''
    plain_words = ('A firmware fault is one known way small embedded programs go wrong, such as two parts of the program '
                   'reading the same value at the same moment. Each one names the assumption it breaks, what you would '
                   'see when it happens, and which techniques make it safe.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', layer: str = '', assumption_broken: str = '', observable: str = '',
                 primitives_json: str = '[]', remedies_json: str = '[]', rate: float = 0.0, rate_unit: str = '',
                 rate_source: str = 'unverified', needs_rtos: bool = False, forcing_status: str = '', provenance: str = '',
                 notes: str = '', manager=None):
        self._fault_fields(locals())

    def _fault_fields(self, values):
        """Set the base fields from a kind's __init__ locals (a kind never calls this class's decorated __init__)."""
        for k in BASE_FIELDS:
            setattr(self, k, values.get(k))
        if not self.layer:
            self.layer = self.LAYER
        # layer: concurrency | physical-trigger | space-safety · assumption_broken: an Assumption name ·
        # primitives_json / remedies_json: ConcurrencyPrimitive / Technique names · rate_source: a citation, `measured: run …`,
        # an `estimate …` or `unverified` · forcing_status: which simulator can force it today, or why none can yet
