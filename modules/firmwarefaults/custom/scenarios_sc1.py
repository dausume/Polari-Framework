"""
@module firmwarefaults.custom.scenarios_sc1

THE sc-1 SCENARIOS AS ROWS (FIRMWARE_SCENARIO_PLAN.md §3a, §4, §9 sc-1): the five single-board scenarios on the UNO
twin — each a BEFORE/AFTER pair of FirmwareVariants that differ in exactly the technique — plus the two RTOS scenarios
written down as recipes that are NOT forcible on the UNO (no RTOS), so sc-3 only needs the board:

  lost-ack-hang               S2  uno-ack-wait (waits for the ack forever)  → uno-ack-wait-timeout (timeout + state machine)
  button-bounce-double-count  S3  uno-button-count (every INT0 edge counts) → uno-button-debounce (20 ms debounce)
  uart-residual-frame-loss    S4  uno-echo-uartstat (the shipped resync parser) → uno-echo-keeptail (rx_parser keep-tail)
  brownout-mid-eeprom-write   S5  uno-eeprom-record (in place)              → uno-eeprom-commit (two slots, crc written last)
  runaway-hang-watchdog       §4  uno-sim-rig (no watchdog)                 → uno-sim-rig-wdt (HAL_WDT 1, kicked per pass)
  priority-inversion-mutex    S6  not-yet-forcible: needs an RTOS
  two-lock-deadlock           S7  not-yet-forcible: needs an RTOS

Every variant is board's FirmwareVariant (seeded here, marked SCENARIO ONLY); the BEFORE/AFTER difference is a build flag
(hal.c / apps/scenario_rig.c, C only — RULE 2) or the header's rx_parser knob, so `uno-sim-rig` itself stays
byte-identical. OBSERVE says what each scenario's run reads (SRAM words by symbol, the EEPROM, the TX log) and which
function or ISR prices the technique.
"""
import json

J = json.dumps

INT0 = 1
TIMER2_COMPA = 7
ACK_MATCH = '4c50027f'           # a request frame: magic 0x504C (LE: 4C 50), version 2, msg_type 0x7F (scenario_rig.c ACK_MSG_TYPE)
#: sc-1's status for the two RTOS rows (kept for the record; sc-3 made them forcible on the C3 — custom/scenarios_sc3.py)
RTOS_STATUS = ('not-yet-forcible: needs FreeRTOS (ESP32-C3 — his "STM32-C3" still to confirm, D-sc-4) or Zephyr (SAMD21); the UNO '
               'runs no RTOS, so there are no tasks, no mutexes and no preemption to force')
SC_APP_FEATURES = {'led': True, 'pwm': False, 'adc': False, 'commands': True}


def _s(name, title, description, before, after, fault_class, fault, breaks, technique, expected, kind, seconds, notes='',
       status='runnable', board='arduino-uno-r3', simulator='avr-twin', seed_policy='fixed'):
    return {'name': name, 'title': title, 'description': description, 'target_board': board, 'before_variant': before,
            'after_variant': after, 'fault_class': fault_class, 'fault': fault, 'breaks': breaks, 'technique': technique,
            'expected_observable': expected, 'observable_kind': kind, 'window_cycles': int(seconds * 16000000), 'run_seconds': seconds,
            'seed_policy': seed_policy, 'seed': 0, 'simulator': simulator, 'status': status,
            'provenance': 'sc-1 seed (FIRMWARE_SCENARIO_PLAN.md §3a/§4)', 'notes': notes}


