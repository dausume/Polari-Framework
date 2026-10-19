"""board_light_c3_selftest - smp S5: the light Mission on the ESP32-C3 under FreeRTOS, proven on the C3 TWIN (QEMU esp32c3; no C3 board is on the bench; the pins are a RAM shim because QEMU's C3
GPIO is a register stub). SKIPS honestly without the esp engines image. Parts:

  pins     the chosen GPIOs carry no constraint row in board.custom.lifecycle_c3 (no strapping / USB / UART0 / flash / JTAG), the knob validator refuses the ones that do
  gen      the C3 light project holds the ButtonClockState + ButtonClockEvent headers, light_hal.h and the extra REQUIRES; the other C3 variants' projects are untouched
  build    the shim build and the chip-HAL build compile; a forced rebuild gives the same image sha256; the cost (wall, CPU, peak RSS, sizes) is measured
  twin     the four Purposes' own acceptance scenarios, run on the config through firmwarefaults.custom.acceptance (variant=esp32c3-light), all four passed ScenarioRuns, every negative
           control rejected; fsc_link reads the config as finished; the board is refused for the UNO's pin route check
  chip HAL the chip-HAL build boots on the twin and speaks frames, but the LED write is NOT observable (no pin trace) - the twin's stated limit, measured

    PYTHONPATH=.:modules python3 -m board.board_light_c3_selftest      # from polari-framework/ (standalone)
"""
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
    finally:
        shutil.rmtree(work, ignore_errors=True)

    from board.custom import light_c3_run as R
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
                  r['outcome'] == 'passed' and r['variant'] == V3.LIGHT_NAME and 'NOT a chip' in r['verdict_words'] and 'rejected by the same judge: True' in r['verdict_words'], r['verdict_words'][:400])
        state = fsc_link.config_state(V3.LIGHT_NAME, {'purposes': purposes}, mgr)
        check('smp S5 LINK: fsc_link reads the C3 config as %s - %s' % (state['state'], state['why'][:300]), state['state'] == 'finished', state)
        links, _unm = fsc_link.resolve(['drive-led'], [{'id': 'x', 'routes': {'drive-led': 'gpio-out'}, 'rank': 1, 'assignment': []}], mgr, {'purposes': purposes, 'job_purposes': {}})
        check('smp S5 LINK: the config is a built config of the Mission (the Purpose scenarios are accepted for it) and takes NO UNO solver candidate away from a UNO config',
              fsc_link.proof_config_refusal(V3.LIGHT_NAME, CAP.find('initialization')['acceptance_scenario'], mgr) == '' and V3.LIGHT_NAME not in {v['config'] for v in links.values()}, links)

        # ---- what the twin cannot show (chip HAL)
        res = R.command_run(chip, [L3.LVT.set_led_frame(1, True)])
        last = res['states'][-1] if res['states'] else {}
        check('smp S5 LIMIT: the CHIP-HAL build on the twin speaks frames (%d), takes SET_LED into its struct (led_on=%s, status %s) but the LED write is not observable: %d pin-trace lines '
              '(QEMU esp32c3 GPIO is a register stub)' % (len(res['states']), last.get('led_on'), last.get('status'), len(res['pin'])),
              bool(last.get('led_on')) and last.get('status') == 'commanded' and not res['pin'])
        pr = R.press_run(chip)
        check('smp S5 LIMIT: the same chip-HAL build with a scripted press does nothing on the twin (no button input exists): button_presses=%s' % (pr['states'][-1].get('button_presses') if pr['states'] else None),
              bool(pr['states']) and not pr['states'][-1].get('button_presses'))
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
