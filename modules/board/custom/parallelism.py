"""
@module board.custom.parallelism

ipb-6 (INTERRUPT_POLL_BUDGET_PLAN.md §2c): the KINDS OF PARALLELISM a chip can hold, as cited rows, and the per-processor facts the budget reads
from them (pipeline depth, issue width, hardware threads per core, vector / subword units, lockstep). His ask 2026-10-27: "think of different
kinds of chip internal parallelism like instruction level parallelism and other forms of parallelism defined like those found in the RISC-V book".

THE BOOK = Patterson & Hennessy, "Computer Organization and Design RISC-V Edition: The Hardware/Software Interface" (2nd ed., Morgan Kaufmann).
Its TABLE OF CONTENTS was read 2026-10-27 (the zyBooks catalog listing of the edition); the section BODIES were NOT re-read today - every row
cites the section title it stands on and names it again in `to_read`. The four-kind frame (ILP / DLP / TLP / RLP) is Hennessy & Patterson,
"Computer Architecture: A Quantitative Approach" §1.2 - named, not read today.

What the budget does with each kind (the honest part, §2c):
  - instruction-level (pipelining, multiple issue) and subword / vector (data-level) change how many CYCLES an atom costs; measured cycle
    counts already include them (their basis says "measured") and a hart stays ONE program counter: no new column.
  - hardware multithreading (thread-level on one core): RISC-V's word for each hardware thread is a HART, so every hardware thread IS a
    column pair (the facts' `harts` already counts PCs, not cores).
  - multicore (thread-level across cores): one pair per core, each ASSIGNABLE separately (knobs hart_of / isr_hart_of) - unless the cores run
    in LOCKSTEP (two cores execute the same instruction stream and compare results for faults): then ONE stream is assignable and the other
    core is a MIRROR of it - his words: "unless they are configured to be lockstep and in the same chip".
  - message passing (clusters; two chips on a board): the budget's links[] rows and the deadline chain (TC-B1/B2).
Every number is cited or -1; every yes/no is 'unverified' until its document is read (rule derive-or-cite-chip-data).

ipb-8 (§2d, his ask 2026-10-28 "Symmetric Multi-Core and Asymmetric Multi-Core Chips"): each processor row carries `multicore_model` —
single (one hart) · smp (identical harts, shared memory, ONE kernel schedules across them: a null-affinity task may land on any) · amp (harts
with different ISAs or separate kernels/images: AMP harts never share a task set) · lockstep (§2c) · configurable · unverified — with
`multicore_citation` and `amp_with` (a co-processor beside the SMP pair, e.g. the S3's ULP). SCHEDULER_TIERS = the ladder bare-c -> freertos ->
freertos-smp -> zephyr as cited rows (D-ipb-11 recommended: freertos-smp its own row; the IDF variant cited on it).

    python3 -m board.custom.parallelism            # prints the rows
"""
import json

_COD = 'Patterson & Hennessy, Computer Organization and Design RISC-V Edition, 2nd ed. - table of contents read 2026-10-27 (zyBooks catalog); section body NOT read today'
_CAQA = 'Hennessy & Patterson, Computer Architecture: A Quantitative Approach, §1.2 "Classes of Parallelism and Parallel Architectures" (named; not read today)'

LEVELS = ('instruction', 'data', 'thread', 'core', 'request')
LOCKSTEP = ('yes', 'no', 'n/a (one core)', 'configurable', 'unverified')
MULTICORE_MODELS = ('single', 'smp', 'amp', 'lockstep', 'configurable', 'unverified')


def _kind(name, title, level, section, changes, example, to_read=''):
    return {'name': name, 'title': title, 'level': level, 'book_section': section, 'budget_effect': changes, 'example': example,
            'citation': _COD, 'to_read': to_read or ('COD RISC-V 2nd ed. %s (the body)' % section)}


