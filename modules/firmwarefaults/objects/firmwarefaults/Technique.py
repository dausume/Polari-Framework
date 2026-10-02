"""
@module firmwarefaults.objects.firmwarefaults.Technique

Technique — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class Technique(treeObject):
    """What it is: A way to make firmware safe against a fault — an atomic section, a timeout + state machine, a CRC
    with resync, a debounce or synchroniser, a watchdog, write-then-commit, lock ordering, priority inheritance, a
    static guard (FIRMWARE_SCENARIO_PLAN.md §1). It RESTORES one assumption, and it COSTS something: `typical_cost_*` is
    the estimate it was seeded with (from the disassembly or the literature), `measured_*` what a scenario pair measured
    on the twin (bytes from avr-size, cycles from the harness, ISR latency from --isr-latency) and which run measured it.
    The idiom is C only (RULE 2).
    Related concepts: `Assumption`, `FirmwareFault.remedies_json`, `ScenarioRun.technique_applied`.
    """

    plain_words = ('A technique is a known fix that makes a program safe against one kind of fault. Each technique also '
                   'costs something, such as a few extra bytes of program or a few extra clock cycles, and that cost is '
                   'measured and kept with it.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', restores: str = '', primitive: str = '', idiom_c: str = '',
                 typical_cost_bytes: int = 0, typical_cost_cycles: int = 0, typical_latency_cycles: int = 0, cost_source: str = 'estimate',
                 measured_cost_bytes: int = 0, measured_cost_cycles: int = 0, measured_latency_delta_cycles: int = 0,
                 measured_by_run: str = '', alternative_of: str = '', caveats: str = '', provenance: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.description = description
        self.restores = restores  # an Assumption name
        self.primitive = primitive  # a ConcurrencyPrimitive name ('' when none)
        self.idiom_c = idiom_c  # the C idiom (RULE 2)
        self.typical_cost_bytes = typical_cost_bytes  # flash bytes added (estimate / disassembly)
        self.typical_cost_cycles = typical_cost_cycles  # cycles added per use
        self.typical_latency_cycles = typical_latency_cycles  # worst-case ISR latency added (interrupts masked)
        self.cost_source = cost_source  # where the typical numbers come from
        self.measured_cost_bytes = measured_cost_bytes  # what the twin measured (avr-size delta of a scenario pair)
        self.measured_cost_cycles = measured_cost_cycles  # min cycles delta of the guarded function (--fn-cycles)
        self.measured_latency_delta_cycles = measured_latency_delta_cycles  # max ISR latency delta (--isr-latency)
        self.measured_by_run = measured_by_run  # the AFTER ScenarioRun that measured it
        self.alternative_of = alternative_of  # a cheaper / narrower technique names the one it replaces
        self.caveats = caveats  # where it is NOT correct
        self.provenance = provenance
        self.notes = notes
