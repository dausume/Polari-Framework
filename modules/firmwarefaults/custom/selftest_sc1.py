"""firmwarefaults.custom.selftest_sc1 — the sc-1 half of the module selftest (FIRMWARE_SCENARIO_PLAN.md §3a, §4, §9 sc-1), run from
firmwarefaults_selftest (one count). Each scenario's outcome logic on FIXTURE sequences (the hang, the double count, the residual,
the half record, the watchdog recovery), the Wilson interval, the TX-log decoder, the host payloads (the residual pattern an ideal
parser reads as two frames, the EEPROM layouts, the crc8), the harness flags each sc-1 step renders, the not-yet-forcible RTOS rows
(refused with the reason, nothing built), the nine scenario variants through board's own validation, the hal.c / scenario_rig.c /
sim_rig.c knobs (every one default-off), and the c_twin keep-tail parser (the default header unchanged). No engine runs here.
"""
import json
import os
import struct

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the module dir
NM_SC1 = """00000074 T hal_wdt_boot
00000b82 T eeprom_write_byte
000011f6 T _exit
000001d2 T __vector_1
00000300 t ack_step
00800108 b g_presses
0080014e b g_rec_writes
0080014f b g_rec_valid
00800150 b g_rec_boot
00800151 b g_ack_state
008002eb B __bss_end
"""


