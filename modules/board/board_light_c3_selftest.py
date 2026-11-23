"""board_light_c3_selftest - smp S5: the light Mission on the ESP32-C3 under FreeRTOS, proven on the C3 TWIN (QEMU esp32c3; no C3 board is on the bench; the pins are a RAM shim because QEMU's C3
GPIO is a register stub - or, pt-4, modelled pads where the esp engines hold the polari-block QEMU). SKIPS honestly without the esp engines image. Parts:

  pins     the chosen GPIOs carry no constraint row in board.custom.lifecycle_c3 (no strapping / USB / UART0 / flash / JTAG), the knob validator refuses the ones that do
  gen      the C3 light project holds the ButtonClockState + ButtonClockEvent headers, light_hal.h and the extra REQUIRES; the other C3 variants' projects are untouched
  build    the shim build and the chip-HAL build compile; a forced rebuild gives the same image sha256; the cost (wall, CPU, peak RSS, sizes) is measured
  twin     the four Purposes' own acceptance scenarios, run on the config through firmwarefaults.custom.acceptance (variant=esp32c3-light), all four passed ScenarioRuns, every negative
           control rejected; fsc_link reads the config as finished; the board is refused for the UNO's pin route check
  chip HAL an engine WITHOUT the pin model: the chip-HAL build boots on the twin and speaks frames, but the LED write is NOT observable (no pin trace) - the twin's stated limit, measured
  pt-4     an engine WITH the pin model (c3-run --pins, the polari-block QEMU): the four Purposes above are proven on the CHIP-HAL build (PIN_SHIM 0) - presses are stamped pad levels, the
           LED is read off its pad, the jumper is a board wire; the run repeats to the nanosecond; the shim build still passes its own proof; the same image on the prebuilt QEMU still
           sees no button (the stub's limit stands)

    PYTHONPATH=.:modules python3 -m board.board_light_c3_selftest      # from polari-framework/ (standalone)
"""
import json
import shutil
import tempfile

LIGHT = 'uno-light-mission'


