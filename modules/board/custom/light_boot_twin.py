"""
@module board.custom.light_boot_twin

THE BOOT PURPOSE (`initialization`) ON THE SIMAVR TWIN (fsc-0b). Its contract (cmod.custom.purpose_seeds): trigger = the board starts or restarts; outcome = the first report
arrives carrying a NEW boot session number; criterion max_latency_ms = 100 (one report period at 10 Hz, the same bound the other light Purposes cite).

Builds the variant (default uno-light, LightState v1) through the shipped pipeline and drives it cycle-scheduled through firmwarefaults.custom.harness (never real-time sleeps),
decoding every frame with the independent Python reference codec. Three twin runs of the SAME hex:

  A  from reset, 100 ms of simulated time (1.6 M cycles at 16 MHz)      -> at least one whole report has arrived, and it carries boot_session
  B  the same, with avr_reset at 200 ms and 100 ms more                  -> the stream shows two boot sessions; the second differs from the first (EEPROM is kept across a
                                                                            reset, the atom boot_session_mint adds 1) and its first report is inside the 100 ms after the reset
  C  control: only 2 ms of simulated time                                -> no whole report yet; the judge must FAIL it (a first report later than the bound)

`judge_boot` is a pure function over decoded frames, so the negative controls are real: C's frames, the frames of A with boot_session removed, and B's frames with the second boot's
session forced equal to the first all go through the SAME judge and must fail. `prove()` returns the {'ok', 'route', 'why', 'frames_compared', 'how'} shape the acceptance runner
(firmwarefaults.custom.acceptance) turns into a ScenarioRun; it refuses honestly (route 'refused') with no twin. The runner works for any variant whose first class carries
boot_session (`variant=`); only uno-light is claimed as proof of the Purpose today.
"""
import shutil
import tempfile

VARIANT = 'uno-light'
CPS = 16000000
BOUND_MS = 100                      # the Purpose's max_latency_ms (one report period at 10 Hz)
BOUND_CYCLES = CPS * BOUND_MS // 1000
RESET_CYCLE = 2 * BOUND_CYCLES      # 200 ms: well after the first boot's reports
TOO_EARLY_CYCLES = CPS * 2 // 1000  # 2 ms: the board has barely finished set-up, no whole report yet


def _class_of(variant):
    from board.custom import variants as V
    return V.APP_CLASSES[V.find(variant)['app']][0]


def _decode(uart, cls):
    from board.custom import gen, packet_ref
    from board.custom.compat import wire_spec
    fmap = gen.pinned_contract(cls)[0]['field_map']
    spec = wire_spec(None, cls, fmap)
    p = packet_ref.StreamParser()
    out = []
    for mt, _dev, _seq, payload, ver in p.feed(bytes(uart)):
        if mt == 1:
            try:
                out.append(packet_ref.decode_any(fmap, payload, ver, spec))
            except ValueError:
                pass
    return out, p.bad_crc


def _run(hex_bytes, cycles, cls, reset_at=None):
    from firmwarefaults.custom import harness
    extra = ['--reset-at', 'cycle=%d' % reset_at] if reset_at is not None else []
    argv = ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', str(CPS), '--free', '--seconds', '%g' % (float(cycles) / CPS),
            '--status-ms', '0', '--uart-out', 'uart.bin'] + extra
    r = harness.run(argv, hex_bytes, timeout=120)
    frames, bad = _decode(r['uart'], cls)
    return r, frames, bad


def _sessions(frames):
    """The boot_session values in stream order, consecutive repeats folded; None when a frame does not carry one."""
    out = []
    for f in frames:
        s = f.get('boot_session')
        if s is None:
            return None
        if not out or out[-1] != int(s):
            out.append(int(s))
    return out


