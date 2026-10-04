"""
@module firmwarefaults.objects.firmwarefaults.ConcurrencyPrimitive

ConcurrencyPrimitive — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ConcurrencyPrimitive(treeObject):
    """What it is: A mechanism firmware uses to share state between an ISR and the main loop, or between tasks
    (FIRMWARE_SCENARIO_PLAN.md §1): masking interrupts, an atomic section, a volatile flag, a single-producer
    single-consumer ring; with an RTOS also semaphores, mutexes, queues. `uno_uses` says whether the UNO firmware relies
    on it today (the three it does: irq-mask, volatile-flag, spsc-ring), `site` names the code.
    Related concepts: `FirmwareFault.primitives_json`, `Technique.primitive`.
    """

    plain_words = ('A concurrency primitive is a basic tool that lets two parts of a program share data safely, such as '
                   'briefly pausing interrupts or using a queue with one writer and one reader.')

    @treeObjectInit
    def __init__(self, name: str = '', description: str = '', kind: str = '', needs_rtos: bool = False, typical_cost_cycles: int = 0,
                 uno_uses: bool = False, site: str = '', provenance: str = '', notes: str = '', manager=None):
        self.name = name
        self.description = description
        self.kind = kind  # irq-mask | atomic-section | volatile-flag | spsc-ring | semaphore | mutex | spinlock | queue | message-passing | lock-free
        self.needs_rtos = needs_rtos
        self.typical_cost_cycles = typical_cost_cycles  # what using it once costs (cycles, from the disassembly or measured)
        self.uno_uses = uno_uses  # the UNO firmware relies on it today
        # fw-2: named `site`, not `where` — `where` is a SQLite reserved word and broke CREATE
        # TABLE for this class ('near "where": syntax error'); rows never persisted.
        self.site = site  # file:symbol in board/custom/firmware/uno
        self.provenance = provenance
        self.notes = notes