SC1_SCENARIOS = [
    _s('lost-ack-hang', 'Scenario 2 — a lost acknowledgement with no timeout → the firmware hangs',
       'At 500 ms the board sends a REQUEST frame (msg_type 0x7F) and needs the host\'s ACK before it goes on. The scripted host '
       'answers every request after 0.2 ms; the harness DROPS the first answer on the host→board line. BEFORE (uno-ack-wait) waits '
       'in a loop with no way out: telemetry stops for good. AFTER (uno-ack-wait-timeout) polls an explicit state machine from the '
       'main loop: after 50 ms it sends the request again, the second ack arrives, and telemetry never paused.',
       'uno-ack-wait', 'uno-ack-wait-timeout', 'LivelockFault', 'lost-ack-hang', 'every-message-arrives', 'timeout-fsm',
       'BEFORE: the last telemetry frame before the request, then nothing for > 250 ms (2.5 frame periods) to the end → refuted. '
       'AFTER: a second request ~50 ms after the first, the ack, telemetry gaps never above 250 ms → witnessed.',
       'telemetry-continues', 2.0),
    _s('lost-request-hang', 'Scenario 2, the other direction — the board\'s REQUEST lost on the board→host line',
       'The same request/ack pair as lost-ack-hang, but the harness drops the board\'s first REQUEST frame (msg_type 0x7F) on its way '
       'to the host (--drop-frame tx:1,type=0x7f): the host never answers. BEFORE (uno-ack-wait) hangs exactly as when the ack is lost; '
       'AFTER (uno-ack-wait-timeout) sends the request again after 50 ms. A lost message is a lost message, whichever way it travelled.',
       'uno-ack-wait', 'uno-ack-wait-timeout', 'LivelockFault', 'lost-ack-hang', 'every-message-arrives', 'timeout-fsm',
       'BEFORE: telemetry stops for > 250 ms to the end → refuted. AFTER: a second request ~50 ms later, acked, no gap → witnessed.',
       'telemetry-continues', 2.0,
       notes='sc-2: the board→host drop (--drop-frame tx:) the sc-1 harness refused; TX bytes are held 4 byte slots while it is on'),
    _s('button-bounce-double-count', 'Scenario 3 — a ringing edge raises INT0 twice → one press counted twice',
       'A press on D2 whose contact rings: INT0 raised at 500 ms and again 300 cycles (18.75 µs) later, then a second, REAL press '
       '50 ms after. BEFORE (uno-button-count) counts every edge: 3 for 2 presses. AFTER (uno-button-debounce) ignores edges within '
       '20 ms of the last one it counted: 2 — and the real second press is still counted.',
       'uno-button-count', 'uno-button-debounce', 'DoubleEdgeFault', 'contact-bounce', 'one-edge-one-interrupt', 'debounce-synchroniser',
       'BEFORE: g_presses = 3 for 2 presses → refuted. AFTER: g_presses = 2 → witnessed (and fewer would mean the debounce ate a real press).',
       'press-count', 0.7,
       notes='forced as two irq-at-cycle raises of vector 1 (the plan\'s pin-level PD2 edge is a later refinement: a vector raise is '
             'what the ringing edge does to the core once EIMSK has INT0 enabled)'),
    _s('uart-residual-frame-loss', 'Scenario 4 — garbage ending in a frame start hides the NEXT frame from the resync parser',
       'The residual case GRPC_BRIDGE_PLAN Finding (3) documented: a false start (4C 50, version 2, a length that reaches 10 bytes '
       'into frame B) right before two real commands A and B. The shipped parser rejects the false candidate at its CRC, rescues A '
       'from the bytes it holds — and drops the 10 bytes of B that followed A in the same span, so B is lost. AFTER (rx_parser '
       'keep-tail) keeps those bytes and re-reads them: both commands apply. The echo app counts applied commands (`echoes`); '
       'HAL_UART_ERRCOUNT counts FE0 / DOR0 / ring drops in the RX ISR on both sides.',
       'uno-echo-uartstat', 'uno-echo-keeptail', 'UartBitErrorFault', 'uart-bit-error', 'rejected-span-one-frame', 'rescan-keep-tail',
       'BEFORE: 1 of the 2 commands applied while an ideal parser (board.custom.packet_ref.StreamParser over the same bytes) finds 2 → '
       'refuted. AFTER: 2 of 2 → witnessed. The statistics tier runs --uart-ber over 500 commands x 20 seeds per BER.',
       'commands-applied', 0.5),
    _s('brownout-mid-eeprom-write', 'Scenario 5 — the supply drops between EEPROM byte writes → a half-updated record',
       'EEPROM holds record 0x11111111; a command asks for 0x22222222; the core is reset at the THIRD entry of eeprom_write_byte '
       '(two bytes written, the rest not). simavr 1.6 has NO brown-out detector model, so the droop is approximated by stopping '
       'the core there and avr_reset() — said so on every run. BEFORE (uno-eeprom-record, in place) boots reading 0x11112222. AFTER '
       '(uno-eeprom-commit: two slots {value, seq, crc8}, the crc written last) boots with the old record intact.',
       'uno-eeprom-record', 'uno-eeprom-commit', 'BrownoutMidWriteFault', 'brownout-mid-write', 'write-completes', 'write-then-commit',
       'BEFORE: the record read at boot is neither the old nor the new value → refuted. AFTER: the old (or the new) value, never a '
       'mix → witnessed.', 'record-consistent', 0.9,
       notes='EEPROM persistence across avr_reset is VERIFIED on the twin by the control run (reset after the write completed → '
             'the new value is read at boot); sc-0 had it as assumed'),
    _s('runaway-hang-watchdog', 'Plan §4 — a runaway into a dead loop: frozen forever, or reset by the watchdog',
       'At 500 ms the harness sets the PC to _exit (avr-libc: cli, then a self-loop) — a corrupted return address in miniature. '
       'BEFORE (uno-sim-rig, no watchdog) never sends another frame. AFTER (uno-sim-rig-wdt: HAL_WDT 1, WDTO_250MS, kicked once per '
       'main-loop pass, MCUSR + the WDT cleared in .init3) is reset by the watchdog ~256 ms later (WDRF set) and telemetry resumes.',
       'uno-sim-rig', 'uno-sim-rig-wdt', 'LivelockFault', 'runaway-hang', 'main-loop-returns', 'watchdog',
       'BEFORE: no frame after the runaway → refuted. AFTER: one watchdog reset (WDRF), frames again → witnessed.',
       'recovers-after-hang', 2.0),
]