#: the kinds, in the book's order of appearance. `level` = the H&P four-kind frame plus "core" split out of "thread" because the budget treats them differently.
PARALLELISM_KINDS = [
    _kind('synchronization', 'Parallelism and instructions: synchronization (lr/sc, amo - the atomics two harts share state with)', 'thread',
          '§2.11 Parallelism and instructions: synchronization', 'no column; a masked window or an atomic sequence inside an atom is where a poll and an interrupt (or two harts) '
          'contend for one variable - the masked_window_cycles field', 'lr.w / sc.w, amoswap.w; on AVR cli/sei; on Arm-M PRIMASK / ldrex-strex'),
    _kind('subword', 'Subword parallelism (one register holding several narrow lanes: SIMD within a word)', 'data',
          '§3.6 Parallelism and computer arithmetic: subword parallelism', 'cycles per atom only (measured counts include it); no column', 'RISC-V P-extension draft; x86 SSE/AVX (§3.7)'),
    _kind('pipelining', 'Pipelining (several instructions in flight, one issued per cycle at best)', 'instruction',
          '§4.6 An overview of pipelining', 'cycles per atom only: the depth sets branch / hazard costs (why a measured count beats an instruction count); no column',
          'Hazard3: 3 stages (readme); AVR: "single level pipelining" (datasheet, not re-read: -1); Cortex-M0+: 2 stages (Arm TRM, not read: -1)'),
    _kind('multiple-issue', 'Parallelism via instructions: multiple issue (static / dynamic), speculation', 'instruction',
          '§4.11 Parallelism via instructions', 'cycles per atom only; makes cycle counts data-dependent (why min AND max are kept per atom); no column',
          'none of the bench MCUs is known multi-issue; issue_width -1 until a TRM is read'),
    _kind('cache-coherence', 'Parallelism and memory hierarchies: cache coherence (what multicore shared memory costs)', 'core',
          '§5.10 Parallelism and memory hierarchies: cache coherence', 'a link-like cost INSIDE a chip when two harts share a buffer; -1 (no MCU here has a coherent cache: said per row)',
          'ESP32-S3 / P4 dual core: cache behaviour per TRM (not read)'),
    _kind('simd-vector', 'SISD, MIMD, SIMD, SPMD, and vector (Flynn\'s classes; the RISC-V V extension is the vector case)', 'data',
          '§6.3 SISD, MIMD, SIMD, SPMD, and vector', 'cycles per atom only; a vector unit is part of its hart (no own PC): no column',
          'RISC-V "V" / Zve*; ESP32-S3 PIE (Xtensa SIMD, not read); none on AVR'),
    _kind('hardware-multithreading', 'Hardware multithreading (several hardware threads sharing one core\'s pipeline: fine / coarse / simultaneous)', 'thread',
          '§6.4 Hardware multithreading', 'EACH hardware thread is a RISC-V HART = its own column pair (the facts count PCs); the pair\'s cycles are shared with its siblings (said)',
          'no bench MCU has it (hw_threads_per_core 1 or -1)'),
    _kind('multicore', 'Multicore and other shared memory multiprocessors (MIMD in one chip)', 'core',
          '§6.5 Multicore and other shared memory multiprocessors', 'one column pair PER CORE, assignable separately (hart_of / isr_hart_of) unless LOCKSTEP -> one stream + mirrors',
          'RP2350 (2 Hazard3), ESP32-S3 (2 LX7), ESP32-P4 (2 RV32), K210 (2 RV64), CV1800B (2 C906)'),
    _kind('gpu-dsa', 'GPUs and domain-specific architectures (many lanes under few PCs; not a hart in the budget\'s sense)', 'data',
          '§6.6 Introduction to graphics processing units; §6.7 Domain specific architectures', 'out of scope for an MCU budget; a co-processor with its own PC is the D-ipb-6 kind (PIO)',
          'RP2350 PIO state machines: own PC, no interrupt intake (D-ipb-6)'),
    _kind('message-passing', 'Clusters and other message-passing multiprocessors (two chips on a board are this)', 'request',
          '§6.8 Clusters, warehouse scale computers, and other message-passing multiprocessors', 'the links[] rows: transport, baud, frame, transit; the deadline CHAIN across column pairs (TC-B1/B2)',
          'UNO <-> C3 over the UART (TC-B2)'),
]


def _facts(processor, pipeline_stages=-1, issue_width=-1, hw_threads_per_core=-1, vector='unverified', lockstep='unverified', citation='', to_read='',
           multicore_model='', multicore_citation='', amp_with=''):
    # a single-core chip is `single` by its own lockstep fact (one core); a multi-core chip stays `unverified` until a document says how its harts are run
    model = multicore_model or ('single' if lockstep == 'n/a (one core)' else 'unverified')
    return {'processor': processor, 'pipeline_stages': pipeline_stages, 'issue_width': issue_width, 'hw_threads_per_core': hw_threads_per_core,
            'vector': vector, 'lockstep': lockstep, 'citation': citation, 'to_read': to_read, 'multicore_model': model,
            'multicore_citation': multicore_citation or ('one core (the lockstep fact): nothing to share' if model == 'single' else ''), 'amp_with': amp_with}


