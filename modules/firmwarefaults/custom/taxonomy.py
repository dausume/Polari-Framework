"""
@module firmwarefaults.custom.taxonomy

THE TAXONOMY AS ROWS (FIRMWARE_SCENARIO_PLAN.md §1, §4): the UNO's concurrency primitives (and the RTOS ones the
faults name), the assumptions the UNO firmware makes, and the techniques that restore them — each with what it costs.
Costs are the disassembly's or the literature's ESTIMATE (`cost_source` says which) until a scenario pair measures
them on the twin (`measured_*`, written by the runner). The fault rows themselves are in custom/fault_rows.py.

Every number here is cited, read from the disassembly of the shipped build (avr-gcc 14.2.0 -Os, plan §3), or labelled
`unverified` — never a silent guess (his rule 2026-09-26).
"""
import json

HAL = 'board/custom/firmware/uno/hal.c'
APP = 'board/custom/firmware/uno/apps/sim_rig.c'


def _p(name, kind, description, needs_rtos=False, cycles=0, uno=False, where='', notes=''):
    return {'name': name, 'description': description, 'kind': kind, 'needs_rtos': needs_rtos, 'typical_cost_cycles': cycles,
            'uno_uses': uno, 'where': where, 'provenance': 'sc-0 seed (FIRMWARE_SCENARIO_PLAN.md §1)', 'notes': notes}


SEED_PRIMITIVES = [
    _p('irq-mask', 'irq-mask', 'Interrupts masked around a critical section: `in r18,SREG; cli` … `out SREG,r18` '
       '(avr-libc ATOMIC_BLOCK(ATOMIC_RESTORESTATE)) — the UNO\'s hal_millis.', cycles=3, uno=True, where=HAL + ':hal_millis',
       notes='3 cycles per use (in 1 + cli 1 + out 1, plan §3 disassembly); every ISR waits while it is held'),
    _p('volatile-flag', 'volatile-flag', 'A `volatile` variable an ISR writes and the main loop reads — g_ms (4 bytes: NOT atomic '
       'on an 8-bit core by itself) and the ring indices (1 byte: atomic).', uno=True, where=HAL + ':g_ms, rx_head, rx_tail',
       notes='volatile stops the compiler caching it; it does NOT make a multi-byte read atomic'),
    _p('spsc-ring', 'spsc-ring', 'A single-producer single-consumer byte ring: the RX ISR writes rx_head only, the main loop '
       'writes rx_tail only; uint8_t indices are one `lds` each, so it cannot tear (plan §3).', uno=True,
       where=HAL + ':ISR(USART_RX_vect), hal_rx_pop', notes='correct only while each index has ONE writer and fits one load (RX_RING <= 256)'),
    _p('semaphore', 'semaphore', 'A counting / binary semaphore (an RTOS primitive): give from an ISR, take in a task.', needs_rtos=True,
       notes='not on the UNO (no RTOS); named by DoubleGiveFault / LostWakeupFault'),
    _p('mutex', 'mutex', 'A mutual-exclusion lock owned by one task (an RTOS primitive; FreeRTOS mutexes carry priority inheritance).',
       needs_rtos=True, notes='not on the UNO; named by PriorityInversionFault / DeadlockFault (scenarios 6–7, the ESP32-C3, D-sc-4)'),
    _p('queue', 'queue', 'A message queue between tasks or from an ISR to a task (an RTOS primitive).', needs_rtos=True,
       notes='not on the UNO'),
]


def _a(name, statement, who, checkable='scenario', holds='yes', holder='arduino-uno-r3 template (board/custom/firmware/uno)', notes=''):
    return {'name': name, 'statement': statement, 'holder': holder, 'who_relies': who, 'checkable_by': checkable,
            'holds_in_shipped': holds, 'provenance': 'sc-0 seed (FIRMWARE_SCENARIO_PLAN.md §0/§3)', 'notes': notes}


