"""
@module board.custom.light_c3_twin

smp S5: THE FOUR PURPOSES OF THE LIGHT MISSION ON THE ESP32-C3 TWIN. `prove(which, mode, variant)` returns the {'ok', 'route', 'why', 'frames_compared', 'controls', 'how'} shape
board.custom.light_twin.prove returns, so firmwarefaults.custom.acceptance_config turns it into a ScenarioRun of THIS config's own firmware (cmod.custom.fsc_link). PROOF LEVEL, said in
every result: the C3 TWIN (Espressif QEMU `-machine esp32c3`, the real ESP-IDF FreeRTOS build) with the pin HAL replaced by a RAM shim - QEMU's C3 GPIO is a register stub. No C3 board
is on the bench; nothing here is a chip result (board.custom.light_c3_run says what the twin is and is not).

The judges are the ones the UNO sense configs use (board.custom.light_variant_twin: ButtonClockState stand-ins for the light check), and the boot judge is board.custom.light_boot_twin's:

  button   (ensure-button-controls-light / ensure-polari-observes-hardware-state)  3 presses -> button_presses == 3, led_on flips each time, status idle, 3 `press` events; AND the LED
           line: the shim's pin writes flip with the presses and the sense line counted one edge per change (sense_rises + sense_falls == 3, led_on == rises > falls)
  polari   (ensure-polari-can-control-light)  STARTS FROM THE STRUCT: board.custom.light_struct.Session runs the backend solution light-toggle, the command frames are DERIVED from the
           committed change, sent over UART0 RX: the board's struct takes it, the LED pin follows, the next report says status commanded; then OFF; the quiet run stays quiet
  boot     (initialization)  the first report arrives within 100 ms of the app's start and names a boot_session; after a power cycle (flash kept) the first report names a NEW one

Negative controls, real twin runs through the SAME judges (each must be rejected): no press; presses on a pin that is not the button; presses with the sense jumper off (the sense check);
no command sent; plus the boot judge's four controls and the derived-frame controls of the struct proof.
"""
import atexit
import shutil
import tempfile

from board.custom import light_c3_run as R
from board.custom import light_variant_twin as LVT

VARIANT = R.VARIANT
HOW = 'board.custom.light_c3_twin (QEMU esp32c3 via the esp engines c3-run: UART0 frames decoded by the Python reference codec; pin writes read off the trace; the LED/sense/button pins are a RAM shim)'
LEVEL = ('ON THE C3 TWIN (Espressif QEMU esp32c3 running the real ESP-IDF FreeRTOS build; its GPIO is a register stub, so the pins are a RAM shim) - NOT a chip: no C3 board is on the bench. ')


_BUILT = {}


def built(variant=VARIANT):
    """The built config, once per process (the four Purposes of `pol firmware prove` share one ~35 s build); its work dir goes at exit."""
    if variant not in _BUILT:
        work = tempfile.mkdtemp(prefix='smp-c3-')
        atexit.register(shutil.rmtree, work, True)
        _BUILT[variant] = R.build(work, variant)
    return _BUILT[variant]


def judge_led_line(res, n=R.N_PRESSES):
    """(ok, why): the pin the LED task drives changed once per press (low -> high -> low ...) and the sense line counted the same edges."""
    last = res['states'][-1] if res['states'] else {}
    levels = [lv for _ms, lv in res['pin']]
    want = [(i + 1) % 2 for i in range(n)]
    edges = (last.get('sense_rises') or 0) + (last.get('sense_falls') or 0)
    sensed = bool(last.get('led_on')) == ((last.get('sense_rises') or 0) > (last.get('sense_falls') or 0))
    ok = levels == want and edges == n and sensed
    return ok, 'LED pin writes %s (want %s); sense edges counted %d (want %d); led_on == (rises > falls): %s' % (levels, want, edges, n, sensed)


def press_check(row, n=R.N_PRESSES, want=R.N_PRESSES, **kw):
    """Run `n` scripted presses and judge them against `want` (the controls run fewer or misdirected presses and must fail the judgement for the full set)."""
    res = R.press_run(row, n, **kw)
    ok, why = LVT.judge_presses(res['states'], res['events'], want)
    lok, lwhy = judge_led_line(res, want)
    return res, ok and lok and res['ok'] and res['bad_crc'] == 0, '%s; %s' % (why, lwhy)


def prove_button(row):
    res, ok, words = press_check(row)
    r0, o0, _ = press_check(row, 0)
    r1, o1, _ = press_check(row, R.N_PRESSES, press_gpio=R.WRONG_GPIO)
    r2, o2, _ = press_check(row, R.N_PRESSES, jumper=0)
    ctl = [('no press at all', o0 and r0['ok']), ('the same presses on a GPIO that is not the button', o1 and r1['ok']),
           ('the same presses with the LED-to-sense jumper off (the sense line must count the changes)', o2 and r2['ok'])]
    return ok, 'button: ' + words, len(res['states']) + len(res['events']), ctl


