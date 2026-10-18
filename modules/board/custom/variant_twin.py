"""
@module board.custom.variant_twin

fgm-5a: THE ISOTOPE VARIANTS ON THE SIMAVR TWIN. A catalogue route climbs from `compiles` to `proven-on-twin` only when a
passing ScenarioRun says it worked; this module is the runner those ScenarioRuns come from (firmwarefaults.custom.acceptance
dispatches here by the Scenario's `before_variant`). Same posture as board.custom.light_twin: builds the variant through the
shipped pipeline (gen + build, the board engines seam), drives it deterministically through firmwarefaults.custom.harness
(cycle-scheduled, never real-time sleeps), decodes every frame with the independent Python reference codec, and returns the
{'ok', 'route', 'why', 'frames_compared'} shape cmod.custom.firmware.run() returns. Refuses honestly (route 'refused') with no twin.

  uno-light-pcint    3 debounced presses on D4 (--pin-at PD4): each flips led_on, toggles == presses, source == button, and the
                     LIGHT PIN ITSELF follows (PORTD bit 6 read from the twin); presses on D2 (no INT0, not armed) change nothing;
                     a bouncing contact (0,1,0 within 125 us) counts once
  uno-light-analog   A0 driven by the twin's triangle ramp (--adc0-ramp 200,4800,1000): the falling crossings of the press
                     threshold are the presses, counted by a pure model of the ramp and compared with the frames; a constant
                     high level (never pressed) and a switch already closed at boot (200 mV constant) count nothing
  uno-sim-rig PWM    SET pwm_duty 25 / 50 / 100 over the serial link -> OCR0A read from the twin's status lines becomes
                     63 / 127 / 255 (= duty x 255 / 100) and the duty the timer produces = OCR0A / 255 is within 0.5 percentage points
"""
import json
import tempfile

N_PRESSES = 3
PRESS_HOLD_CYCLES = 80000
PRESS_GAP_CYCLES = 2400000     # 150 ms: >= 3 x the 30 ms debounce
START_CYCLE = 1600000          # 100 ms in, past the init at the top of main()
RUN_TAIL = 1600000
RAMP = (200, 4800, 1000)       # mV lo, hi, period ms of the twin's triangle on ADC0 (starts LOW = the switch closed)
RAMP_SECONDS = 3.6
PWM_STEPS = ((25, 4800000), (50, 16000000), (100, 24000000))   # (commanded duty %, inject cycle)
PWM_SECONDS = 2.0
PORTD_ADDR, OCR0A_ADDR = 0x2B, 0x47    # data-space addresses (I/O 0x0B + 0x20, 0x27 + 0x20)
LED_BIT = 6

CHECKS = {'uno-light-pcint': ('presses', 'wrong-pin', 'bounce'), 'uno-light-analog': ('ramp', 'high', 'closed-at-boot'),
          'uno-sim-rig': ('pwm',)}


def engine_ready():
    from board.custom import light_twin as LT
    return LT.engine_ready()


def build(variant, work):
    from board.custom import gen, build as B
    gen.gen('uno', None, work, variant=variant)
    return B.build('uno', work)


def _argv(seconds, extra, adc='--adc0-mv 750', status_ms=0):
    return ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds,
            '--status-ms', str(status_ms), '--uart-out', 'uart.bin'] + adc.split() + extra


def _watch_portd():
    return ['--watch', '0x%x/1=PORTD' % PORTD_ADDR]


def led_pin_high(res):
    """PORTD bit 6 (the light) as the twin read it at the end of the run -> bool, or None when the twin gave no watch."""
    w = ((res.get('final') or {}).get('watch') or {})
    return bool(int(w['final']) & (1 << LED_BIT)) if 'final' in w else None


def press_pinat(pin, n=N_PRESSES, start=START_CYCLE):
    out, c = [], start
    for _ in range(n):
        out += ['--pin-at', 'cycle=%d,pin=%s,level=0' % (c, pin), '--pin-at', 'cycle=%d,pin=%s,level=1' % (c + PRESS_HOLD_CYCLES, pin)]
        c += PRESS_GAP_CYCLES
    return out, c


def _run_light(hex_bytes, seconds, extra, adc='--adc0-mv 750'):
    from firmwarefaults.custom import harness
    from board.custom import light_twin as LT
    r = harness.run(_argv(seconds, extra + _watch_portd(), adc), hex_bytes, timeout=120)
    frames, bad = LT.decode(r['uart'])
    return r, frames, bad


def _last(frames):
    return frames[-1] if frames else {}


# ------------------------------------------------------------------ uno-light-pcint
def check_presses(hex_bytes):
    from board.custom import light_twin as LT
    pinat, end = press_pinat('PD4')
    r, fr, bad = _run_light(hex_bytes, (end + RUN_TAIL) / 16e6, pinat)
    ok, why = LT.judge_presses(fr, N_PRESSES)
    led = led_pin_high(r)
    ok = ok and r['ok'] and bad == 0 and led == bool(N_PRESSES % 2)
    return ok, '%d presses on D4: %s; the light pin (PD6) read %s from the twin' % (N_PRESSES, why, 'high' if led else 'low' if led is False else 'unread'), len(fr)


