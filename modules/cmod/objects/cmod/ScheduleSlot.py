"""
@module cmod.objects.cmod.ScheduleSlot

ScheduleSlot — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ScheduleSlot(treeObject):
    """What it is: WHEN one task (a `CGraphNode` of kind c-atom, or a glue-owned kind) runs inside a `FirmwareSolution`
    (D-fs-1, his ruling 2026-10-05: "go with your picks" — the schedule lane is DERIVED from the atoms' own ISR/tick/loop
    annotations, NEVER authored by dragging). `lane` is isr (an ISR vector atom/the ISR node itself) | tick (the glue's
    periodic tick + whatever it calls) | loop (a `stage='loop'` c-atom, called every pass of `main()`) | init (a
    `stage='init'` c-atom, before `sei()`). `order` mirrors the `CGraphNode.order` the glue already renders from (the
    SAME order `polari_graph.c`'s `main()`/ISRs emit — never a second ordering scheme). `measured_cycles` comes from the
    atom's own committed cost row where known (`CFunctionAtom.cost` — avr-size/`.su`, cmod-0's own measurement); '' when
    the atom has no timed proof yet. `provenance` is always 'derived' here — the one value this row ever carries, stated
    on every row rather than silently assumed, since a canvas-authored slot (fs-1) would set it to 'canvas'.
    Related concepts: `FirmwareSolution`, `CGraphNode`, `CFunctionAtom` (isr_vector, cost), `CGraph`.
    """

    plain_words = 'A schedule slot says WHEN a task runs — at interrupt time, on a tick, in the main loop, or once at startup — read off the C itself, never typed in.'

    @treeObjectInit
    def __init__(self, name: str = '', solution: str = '', task: str = '', lane: str = 'loop', order: int = 0,
                 trigger: str = '', period_ms: int = 0, measured_cycles: int = -1, isr_vector: str = '',
                 provenance: str = 'derived', notes: str = '', manager=None):
        self.name = name                  # '<solution>:<task>'
        self.solution = solution
        self.task = task                  # the CGraphNode instance this slot schedules
        self.lane = lane                  # isr | tick | loop | init
        self.order = order                # mirrors CGraphNode.order (the glue's own emission order)
        self.trigger = trigger            # 'USART_RX_vect' (isr) / 'TELEMETRY_MS' (tick) / '' (loop/init: every pass / once)
        self.period_ms = period_ms        # tick lane only; 0 otherwise
        self.measured_cycles = measured_cycles   # -1 = not measured; else the atom's committed cost (cycles where known)
        self.isr_vector = isr_vector      # isr lane only: the atom's own isr_vector field
        self.provenance = provenance      # always 'derived' (D-fs-1)
        self.notes = notes
