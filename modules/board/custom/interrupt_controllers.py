"""
@module board.custom.interrupt_controllers

ipb-0 (INTERRUPT_POLL_BUDGET_PLAN.md §1, §4 ipb-0): the FACT rows a hart budget stands on — one `InterruptControllerKind` row per
controller family and one `HartFacts` row per processor the chips-and-levels ladder knows. Code-owned rows, never stored.

RISC-V IS THE CANONICAL VOCABULARY (his ruling 2026-10-27): every controller row answers the same RISC-V-named questions — the global
enable (`mstatus.MIE`), the per-source enable (`mie`), the pending bits (`mip`), the trap vector (`mtvec`), the cause (`mcause`), the
timer / external sources (CLINT / PLIC / CLIC), the idle instruction (`wfi`) and the cycle counter (`mcycle`). A chip on another ISA
carries the SAME fields with its own mechanism's name in them: that is the adaptation row, shown beside the number on the page.

EVERY NUMBER IS CITED OR -1 (rule `derive-or-cite-chip-data`). `citation` names the document read; `to_read` names the document that
would fill a -1. Numbers read 2026-10-27: the RISC-V PLIC specification (github riscv/riscv-plic-spec, Ratified), the QEMU `virt`
machine page (qemu.org docs/master/system/riscv/virt), the Hazard3 Readme (github Wren6991/Hazard3). The ATmega328P datasheet
(DS40002061B) and the Arm TRMs were NOT re-read today: their names are definitional, their cycle numbers stay -1.

    python3 -m board.custom.interrupt_controllers            # prints the rows
"""
import json

NESTING = ('hardware', 'software', 'none', 'unverified')
OPEN = ('open', 'closed', 'unverified')

_PRIV = 'The RISC-V Instruction Set Manual Volume II: Privileged Architecture (CSR names: mstatus.MIE, mie, mip, mtvec, mcause; not re-read today)'
_PLIC = 'RISC-V Platform-Level Interrupt Controller Specification, Ratified (github riscv/riscv-plic-spec, read 2026-10-27)'
_QEMU = 'QEMU docs, "RISC-V virt board" (qemu.org/docs/master/system/riscv/virt.html, read 2026-10-27)'
_HZ3 = 'Hazard3 Readme (github Wren6991/Hazard3, read 2026-10-27)'


def _row(name, title, isa, **kw):
    r = {'name': name, 'title': title, 'isa': isa,
         'global_enable': '', 'per_source_enable': '', 'pending': '', 'vector_mode': '', 'cause': '',
         'priority_levels': -1, 'priority_0_meaning': '', 'nesting': 'unverified', 'entry_latency_cycles': -1, 'exit_instruction': '',
         'timer_source': '', 'external_source': '', 'idle_instruction': '', 'cycle_counter': '', 'max_sources': -1,
         'spec_openness': 'unverified', 'citation': '', 'to_read': '', 'notes': ''}
    r.update(kw)
    return r


