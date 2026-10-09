"""
@module board.custom.button_clock_acceptance

THE ACCEPTANCE RUNNER for the Purpose `button-clock-to-os` (ucd-0e2, UNO_CORE_DEMO_PLAN.md §1): exercises exactly the
probe's (a)+(f) case — N presses + --wire PD6:PD3 → the invariant holds; the SAME presses with NO --wire → the sense
counters stay 0 while button_presses does not — on the simavr twin, deterministically (firmwarefaults.custom.harness,
never real-time sleeps), and reports a result shaped like cmod.custom.firmware.run()'s so firmwarefaults.custom.
acceptance.run() can turn it into a ScenarioRun the SAME way it already does for the other capabilities.

Why a dedicated runner instead of acceptance.run()'s usual `FW.run(fs, mode)` (glue_build.prove, the twin-equivalence
check every other seeded capability reuses): button-clock-to-os has NO FirmwareSolution/CGraph yet (0e2b's job,
explicitly out of scope here) — there is no graph for glue_build to prove equivalent to anything. This runner proves
the GOAL directly instead (the invariant on real simulated silicon), reusing the SAME building blocks board.
board_button_clock_twin_selftest already proves with (gen/build, --pin-at, --wire, the Python wire reference decoder)
— never a second simulator, never a second codec.

    PYTHONPATH=.:modules python3 -m cmod.custom.capability_cli prove button-clock-to-os --twin
"""
import tempfile

from board import board_button_clock_twin_selftest as T


def run_acceptance(mode='digital-twin'):
    """-> {'ok', 'route', 'why', 'frames_compared', 'how'} — the shape acceptance.run() already expects from
    cmod.custom.firmware.run(); 'route' 'refused' turns into outcome 'inapplicable' there, matching the existing
    posture (never a hollow 'undetermined' when the thing that cannot run is named)."""
    if mode == 'hardware':
        return {'ok': False, 'route': 'refused',
                'why': 'button-clock-to-os --hardware is not wired yet (ucd-3: the UNO is not attached — the stopgap '
                       'flash.py path is this slice\'s explicit do-not-touch list)'}
    from board.custom import board_engines as be
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        return {'ok': False, 'route': 'refused', 'why': 'no simavr twin here: %s' % where['why']}
    from firmwarefaults.custom import harness

    fmap_s, spec_s, fmap_e, spec_e = T._specs()
    work = tempfile.mkdtemp(prefix='ucd-0e2-acceptance-')
    row = T._build(work)
    if row.get('state') != 'built':
        return {'ok': False, 'route': 'digital-twin', 'why': 'uno-button-clock did not build: %s' % row.get('notes')}
    hex_bytes = open(row['hex_path'], 'rb').read()

    pinat, end_cycle = T._press_pinat()
    seconds = (end_cycle + 1600000) / 16000000.0

    # (a) the invariant, with --wire PD6:PD3
    argv_a = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds,
              '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin', '--wire', 'PD6:PD3'] + pinat
    r_a = harness.run(argv_a, hex_bytes, timeout=120)
    states_a, events_a, bad_crc_a = T._decode_frames(r_a['uart'], fmap_s, spec_s, fmap_e, spec_e)
    last_a = states_a[-1] if states_a else {}
    n = T.N_PRESSES
    ok_a = (r_a['ok'] and bad_crc_a == 0 and last_a.get('button_presses') == n
            and (last_a.get('sense_rises', 0) + last_a.get('sense_falls', 0)) == n
            and last_a.get('led_on') == bool(n % 2) and last_a.get('dropped_events', -1) == 0)

    # (f) the negative, no --wire
    argv_f = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds,
              '--status-ms', '0', '--adc0-mv', '750', '--uart-out', 'uart.bin'] + pinat
    r_f = harness.run(argv_f, hex_bytes, timeout=120)
    states_f, _, _ = T._decode_frames(r_f['uart'], fmap_s, spec_s, fmap_e, spec_e)
    last_f = states_f[-1] if states_f else {}
    ok_f = (r_f['ok'] and last_f.get('button_presses') == n
            and last_f.get('sense_rises', -1) == 0 and last_f.get('sense_falls', -1) == 0)

    ok = ok_a and ok_f
    why = ('(a) %s presses + --wire PD6:PD3: button_presses=%s sense_rises+falls=%s led_on=%s dropped=%s; '
           '(f) NO --wire: button_presses=%s sense_rises=%s sense_falls=%s' % (
               n, last_a.get('button_presses'), last_a.get('sense_rises', 0) + last_a.get('sense_falls', 0),
               last_a.get('led_on'), last_a.get('dropped_events'), last_f.get('button_presses'),
               last_f.get('sense_rises'), last_f.get('sense_falls')))
    return {'ok': ok, 'route': 'digital-twin', 'why': why, 'frames_compared': len(states_a) + len(events_a),
            'how': 'board.custom.button_clock_acceptance (firmwarefaults.custom.harness, --pin-at + --wire, the Python '
                   'wire reference decoder) — the SAME building blocks as board.board_button_clock_twin_selftest'}