SEED_ASSUMPTIONS = [
    _a('g-ms-read-atomic', 'A 32-bit read of g_ms in hal_millis sees ONE tick\'s value — the tick ISR cannot change it between the '
       'four loads.', HAL + ':hal_millis; ' + APP + ':main ((int32_t)(now - next_ms) < 0)', notes='true in the shipped build (ATOMIC_BLOCK); '
       'false in uno-sim-rig-torn (HAL_MILLIS_ATOMIC 0) — scenario torn-millis-read'),
    _a('rx-index-single-load', 'rx_head and rx_tail are each read in ONE instruction, so the ISR and the main loop never see half an '
       'index.', HAL + ':hal_rx_pop, ISR(USART_RX_vect)', checkable='static', notes='holds while RX_RING <= 256 (uint8_t indices); the '
       '_Static_assert in hal.c refuses any other build (scenario rx-ring-over-256)'),
    _a('rx-spsc-one-writer', 'Each ring index has exactly one writer (head: the ISR; tail: the main loop).', HAL + ':rx_head, rx_tail',
       checkable='static'),
    _a('every-message-arrives', 'Every frame / ack sent is received.', 'a request/ack variant (none yet; grpc-j4\'s boot-announced '
       'index handshake would be the first)', holds='n/a', notes='scenario 2 (sc-1): drop-nth-frame'),
    _a('one-edge-one-interrupt', 'One press or one transition raises one interrupt.', 'a button-on-INT0 variant (kit project 02; none '
       'yet)', holds='n/a', notes='scenario 3 (sc-1)'),
    _a('rejected-span-one-frame', 'A byte span the parser rejects holds at most one frame.', 'grpcbridge c_twin polari_rx_feed (the '
       'generated header)', holds='no', notes='GRPC_BRIDGE_PLAN Finding 3: a valid frame inside a rejected span is lost — scenario 4 (sc-1)'),
    _a('write-completes', 'A multi-byte persistent write completes once started.', 'an EEPROM-record variant (none yet)', holds='n/a',
       notes='scenario 5 (sc-1); simavr has no brown-out model — the harness emulates stop-and-reset'),
    _a('locks-one-order', 'Every task takes locks in one global order.', 'an RTOS target (ESP32-C3 FreeRTOS, D-sc-4)', holds='n/a',
       holder='an RTOS firmware (sc-3)'),
    _a('high-task-waits-cs', 'A high-priority task waits at most one critical section of a lower one.', 'an RTOS target (D-sc-4)',
       holds='n/a', holder='an RTOS firmware (sc-3)'),
    _a('stack-fits', 'The deepest call chain plus one ISR frame fits between the end of .bss and RAMEND.', 'every UNO variant '
       '(2048 B SRAM)', checkable='scenario', notes='measured per run: --sp-watch (exact), --stack-fill (paint), -fstack-usage (static)'),
    _a('isr-latency-bounded', 'Every ISR starts within a bounded number of cycles of its flag — interrupts are never masked for long.',
       'every ISR (the 1 ms tick: TIMER2_COMPA)', notes='the atomic section adds its masked window; --isr-latency measures it'),
    _a('one-clock', 'Both ends of the serial link agree on time within the baud tolerance.', 'USART0 at 115200 Bd (UBRR0 16, U2X0 1: '
       '+2.1 %, DatasheetFact)', holds='yes', notes='ClockSkewFault; one simavr clock cannot skew (sc-3 / Renode)'),
]


def _t(name, description, restores, primitive='', idiom='', b=0, c=0, lat=0, source='estimate', alt='', caveats='', notes=''):
    return {'name': name, 'description': description, 'restores': restores, 'primitive': primitive, 'idiom_c': idiom,
            'typical_cost_bytes': b, 'typical_cost_cycles': c, 'typical_latency_cycles': lat, 'cost_source': source,
            'measured_cost_bytes': 0, 'measured_cost_cycles': 0, 'measured_latency_delta_cycles': 0, 'measured_by_run': '',
            'alternative_of': alt, 'caveats': caveats, 'provenance': 'sc-0 seed (FIRMWARE_SCENARIO_PLAN.md §1/§3)', 'notes': notes}


