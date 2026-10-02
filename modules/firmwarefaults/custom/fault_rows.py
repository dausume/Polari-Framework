"""
@module firmwarefaults.custom.fault_rows

ONE ROW PER FAULT KIND (FIRMWARE_SCENARIO_PLAN.md §1): which assumption it breaks, what you would observe, the
primitives involved, the remedies (Technique names), the rate and WHERE THE RATE COMES FROM, and which simulator can
force it today. A rate without a source is `unverified`; an estimate says so; a measured one names the run (the runner
writes `measured: run …` into TornReadFault's row after the natural run — the seed carries the plan's estimate).

    SEED_FAULT_ROWS = [(class_name, row_dict), ...]   — 7 concurrency + 6 physical-trigger + 3 space-safety
"""
import json

J = json.dumps
UNO = 'avr-twin (prf-board-engines: polari-avr-twin)'


def _f(cls, name, description, assumption, observable, primitives, remedies, rate=0.0, unit='', source='unverified', rtos=False,
       forcing='', notes='', **kind):
    row = {'name': name, 'description': description, 'assumption_broken': assumption, 'observable': observable,
           'primitives_json': J(primitives), 'remedies_json': J(remedies), 'rate': float(rate), 'rate_unit': unit, 'rate_source': source,
           'needs_rtos': rtos, 'forcing_status': forcing, 'provenance': 'sc-0 seed (FIRMWARE_SCENARIO_PLAN.md §1/§3/§3a)', 'notes': notes}
    row.update(kind)
    return cls, row