def _step(scenario, order, kind, args, condition=None, notes=''):
    from firmwarefaults.custom.scenarios import STEP_KINDS
    ok, why = STEP_KINDS[kind]
    return {'name': '%s#%d' % (scenario, order), 'scenario': scenario, 'order': order, 'kind': kind, 'args_json': J(args),
            'condition_json': J(condition or {}), 'forcible': ok, 'not_forcible_reason': '' if ok else why, 'notes': notes}


def sc1_steps():
    return [
        _step('lost-ack-hang', 1, 'respond', {'match': ACK_MATCH, 'reply': 'ack', 'delay_cycles': 3200, 'max': 8},
              notes='the scripted host: every request frame the board transmits is answered with an ACK frame 0.2 ms later'),
        _step('lost-ack-hang', 2, 'drop-nth-frame', {'direction': 'rx', 'n': 1}, notes='the FIRST ack never reaches the board'),
        _step('lost-request-hang', 1, 'respond', {'match': ACK_MATCH, 'reply': 'ack', 'delay_cycles': 3200, 'max': 8},
              notes='the scripted host answers every request it SEES'),
        _step('lost-request-hang', 2, 'drop-nth-frame', {'direction': 'tx', 'n': 1, 'msg_type': 0x7F},
              notes='the board\'s FIRST request frame never reaches the host'),
        _step('button-bounce-double-count', 1, 'irq-at-cycle', {'cycle': 8000000, 'vec': INT0, 'vector_name': 'INT0'},
              notes='press 1, first edge (500 ms)'),
        _step('button-bounce-double-count', 2, 'irq-at-cycle', {'cycle': 8000300, 'vec': INT0, 'vector_name': 'INT0'},
              notes='press 1, the contact rings: a second edge 300 cycles (18.75 µs) later'),
        _step('button-bounce-double-count', 3, 'irq-at-cycle', {'cycle': 8800000, 'vec': INT0, 'vector_name': 'INT0'},
              notes='press 2, a real one, 50 ms later (a debounce must still count it)'),
        _step('uart-residual-frame-loss', 1, 'inject-bytes', {'cycle': 4800000, 'payload': 'residual', 'trailing_bytes': 10},
              notes='false start (12 B, its length reaching 10 B into B) + command A + command B, host→board'),
        _step('brownout-mid-eeprom-write', 1, 'eeprom-preload', {'layout': 'from-variant', 'value': 0x11111111},
              notes='the old record, in the layout of the variant under test'),
        _step('brownout-mid-eeprom-write', 2, 'inject-bytes', {'cycle': 4800000, 'payload': 'record-command', 'value': 0x22222222},
              notes='a SimRigState command whose pwm_duty is the new record'),
        _step('brownout-mid-eeprom-write', 3, 'reset-at', {'symbol': 'eeprom_write_byte', 'nth': 3, 'after_cycle': 4800000},
              notes='the 3rd byte write begins: two bytes are new, two old — the core is stopped and reset (no BOD model in simavr)'),
        _step('runaway-hang-watchdog', 1, 'jump-at', {'cycle': 8000000, 'symbol': '_exit'},
              notes='the PC is set to _exit (cli; rjmp .) at 500 ms — a dead loop with interrupts off'),
    ]


