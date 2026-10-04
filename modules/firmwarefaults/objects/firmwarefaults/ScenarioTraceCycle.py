"""
@module firmwarefaults.objects.firmwarefaults.ScenarioTraceCycle

ScenarioTraceCycle — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ScenarioTraceCycle(treeObject):
    """What it is: One instruction boundary of a run's trace window — the "cycles around the fault" table
    (FIRMWARE_SCENARIO_PLAN.md §6): cycle (absolute, and relative to the forced event), PC with its symbol+offset and
    instruction, SP, SREG.I, the running vector (0 = main loop), r22..r25 (hal_millis's return registers) and the
    watched word (g_ms). Read engine-side from the VCD by pyvcd (polari-vcd-window), annotated from the ELF here.
    Exists as rows so the page shows it in a CONFIGURED table — never raw JSON — until the 2D viewer takes the VCD.
    Related concepts: `ScenarioRun.trace_sha256` (the VCD these rows came from).
    """

    plain_words = ('One step of the recorded timeline around a forced bug: which instruction ran at which clock cycle, '
                   'whether an interrupt was running, and the values the program was holding.')

    @treeObjectInit
    def __init__(self, name: str = '', run: str = '', idx: int = 0, cycle: int = 0, rel_cycle: int = 0, pc: str = '', symbol: str = '',
                 instruction: str = '', sp: int = 0, sreg_i: int = 0, isr_vector: int = 0, r22: str = '', r23: str = '', r24: str = '',
                 r25: str = '', watch: str = '', forced: int = 0, note: str = '', manager=None):
        self.name = name
        self.run = run  # the ScenarioRun name
        self.idx = idx
        self.cycle = cycle
        self.rel_cycle = rel_cycle  # cycle − the forced event's cycle
        self.pc = pc
        self.symbol = symbol  # symbol+offset from the ELF
        self.instruction = instruction  # avr-objdump's text for that PC
        self.sp = sp
        self.sreg_i = sreg_i
        self.isr_vector = isr_vector  # 0 = main loop
        self.r22 = r22
        self.r23 = r23
        self.r24 = r24
        self.r25 = r25
        self.watch = watch  # the watched word (g_ms) as hex
        self.forced = forced  # 1 on the boundary the harness forced the interrupt
        self.note = note  # e.g. "lds 1 of g_ms", "ISR entered (vector 7)", "torn: 0x000001FF"