#: one row per controller family. RISC-V rows first (the basis); the others are adaptation rows in the same fields.
CONTROLLERS = [
    _row('riscv-clint-plic', 'RISC-V: CLINT timer/software + PLIC external (the QEMU virt / SiFive-style layout)', 'riscv',
         global_enable='mstatus.MIE', per_source_enable='mie (MTIE timer, MSIE software, MEIE external)', pending='mip (MTIP, MSIP, MEIP)',
         vector_mode='mtvec MODE 0 = direct (one entry), 1 = vectored (base + 4 x cause)', cause='mcause (interrupt bit + code)',
         priority_levels=-1, priority_0_meaning='PLIC priority 0 = "never interrupt" (disables the source); the number of levels is platform-specific',
         nesting='none', entry_latency_cycles=-1, exit_instruction='mret',
         timer_source='CLINT mtime / mtimecmp (SiFive de facto; ACLINT is its standardisation - QEMU aclint=on)',
         external_source='PLIC: per-target threshold, claim (returns the highest-priority pending id, clears pending) / complete (write the id back)',
         idle_instruction='wfi', cycle_counter='mcycle / rdcycle', max_sources=1023,
         spec_openness='open', citation='%s; %s' % (_PLIC, _PRIV),
         notes='PLIC: "provides no concept of interrupt preemption or nesting" - nesting is software; ties broken by the lower interrupt id; the spec gives no '
               'latency bound ("might take some time"); 1023 usable sources (id 0 = none), contexts up to 15872. Entry latency is per core: -1 here.'),
    _row('riscv-clic', 'RISC-V: CLIC (core-local, levels + selective hardware vectoring)', 'riscv',
         global_enable='mstatus.MIE', per_source_enable='clicintie[i]', pending='clicintip[i]', vector_mode='mtvec + mtvt (selective vectoring per source)',
         cause='mcause (+ level / priority fields)', nesting='hardware', exit_instruction='mret', timer_source='CLIC timer source', external_source='CLIC (replaces PLIC for the core)',
         idle_instruction='wfi', cycle_counter='mcycle / rdcycle', spec_openness='open',
         citation='', to_read='RISC-V CLIC specification (github riscv/riscv-fast-interrupt) - its ratification state, level count and vectoring rules; NOT read today',
         notes='Named here so an ESP32-P4 / CLIC chip has a row; every field beyond the CSR names is unverified until the spec is read.'),
    _row('riscv-hazard3', 'RISC-V: Hazard3 (RP2350) - standard mie/mip plus its own interrupt-priority extension', 'riscv',
         global_enable='mstatus.MIE', per_source_enable='mie + the Xh3irq per-IRQ enables', pending='mip + the Xh3irq pending array',
         vector_mode='mtvec (direct / vectored)', cause='mcause', priority_levels=-1, nesting='unverified', entry_latency_cycles=-1, exit_instruction='mret',
         timer_source='machine timer (mtime / mtimecmp)', external_source='Xh3irq (Hazard3\'s external interrupt controller extension)',
         idle_instruction='wfi', cycle_counter='mcycle (Zicsr present)', max_sources=-1, spec_openness='open',
         citation='%s: RV32I or RV32E; optional M, A, C, Zicsr, Zilsd, Zba, Zbb, Zbc, Zbs, Zbkb, Zbkx, Zcb, Zclsd, Zcmp; Machine + User + Debug modes; '
                  'wfi; PMP up to 16 regions; the RP2350 configuration = 4.15 CoreMark/MHz' % _HZ3,
         to_read='RP2350 datasheet, the Hazard3 chapter (Xh3irq: IRQ count, priority levels, preemption, entry latency) - NOT read today',
         notes='The Readme names no licence; the ladder row cites Apache-2.0 (memory riscv-cores-reference).'),
    _row('riscv-esp32c3-matrix', 'RISC-V: ESP32-C3 interrupt matrix (Espressif core)', 'riscv',
         global_enable='mstatus.MIE', per_source_enable='mie + the interrupt matrix (peripheral source -> CPU interrupt slot)', pending='mip',
         vector_mode='mtvec vectored', cause='mcause', priority_levels=-1, nesting='unverified', entry_latency_cycles=-1, exit_instruction='mret',
         timer_source='SYSTIMER / machine timer', external_source='interrupt matrix', idle_instruction='wfi', cycle_counter='mcycle', spec_openness='open',
         citation='', to_read='ESP32-C3 Technical Reference Manual, "Interrupt Matrix" + "Interrupt Controller" chapters - NOT read today',
         notes='Open ISA, closed core RTL: the matrix\'s slot count and levels come only from the TRM.'),
    _row('avr-vectors', 'AVR (ATmega328P): a fixed vector table, one global enable bit', 'avr',
         global_enable='SREG I bit (sei / cli) = mstatus.MIE', per_source_enable='each peripheral\'s enable bit (e.g. UCSR0B.RXCIE0) = mie',
         pending='each peripheral\'s flag bit (e.g. UCSR0A.RXC0) = mip', vector_mode='fixed vector table at program address 0x0000 (vectored only) = mtvec vectored',
         cause='implied by the vector taken = mcause', priority_levels=-1, priority_0_meaning='priority is the vector order: the lower address wins',
         nesting='software', entry_latency_cycles=-1, exit_instruction='reti', timer_source='TIMER0/1/2 compare / overflow vectors', external_source='INT0 / INT1 / PCINT',
         idle_instruction='sleep', cycle_counter='none on the chip (the simavr twin\'s own counter: board.custom.cycle_measure)', max_sources=-1, spec_openness='closed',
         citation='', to_read='ATmega328P datasheet DS40002061B, "Reset and Interrupt Handling" + "Interrupt Response Time" (minimum entry cycles, reti cycles, vector count) - NOT read today',
         notes='The I bit is cleared on entry and a handler may set it again (software nesting). Closed core, public datasheet, open tooling (avr-gcc, avr-libc, avrdude, simavr).'),
    _row('arm-nvic', 'Arm Cortex-M NVIC', 'arm-m',
         global_enable='PRIMASK (cpsie i / cpsid i) = mstatus.MIE; BASEPRI masks below a level', per_source_enable='NVIC_ISER / ICER = mie', pending='NVIC_ISPR / ICPR = mip',
         vector_mode='VTOR vector table (vectored only) = mtvec vectored', cause='IPSR exception number = mcause', priority_levels=-1,
         priority_0_meaning='0 is the HIGHEST priority (inverse of the PLIC)', nesting='hardware', entry_latency_cycles=-1, exit_instruction='bx lr with EXC_RETURN',
         timer_source='SysTick', external_source='NVIC', idle_instruction='wfi / wfe', cycle_counter='DWT_CYCCNT (where DWT is present)', max_sources=-1, spec_openness='closed',
         citation='', to_read='Arm Cortex-M0+ TRM (SAMD21) and Cortex-M33 TRM: priority bits, entry latency, nesting / grouping - NOT read today',
         notes='Closed core (Arm IP), open tooling (gcc, OpenOCD, QEMU).'),
    _row('xtensa-matrix', 'Xtensa LX7 (ESP32-S3) interrupt matrix', 'xtensa',
         global_enable='PS.INTLEVEL = mstatus.MIE', per_source_enable='INTENABLE + the interrupt matrix = mie', pending='INTERRUPT register = mip',
         vector_mode='per-level vector table (vectored only) = mtvec vectored', cause='INTERRUPT / EXCCAUSE = mcause', priority_levels=-1, nesting='hardware',
         entry_latency_cycles=-1, exit_instruction='rfi', timer_source='CCOMPARE timers', external_source='interrupt matrix', idle_instruction='waiti',
         cycle_counter='CCOUNT', max_sources=-1, spec_openness='closed',
         citation='', to_read='ESP32-S3 Technical Reference Manual, "Interrupt Matrix" - NOT read today',
         notes='An ISA exception on the bench (the Elecrow board); shown as one.'),
]