def judge_boot(first_frames, reboot_frames):
    """(ok, why). first_frames = the frames of 100 ms from reset; reboot_frames = the frames of a run with a reset at 200 ms and 100 ms more. Pass only when
    (1) a whole report arrived inside the first 100 ms and carries boot_session; (2) the reboot stream holds exactly two boot sessions, in order, the second different from
    the first, so the first report after the second reset arrived inside its 100 ms and names a NEW session."""
    s1 = _sessions(first_frames)
    if not first_frames:
        return False, 'no whole report arrived within the %d ms after reset' % BOUND_MS
    if s1 is None:
        return False, 'a report arrived but does not carry boot_session'
    s2 = _sessions(reboot_frames)
    if s2 is None:
        return False, 'a report after the reset does not carry boot_session'
    if len(s2) != 2:
        return False, 'the stream with a reset in it shows %d boot session(s) %s, wanted 2 (one before the reset and a report of the new one within %d ms after it)' % (len(s2), s2, BOUND_MS)
    if s2[0] == s2[1]:
        return False, 'the first report after the second reset carries the same boot_session (%d) as before it' % s2[0]
    return True, ('the first report arrives inside %d ms of reset carrying boot_session %d; after a second reset the first report inside its %d ms carries boot_session %d, which differs'
                  % (BOUND_MS, s1[0], BOUND_MS, s2[1]))


def controls(first_frames, reboot_frames, too_early_frames):
    """-> [(label, judged_ok)] - every one must be False (the judge must reject it). Built from the real runs."""
    nobs = [{k: v for k, v in f.items() if k != 'boot_session'} for f in first_frames]
    same = [dict(f, boot_session=reboot_frames[0].get('boot_session')) for f in reboot_frames] if reboot_frames else []
    return [('first report later than the bound (only 2 ms of the boot seen: %d report(s))' % len(too_early_frames), judge_boot(too_early_frames, reboot_frames)[0]),
            ('reports without boot_session', judge_boot(nobs, reboot_frames)[0]),
            ('second boot reports the first boot\'s session', judge_boot(first_frames, same)[0]),
            ('no reset in the stream (one session only)', judge_boot(first_frames, first_frames)[0])]


def engine_ready():
    from board.custom import light_twin as LT
    return LT.engine_ready()


def prove(mode='digital-twin', variant=VARIANT):
    if mode == 'hardware':
        return {'ok': False, 'route': 'refused', 'why': 'the boot test --hardware is not wired yet (the UNO is not attached)'}
    ready, why = engine_ready()
    if not ready:
        return {'ok': False, 'route': 'refused', 'why': 'no simavr twin here: %s' % why}
    from board.custom import gen, build as B
    work = tempfile.mkdtemp(prefix='fsc0b-boot-')
    try:
        gen.gen('uno', None, work, variant=variant)
        row = B.build('uno', work)
        if row.get('state') != 'built':
            return {'ok': False, 'route': 'digital-twin', 'why': '%s did not build: %s' % (variant, row.get('notes'))}
        hex_bytes = open(row['hex_path'], 'rb').read()
        cls = _class_of(variant)
        ra, fa, bad_a = _run(hex_bytes, BOUND_CYCLES, cls)
        rb, fb, bad_b = _run(hex_bytes, RESET_CYCLE + BOUND_CYCLES, cls, reset_at=RESET_CYCLE)
        rc, fc, _bad_c = _run(hex_bytes, TOO_EARLY_CYCLES, cls)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    ok, words = judge_boot(fa, fb)
    ctl = controls(fa, fb, fc)
    ctl_ok = all(not passed for _l, passed in ctl)
    ok = ok and ctl_ok and ra['ok'] and rb['ok'] and bad_a == 0 and bad_b == 0
    return {'ok': ok, 'route': 'digital-twin', 'frames_compared': len(fa) + len(fb) + len(fc),
            'why': '%s on %s; negative controls all rejected by the same judge: %s%s' % (words, variant, ctl_ok, '' if ctl_ok else ' [' + '; '.join(l for l, p in ctl if p) + ' WRONGLY PASSED]'),
            'controls': [{'control': l, 'judged_ok': p} for l, p in ctl],
            'how': 'board.custom.light_boot_twin (firmwarefaults.custom.harness: --reset-at, the Python wire reference decoder; bound %d ms = %d cycles at 16 MHz)' % (BOUND_MS, BOUND_CYCLES)}