def sc1_parts(check):
    def sc1_outcomes():
        from firmwarefaults.custom import outcome as O
        before = [(t * 100.0 + 0.7, 1, t) for t in range(5)] + [(503.2, 0x7F, 5)]
        d = O.decide_telemetry(before, 2000.0, 250, True, 1)
        check('S2 fixture BEFORE (telemetry to 400 ms, a request at 503 ms, silence to 2000 ms, ack dropped) → failed / refuted, the silence named',
              d['outcome'] == 'failed' and d['claim_status'] == 'refuted' and 'never left WAIT' in d['words'] and '1599.3' in d['words'], d)
        after = [(t * 100.0 + 0.7, 1, t) for t in range(20)] + [(503.2, 0x7F, 90), (553.2, 0x7F, 91)]
        d = O.decide_telemetry(sorted(after), 2000.0, 250, True, 2)
        check('S2 fixture AFTER (a retry 50 ms later, telemetry every 100 ms, acked) → passed / witnessed, the retry named',
              d['outcome'] == 'passed' and 'went again at 553.2 ms (50.0 ms after the first)' in d['words'] and 'acked' in d['words'], d)
        check('S2: the ack never dropped → undetermined (never a pass)', O.decide_telemetry(after, 2000.0, 250, False, 2)['outcome'] == 'undetermined')
        check('S3 fixtures: 3 counted for 2 presses → failed; 2 → passed; 1 → failed (a REAL press swallowed); no counter → inapplicable',
              [O.decide_presses(n, 2)['outcome'] for n in (3, 2, 1, None)] == ['failed', 'passed', 'failed', 'inapplicable']
              and 'swallowed' in O.decide_presses(1, 2)['words'])
        check('S4 fixtures: 1 applied / 2 intact → failed (the parser lost one the line delivered whole); 2/2 → passed; nothing intact → undetermined',
              [O.decide_commands(a, i, 2)['outcome'] for a, i in ((1, 2), (2, 2), (0, 0))] == ['failed', 'passed', 'undetermined']
              and 'LOST 1' in O.decide_commands(1, 2, 2)['words'])
        old, new = 0x11111111, 0x22222222
        check('S5 fixtures: 0x11112222 at boot → failed (half-updated); the old or the new value → passed; no valid record → failed; the reset '
              'never fired → undetermined',
              [O.decide_record(v, ok, old, new, done)['outcome'] for v, ok, done in ((0x11112222, 1, 1), (old, 1, 1), (new, 1, 1), (0, 0, 1), (old, 1, 0))]
              == ['failed', 'passed', 'passed', 'failed', 'undetermined'] and 'half-updated' in O.decide_record(0x11112222, 1, old, new, 1)['words'])
        wd = [{'cycle': 12095934, 'wdrf': 1, 'forced': 0}]
        check('watchdog fixtures: frames after the runaway with a WDRF reset → passed (the reset named); none after → failed (HUNG); never forced '
              '→ undetermined',
              O.decide_recovery([100.0, 757.3, 857.2], 500.0, 2000.0, wd)['outcome'] == 'passed'
              and '756.0' in O.decide_recovery([100.0, 757.3], 500.0, 2000.0, wd)['words']
              and O.decide_recovery([100.0, 400.0], 500.0, 2000.0, [])['outcome'] == 'failed'
              and O.decide_recovery([100.0], None, 2000.0, [])['outcome'] == 'undetermined')
        p, lo, hi = O.wilson(0, 39)
        p2, lo2, hi2 = O.wilson(7, 234)
        check('Wilson 95 %: 0/39 → [0, 9.0 %]; 7/234 → 3.0 % [1.5, 6.1] % (the interval the statistics rows carry)',
              p == 0 and lo == 0 and abs(hi - 0.0899) < 0.001 and abs(p2 - 0.0299) < 0.001 and abs(lo2 - 0.0146) < 0.001 and abs(hi2 - 0.0604) < 0.001,
              (hi, lo2, hi2))
        from firmwarefaults.custom import payloads
        f1, f2 = payloads.command(1, 5), payloads.ack()
        log = b''.join(struct.pack('<Q', 16000 * (10 if k < len(f1) else 20) + k) + bytes([x]) for k, x in enumerate(f1 + f2))
        fr = O.frames_from_tx_log(log)
        check('the TX-log decoder dates each frame by its last byte (cycle → ms) and keeps its msg_type (1 telemetry, 0x7F request)',
              [(mt, round(t)) for t, mt, _ in fr] == [(1, 10), (0x7F, 20)], fr)

    def sc1_payloads_and_flags():
        from firmwarefaults.custom import payloads, harness, disasm
        from firmwarefaults.custom import scenarios as SC
        body, info = payloads.residual(10)
        check('the residual pattern = a false 12-byte header (length reaching 10 B into frame B) + A + B; an IDEAL parser reads 2 frames in it',
              len(body) == 12 + 2 * info['frame_len'] and info['false_header_len'] == info['frame_len'] + 6 and payloads.ideal_commands(body) == 2
              and body[:2] == b'\x4c\x50', info)
        check('crc8 (poly 0x07) of 11 11 11 11 01 = 0xad — the commit byte the two-slot layout writes (scenario_rig.c\'s crc8)',
              payloads.crc8(bytes([0x11] * 4 + [1])) == 0xAD)
        check('EEPROM layouts: 1 = the value in place at 0; 2 = slot 0 {value, seq 1, crc} + slot 1 erased',
              payloads.eeprom_record(1, 0x11111111) == [(0, b'\x11' * 4)]
              and payloads.eeprom_record(2, 0x11111111) == [(0, b'\x11' * 4 + b'\x01\xad\xff\xff'), (8, b'\xff' * 8)])
        log = struct.pack('<QBB', 5, 0x4C, 0) + struct.pack('<QBB', 6, 0x50, 0x80) + struct.pack('<QBB', 7, 0x02, 0x01)
        check('the RX log → the bytes the UART received (a byte lost on the line, flag 0x80, is not among them)',
              payloads.delivered_from_rx_log(log) == b'\x4c\x02')
        nm = disasm.parse_nm(NM_SC1)
        st = SC.steps_of('lost-ack-hang')
        a, files, meta = harness.render_sc1(st, nm, 2.0, 0, {'watch': [('g_ack_state', 1)]}, 'uno-ack-wait', fn=(0x300, None))
        s = ' '.join(a)
        check('S2 renders --respond 0x4c50027f=reply0.bin,delay=3200,max=8 (the ACK file), --drop-frame rx:1, the TX + RX logs, the watch, '
              'and ack_step priced to its return (--fn-cycles 0x300:ret)',
              '--respond 0x4c50027f=reply0.bin,delay=3200,max=8' in s and '--drop-frame rx:1' in s and files['reply0.bin'] == payloads.ack()
              and '--uart-tx-log tx.bin' in s and '--uart-rx-log rx.bin' in s and '--watch 0x151/1=g_ack_state' in s and '--fn-cycles 0x300:ret' in s, s)
        a, files, meta = harness.render_sc1(SC.steps_of('brownout-mid-eeprom-write'), nm, 0.9, 0, {'eeprom_dump': (0, 16)}, 'uno-eeprom-record')
        s = ' '.join(a)
        check('S5 BEFORE renders the in-place preload, the command at 4 800 000, the reset at the 3rd eeprom_write_byte after it, the EEPROM dump',
              '--eeprom-set 0x0=11111111' in s and '--inject inject1.bin@4800000' in s and '--reset-at pc=0xb82,nth=3,after=4800000' in s
              and '--eeprom-dump 0x0:16' in s and meta['sent'] == 1, s)
        a2, _, _ = harness.render_sc1(SC.steps_of('brownout-mid-eeprom-write'), nm, 0.9, 0, {}, 'uno-eeprom-commit')
        check('S5 AFTER renders the SAME steps with the two-slot preload (the layout follows the variant\'s SC_EEPROM_RECORD)',
              '--eeprom-set 0x0=1111111101adffff' in ' '.join(a2) and '--eeprom-set 0x8=ffffffffffffffff' in ' '.join(a2))
        a, _, meta = harness.render_sc1(SC.steps_of('runaway-hang-watchdog'), nm, 2.0, 0, {}, 'uno-sim-rig')
        check('the watchdog scenario renders --jump-at cycle=8000000,pc=0x11f6 (_exit) — resolved by symbol', '--jump-at cycle=8000000,pc=0x11f6' in ' '.join(a))
        a, _, meta = harness.render_sc1(SC.steps_of('runaway-hang-watchdog'), {}, 2.0, 0, {}, 'uno-sim-rig')
        check('…and a build without the symbol → `missing` (the run is inapplicable there, with the reason)', meta['missing'] and '_exit' in meta['missing'][0])
        a, _, _ = harness.render_sc1(SC.steps_of('button-bounce-double-count'), nm, 0.7, 0, {'watch': [('g_presses', 2)]}, 'uno-button-count')
        check('S3 renders three INT0 raises (vector 1) at 8 000 000, 8 000 300 (the ring) and 8 800 000 (a real press)',
              ' '.join(a).count('--irq-at') == 3 and 'cycle=8000300,vec=1' in ' '.join(a))
        a, _, _ = harness.render_sc1([], nm, 1.0, 7, {}, 'x', extra_steps=[{'kind': 'uart-ber', 'args_json': '{"p": 0.001}'},
                                                                             {'kind': 'rx-noise', 'args_json': '{"rate": 200}'}])
        check('the statistics tier\'s extra steps: --uart-ber 0.001 and --rx-noise 200 with the seed', '--uart-ber 0.001' in ' '.join(a) and '--rx-noise 200' in ' '.join(a)
              and a[a.index('--seed') + 1] == '7')

    def sc1_rtos_and_variants():
        from firmwarefaults.custom import scenarios as SC, runner
        from firmwarefaults.custom.sink import LocalSink
        from firmwarefaults.custom.scenarios_sc1 import RTOS_STATUS
        for name in ('priority-inversion-mutex', 'two-lock-deadlock'):
            sc = SC.find(name)
            try:
                runner.run_scenario(name, 'both', LocalSink())
                why = ''
            except runner.ScenarioRefused as e:
                why = str(e)
            check('%s: status not-yet-forcible (FreeRTOS on the ESP32-C3 — "STM32-C3" unconfirmed — or Zephyr on the SAMD21), the recipe written '
                  '(hold-lock-order), and the runner REFUSES it with that reason before building' % name,
                  sc['status'] == RTOS_STATUS and not SC.runnable(sc) and 'FreeRTOS' in why and 'STM32-C3' in why
                  and SC.steps_of(name)[0]['kind'] == 'hold-lock-order' and json.loads(SC.steps_of(name)[0]['args_json'])['tasks'], why)
        from board.custom import variants as V
        vs = {v['name']: v for v in SC.scenario_variants()}
        want = {'uno-ack-wait': [('SC_ACK_WAIT', 1)], 'uno-ack-wait-timeout': [('SC_ACK_WAIT', 1), ('SC_ACK_TIMEOUT_MS', 50)],
                'uno-button-count': [('HAL_INT0', 1)], 'uno-button-debounce': [('HAL_INT0', 1), ('HAL_INT0_DEBOUNCE_MS', 20)],
                'uno-echo-uartstat': [('HAL_UART_ERRCOUNT', 1)], 'uno-echo-keeptail': [('HAL_UART_ERRCOUNT', 1)],
                'uno-eeprom-record': [('SC_EEPROM_RECORD', 1)], 'uno-eeprom-commit': [('SC_EEPROM_RECORD', 2)], 'uno-sim-rig-wdt': [('HAL_WDT', 1)]}
        got = {n: V.resolve(vs[n])['flags'] for n in want}
        check('the nine sc-1 variants resolve through board\'s own validation with exactly their scenario flags', got == want, got)
        check('…the request/ack, button and EEPROM ones use the scenario_rig app; S4\'s pair is the echo app, AFTER with rx_parser keep-tail; '
              'the watchdog one is the whole rig',
              all(V.resolve(vs[n])['app'] == 'scenario_rig' for n in ('uno-ack-wait', 'uno-button-count', 'uno-eeprom-commit'))
              and V.resolve(vs['uno-echo-keeptail'])['app'] == 'echo' and V.resolve(vs['uno-echo-keeptail'])['knobs']['rx_parser'] == 'keep-tail'
              and 'rx_parser' not in V.resolve(vs['uno-echo-uartstat'])['knobs'] and V.resolve(vs['uno-sim-rig-wdt'])['app'] == 'sim_rig')
        try:
            V.resolve(dict(vs['uno-echo-keeptail'], knobs_json=json.dumps({'rx_parser': 'fast'})))
            bad = ''
        except V.VariantRefused as e:
            bad = str(e)
        check('an unknown rx_parser is REFUSED by board\'s variant validation, naming the choices', 'resync | keep-tail' in bad, bad)
        from board.custom import gen
        try:
            gen.header('SimRigState', api='https://x', rx_parser='keep-tail')
            g = ''
        except gen.GenRefused as e:
            g = str(e)
        check('board gen refuses keep-tail against a live server header (it is rendered offline from the pinned contract only)', 'offline' in g, g)
        fw = os.path.join(HERE, '..', 'board', 'custom', 'firmware', 'uno')
        hal, halh = open(os.path.join(fw, 'hal.c')).read(), open(os.path.join(fw, 'hal.h')).read()
        rig, scn = open(os.path.join(fw, 'apps', 'sim_rig.c')).read(), open(os.path.join(fw, 'apps', 'scenario_rig.c')).read()
        check('hal.h: every sc-1 knob defaults to 0 (HAL_UART_ERRCOUNT, HAL_INT0, HAL_INT0_DEBOUNCE_MS, HAL_WDT) — a shipped build compiles none of it',
              all('#define %s 0' % k in halh for k in ('HAL_UART_ERRCOUNT', 'HAL_INT0', 'HAL_INT0_DEBOUNCE_MS', 'HAL_WDT')))
        check('hal.c: the RX ISR reads UCSR0A BEFORE UDR0 under HAL_UART_ERRCOUNT (FE0/DOR0 are valid only before the read) and keeps the '
              'shipped ISR verbatim under #else; .init3 clears MCUSR + the WDT under HAL_WDT',
              'uint8_t st = UCSR0A;\n    uint8_t b = UDR0' in hal and '#else\nISR(USART_RX_vect)\n{\n    uint8_t b = UDR0, next' in hal
              and 'section(".init3")' in hal and 'MCUSR = 0u;\n    wdt_disable();' in hal)
        check('sim_rig.c: the watchdog init + kick exist only under #if HAL_WDT (uno-sim-rig stays byte-identical)',
              rig.count('#if HAL_WDT') == 2 and 'hal_wdt_kick();' in rig)
        check('scenario_rig.c: BEFORE/AFTER differ in exactly the technique — the blocking ack wait vs ack_step(); the in-place record vs the '
              'two-slot crc-last write; the observables are volatile (the twin reads them by symbol)',
              'while (!g_ack_seen) drain_rx();' in scn and 'static void ack_step(uint32_t now)' in scn and 'crc LAST = commit' in scn
              and 'static volatile uint32_t g_rec_boot' in scn and 'static volatile uint8_t g_ack_state' in scn)

    def sc1_keep_tail_header():
        from grpcbridge.custom import c_twin_v2 as V2
        base, kt = V2.common_block('resync'), V2.common_block('keep-tail')
        check('c_twin_v2: rx_parser resync IS the grpc-j4 block (every existing header byte-identical); keep-tail adds rx->tail / rx->used '
              'and re-reads them on the next feed',
              base is V2._COMMON_V2 and 'rx->tail' not in base and 'size_t tail;' in kt and 'memmove(rx->buf, rx->buf + rx->used, rx->tail);' in kt
              and 'rx->tail = rx->have - rx->used;' in kt)
        try:
            V2.common_block('fast')
            ok = False
        except ValueError:
            ok = True
        check('…and an unknown parser is a ValueError, never a silent default', ok)

    sc1_outcomes.__name__ = 'sc1_outcomes'
    return (sc1_outcomes, sc1_payloads_and_flags, sc1_rtos_and_variants, sc1_keep_tail_header)
