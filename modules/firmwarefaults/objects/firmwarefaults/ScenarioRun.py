"""
@module firmwarefaults.objects.firmwarefaults.ScenarioRun

ScenarioRun — one class per file (design §7).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ScenarioRun(treeObject):
    """What it is: One run of a Scenario on one firmware build (FIRMWARE_SCENARIO_PLAN.md §1): BEFORE (the build
    without the technique), AFTER (with it) or NATURAL (no forcing, the fault's own rate). The outcome is failed |
    passed | inapplicable (the scenario's PC/ISR/build does not exist here) | undetermined (the forcing condition never
    held in the window). It records WHERE: the cycle and PC of the forced event, the PC the interrupt actually landed
    on, the torn value; WHAT IT COST: sizes, the guarded function's cycles, the worst ISR latency, the stack high-water
    (exact SP watch, paint read-back, the static -fstack-usage peak); and HOW TO REPRODUCE: firmware/ELF/trace sha256,
    the harness digest, the seed and the repro block. A run is a witness or a counterexample — never a proof — and it
    writes the MathClaim named in `claim`.
    Related concepts: `Scenario`, `ScenarioTraceCycle` (the cycles around the fault), mathproofs' `MathClaim`.
    """

    plain_words = ('A scenario run is one attempt to make a bug happen in the simulated board. It records whether the bug '
                   'happened, the exact clock cycle and instruction where it did, and what the fix cost, so anyone can '
                   'run it again and get the same result.')

    @treeObjectInit
    def __init__(self, name: str = '', scenario: str = '', side: str = '', variant: str = '', build_name: str = '',
                 technique_applied: str = '', outcome: str = '', verdict_words: str = '', fault_cycle: int = 0, fault_pc: str = '',
                 fault_symbol: str = '', landed_pc: str = '', landed_symbol: str = '', landed_cycle: int = 0, torn_value: int = -1,
                 expected_value: int = -1, frames_seen: int = 0, frames_backwards: int = 0, bad_crc: int = 0, uptime_sequence: str = '',
                 observed_json: str = '{}', trace_sha256: str = '', trace_samples: int = 0, uart_sha256: str = '', firmware_sha256: str = '',
                 elf_sha256: str = '', harness_digest: str = '', simulator_version: str = '', seed: int = 0, sim_cycles: int = 0,
                 sim_seconds: float = 0.0, wall_s: float = 0.0, stack_high_water: int = 0, stack_high_water_paint: int = 0,
                 stack_static_peak: int = 0, isr_latency_max_cycles: int = 0, isr_latency_vector: int = 0, fn_cycles_min: int = 0,
                 size_text: int = 0, size_data: int = 0, size_bss: int = 0, cost_delta_json: str = '{}', cost_flash_bytes_delta: int = 0,
                 cost_cycles_delta: int = 0, latency_delta_cycles: int = 0, claim: str = '', repro_json: str = '{}', ran_at: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.scenario = scenario
        self.side = side  # before | after | natural
        self.variant = variant  # the FirmwareVariant built
        self.build_name = build_name  # the FirmwareBuild name (variant + source sha)
        self.technique_applied = technique_applied  # a Technique name, or '' (none)
        self.outcome = outcome  # failed | passed | inapplicable | undetermined
        self.verdict_words = verdict_words  # the decision in one sentence
        self.fault_cycle = fault_cycle  # the cycle the forced event fired at
        self.fault_pc = fault_pc  # 0x… — where it fired (the instruction about to run)
        self.fault_symbol = fault_symbol  # symbol+offset of fault_pc
        self.landed_pc = landed_pc  # 0x… — the return address the ISR was entered with (recorded, never assumed)
        self.landed_symbol = landed_symbol
        self.landed_cycle = landed_cycle
        self.torn_value = torn_value  # the value the reader got (r22..r25 at the guarded function's ret), -1 when none
        self.expected_value = expected_value  # what an atomic read returns at that moment
        self.frames_seen = frames_seen  # CRC-valid frames decoded from the UART
        self.frames_backwards = frames_backwards  # frames whose uptime_ms is below the previous frame's
        self.bad_crc = bad_crc
        self.uptime_sequence = uptime_sequence  # the decoded uptime_ms values, as text (… 200, 511, 400 …)
        self.observed_json = observed_json  # the harness's final line, the frames summary (rendered as key/value, never raw)
        self.trace_sha256 = trace_sha256  # the VCD window
        self.trace_samples = trace_samples
        self.uart_sha256 = uart_sha256  # every byte the firmware sent
        self.firmware_sha256 = firmware_sha256  # the .hex
        self.elf_sha256 = elf_sha256
        self.harness_digest = harness_digest  # the image id / binary the harness ran from
        self.simulator_version = simulator_version
        self.seed = seed
        self.sim_cycles = sim_cycles
        self.sim_seconds = sim_seconds
        self.wall_s = wall_s
        self.stack_high_water = stack_high_water  # bytes, from the lowest SP seen (exact)
        self.stack_high_water_paint = stack_high_water_paint  # bytes, from the 0xA5 paint read back
        self.stack_static_peak = stack_static_peak  # bytes, -fstack-usage + -fcallgraph-info (an estimate; libgcc frames not counted)
        self.isr_latency_max_cycles = isr_latency_max_cycles  # natural interrupts only (the forced one is on its event)
        self.isr_latency_vector = isr_latency_vector  # the vector that had it
        self.fn_cycles_min = fn_cycles_min  # the guarded function's uninterrupted cycles (hal_millis entry → ret)
        self.size_text = size_text
        self.size_data = size_data
        self.size_bss = size_bss
        self.cost_delta_json = cost_delta_json  # vs its pair (AFTER − BEFORE)
        self.cost_flash_bytes_delta = cost_flash_bytes_delta
        self.cost_cycles_delta = cost_cycles_delta
        self.latency_delta_cycles = latency_delta_cycles
        self.claim = claim  # the MathClaim this run wrote
        self.repro_json = repro_json  # inputs by sha256, tools, knobs, seed (the reproducibility rule)
        self.ran_at = ran_at
        self.notes = notes
