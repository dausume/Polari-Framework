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


def _p(name, kind, description, needs_rtos=False, cycles=0, uno=False, site='', notes=''):
    # fw-2: `site`, not `where` (a SQLite reserved word — see ConcurrencyPrimitive.py)
    return {'name': name, 'description': description, 'kind': kind, 'needs_rtos': needs_rtos, 'typical_cost_cycles': cycles,
            'uno_uses': uno, 'site': site, 'provenance': 'sc-0 seed (FIRMWARE_SCENARIO_PLAN.md §1)', 'notes': notes}


SEED_PRIMITIVES = [
    _p('irq-mask', 'irq-mask', 'Interrupts masked around a critical section: `in r18,SREG; cli` … `out SREG,r18` '
       '(avr-libc ATOMIC_BLOCK(ATOMIC_RESTORESTATE)) — the UNO\'s hal_millis.', cycles=3, uno=True, site=HAL + ':hal_millis',
       notes='3 cycles per use (in 1 + cli 1 + out 1, plan §3 disassembly); every ISR waits while it is held'),
    _p('volatile-flag', 'volatile-flag', 'A `volatile` variable an ISR writes and the main loop reads — g_ms (4 bytes: NOT atomic '
       'on an 8-bit core by itself) and the ring indices (1 byte: atomic).', uno=True, site=HAL + ':g_ms, rx_head, rx_tail',
       notes='volatile stops the compiler caching it; it does NOT make a multi-byte read atomic'),
    _p('spsc-ring', 'spsc-ring', 'A single-producer single-consumer byte ring: the RX ISR writes rx_head only, the main loop '
       'writes rx_tail only; uint8_t indices are one `lds` each, so it cannot tear (plan §3).', uno=True,
       site=HAL + ':ISR(USART_RX_vect), hal_rx_pop', notes='correct only while each index has ONE writer and fits one load (RX_RING <= 256)'),
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
    _a('every-message-arrives', 'Every frame / ack sent is received.', 'board/custom/firmware/uno/apps/scenario_rig.c' + ':main (SC_ACK_WAIT: the request/ack of variants uno-ack-wait '
       '/ uno-ack-wait-timeout)', holds='n/a', notes='no shipped variant waits for an ack; scenario lost-ack-hang (sc-1) drops the first '
       'one — uno-ack-wait relies on it, uno-ack-wait-timeout does not'),
    _a('one-edge-one-interrupt', 'One press or one transition raises one interrupt.', HAL + ':ISR(INT0_vect) (HAL_INT0: variants '
       'uno-button-count / uno-button-debounce)', holds='n/a', notes='scenario button-bounce-double-count (sc-1)'),
    _a('rejected-span-one-frame', 'A byte span the parser rejects holds at most one frame.', 'grpcbridge c_twin polari_rx_feed (the '
       'generated header)', holds='no', notes='GRPC_BRIDGE_PLAN Finding 3: a valid frame inside a rejected span is lost — scenario 4 (sc-1)'),
    _a('write-completes', 'A multi-byte persistent write completes once started.', 'board/custom/firmware/uno/apps/scenario_rig.c' + ':record_write (SC_EEPROM_RECORD: variants '
       'uno-eeprom-record / uno-eeprom-commit)', holds='n/a',
       notes='scenario brownout-mid-eeprom-write (sc-1); simavr has no brown-out model — the harness stops the core and avr_reset()s it'),
    _a('main-loop-returns', 'Every main-loop pass comes back to the top of the loop (nothing waits forever, no runaway).',
       APP + ':main (and every app\'s for (;;))', notes='sc-1 plan §4: no shipped variant enables the watchdog, so a pass that never '
       'returns freezes the board; uno-sim-rig-wdt (HAL_WDT 1) restores it — scenario runaway-hang-watchdog'),
    _a('locks-one-order', 'Every task takes locks in one global order.', 'board/custom/firmware/esp32c3/apps/two_lock.c:round_of (variants '
       'c3-two-lock / c3-two-lock-ordered / c3-two-lock-backoff)', holds='n/a', holder='the ESP32-C3 two_lock app (sc-3)',
       notes='scenario two-lock-deadlock (sc-3): BEFORE breaks it (T2 takes B then A)'),
    _a('high-task-waits-cs', 'A high-priority task waits at most one critical section of a lower one.',
       'board/custom/firmware/esp32c3/apps/prio_inversion.c:task_h (variants c3-prio-inversion / c3-prio-inversion-mutex)',
       holds='n/a', holder='the ESP32-C3 prio_inversion app (sc-3)', notes='scenario priority-inversion-mutex (sc-3): a binary semaphore breaks it'),
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
            'measured_ram_bytes': 0, 'measured_cost_what': '',
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
    _t('timeout-fsm', 'A timeout on every wait plus an explicit state machine: a lost ack becomes a retry, never a hang (the task\'s '
       '`timeout+state-machine`).', 'every-message-arrives', '',
       'switch (state) { case WAITING: if (acked) state = ACKED; else if ((int32_t)(now - deadline) >= 0) { resend(); deadline = now + T; } }',
       source='sc-1 measures it (scenario lost-ack-hang: uno-ack-wait → uno-ack-wait-timeout, ack_step() per pass)'),
    _t('crc-resync', 'A CRC per frame and a parser that resyncs one byte later: a corrupted frame is dropped, the next one is read.',
       'rejected-span-one-frame', '', 'if (crc32(frame) != rx_crc) { shift one byte; hunt for the magic again; }',
       source='the shipped parser (c_twin polari_rx_feed); cost unverified', caveats='a CRC does NOT catch a wrong VALUE sent on a correct '
       'wire — the torn read passes its CRC (plan §3)'),
    _t('debounce-synchroniser', 'Qualify an edge by time (a timer-checked debounce) on an MCU; a two-flop synchroniser on an FPGA (the '
       'task\'s `debounce`).', 'one-edge-one-interrupt', '',
       'ISR(INT0_vect) { uint32_t now = g_ms; if (seen && now - last < DEBOUNCE_MS) return; seen = 1; last = now; presses++; }',
       source='sc-1 measures it (scenario button-bounce-double-count: the INT0 ISR\'s cycles)',
       caveats='a window longer than the shortest real press interval swallows real presses — the scenario includes a real second press'),
    _t('watchdog', 'A hardware watchdog kicked from the main loop only: a hang resets the board instead of freezing it.',
       'main-loop-returns', '', 'wdt_enable(WDTO_250MS); … wdt_reset(); /* in the loop, never in an ISR */  + .init3: MCUSR = 0; wdt_disable();',
       source='sc-1 measures it (scenario runaway-hang-watchdog: uno-sim-rig → uno-sim-rig-wdt)',
       caveats='after a watchdog reset WDRF stays set and the WDT stays on at 15 ms — clear both before main or the board resets forever',
       notes='until sc-1 no UNO variant enabled the WDT (plan §4); HAL_WDT 1 is a variant knob, every shipped variant leaves it 0'),
    _t('write-then-commit', 'Write the new record, then a commit flag (or two copies with a sequence + CRC): a cut write is detected.',
       'write-completes', '', 'write value + seq into the slot NOT in use; write crc8(value, seq) LAST; boot: the valid slot with the newer seq',
       source='sc-1 measures it (scenario brownout-mid-eeprom-write: uno-eeprom-record → uno-eeprom-commit)',
       caveats='a crc8 commit byte has a 1-in-256 chance that a stale byte matches; a separate commit byte after the crc closes it'),
    _t('rescan-keep-tail', 'When the resync parser rescues a frame from bytes it already holds, keep the bytes that FOLLOW that frame and '
       're-read them, instead of dropping them with the rejected span.', 'rejected-span-one-frame', '',
       'if (rx->tail) { memmove(rx->buf, rx->buf + rx->used, rx->tail); rx->have = rx->tail; rx->tail = 0; }   /* c_twin_v2 keep-tail */',
       source='sc-1 measures it (scenario uart-residual-frame-loss: uno-echo-uartstat → uno-echo-keeptail, rx_parser keep-tail)',
       caveats='receiver-side only (the wire is unchanged); a frame lying wholly inside the kept tail completes one byte later'),
    _t('lock-ordering', 'Take locks in one global order: no circular wait can form.', 'locks-one-order', 'mutex',
       'xSemaphoreTake(lockA, …); xSemaphoreTake(lockB, …);   /* everywhere A before B */',
       source='sc-3 measures it on the ESP32-C3 twin (scenario two-lock-deadlock: c3-two-lock → c3-two-lock-ordered, one build flag)',
       caveats='a convention every task must keep — nothing in FreeRTOS enforces it; a new lock needs its place in the order'),
    _t('try-lock-backoff', 'Take the second lock with a timeout; on a timeout give the first back, wait (unequal back-offs) and retry: '
       'a cycle can form for a moment but never persists.', 'locks-one-order', 'mutex',
       'if (xSemaphoreTake(lockB, pdMS_TO_TICKS(5)) != pdTRUE) { xSemaphoreGive(lockA); vTaskDelay(backoff); continue; }',
       alt='lock-ordering', source='sc-3 measures it on the ESP32-C3 twin (scenario two-lock-deadlock-backoff: c3-two-lock → c3-two-lock-backoff)',
       caveats='equal back-offs can retry in lock-step for ever (a livelock) — the template\'s are unequal (1 vs 3 ticks); every round that '
               'met the cycle pays the timeout'),
    _t('priority-inheritance', 'A mutex that lends the waiter\'s priority to the holder: the wait is bounded by the critical section.',
       'high-task-waits-cs', 'mutex', 'xSemaphoreCreateMutex();   /* FreeRTOS mutexes inherit; binary semaphores do not */',
       source='sc-3 measures it on the ESP32-C3 twin (scenario priority-inversion-mutex): ESP-IDF v5.5.5\'s FreeRTOS DOES inherit — '
              'traceTASK_PRIORITY_INHERIT fires, L runs at priority 4 while H waits (plan §3a had it unverified)',
       caveats='bounded by ONE critical section only: a chain of holders, or a section that blocks, still waits longer'),
]


def techniques_by_name():
    return {t['name']: t for t in SEED_TECHNIQUES}


def assumption_names():
    return [a['name'] for a in SEED_ASSUMPTIONS]


def primitive_names():
    return [p['name'] for p in SEED_PRIMITIVES]


def dumps(v):
    return json.dumps(v)