_HZ3 = 'Hazard3 Readme (github Wren6991/Hazard3, read 2026-10-27): "Hazard3 is a 3-stage RISC-V processor"; extensions listed M, A, C, Zicsr, Zilsd, Zba, Zbb, Zbc, Zbs, Zbkb, Zbkx, Zcb, Zclsd, Zcmp (no V); the readme describes a single core and says nothing of issue width or lockstep'
_ONE = 'n/a (one core)'
_IDF_SMP = ('ESP-IDF Programming Guide, API reference "FreeRTOS (IDF)" (Espressif, Apache-2.0; searched 2026-10-28, INTERRUPT_POLL_BUDGET_PLAN §2d): the dual-core '
            'SMP kernel schedules both cores from one ready list; xTaskCreatePinnedToCore pins, tskNO_AFFINITY lets a task run on either core')
_FREERTOS_SMP = ('FreeRTOS SMP kernel (FreeRTOS project, MIT; searched 2026-10-28, INTERRUPT_POLL_BUDGET_PLAN §2d): merged to main after the 2021 SMP branch, '
                 'first ports XMOS xcore + RP2040; configUSE_CORE_AFFINITY, vTaskCoreAffinitySet(mask), tskNO_AFFINITY = any core; Pigweed (Apache-2.0) only mirrors it')

#: per processor (the chips-and-levels ladder keys + the QEMU virt machine). Single-core chips: lockstep n/a; multi-core: unverified until the datasheet is read.
HART_PARALLELISM = [
    _facts('qemu-virt-rv32', vector='configurable (QEMU -cpu options; unverified: the virt page read today does not list them)', lockstep='no',
           citation='virtual machine: pipeline / issue are not modelled (icount counts instructions, not cycles) - said on every number', to_read='QEMU docs: RISC-V CPU options (V extension flag)',
           multicore_model='smp', multicore_citation='QEMU "virt" machine: -smp N identical harts over one shared memory map (the hart count is the knob, ipb-6)'),
    _facts('rp2350', pipeline_stages=3, vector='none (the readme\'s extension list has no V)', lockstep='unverified', citation=_HZ3,
           to_read='RP2350 Datasheet (Raspberry Pi): whether the two cores can run in lockstep; Hazard3 issue width; whether mixed Arm + Hazard3 operation (amp) is supported',
           multicore_model='smp', multicore_citation=_FREERTOS_SMP + '; the RP2350 boots both cores as Arm OR both as Hazard3 (architecture select) - mixed operation unverified'),
    _facts('esp32c3', lockstep=_ONE, to_read='ESP32-C3 Technical Reference Manual, "CPU" chapter (pipeline depth); ESP32-C3 datasheet (no vector unit claimed - unverified)'),
    _facts('esp32c6', lockstep=_ONE, to_read='ESP32-C6 Technical Reference Manual, "CPU" chapter'),
    _facts('esp32p4', lockstep='unverified', to_read='ESP32-P4 Technical Reference Manual: CPU pipeline, the PIE / vector unit, any lockstep mode'),
    _facts('k210', lockstep='unverified', to_read='K210 datasheet (Kendryte): the two RV64GC cores'),
    _facts('ch32v003', lockstep=_ONE, to_read='QingKe V2A microprocessor manual (WCH): pipeline depth'),
    _facts('litex-vexriscv', lockstep='configurable', citation='VexRiscv is a generated core: pipeline depth and plugins are build parameters (said; the build not read)',
           to_read='the LiteX build\'s VexRiscv configuration (variant, pipeline plugins)'),
    _facts('milkv-duo', lockstep='unverified', to_read='CV1800B datasheet (Sophgo): the two C906 cores; the C906 user manual (pipeline, vector 0.7.1 draft support)'),
    _facts('atmega328p', vector='none', lockstep=_ONE, to_read='ATmega328P datasheet DS40002061B, "AVR CPU Core" (the "single level pipelining" sentence; issue width 1 by that sentence) - not re-read today'),
    _facts('atmega2560', vector='none', lockstep=_ONE, to_read='ATmega2560 datasheet, "AVR CPU Core"'),
    _facts('attiny85', vector='none', lockstep=_ONE, to_read='ATtiny85 datasheet, "AVR CPU Core"'),
    _facts('samd21g18a', lockstep=_ONE, to_read='Arm Cortex-M0+ Technical Reference Manual (pipeline depth); SAMD21 datasheet'),
    _facts('esp32-xtensa', lockstep='unverified', to_read='ESP32-S3 Technical Reference Manual: CPU (Xtensa LX7 pipeline), PIE (SIMD) chapter; any lockstep mode; the ULP chapter',
           multicore_model='smp', multicore_citation=_IDF_SMP, amp_with='ULP RISC-V co-processor (its own image and PC: amp beside the SMP pair; not a budget hart until D-ipb-6)'),
]