def run_light_c3(check):
    from board.custom import lifecycle_c3, variants_c3 as V3

    # ---- pins
    k = V3.LIGHT_KNOBS
    pins = {k['led_pin'], k['button_pin'], k['sense_pin']}
    rows = lifecycle_c3.constraints()
    cons = sorted({r['pin'] for r in rows}, key=lambda g: int(g[4:]))
    touched = [n for n in pins if 'GPIO%d' % n in {r['pin'] for r in rows}]
    free = sorted(set(range(22)) - {int(g[4:]) for g in cons})
    check('smp S5 pins: the light uses GPIO%d (LED), GPIO%d (button), GPIO%d (sense); lifecycle_c3 (datasheet v2.4) has NO constraint row for any of them (constrained: %s)'
          % (k['led_pin'], k['button_pin'], k['sense_pin'], ', '.join(cons)), not touched, touched)
    check('smp S5 pins: the validator\'s forbidden list equals the set of GPIOs lifecycle_c3 constrains', set(V3.LIGHT_FORBIDDEN) == {int(g[4:]) for g in cons}, sorted(set(V3.LIGHT_FORBIDDEN) ^ {int(g[4:]) for g in cons}))
    check('smp S5 pins: those are exactly the C3 GPIOs with no constraint row at all: %s' % free, sorted(pins) == free, free)
    refused = {}
    for n, why in sorted(V3.LIGHT_FORBIDDEN.items()):
        try:
            V3.resolve(V3.find(V3.LIGHT_NAME), {'led_pin': n})
        except V3.VariantRefused as e:
            refused[n] = str(e)
    check('smp S5 pins: the knob validator refuses every strapping (2/8/9), USB (18/19), UART0 (20/21), JTAG (4-7), glitch (10), VDD_SPI (11) and flash (12-17) GPIO as the LED pin: %d of %d refused'
          % (len(refused), len(V3.LIGHT_FORBIDDEN)), len(refused) == len(V3.LIGHT_FORBIDDEN), sorted(set(V3.LIGHT_FORBIDDEN) - set(refused)))
    for n, role in ((2, 'strapping'), (8, 'strapping'), (9, 'strapping'), (18, 'USB'), (20, 'UART0'), (12, 'flash')):
        check('smp S5 pins: GPIO%d (%s) carries a lifecycle_c3 constraint row, so avoiding it is derived, not assumed' % (n, role),
              'GPIO%d' % n in {r['pin'] for r in rows})

    # ---- gen
    from board.custom import gen_c3
    work = tempfile.mkdtemp(prefix='smp-c3-gen-')
    try:
        row = gen_c3.gen_c3(V3.LIGHT_NAME, work)
        files = gen_c3.project_files(row['project_dir'])
        cm = open(row['project_dir'] + '/main/CMakeLists.txt').read()
        check('smp S5 gen: the light project holds app.c, light_hal.h, the ButtonClockState + ButtonClockEvent headers (and SimRigState for the common layer); %d files' % len(files),
              all(f in files for f in ('main/app.c', 'main/light_hal.h', 'main/buttonclockstate_packets.h', 'main/buttonclockevent_packets.h', 'main/simrigstate_packets.h')), files)
        check('smp S5 gen: the main component REQUIRES nvs_flash and esp_driver_gpio, and board_config.h carries the pins', 'nvs_flash esp_driver_gpio' in cm
              and '#define BUTTON_GPIO 3' in open(row['project_dir'] + '/main/board_config.h').read(), cm)
        base = gen_c3.gen_c3('c3-sim-rig', work)
        bf = gen_c3.project_files(base['project_dir'])
        check('smp S5 gen: a C3 variant that is not the light is untouched (no extra header or file): %s' % bf, bf == sorted(set(gen_c3.TEMPLATE_FILES) | {'main/app.c', 'main/board_config.h', 'main/board_pins.h',
                                                                                                         'main/simrigstate_packets.h'}), bf)
        # ---- the command line: `pol board gen c3 --variant esp32c3-light --knob pin_shim=0` (the chip-HAL build as a CLI step)
        import contextlib
        import io
        from board.custom import gen as G

        def cli(*words):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = gen_c3.main(['c3', '--out', work] + list(words))
            return rc, out.getvalue()
        rc, said = cli('--variant', V3.LIGHT_NAME, '--knob', 'pin_shim=0', '--knob', 'debounce_ms=40', '--device-id', '9')
        cfg = open(work + '/project/main/board_config.h').read()
        kept = json.loads(G.read_record(work)['repro_json'])['knobs']
        check('smp S5 CLI: --knob pin_shim=0 generates the chip-HAL light (PIN_SHIM 0 in board_config.h, the knob in the record and in what is printed)',
              rc == 0 and '#define PIN_SHIM 0 ' in cfg and kept['pin_shim'] == 0 and kept['debounce_ms'] == 40 and kept['device_id'] == 9 and 'pin_shim=0' in said, said)
        rc, said = cli('--variant', V3.LIGHT_NAME)
        check('smp S5 CLI: without the knob the light keeps the RAM pin shim (PIN_SHIM 1)', rc == 0 and '#define PIN_SHIM 1 ' in open(work + '/project/main/board_config.h').read()
              and 'pin_shim=1' in said, said)
        refusals = {'a knob the variant does not have': (['--variant', 'c3-sim-rig', '--knob', 'pin_shim=0'], 'has no knob pin_shim'),
                    'an unknown knob': (['--variant', V3.LIGHT_NAME, '--knob', 'pin_shmi=0'], 'has no knob pin_shmi'),
                    'a word without a value': (['--variant', V3.LIGHT_NAME, '--knob', 'pin_shim'], 'wants NAME=VALUE'),
                    'a knob named twice': (['--variant', V3.LIGHT_NAME, '--knob', 'pin_shim=0', '--knob', 'pin_shim=1'], 'twice'),
                    'a knob given by its own option and by --knob': (['--variant', V3.LIGHT_NAME, '--rig-name', 'a', '--knob', 'rig_name=b'], 'given twice'),
                    'a value outside the knob': (['--variant', V3.LIGHT_NAME, '--knob', 'pin_shim=2'], 'pin_shim is 0 (the chip HAL) or 1')}
        got = {n: cli(*words) for n, (words, _) in refusals.items()}
        check('smp S5 CLI: refused with exit 1 and the reason, never dropped: %s' % ', '.join(refusals),
              all(got[n][0] == 1 and '[REFUSED]' in got[n][1] and want in got[n][1] for n, (_, want) in refusals.items()), {n: g[1][:160] for n, g in got.items()})
    finally:
        shutil.rmtree(work, ignore_errors=True)

    from board.custom import light_c3_run as R
    from board.custom import board_engines as BE
    real = BE.resolve
    try:
        seen = {}
        for how in ('local-binary', BE.LOCAL_IMAGE, BE.REMOTE, 'refused'):
            BE.resolve = lambda engine, flash=False, how=how: {'how': how, 'where': 'x', 'kind': 'sim', 'why': 'said by the test'}
            seen[how] = R.engine_ready()
    finally:
        BE.resolve = real
    check('smp S5 engine: the C3 light is provable on a local engine AND on a worker over the ladder (c3-run is a batch engine); a refused ladder is not ready, with its reason: %s'
          % {h: r[0] for h, r in seen.items()}, [seen[h][0] for h in ('local-binary', BE.LOCAL_IMAGE, BE.REMOTE, 'refused')] == [True, True, True, False]
          and seen['refused'][1] == 'said by the test', seen)
    ready, why = R.engine_ready()
    if not ready:
        check('SKIP smp S5 (the light on the C3 twin): no esp engines here - %s' % why, True)
        return
    from board.custom import light_c3_twin as L3
    work = tempfile.mkdtemp(prefix='smp-c3-st-')
    try:
        # ---- build
        shim = R.build(work + '/shim')
        bc = shim.get('build_cost') or {}
        sz = shim.get('sizes') or {}
        check('smp S5 build: esp32c3-light (shim) builds: app %s B, DRAM %s / %s B; the build took %.0f s wall, %.0f CPU-s, peak RSS %.0f MB'
              % (shim.get('flash_bytes'), sz.get('dram_used'), sz.get('dram_total'), bc.get('wall_s', 0), bc.get('cpu_s', 0), bc.get('peak_rss_mb', 0)), shim.get('state') == 'built', shim.get('notes'))
        from board.custom import build_c3
        again = build_c3.build('c3', work + '/shim', force=True)
        check('smp S5 build: a forced rebuild gives the same merged-image sha256 (reproducible): %s' % shim.get('artifact_sha256', '')[:16], again.get('artifact_sha256') == shim.get('artifact_sha256') != '')
        chip = R.build(work + '/chip', pin_shim=0)
        check('smp S5 build: the CHIP HAL build (pin_shim=0, the gpio driver + interrupt service routine) compiles too: app %s B' % chip.get('flash_bytes'), chip.get('state') == 'built', chip.get('notes'))
        if shim.get('state') != 'built':
            return
        pads = not R.pin_model()
        check('pt-4: the esp engines here %s' % ('hold the PIN MODEL: the Purposes below are proven on the CHIP-HAL build (PIN_SHIM 0), the image a chip is flashed with' if pads
                                                 else 'have NO pin model (%s): the Purposes below are proven on the shim build' % R.pin_model()), True)

        # ---- the four Purposes through the per-config mechanism, then fsc_link
        from cmod.custom import approach_profile_input as AI
        from cmod.custom import capabilities as CAP
        from cmod.custom import fsc_link
        from cmod.custom.selftest_purpose import _manager
        from firmwarefaults.custom import acceptance as ACC
        from firmwarefaults.custom.sink import ManagerSink
        mgr = _manager()
        sink = ManagerSink(mgr, save=False)
        purposes = AI.purposes_of(AI.find_mission(LIGHT, mgr), mgr)
        runs = {}
        for p in purposes:
            sc = CAP.find(p['purpose'])['acceptance_scenario']
            r = ACC.run(sc, 'digital-twin', manager=mgr, sink=sink, variant=V3.LIGHT_NAME)
            runs[p['purpose']] = r
            check('smp S5 PURPOSE %s: %s on %s -> %s (%s frames); %s' % (p['purpose'], sc, V3.LIGHT_NAME, r['outcome'], r.get('frames_seen'), r['verdict_words'][:700]),
                  r['outcome'] == 'passed' and r['variant'] == V3.LIGHT_NAME and 'NOT a chip' in r['verdict_words'] and 'rejected by the same judge: True' in r['verdict_words']
                  and ('PIN_SHIM 0' in r['verdict_words']) == pads and ('RAM shim' in r['verdict_words']) != pads, r['verdict_words'][:400])
        state = fsc_link.config_state(V3.LIGHT_NAME, {'purposes': purposes}, mgr)
        check('smp S5 LINK: fsc_link reads the C3 config as %s - %s' % (state['state'], state['why'][:300]), state['state'] == 'finished', state)
        links, _unm = fsc_link.resolve(['drive-led'], [{'id': 'x', 'routes': {'drive-led': 'gpio-out'}, 'rank': 1, 'assignment': []}], mgr, {'purposes': purposes, 'job_purposes': {}})
        check('smp S5 LINK: the config is a built config of the Mission (the Purpose scenarios are accepted for it) and takes NO UNO solver candidate away from a UNO config',
              fsc_link.proof_config_refusal(V3.LIGHT_NAME, CAP.find('initialization')['acceptance_scenario'], mgr) == '' and V3.LIGHT_NAME not in {v['config'] for v in links.values()}, links)

        # ---- the chip HAL: on the pin model (pt-4) its pins are pads; on the prebuilt QEMU they are a register stub (the limit, still measured)
        if chip.get('state') != 'built':
            return
        k = R.knobs_of(chip)
        stub = R.run(chip, R.params(R.WINDOW_MS, R.N_PRESSES, R.BUTTON_GPIO, 1))          # no pads: the prebuilt QEMU, whatever the engine holds
        check('smp S5 LIMIT: the CHIP-HAL build on the prebuilt QEMU (GPIO a register stub) speaks frames (%d) but has no pins: %d pin-trace lines, no pin channel, button_presses=%s'
              % (len(stub['states']), len(stub['pin']), stub['states'][-1].get('button_presses') if stub['states'] else None),
              bool(stub['states']) and not stub['pin'] and not stub['pad_lines'] and not stub['states'][-1].get('button_presses'))
        if not pads:
            res = R.command_run(chip, [L3.LVT.set_led_frame(1, True)])
            check('pt-4 REFUSED: with no pin model the chip-HAL build cannot be run on pads - the run says so and is not a pass (%s)' % res['stderr'][-160:], not res['ok'] and res['stale_image'])
            proof = L3.prove('button', row=chip)
            check('pt-4 REFUSED: its proof is refused, not passed on the stub: %s' % proof['why'][:200], proof['route'] == 'refused' and not proof['ok'])
            return
        res = R.command_run(chip, [L3.LVT.set_led_frame(1, True)])
        last = res['states'][-1] if res['states'] else {}
        check('pt-4 PADS: SET_LED on the chip-HAL build reaches the LED pad: struct led_on=%s status %s, GPIO%d changes %s on the pin channel (%d pad lines)'
              % (last.get('led_on'), last.get('status'), k['led_pin'], res['pin'], len(res['pad_lines'].splitlines())),
              bool(last.get('led_on')) and last.get('status') == 'commanded' and res['pin'] and [lv for _m, lv in res['pin']] == [1] and res['on_pads'])
        pr, again = R.press_run(chip), R.press_run(chip)
        plast = pr['states'][-1] if pr['states'] else {}
        btn = [lv for _ns, lv in R.pad_levels(pr['pad_lines'], k['button_pin'])[0]]
        check('pt-4 PADS: %d stamped presses on GPIO%d reach the firmware through the GPIO interrupt: button_presses=%s, the button pad went %s, the dump counts the interrupts and '
              'names the wire' % (R.N_PRESSES, k['button_pin'], plast.get('button_presses'), ''.join(btn)),
              plast.get('button_presses') == R.N_PRESSES and btn == ['z', '1'] + ['0', '1'] * R.N_PRESSES and 'interrupts %d)' % R.N_PRESSES in pr['pin_dump']
              and '# wire %d-%d' % (k['led_pin'], k['sense_pin']) in pr['pin_dump'], pr['pin_dump'][-400:])
        led, sense = R.pad_levels(pr['pad_lines'], k['led_pin'])[0], R.pad_levels(pr['pad_lines'], k['sense_pin'])[0]
        check('pt-4 PADS: the sense pad follows the LED pad through the board wire at the same virtual instant, every change (%d): %s' % (len(led), ''.join(lv for _n, lv in led)),
              len(led) == 2 + R.N_PRESSES and led == sense, (led, sense))
        check('pt-4 PADS: the run repeats exactly - a second press run gives the same pin channel, byte for byte (the presses land on the same instruction)',
              bool(pr['pad_lines']) and pr['pad_lines'] == again['pad_lines'])
        nowire = R.press_run(chip, jumper=0)
        check('pt-4 PADS: with the wire off the sense pad never moves from its pull-down and the firmware counts no sense edge (%s rises, %s falls) while the LED pad still flips'
              % (nowire['states'][-1].get('sense_rises') if nowire['states'] else None, nowire['states'][-1].get('sense_falls') if nowire['states'] else None),
              bool(nowire['states']) and not nowire['states'][-1].get('sense_rises') and not nowire['states'][-1].get('sense_falls')
              and [lv for _m, lv in nowire['pin']] == [1, 0, 1] and '# wire' not in nowire['pin_dump'])
        sp = L3.prove('both', row=shim)
        check('pt-4: the shim build still passes its own proof on this engine, and its words still say RAM shim: %s' % sp['why'][:160],
              sp['ok'] and 'RAM shim' in sp['why'] and not sp.get('pin_model'), sp['why'][:400])
        check('smp S5 COST: the twin runs cost %s' % [(c.get('wall_s'), c.get('peak_rss_mb')) for c in (res['run'].get('boots') or [])], True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    n = [0, 0]

    def _check(label, cond, extra=''):
        n[0] += 1
        n[1] += bool(cond)
        print('  [%s] %s %s' % ('PASS' if cond else 'FAIL', label, '' if cond else extra))
    run_light_c3(_check)
    print('%d/%d checks passed' % (n[1], n[0]))
    raise SystemExit(0 if n[0] == n[1] else 1)