def prove_polari(row):
    from board.custom import light_struct as LS
    from board.custom import light_twin as LT
    ses = LS.Session('ButtonClockState')
    on, off = ses.run('toggle'), ses.run('toggle')
    derived = on['frames'] + off['frames']
    solution_ok = (on['status'] == 'completed' and off['status'] == 'completed' and len(on['frames']) == 1 and len(off['frames']) == 1
                   and [c['fields'] for r in (on, off) for c in r['committed']] == [{ses.cmd: True}, {ses.cmd: False}])
    ra = R.command_run(row, on['frames'])
    last_a = ra['states'][-1] if ra['states'] else {}
    a_ok = ra['ok'] and ra['bad_crc'] == 0 and bool(last_a.get('led_on')) and last_a.get('status') == 'commanded' and not last_a.get('button_presses') and R.led_pin_high(ra) is True
    rb = R.command_run(row, derived)
    jb, wb = LVT.judge_commands(rb['states'])
    b_ok = rb['ok'] and rb['bad_crc'] == 0 and jb and R.led_pin_high(rb) is False and [lv for _m, lv in rb['pin']] == [1, 0]
    hand = R.command_run(row, [LVT.set_led_frame(1, True), LVT.set_led_frame(2, False)])
    hok, hw = LVT.judge_commands(hand['states'])
    half = hok and hand['ok'] and hand['bad_crc'] == 0
    rq = R.command_run(row, [])
    lq = rq['states'][-1] if rq['states'] else {}
    quiet = rq['ok'] and bool(rq['states']) and not lq.get('led_on') and not rq['pin'] and lq.get('status') == 'idle'
    ctl = []
    for kind, label in (('same', 'a write that leaves set_led unchanged derives a frame'), ('other', 'a write of %s only derives a frame' % ses.other)):
        w = LS.Session('ButtonClockState').run(kind)
        ctl.append((label, bool(w['frames']) or w['status'] != 'completed'))
    ctl.append(('the command judge passes a twin run with nothing sent', LVT.judge_commands(rq['states'])[0]))
    ok = solution_ok and a_ok and b_ok and half and quiet
    words = ('polari: the struct was altered through the backend solution light-toggle on a test manager (%d StateChangeCommit(s): %s); the command frames were DERIVED from those committed changes '
             '(%d frames, none hand-built); ON: board struct led_on=%s status=%s, the LED pin %s; ON then OFF: %s, pin writes %s; board-half (hand frames): %s; with nothing sent the board stays quiet '
             '(LED never written, status idle): %s'
             % (len(on['committed']) + len(off['committed']), '/'.join('%s=%s' % (k, v) for r in (on, off) for c in r['committed'] for k, v in c['fields'].items()), len(derived),
                last_a.get('led_on'), last_a.get('status'), 'high' if R.led_pin_high(ra) else 'low', wb, [lv for _m, lv in rb['pin']], hw, quiet))
    return ok, words, len(ra['states']) + len(rb['states']) + len(hand['states']), ctl


def prove_boot(row):
    from board.custom import light_boot_twin as LB
    ra = R.reboot_run(row)
    boots = R.first_reports(ra['states'])
    first, again = (boots + [[], []])[:2]
    ok, words = LB.judge_boot(first, first + again)
    too_early = [f for f in ra['states'][:3] if int(f.get('uptime_ms') or 0) <= 2]
    ctl = LB.controls(first, first + again, too_early)
    return ok and ra['ok'] and ra['bad_crc'] == 0 and len(boots) == 2, 'boot: %s (app time from esp_timer 0; the ROM and bootloader time before it is not counted)' % words, len(ra['states']), ctl


def prove(which='both', mode='digital-twin', variant=VARIANT, row=None):
    """which: 'button' | 'polari' | 'boot' | 'both' (button + polari)."""
    if mode == 'hardware':
        return {'ok': False, 'route': 'refused', 'why': 'no C3 board is on the bench: %s is proven on the twin only' % variant}
    ready, why = R.engine_ready()
    if not ready:
        return {'ok': False, 'route': 'refused', 'why': 'no C3 twin here: %s' % why}
    row = row or built(variant)
    if row.get('state') != 'built':
        return {'ok': False, 'route': 'digital-twin', 'why': '%s did not build: %s' % (variant, row.get('notes'))}
    ok, parts, seen, ctl = True, [], 0, []
    for name, fn in (('button', prove_button), ('polari', prove_polari), ('boot', prove_boot)):
        if which == name or (which == 'both' and name != 'boot'):
            o, w, n, c = fn(row)
            ok, seen, ctl = ok and o, seen + n, ctl + c
            parts.append(w)
    ctl_ok = all(not passed for _l, passed in ctl)
    return {'ok': ok and ctl_ok, 'route': 'digital-twin', 'frames_compared': seen, 'sha256': row.get('artifact_sha256', ''),
            'why': '%s%s; negative controls all rejected by the same judge: %s%s' % (LEVEL, '; '.join(parts), ctl_ok, '' if ctl_ok else ' [' + '; '.join(l for l, p in ctl if p) + ' WRONGLY PASSED]'),
            'controls': [{'control': l, 'judged_ok': p} for l, p in ctl], 'how': HOW}
