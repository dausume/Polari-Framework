"""board_pinlevel_selftest — ucd-0d PROVEN: PIN-LEVEL forcing and pin-to-pin wiring in the simavr digital twin
(UNO_CORE_DEMO_PLAN.md §5e Q7, §5f's ucd-0d row, §5g). `pin_parts(check)` is wired into board_selftest.run(); the same
checks run standalone from tests/board_uno_pinlevel_probe.py. Five cases, all against the REAL twin (no fake / mock):

  (a) N presses on PD2 (--pin-at, falling-edge default build) → g_presses == N
  (b) the SAME presses with EIMSK cleared (--poke) → g_presses == 0 (the pin toggles; nothing is enabled to catch it)
  (c) the SAME presses with EICRA set to any-edge (--poke) → g_presses == 2N (press AND release both count)
  (d) --wire PD6:PD3 on a firmware that toggles D6 → PD3 (PIND bit 3 / the wire-edge JSON) follows it
  (e) the SAME wire on a firmware that ALSO drives PD3 as an output → {"t":"wire-conflict"} is printed

Skips HONESTLY (every check SKIP, exit implied by the caller's pass==total) when the avr-twin engine (prf-board-engines
image or a local polari-avr-twin) is not reachable on this device — board.custom.board_engines.resolve names why.

    PYTHONPATH=.:modules python3 -m board.board_pinlevel_selftest     # from polari-framework/
"""
import json

N_PRESSES = 4
PRESS_GAP_CYCLES = 1000000    # 62.5 ms apart at 16 MHz — plenty for uno-button-count (no debounce to respect)
PRESS_HOLD_CYCLES = 50000     # ~3 ms "held" before release
POKE_CYCLE = 200000           # well after hal_button_init()/hal_led_init() run at the top of main()


def _edges(n=N_PRESSES, start=PRESS_GAP_CYCLES, gap=PRESS_GAP_CYCLES, hold=PRESS_HOLD_CYCLES):
    """N press/release pairs on PD2 as (cycle, pin, level) triples for twin.twin_args' pin_at=…"""
    out, c = [], start
    for _ in range(n):
        out += [(c, 'PD2', 0), (c + hold, 'PD2', 1)]
        c += gap
    return out


def _pinat_args(edges):
    """(cycle, pin, level) triples -> flat --pin-at argv (twin.twin_args does the same rendering for `pol board twin`)."""
    out = []
    for cycle, pin, level in edges:
        out += ['--pin-at', 'cycle=%d,pin=%s,level=%d' % (cycle, pin, level)]
    return out


def _mem_addr(name):
    """A register's DATA-MEMORY address from the cited snapshot (board.custom.registers) — I/O-space registers are
    +0x20 (the AVR's own in/out vs lds/sts split; OCR0A_ADDR in polari_avr_twin.c is the same rule)."""
    from board.custom import registers as R
    e = R.load()['registers'][name]
    a = int(e['addr'], 16)
    return a if e['space'] == 'mem' else a + 0x20


def _blink_variant(name, led_pin, blink_ms=20):
    """uno-blink-only with LED_PIN overridden — the smallest firmware that drives one named pin as an output, used
    here only to exercise --wire / the DDR conflict check (never flashed, never a seeded board variant)."""
    from board.custom import variants as V
    base = V.find('uno-blink-only')
    k = json.loads(base['knobs_json'])
    k['led_pin'] = led_pin
    k['blink_ms'] = blink_ms
    return dict(base, name=name, knobs_json=json.dumps(k))


def _build(work, variant_row):
    from board.custom import gen, build
    row = gen.gen('uno', None, work, variant=variant_row['name'], variant_rows=[variant_row])
    row = build.build('uno', work)
    return row