SEED_FAULT_ROWS = [
    # ---- concurrency: logic faults — the rate is the interleaving's probability, measured on the twin
    _f('TornReadFault', 'torn-read-g-ms', 'hal_millis reads the 4-byte tick g_ms in four `lds`; the tick ISR landing after the first '
       'one carries into byte 1, so 0x000000FF reads back as 0x000001FF (511): time jumps 256 ms ahead, then falls back.',
       'g-ms-read-atomic', 'uptime_ms goes BACKWARDS between consecutive frames (… 200, 511, 400 …) while every CRC passes — the wire is '
       'fine, the value is wrong', ['volatile-flag', 'irq-mask'], ['atomic-block', 'atomic-forceon'], rate=0.13,
       unit='torn reads per byte-0 carry of g_ms (one carry every 256 ms)',
       source='estimate ≈ 13 % (plan §5: a ~6-cycle window over a ~45-cycle idle loop) — the sc-0 natural run measures it',
       forcing='forcible on %s: irq-at-pc between the 1st and 2nd lds (scenario torn-millis-read)' % UNO,
       width_bytes=4, read_order='lo→hi (lds r22..r25 = g_ms+0..+3, avr-gcc 14.2.0 -Os)'),
    _f('DoubleGiveFault', 'double-give', 'A semaphore given twice for one event (a re-entered ISR, a ringing edge): the consumer runs twice.',
       'one-edge-one-interrupt', 'the work runs twice for one event (a count off by one)', ['semaphore'], ['debounce-synchroniser'],
       rtos=True, forcing='not yet: needs an RTOS target or the INT0 button variant (sc-1/sc-3)'),
    _f('LostWakeupFault', 'lost-wakeup', 'The give lands between the waiter\'s check and its sleep: the wakeup is lost.',
       'isr-latency-bounded', 'a task sleeps although its event happened; progress resumes only on the NEXT event', ['semaphore'],
       ['timeout-fsm'], rtos=True, forcing='not yet: needs an RTOS target (D-sc-4)'),
    _f('PriorityInversionFault', 'priority-inversion', 'The high task waits on a mutex the low task holds while a medium task runs.',
       'high-task-waits-cs', 'the high task misses its deadline by the medium task\'s run time', ['mutex'], ['priority-inheritance'],
       rtos=True, forcing='not yet: scenario 6 on the ESP32-C3 FreeRTOS twin (sc-3, D-sc-4 unconfirmed board)', bounded=False),
    _f('DeadlockFault', 'two-lock-deadlock', 'T1 takes A then B, T2 takes B then A; preempted between: both wait forever. A LOGIC '
       'property — physics only triggers it (plan §0).', 'locks-one-order', 'both tasks blocked; the wait-for graph has a cycle', ['mutex'],
       ['lock-ordering', 'watchdog'], rtos=True, forcing='not yet: scenario 7 (sc-3); SPIN/TLA+ proves the order',
       lock_cycle_json=J(['A', 'B', 'A'])),
    _f('LivelockFault', 'lost-ack-hang', 'A request whose ack is lost, with no timeout: the firmware waits (or retries) forever.',
       'every-message-arrives', 'the firmware never leaves WAIT; telemetry stops', ['queue'], ['timeout-fsm', 'watchdog'],
       forcing='not yet: drop-nth-frame is sc-1 and needs a request/ack variant (the boot-announced index, grpc-j4, not built)'),
    _f('StarvationFault', 'starvation', 'One party never gets the CPU or the lock because others always win (a busy ISR, a greedy task).',
       'isr-latency-bounded', 'a job\'s period stretches without bound under load', ['irq-mask'], ['timeout-fsm', 'watchdog'],
       forcing='not yet (sc-1: a UART flood at line rate against the main loop)'),
    # ---- physical triggers: physics breaks an assumption; the RATE comes from physics, sourced or unverified
    _f('UartBitErrorFault', 'uart-bit-error', 'A bit flips on the serial line; a byte is wrong; a framing error sets FE0 (the firmware never '
       'reads FE0/DOR0 today).', 'rejected-span-one-frame', 'frames lost per 1000 vs the bit error rate; the residual (a valid frame inside '
       'a rejected span) counted apart', [], ['crc-resync'], unit='errors per bit', source='unverified (no cited BER for the UNO\'s '
       'ATmega16U2 USB-CDC leg)', forcing='not yet: --uart-ber is sc-1 (scenario 4)', ber=0.0),
    _f('DoubleEdgeFault', 'contact-bounce', 'A mechanical contact bounces: several edges, several interrupts, for one press.',
       'one-edge-one-interrupt', 'a press counted twice', [], ['debounce-synchroniser'], unit='µs of bounce',
       source='unverified (switch bounce durations vary by part; none cited here)', forcing='not yet: needs the INT0 button variant (sc-1)',
       bounce_us=0.0),
    _f('MetastableInputFault', 'metastable-input', 'An asynchronous input sampled mid-transition resolves late or either way.',
       'one-edge-one-interrupt', 'a flag read as both values within one pass', [], ['debounce-synchroniser'], unit='MTBF (s)',
       source='unverified (MTBF parameters belong to the silicon; the Verilator rung)', forcing='not in scope (plan §9: waits for the Verilator rung)',
       mtbf_params_json=J({})),
    _f('BrownoutMidWriteFault', 'brownout-mid-write', 'The supply sags inside a multi-byte EEPROM write; the record is half new, half old.',
       'write-completes', 'a record with new field A and old field B', [], ['write-then-commit'], unit='V droop',
       source='BOD levels are fuse-set (ATmega328P datasheet, BODLEVEL fuse coding — page unverified); droop unverified',
       forcing='not yet: simavr has no BOD model — the harness will stop and reset (sc-1, scenario 5)', droop_v=0.0, droop_ms=0.0, bod_level_v=0.0),
    _f('BitFlipFault', 'sram-bit-flip', 'A stored bit changes by itself (an upset): a value, a pointer or a flag is wrong.', 'stack-fits',
       'a wrong value with a valid CRC (the frame is built from the flipped value)', [], ['crc-resync', 'watchdog'], unit='upsets per bit per day',
       source='unverified (SEU rates are cited only, plan §9)', forcing='forcible as a write today (--poke = corrupt-word); an XOR at a cycle is sc-1',
       upsets_per_bit_day=0.0),
    _f('ClockSkewFault', 'clock-skew', 'Two clocks disagree (resonator tolerance, temperature): the baud and the timeouts drift apart.',
       'one-clock', 'framing errors at the far end; timeouts firing early or late', [], ['crc-resync', 'timeout-fsm'], unit='ppm',
       source='the USART divisor error is cited (+2.1 % at UBRR0 16, U2X0 1 — DatasheetFact); resonator ppm unverified',
       forcing='not yet: one simavr clock cannot skew (sc-3 / Renode)', ppm=0.0),
    # ---- space / safety: space pressure is a cause
    _f('StackOverflowFault', 'stack-into-bss', 'The deepest call chain plus an ISR frame grows into .bss.', 'stack-fits',
       'silent corruption of the highest .bss variables', [], ['static-guard'], unit='bytes of headroom',
       source='measured per run (--sp-watch exact, --stack-fill paint, -fstack-usage static)', forcing='measured on every run (not forced)',
       headroom_bytes=0),
    _f('BufferOverrunFault', 'rx-ring-over-256', 'A ring larger than its index type (RX_RING 512 with uint8_t indices) silently uses 256 slots; '
       'with 16-bit indices the head read is two loads and DOES tear (scenario 1b).', 'rx-index-single-load',
       'stale slots popped, the parser sees garbage, the CRC fails and resyncs', ['spsc-ring'], ['static-guard'],
       source='a design fact of hal.c (plan §3 1b)', forcing='refused at build time since sc-0 (_Static_assert) — the fault cannot be built',
       buffer='rx_ring', bound=64),
    _f('MissedDeadlineFault', 'tick-late', 'The 1 ms tick ISR starts late because interrupts are masked or another ISR runs.',
       'isr-latency-bounded', 'max ISR latency (cycles) grows; at 16 000 cycles a tick is lost', ['irq-mask'], ['atomic-block'],
       unit='cycles', source='measured per run (--isr-latency)', forcing='measured on every run (not forced)', deadline_cycles=16000),
]


def by_class():
    out = {}
    for cls, row in SEED_FAULT_ROWS:
        out.setdefault(cls, []).append(row)
    return out