_BY_PROC = {f['processor']: f for f in HART_PARALLELISM}


def facts_for(processor):
    """The parallelism facts row for a processor key, or an all-unverified row that SAYS it has none."""
    return _BY_PROC.get(processor) or _facts(processor, to_read='no parallelism row for %r: add one in board.custom.parallelism' % processor)


def words(f):
    """One line for a hart row: 'pipeline 3 stages, issue -1, 1 hw thread/core, vector none, lockstep unverified, multicore smp'."""
    return 'pipeline %s, issue width %s, hw threads/core %s, vector %s, lockstep %s, multicore %s%s' % (
        ('%d stages' % f['pipeline_stages']) if f['pipeline_stages'] > 0 else '-1', f['issue_width'] if f['issue_width'] > 0 else '-1',
        f['hw_threads_per_core'] if f['hw_threads_per_core'] > 0 else '-1', f['vector'], f['lockstep'], f['multicore_model'], (' + amp ' + f['amp_with'].split(' (')[0]) if f['amp_with'] else '')


def is_lockstep(f):
    return f['lockstep'] == 'yes'


def is_smp(f):
    """ipb-8: may a null-affinity (`any`) task land on any hart of this chip? Only when one kernel schedules identical harts."""
    return f['multicore_model'] == 'smp'


def _tier(tier, title, kernel, license_, affinity_api, citation, to_read=''):
    return {'tier': tier, 'title': title, 'kernel': kernel, 'license': license_, 'affinity_api': affinity_api, 'citation': citation, 'to_read': to_read}


#: ipb-8 (§2d; D-ipb-11 recommended): the scheduler ladder as rows. `affinity_api` = how a task is pinned or left free on that tier.
SCHEDULER_TIERS = [
    _tier('bare-c', 'bare C: a superloop + interrupts', 'none', 'n/a', 'none: one stream per hart, placed by the build (hart_of)', 'no scheduler: the main loop IS the schedule'),
    _tier('freertos', 'FreeRTOS (single core)', 'FreeRTOS kernel', 'MIT', 'none: one core', 'FreeRTOS kernel (MIT) - the single-core build'),
    _tier('freertos-smp', 'FreeRTOS-SMP: one kernel over identical cores', 'FreeRTOS SMP kernel (+ the ESP-IDF variant on the S3)', 'MIT (IDF variant Apache-2.0)',
          'vTaskCoreAffinitySet(mask) / tskNO_AFFINITY (IDF: xTaskCreatePinnedToCore)', _FREERTOS_SMP + '; ' + _IDF_SMP),
    _tier('zephyr', 'Zephyr RTOS', 'Zephyr kernel (SMP when CONFIG_SMP)', 'Apache-2.0', 'k_thread_cpu_mask_* (cited when its row is read)', 'Zephyr Project (Apache-2.0)',
          to_read='Zephyr docs: "Symmetric Multiprocessing" (CONFIG_SMP, k_thread_cpu_mask_enable / _disable)'),
]


def tier_rows():
    return [dict(r) for r in SCHEDULER_TIERS]


def kind_rows():
    return [dict(r) for r in PARALLELISM_KINDS]


def hart_rows():
    return [dict(f, summary=words(f)) for f in HART_PARALLELISM]


def uncited_numbers():
    """[(processor, field)] - a numeric fact that is neither -1 nor backed by a citation (the selftest wants this EMPTY)."""
    return [(f['processor'], k) for f in HART_PARALLELISM for k in ('pipeline_stages', 'issue_width', 'hw_threads_per_core') if f[k] != -1 and not f['citation']]


if __name__ == '__main__':
    print(json.dumps({'kinds': kind_rows(), 'harts': hart_rows(), 'uncited': uncited_numbers()}, indent=1))