def pin_parts(check):
    import tempfile
    from board.custom import board_engines as be
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        check('SKIP ucd-0d (pin-level forcing + wiring): no simavr twin here — %s' % where['why'], True)
        return
    from firmwarefaults.custom import runner, harness

    # ---- (a)/(b)/(c): uno-button-count, pin-level presses, three builds of the SAME argv base
    b = runner.prepare_build('uno-button-count', home=tempfile.mkdtemp(prefix='ucd-0d-button-'))
    check('uno-button-count (HAL_INT0=1, no debounce) builds', b['row']['state'] == 'built', b['row'].get('notes'))
    addr = b['nm']['g_presses']['addr']
    base = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '0.5', '--status-ms', '0',
            '--adc0-mv', '750', '--watch', '0x%x/2=g_presses' % addr]

    r = harness.run(base + _pinat_args(_edges()), b['hex'])
    fired = sum(1 for line in r['stdout'].splitlines() if line.startswith('{"t":"pin-at"'))
    check('(a) %d presses on PD2 via --pin-at (falling-edge default EICRA/EIMSK from hal_button_init) -> g_presses == %d'
          % (N_PRESSES, N_PRESSES), r['ok'] and fired == 2 * N_PRESSES and r['final']['watch']['final'] == N_PRESSES,
          r.get('final', {}).get('watch'))

    r = harness.run(base + ['--poke', '0x%x=0x0@%d' % (_mem_addr('EIMSK'), POKE_CYCLE)] + _pinat_args(_edges()), b['hex'])
    check('(b) NEGATIVE: the same presses with EIMSK poked to 0 -> g_presses == 0 (the pin toggles; nothing is armed to catch it)',
          r['ok'] and r['final']['watch']['final'] == 0, r.get('final', {}).get('watch'))

    r = harness.run(base + ['--poke', '0x%x=0x1@%d' % (_mem_addr('EICRA'), POKE_CYCLE)] + _pinat_args(_edges()), b['hex'])
    check('(c) EICRA poked to any-edge (ISC01:00 = 01) -> g_presses == %d (press AND release both count)' % (2 * N_PRESSES),
          r['ok'] and r['final']['watch']['final'] == 2 * N_PRESSES, r.get('final', {}).get('watch'))

    # ---- (d)/(e): --wire PD6:PD3, two tiny blink builds (LED_PIN=6 drives the wire; LED_PIN=3 conflicts with it)
    work6 = tempfile.mkdtemp(prefix='ucd-0d-wire6-')
    row6 = _build(work6, _blink_variant('uno-wire-blink6', 6))
    check('the LED_PIN=6 blink build (drives D6, nothing on D3) builds', row6['state'] == 'built', row6.get('notes'))
    hex6 = open(row6['hex_path'], 'rb').read()
    argv_d = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '0.2', '--status-ms', '0',
              '--adc0-mv', '750', '--watch', '0x%x/1=PIND' % _mem_addr('PIND'), '--wire', 'PD6:PD3']
    r = harness.run(argv_d, hex6)
    applied = any(l.startswith('{"t":"wire"') and '"applied":1' in l for l in r['stdout'].splitlines())
    edges = [l for l in r['stdout'].splitlines() if l.startswith('{"t":"wire-edge"')]
    pind = r.get('final', {}).get('watch', {}).get('final', -1)
    pd6_bit, pd3_bit = bool(pind & 0x40), bool(pind & 0x08)
    conflict_d = any('wire-conflict' in l for l in r['stdout'].splitlines())
    check('(d) --wire PD6:PD3 applied, >=2 propagated edges, PIND bit 3 == PIND bit 6 at the end, no conflict',
          r['ok'] and applied and len(edges) >= 2 and pd6_bit == pd3_bit and not conflict_d,
          {'edges': len(edges), 'pind': pind, 'pd6': pd6_bit, 'pd3': pd3_bit})

    work3 = tempfile.mkdtemp(prefix='ucd-0d-wire3-')
    row3 = _build(work3, _blink_variant('uno-wire-blink3', 3))
    check('the LED_PIN=3 blink build (drives D3 as an output itself) builds', row3['state'] == 'built', row3.get('notes'))
    hex3 = open(row3['hex_path'], 'rb').read()
    argv_e = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '0.05', '--status-ms', '0',
              '--adc0-mv', '750', '--wire', 'PD6:PD3']
    r = harness.run(argv_e, hex3)
    conflict_e = [l for l in r['stdout'].splitlines() if l.startswith('{"t":"wire-conflict"')]
    check('(e) the SAME wire against a firmware that also drives PD3 -> {"t":"wire-conflict",...} printed, the run continues',
          r['ok'] and len(conflict_e) >= 1 and '"dst":"PD3"' in conflict_e[0], conflict_e[:1])


def run_pinlevel(check):
    pin_parts(check)


if __name__ == '__main__':
    import sys
    passed = total = 0

    def check(label, cond, extra=''):
        global passed, total
        total += 1
        passed += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, extra if not cond else ''))

    pin_parts(check)
    print('\n%d/%d checks passed' % (passed, total))
    sys.exit(0 if passed == total else 1)