def _hart(processor, title, isa, harts, controller, clock_hz, clock_citation, isa_open, rtl_open, silicon_open, tooling_open, boards=(), notes='', harts_note=''):
    return {'processor': processor, 'title': title, 'isa': isa, 'harts': harts, 'harts_note': harts_note, 'controller': controller,
            'clock_hz': clock_hz, 'clock_citation': clock_citation, 'isa_open': isa_open, 'core_rtl_open': rtl_open, 'silicon_open': silicon_open,
            'tooling_open': tooling_open, 'boards': list(boards), 'notes': notes}


_LADDER = 'chips-and-levels ladder row %s (board.custom.chip_ladder, its own citations)'

#: one row per processor the ladder knows (key = the ladder entry name) + the open virtual machine the RISC-V test cases run on.
HARTS = [
    _hart('qemu-virt-rv32', 'QEMU RISC-V virt (RV32GC; generic virtual platform, not real silicon)', 'riscv', -1, 'riscv-clint-plic', -1,
          'virtual: no clock - counts are icount (instructions), said on every number', 'open', 'open', 'open', 'open', boards=('qemu-virt-rv32',),
          harts_note='configurable with -smp: up to 512 generic cores (QEMU docs); TC-A1 uses 2', notes='%s: CLINT + PLIC by default, aclint=on / aia=aplic options, one or two NS16550 UARTs; "does not correspond to any real hardware"' % _QEMU),
    _hart('rp2350', 'RP2350: two Hazard3 RV32IMAC harts (the open-RTL pick; Arm cores not used here)', 'riscv', 2, 'riscv-hazard3', 150000000, _LADDER % 'rp2350',
          'open', 'open', 'closed', 'open', boards=('rpi-pico2',), harts_note='two Hazard3 harts when the RISC-V cores are selected (the chip also holds two Cortex-M33)'),
    _hart('esp32c3', 'ESP32-C3: one RV32IMC hart', 'riscv', 1, 'riscv-esp32c3-matrix', 160000000, _LADDER % 'esp32c3', 'open', 'closed', 'closed', 'open', boards=('esp32-c3-devkitm-1',)),
    _hart('esp32c6', 'ESP32-C6: one RV32IMAC hart + a low-power core', 'riscv', 1, 'riscv-esp32c3-matrix', 160000000, _LADDER % 'esp32c6', 'open', 'closed', 'closed', 'open',
          boards=('esp32-c6-devkitc-1',), harts_note='the LP core is a second PC (D-ipb-6 kind) - not counted until its ISA row is read'),
    _hart('esp32p4', 'ESP32-P4: two RV32 harts + a low-power core', 'riscv', 2, 'riscv-clic', 400000000, _LADDER % 'esp32p4', 'open', 'closed', 'closed', 'open',
          boards=('esp32-p4-function-ev-board',), harts_note='the LP core not counted (as the C6)', notes='controller = CLIC is unverified (to read: the P4 TRM)'),
    _hart('k210', 'K210: two RV64GC harts', 'riscv', 2, 'riscv-clint-plic', 400000000, _LADDER % 'k210', 'open', 'closed', 'closed', 'open', boards=('sipeed-maix-bit',),
          notes='CLINT + PLIC layout unverified (to read: the K210 datasheet)'),
    _hart('ch32v003', 'CH32V003: one QingKe RV32EC hart', 'riscv', 1, 'riscv-clic', 48000000, _LADDER % 'ch32v003', 'open', 'closed', 'closed', 'open', boards=('ch32v003-dev-board',),
          notes='its PFIC controller is CLIC-like: unverified (to read: the CH32V003 reference manual)'),
    _hart('litex-vexriscv', 'VexRiscv soft core on an ECP5 (open RTL, generated Verilog)', 'riscv', 1, 'riscv-clint-plic', -1, 'the LiteX build sets the clock: -1 until a build is read',
          'open', 'open', 'closed', 'open', boards=('orangecrab',), notes='the FPGA is closed silicon; the core and the bitstream flow are open'),
    _hart('milkv-duo', 'Sophgo CV1800B: a Linux C906 hart + an RTOS C906 hart (different clocks)', 'riscv', 2, 'riscv-clint-plic', 1000000000, _LADDER % 'milkv-duo',
          'open', 'closed', 'closed', 'open', boards=('milkv-duo', 'milkv-duo-s'), harts_note='clock_hz is hart 0\'s (1 GHz); hart 1 runs at 700 MHz (ladder)'),
    _hart('atmega328p', 'ATmega328P (Arduino UNO R3): one AVR core', 'avr', 1, 'avr-vectors', 16000000, 'the uno-light cycle record (clock_hz, measured on the simavr twin) + %s' % (_LADDER % 'atmega328p'),
          'closed', 'closed', 'closed', 'open', boards=('arduino-uno-r3', 'arduino-nano')),
    _hart('atmega2560', 'ATmega2560: one AVR core', 'avr', 1, 'avr-vectors', 16000000, _LADDER % 'atmega2560', 'closed', 'closed', 'closed', 'open', boards=('arduino-mega-2560',)),
    _hart('attiny85', 'ATtiny85: one AVR core', 'avr', 1, 'avr-vectors', -1, 'the ladder row states no clock (internal RC; -1)', 'closed', 'closed', 'closed', 'open', boards=('attiny85-dip',)),
    _hart('samd21g18a', 'ATSAMD21G18A (Arduino Zero, Feather M0): one Cortex-M0+', 'arm-m', 1, 'arm-nvic', 48000000, _LADDER % 'samd21g18a', 'closed', 'closed', 'closed', 'open',
          boards=('arduino-zero', 'adafruit-feather-m0-express')),
    _hart('esp32-xtensa', 'ESP32-S3: two Xtensa LX7 harts + a low-power core (the Elecrow board; an ISA exception)', 'xtensa', 2, 'xtensa-matrix', 240000000,
          _LADDER % 'esp32-xtensa' + ' (chip READ over USB 2026-10-24: dual core, 240 MHz)', 'closed', 'closed', 'closed', 'open', boards=('elecrow-esp32-eval',),
          harts_note='the LP core not counted'),
]