#: what a run of each scenario reads and how the technique is priced (the runner's per-scenario configuration)
OBSERVE = {
    'lost-ack-hang': {'watch': [('g_ack_state', 1), ('g_ack_tries', 1), ('g_ack_seen', 1)], 'cost_fn': 'ack_step', 'gap_limit_ms': 250,
                      'cost_what': 'cycles of one ack_step() pass of the state machine (min, uninterrupted)'},
    'lost-request-hang': {'watch': [('g_ack_state', 1), ('g_ack_tries', 1), ('g_ack_seen', 1)], 'cost_fn': 'ack_step', 'gap_limit_ms': 250,
                          'cost_what': 'cycles of one ack_step() pass of the state machine (min, uninterrupted)'},
    'button-bounce-double-count': {'watch': [('g_presses', 2)], 'expected_presses': 2, 'cost_isr': INT0,
                                   'cost_what': 'cycles inside the INT0 ISR (max, entry → reti)'},
    'uart-residual-frame-loss': {'watch': [('echoes', 2), ('g_uart_fe', 2), ('g_uart_dor', 2), ('g_rx_dropped', 2)],
                                 'cost_what': 'flash + RAM only (polari_rx_feed is inlined into main: no symbol to time)'},
    'brownout-mid-eeprom-write': {'watch': [('g_rec_boot', 4), ('g_rec_valid', 1), ('g_rec_writes', 1)], 'eeprom_dump': (0, 16),
                                  'old': 0x11111111, 'new': 0x22222222,
                                  'cost_what': 'flash + RAM; EEPROM bytes per record 4 → 12 (two 6-byte slots); writes per record 4 → 6'},
    'runaway-hang-watchdog': {'watch': [], 'cost_fn_kick': True,
                              'cost_what': 'flash + RAM; one wdr per main-loop pass (1 cycle) + .init3 MCUSR/wdt_disable at boot'},
}


def _variant(name, base, title, purpose, flags, watch, notes, app=None, features=None, knobs=None):
    from board.custom.variants import SEED_FIRMWARE_VARIANTS
    b = next(v for v in SEED_FIRMWARE_VARIANTS if v['name'] == base)
    v = dict(b, name=name, title=title, purpose=purpose, build_flags_json=J(flags), what_to_watch=watch, origin='seeded', notes=notes)
    if app:
        v['app'] = app
    if features is not None:
        v['features_json'] = J(features)
    if knobs:
        k = json.loads(b['knobs_json'])
        k.update(knobs)
        v['knobs_json'] = J(k)
    return v