SEED_TECHNIQUES = [
    _t('atomic-block', 'Mask interrupts across the multi-byte read and restore SREG after: the tick lands after the read, never inside it.',
       'g-ms-read-atomic', 'irq-mask', 'ATOMIC_BLOCK(ATOMIC_RESTORESTATE) { v = g_ms; }   /* <util/atomic.h> */', b=6, c=3, lat=9,
       source='disassembly (plan §3, avr-gcc 14.2.0 -Os): in + cli + out = 3 words / 3 cycles; masked ≈ four 2-cycle lds + out ≈ 9 cycles',
       caveats='every ISR waits up to the masked window; never call something slow inside it'),
    _t('atomic-forceon', 'The same section without saving SREG: ATOMIC_FORCEON re-enables interrupts unconditionally.', 'g-ms-read-atomic',
       'irq-mask', 'ATOMIC_BLOCK(ATOMIC_FORCEON) { v = g_ms; }', b=4, c=2, lat=9, alt='atomic-block',
       source='plan §3: saves the `in` (−2 B, −1 cycle) vs atomic-block',
       caveats='only correct where interrupts are KNOWN to be on — called with them off it turns them on (an alternative row, not the default)'),
    _t('static-guard', 'Refuse the vulnerable build at compile time: a _Static_assert on the index width, so the race cannot be built.',
       'rx-index-single-load', '', '_Static_assert(RX_RING <= 256u && (RX_RING & (RX_RING - 1u)) == 0u, "…uint8_t indices…");', b=0, c=0,
       lat=0, source='a compile-time check: no code is emitted', caveats='guards what the compiler can see; a runtime size needs a runtime check'),
    _t('timeout-fsm', 'A timeout on every wait plus an explicit state machine: a lost ack becomes a retry, never a hang.',
       'every-message-arrives', '', 'if ((int32_t)(hal_millis() - t0) > ACK_TIMEOUT_MS) state = RETRY;', source='unverified (not measured; sc-1)'),
    _t('crc-resync', 'A CRC per frame and a parser that resyncs one byte later: a corrupted frame is dropped, the next one is read.',
       'rejected-span-one-frame', '', 'if (crc32(frame) != rx_crc) { shift one byte; hunt for the magic again; }',
       source='the shipped parser (c_twin polari_rx_feed); cost unverified', caveats='a CRC does NOT catch a wrong VALUE sent on a correct '
       'wire — the torn read passes its CRC (plan §3)'),
    _t('debounce-synchroniser', 'Qualify an edge by time (a timer-checked debounce) on an MCU; a two-flop synchroniser on an FPGA.',
       'one-edge-one-interrupt', '', 'if ((uint16_t)(now - last_edge) < DEBOUNCE_MS) return; last_edge = now;', source='unverified (sc-1)'),
    _t('watchdog', 'A hardware watchdog kicked from the main loop only: a hang resets the board instead of freezing it.',
       'every-message-arrives', '', 'wdt_enable(WDTO_250MS); … wdt_reset(); /* in the loop, never in an ISR */',
       source='unverified', notes='no UNO variant enables the WDT today (verified: no wdt_ in hal.c or the apps, plan §4)'),
    _t('write-then-commit', 'Write the new record, then a commit flag (or two copies with a sequence + CRC): a cut write is detected.',
       'write-completes', '', 'eeprom_update_block(&rec, slot, sizeof rec); eeprom_update_byte(commit, seq);', source='unverified (sc-1)'),
    _t('lock-ordering', 'Take locks in one global order (or try-lock with back-off): no circular wait can form.', 'locks-one-order', 'mutex',
       'xSemaphoreTake(lockA, …); xSemaphoreTake(lockB, …);   /* everywhere A before B */', source='unverified (sc-3)'),
    _t('priority-inheritance', 'A mutex that lends the waiter\'s priority to the holder: the wait is bounded by the critical section.',
       'high-task-waits-cs', 'mutex', 'xSemaphoreCreateMutex();   /* FreeRTOS mutexes inherit; binary semaphores do not */',
       source='unverified (sc-3); ESP-IDF FreeRTOS inheritance unverified (plan §3a)'),
]


def techniques_by_name():
    return {t['name']: t for t in SEED_TECHNIQUES}


def assumption_names():
    return [a['name'] for a in SEED_ASSUMPTIONS]


def primitive_names():
    return [p['name'] for p in SEED_PRIMITIVES]


def dumps(v):
    return json.dumps(v)