_BY_NAME = {r['name']: r for r in CONTROLLERS}
_BY_PROC = {r['processor']: r for r in HARTS}
_BY_BOARD = {b: r for r in HARTS for b in r['boards']}


def controller(name):
    return _BY_NAME.get(name)


def hart_facts(processor):
    """The HartFacts row for a ladder entry name / soc key, else None."""
    return _BY_PROC.get(processor)


def facts_for_board(board):
    """The HartFacts row for a dev / eval board key (e.g. arduino-uno-r3), else None."""
    return _BY_BOARD.get(board)


def openness_words(f):
    return 'ISA %s / core RTL %s / silicon %s / tooling %s' % (f['isa_open'], f['core_rtl_open'], f['silicon_open'], f['tooling_open'])


def controller_rows():
    return [dict(r) for r in CONTROLLERS]


def hart_rows():
    out = []
    for f in HARTS:
        c = _BY_NAME[f['controller']]
        out.append(dict(f, boards=', '.join(f['boards']), controller_title=c['title'], openness=openness_words(f),
                        harts_text=('%d' % f['harts']) if f['harts'] >= 0 else 'configurable', clock_text=('%g MHz' % (f['clock_hz'] / 1e6)) if f['clock_hz'] > 0 else 'unverified / virtual'))
    return out


def uncited_numbers():
    """[(row, field)] - every numeric fact that is neither -1 nor backed by a citation (the selftest wants this EMPTY)."""
    bad = []
    for r in CONTROLLERS:
        for k in ('priority_levels', 'entry_latency_cycles', 'max_sources'):
            if r[k] != -1 and not r['citation']:
                bad.append((r['name'], k))
    for f in HARTS:
        if f['clock_hz'] != -1 and not f['clock_citation']:
            bad.append((f['processor'], 'clock_hz'))
    return bad


if __name__ == '__main__':
    print(json.dumps({'controllers': controller_rows(), 'harts': hart_rows(), 'uncited': uncited_numbers()}, indent=1))