def sc1_variants():
    """The nine sc-1 scenario variants (FirmwareVariant rows) — built lazily so importing this file never needs board."""
    sc = dict(app='scenario_rig', features=SC_APP_FEATURES, knobs={'rig_name': 'uno-scenario'})
    tag = 'firmwarefaults (sc-1): a SCENARIO variant — never install it on a board you rely on'
    return [
        _variant('uno-ack-wait', 'uno-sim-rig', 'SCENARIO ONLY — request/ack with NO timeout (scenario 2 BEFORE)',
                 'At 500 ms it sends a request (msg_type 0x7F) and waits for the ack in a loop with no way out: a lost ack hangs it.',
                 ['SC_ACK_WAIT=1'], 'telemetry stops at ~500 ms if the ack is lost (`pol faults run lost-ack-hang --before`)', tag, **sc),
        _variant('uno-ack-wait-timeout', 'uno-sim-rig', 'SCENARIO ONLY — request/ack with a 50 ms timeout + retry state machine (scenario 2 AFTER)',
                 'The same request, polled by an explicit state machine from the main loop: resend after 50 ms, up to 3 tries, then status '
                 '"fault"; telemetry never stops.', ['SC_ACK_WAIT=1', 'SC_ACK_TIMEOUT_MS=50'],
                 'a second request ~50 ms after a lost ack; telemetry continuous', tag, **sc),
        _variant('uno-button-count', 'uno-sim-rig', 'SCENARIO ONLY — a button on D2 (INT0), every edge counted (scenario 3 BEFORE)',
                 'INT0 on a falling edge counts presses into g_presses — a ringing contact counts twice.', ['HAL_INT0=1'],
                 'g_presses counts every edge', tag, **sc),
        _variant('uno-button-debounce', 'uno-sim-rig', 'SCENARIO ONLY — the D2 button with a 20 ms debounce (scenario 3 AFTER)',
                 'Edges within 20 ms of the last counted one are ignored (timer-qualified debounce in the ISR).',
                 ['HAL_INT0=1', 'HAL_INT0_DEBOUNCE_MS=20'], 'g_presses counts presses, not edges', tag, **sc),
        _variant('uno-echo-uartstat', 'uno-echo', 'SCENARIO ONLY — the echo app + the USART error counters (scenario 4 BEFORE)',
                 'The shipped resync parser; the RX ISR also counts FE0, DOR0 and ring-full drops (HAL_UART_ERRCOUNT 1).',
                 ['HAL_UART_ERRCOUNT=1'], 'echoes = commands applied; g_uart_fe / g_uart_dor / g_rx_dropped', tag),
        _variant('uno-echo-keeptail', 'uno-echo', 'SCENARIO ONLY — the echo app with the keep-tail RX parser (scenario 4 AFTER)',
                 'The generated header rendered with rx_parser keep-tail (c_twin_v2): bytes after a rescued frame are re-read, not dropped.',
                 ['HAL_UART_ERRCOUNT=1'], 'echoes = commands applied (no residual loss)', tag, knobs={'rx_parser': 'keep-tail'}),
        _variant('uno-eeprom-record', 'uno-sim-rig', 'SCENARIO ONLY — a 4-byte EEPROM record written in place (scenario 5 BEFORE)',
                 'A command\'s pwm_duty is written as a 4-byte record at EEPROM 0, byte by byte; boot reads it back unchecked.',
                 ['SC_EEPROM_RECORD=1'], 'g_rec_boot = the record read at boot', tag, **sc),
        _variant('uno-eeprom-commit', 'uno-sim-rig', 'SCENARIO ONLY — the record as two slots + seq + crc8, written then committed (scenario 5 AFTER)',
                 'The new value goes into the slot not in use; the crc over value + seq is written last; boot takes the valid slot with the '
                 'newer seq.', ['SC_EEPROM_RECORD=2'], 'g_rec_boot is the old or the new record, never a mix', tag, **sc),
        _variant('uno-sim-rig-wdt', 'uno-sim-rig', 'SCENARIO ONLY — the whole rig with the watchdog on (plan §4)',
                 'HAL_WDT 1: WDTO_250MS, kicked once per main-loop pass; MCUSR and the WDT cleared in .init3 so a watchdog reset does not '
                 'loop.', ['HAL_WDT=1'], 'a hang ends in a watchdog reset ~256 ms later and telemetry resumes', tag),
    ]