def check_wrong_pin(hex_bytes):
    pinat, end = press_pinat('PD2')
    r, fr, bad = _run_light(hex_bytes, (end + RUN_TAIL) / 16e6, pinat)
    last = _last(fr)
    ok = r['ok'] and bad == 0 and bool(fr) and last.get('toggles') == 0 and not last.get('led_on') and led_pin_high(r) is False
    return ok, 'the same %d presses on D2 (not armed on this variant): last frame toggles=%s led_on=%s, light pin %s' % (
        N_PRESSES, last.get('toggles'), last.get('led_on'), 'high' if led_pin_high(r) else 'low'), len(fr)


def check_bounce(hex_bytes):
    c = START_CYCLE
    bounce = []
    for dc, lvl in ((0, 0), (2000, 1), (4000, 0), (20000, 1), (22000, 0)):   # 125 us, 125 us, 1 ms, 125 us: one press with ringing
        bounce += ['--pin-at', 'cycle=%d,pin=PD4,level=%d' % (c + dc, lvl)]
    bounce += ['--pin-at', 'cycle=%d,pin=PD4,level=1' % (c + 22000 + PRESS_HOLD_CYCLES)]
    r, fr, bad = _run_light(hex_bytes, (c + PRESS_GAP_CYCLES) / 16e6, bounce)
    last = _last(fr)
    ok = r['ok'] and bad == 0 and bool(fr) and last.get('toggles') == 1 and bool(last.get('led_on')) and led_pin_high(r) is True
    return ok, 'one press with contact bounce (4 extra edges within 1.4 ms) counted %s time(s): led_on=%s, light pin %s' % (
        last.get('toggles'), last.get('led_on'), 'high' if led_pin_high(r) else 'low'), len(fr)


# ------------------------------------------------------------------ uno-light-analog
def expected_presses(lo, hi, period_ms, seconds, press_below_mv, release_above_mv):
    """The press count a correct threshold-with-hysteresis reader must report for the twin's triangle ramp: a pure model, 1 ms steps
    (the twin's ramp is lo -> hi -> lo over period_ms of SIM time). A switch closed at t = 0 is not a press."""
    half = period_ms // 2
    span = max(hi - lo, 0)

    def mv(ms):
        m = ms % period_ms
        return lo + span * (m if m < half else period_ms - m) // max(half, 1)
    pressed = mv(0) < press_below_mv
    n = 0
    for ms in range(1, int(seconds * 1000)):
        v = mv(ms)
        if pressed and v > release_above_mv:
            pressed = False
        elif not pressed and v < press_below_mv:
            pressed, n = True, n + 1
    return n


def _thresholds(variant='uno-light-analog'):
    from board.custom import variants as V
    k = V.resolve(V.find(variant))['knobs']
    return k['adc_press_below_mv'], k['adc_release_above_mv']


def check_ramp(hex_bytes):
    press, release = _thresholds()
    want = expected_presses(*RAMP, RAMP_SECONDS, press, release)
    r, fr, bad = _run_light(hex_bytes, RAMP_SECONDS, [], adc='--adc0-ramp %d,%d,%d' % RAMP)
    last = _last(fr)
    seen = sorted({(f.get('toggles'), bool(f.get('led_on'))) for f in fr})
    consistent = all(led == bool(t % 2) for t, led in seen)
    led = led_pin_high(r)
    ok = (r['ok'] and bad == 0 and bool(fr) and want >= 2 and last.get('toggles') == want and last.get('source') == 'button'
          and consistent and led == bool(want % 2))
    return ok, ('A0 ramp %d..%d mV over %d ms for %g s (press below %d mV, release above %d mV): the model says %d presses; last frame toggles=%s '
                'led_on=%s source=%s, every state seen had led_on == (toggles odd): %s; the light pin read %s'
                % (RAMP[0], RAMP[1], RAMP[2], RAMP_SECONDS, press, release, want, last.get('toggles'), last.get('led_on'), last.get('source'),
                   consistent, 'high' if led else 'low')), len(fr)


def check_high(hex_bytes):
    r, fr, bad = _run_light(hex_bytes, 1.0, [], adc='--adc0-mv 4800')
    last = _last(fr)
    return (r['ok'] and bad == 0 and bool(fr) and last.get('toggles') == 0 and led_pin_high(r) is False,
            'A0 held at 4800 mV (never pressed) for 1 s: toggles=%s led_on=%s' % (last.get('toggles'), last.get('led_on')), len(fr))


def check_closed_at_boot(hex_bytes):
    r, fr, bad = _run_light(hex_bytes, 1.0, [], adc='--adc0-mv 200')
    last = _last(fr)
    return (r['ok'] and bad == 0 and bool(fr) and last.get('toggles') == 0 and led_pin_high(r) is False,
            'A0 held at 200 mV (the switch closed from boot) for 1 s: toggles=%s led_on=%s - a switch already closed at boot is not a press'
            % (last.get('toggles'), last.get('led_on')), len(fr))


# ------------------------------------------------------------------ the PWM LED (uno-sim-rig)
def _sim_codec():
    from board.custom import gen
    from board.custom.compat import wire_spec
    fmap = gen.pinned_contract('SimRigState')[0]['field_map']
    return fmap, wire_spec(None, 'SimRigState', fmap)


def check_pwm(hex_bytes):
    from board.custom import packet_ref
    from firmwarefaults.custom import harness
    from grpcbridge.custom import wire_ref
    fmap, spec = _sim_codec()
    files, argv_inj = {}, []
    for i, (duty, cycle) in enumerate(PWM_STEPS):
        name = 'duty%d.bin' % i
        files[name] = packet_ref.frame(1, 0, i + 1, wire_ref.encode(spec, {'pwm_duty': duty}, present=['pwm_duty']), version=spec['wire_version'])
        argv_inj += ['--inject', '%s@%d' % (name, cycle)]
    r = harness.run_files(_argv(PWM_SECONDS, argv_inj + ['--watch', '0x%x/1=OCR0A' % OCR0A_ADDR], status_ms=100), hex_bytes, files, timeout=120)
    status = []
    for line in (r.get('stdout') or '').splitlines():
        if line.startswith('{"t":"status"'):
            try:
                status.append(json.loads(line))
            except ValueError:
                pass
    p = packet_ref.StreamParser()
    frames = []
    for mt, dev, seq, pl, ver in p.feed(bytes(r['uart'])):
        try:
            if mt == 1:
                frames.append(packet_ref.decode_any(fmap, pl, ver, spec))
        except ValueError:   # a frame of another class (firmware that is not the sim rig): nothing it says is a SimRigState echo
            pass
    parts, ok, before = [], r['ok'] and bool(status), [s for s in status if s['cycle'] < PWM_STEPS[0][1]]
    ok = ok and bool(before) and before[-1]['ocr0a'] == 0
    parts.append('before any command OCR0A = %s (duty 0 %%)' % (before[-1]['ocr0a'] if before else 'unread'))
    for i, (duty, cycle) in enumerate(PWM_STEPS):
        nxt = PWM_STEPS[i + 1][1] if i + 1 < len(PWM_STEPS) else float('inf')
        window = [s for s in status if cycle < s['cycle'] < nxt]
        ocr = window[-1]['ocr0a'] if window else None
        want = duty * 255 // 100
        got_pct = (ocr * 100.0 / 255.0) if ocr is not None else None
        good = ocr == want and got_pct is not None and abs(got_pct - duty) <= 0.5 and any(f.get('pwm_duty') == duty for f in frames)
        ok = ok and good
        parts.append('SET pwm_duty %d -> OCR0A %s (want %d) = %.1f %% duty%s' % (duty, ocr, want, got_pct if got_pct is not None else float('nan'),
                                                                               '' if good else ' MISMATCH'))
    return ok, '; '.join(parts), len(frames)


FNS = {'presses': check_presses, 'wrong-pin': check_wrong_pin, 'bounce': check_bounce, 'ramp': check_ramp, 'high': check_high,
       'closed-at-boot': check_closed_at_boot, 'pwm': check_pwm}


def prove(variant, mode='digital-twin'):
    """-> {'ok', 'route', 'why', 'frames_compared', 'how', 'build': {...measured sizes + hex sha}} - one build, every check of the variant."""
    if variant not in CHECKS:
        return {'ok': False, 'route': 'refused', 'why': 'no twin proof is written for variant %r (known: %s)' % (variant, ', '.join(sorted(CHECKS)))}
    if mode == 'hardware':
        return {'ok': False, 'route': 'refused', 'why': 'the %s hardware proof is not wired yet (the UNO is not attached)' % variant}
    ready, why = engine_ready()
    if not ready:
        return {'ok': False, 'route': 'refused', 'why': 'no simavr twin here: %s' % why}
    work = tempfile.mkdtemp(prefix='fgm5a-')
    try:
        row = build(variant, work)
        if row.get('state') != 'built':
            return {'ok': False, 'route': 'digital-twin', 'why': '%s did not build: %s' % (variant, row.get('notes'))}
        hex_bytes = open(row['hex_path'], 'rb').read()
        ok, parts, seen = True, [], 0
        for name in CHECKS[variant]:
            good, words, n = FNS[name](hex_bytes)
            ok, seen = ok and good, seen + n
            parts.append('%s: %s%s' % (name, words, '' if good else ' [FAILED]'))
        return {'ok': ok, 'route': 'digital-twin', 'why': '; '.join(parts), 'frames_compared': seen,
                'build': {'flash_bytes': row['flash_bytes'], 'ram_bytes': row['ram_bytes'], 'size_text': row['size_text'], 'size_data': row['size_data'],
                          'size_bss': row['size_bss'], 'hex_sha256': row['artifact_sha256']},
                'how': 'board.custom.variant_twin (firmwarefaults.custom.harness: --pin-at / --adc0-ramp / --inject / --watch, the Python wire reference decoder)'}
    finally:
        import shutil
        shutil.rmtree(work, ignore_errors=True)
