"""
smp-1 selftest part (called by board.board_light_selftest.run_light): THE SAMPLE CONFIGS ON THE SIMAVR TWIN - what each one shows beyond the four Purposes the per-config proofs already cover.

  - board.custom.light_button reads each config's OWN button (INT0 on D2, a pin-change pin, a voltage on A0) from its knobs and the jumper from its own sense pin
  - the SENSE LINE: the report's led_on is the SENSED level. With the jumper D6 -> sense pin the report follows the light; with NO jumper the board still drives D6 (commanded) but reports led_on false
  - S3 (uno-light-pwm-analog): the LED pin is Timer0's PWM output - OCR0A 255 with the output connected while the struct says on, disconnected and low while off; the sense line sees ONE rise and ONE fall
    (the same run on S1 shows the output never connected); the twin's phase-correct choice is why (fast PWM at the top value drops the pin in simavr)
  - S4 (uno-light-transistor): the SAME C as S1 - only the rig name differs - so the twin cannot show the transistor, said
  - F2 (uno-light-slow-loop): the press-to-light time re-measured on the twin repeats the committed record, is over the deadline, and the fast build is far under it
SKIPS honestly with no twin.
"""
import glob
import os
import shutil
import tempfile


def _hex(variant, work):
    from board.custom import build as B
    from board.custom import gen
    gen.gen('uno', None, work, variant=variant)
    row = B.build('uno', work)
    return open(row['hex_path'], 'rb').read() if row.get('state') == 'built' else None


def _watches(res):
    return {w['name']: w['final'] for w in ((res.get('final') or {}).get('watches') or [])}


def _run(variant, hex_bytes, on_only, wired=True):
    """SET_LED 1 (and, unless on_only, SET_LED 0) injected -> (run, watches at the end, last LightState frame, bad crc, wire-edge events)."""
    import json
    from board.custom import light_button as LB
    from board.custom import light_twin as LT
    from firmwarefaults.custom import harness
    spec = LT._spec()[1]
    files = {'on.bin': LT.cmd_frame(spec, 1, led_on=True), 'off.bin': LT.cmd_frame(spec, 2, led_on=False)}
    inj = ['--inject', 'on.bin@%d' % LT.CMD_ON_CYCLE] + ([] if on_only else ['--inject', 'off.bin@%d' % LT.CMD_OFF_CYCLE])
    end = (5000000 if on_only else LT.CMD_OFF_CYCLE + 4 * LT.RUN_TAIL) / 16000000.0
    watch = ['--watch', '0x2b/1=PORTD', '--watch', '0x44/1=TCCR0A', '--watch', '0x47/1=OCR0A']
    r = harness.run_files(LT._argv(end, (LB.wire_args(variant) if wired else []) + inj + watch, LB.default_adc(variant)), hex_bytes, files, timeout=120)
    frames, bad = LT.decode(r['uart'])
    edges = []
    for line in r['stdout'].splitlines():
        if line.startswith('{"t":"wire-edge"'):
            try:
                edges.append(json.loads(line))
            except ValueError:
                pass
    return r, _watches(r), (frames[-1] if frames else {}), bad, edges


def run_samples(check):
    from board.custom import light_button as LB
    from board.custom import light_twin as LT
    from board.custom import variants as V
    pl = {n: LB.plan(n) for n in ('uno-light', 'uno-light-all-pcint', 'uno-light-pwm-analog', 'uno-light-transistor', 'uno-light-pcint', 'uno-light-analog')}
    check('smp-1 BUTTON: each config\'s OWN button is read from its knobs - INT0 on D2 (uno-light, S4), a pin-change pin D4 = PD4 (S2, uno-light-pcint), a voltage on A0 with the config\'s own thresholds (S3, uno-light-analog) - and the wrong-pin control is a pin that is not the button',
          [(pl[n]['route'], pl[n]['pin'], pl[n]['wrong_pin']) for n in ('uno-light', 'uno-light-transistor', 'uno-light-all-pcint', 'uno-light-pcint')] == [('int0', 'PD2', 'PD4')] * 2 + [('pcint', 'PD4', 'PD2')] * 2
          and pl['uno-light-pwm-analog']['route'] == pl['uno-light-analog']['route'] == 'adc' and pl['uno-light-pwm-analog']['press_below_mv'] == 1500 and pl['uno-light-pwm-analog']['release_above_mv'] == 3500
          and LB.ramp_presses(pl['uno-light-pwm-analog']) == 3, pl)
    check('smp-1 JUMPER: the sense jumper is read from each config\'s own sense pin - D6 to D3 (S1, S3, S4, F2: PD3), D6 to D8 (S2: PB0) - and a config with no sense line has none',
          [LB.wire_args(n) for n in ('uno-light', 'uno-light-pwm-analog', 'uno-light-transistor', 'uno-light-all-pcint', 'uno-light-unsensed', 'uno-light-pcint')]
          == [['--wire', 'PD6:PD3']] * 3 + [['--wire', 'PD6:PB0'], [], []], [LB.wire_args(n) for n in ('uno-light', 'uno-light-all-pcint', 'uno-light-unsensed')])
    c1 = [l for l in V.render_config(V.resolve(V.find('uno-light-transistor'))).splitlines() if 'RIG_NAME' not in l and 'board_config.h' not in l]
    c2 = [l for l in V.render_config(V.resolve(V.find('uno-light'))).splitlines() if 'RIG_NAME' not in l and 'board_config.h' not in l]
    check('smp-1 S4 SAME C: the transistor config\'s board_config.h equals S1\'s (uno-light) except the rig name - the pin driver is the plain output; the transistor is wiring', c1 == c2, set(c1) ^ set(c2))
    ready, why = LT.engine_ready()
    if not ready:
        check('SKIP smp-1 (the sample configs on the twin): no simavr twin here - %s' % why, True)
        return
    before = set(glob.glob(os.path.join(tempfile.gettempdir(), 'smp-*')))
    work = tempfile.mkdtemp(prefix='smp-st-')
    try:
        h3, h1 = _hex('uno-light-pwm-analog', work), _hex('uno-light', work)
        r_on, w_on, f_on, bad_on, e_on = _run('uno-light-pwm-analog', h3, True)
        r_off, w_off, f_off, bad_off, e_off = _run('uno-light-pwm-analog', h3, False)
        r_s1, w_s1, f_s1, _b, _e = _run('uno-light', h1, True)
        r_nw, w_nw, f_nw, bad_nw, _e = _run('uno-light', h1, True, wired=False)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    check('smp-1 SENSED: with the jumper the REPORT\'s led_on follows the light pin (S1: SET_LED 1 -> led_on %s, D6 %s); with NO jumper the board still drives D6 (%s) but reports led_on %s - it reports what it senses, not what it was told, and the wire contract is unchanged'
          % (f_s1.get('led_on'), 'high' if w_s1.get('PORTD', 0) & 64 else 'low', 'high' if w_nw.get('PORTD', 0) & 64 else 'low', f_nw.get('led_on')),
          r_s1['ok'] and bool(f_s1.get('led_on')) and bool(w_s1.get('PORTD', 0) & 64) and r_nw['ok'] and bad_nw == 0 and bool(w_nw.get('PORTD', 0) & 64) and not f_nw.get('led_on') and f_nw.get('toggles') == 1
          and f_nw.get('source') == 'command', (f_s1, f_nw))
    com = 0x80      # COM0A1
    check('smp-1 S3 PWM (twin): while the struct says ON the LED pin is Timer0\'s output - OCR0A %s, COM0A1 %s, D6 %s - and the board reports (senses) led_on %s' % (w_on.get('OCR0A'), 'set' if w_on.get('TCCR0A', 0) & com else 'clear', 'high' if w_on.get('PORTD', 0) & 64 else 'low', f_on.get('led_on')),
          r_on['ok'] and bad_on == 0 and w_on.get('OCR0A') == 255 and bool(w_on.get('TCCR0A', 0) & com) and bool(w_on.get('PORTD', 0) & 64) and bool(f_on.get('led_on')), w_on)
    levels = [e['v'] for e in e_off]
    check('smp-1 S3 PWM (twin): after the struct says OFF the output is disconnected (COM0A1 clear) and D6 is low, and the sense jumper saw exactly ONE rise and ONE fall for the two changes (edges %s)' % levels,
          r_off['ok'] and bad_off == 0 and not (w_off.get('TCCR0A', 0) & com) and not (w_off.get('PORTD', 0) & 64) and not f_off.get('led_on') and levels[-2:] == [1, 0] and levels.count(1) == 1, (w_off, levels))
    check('smp-1 S3 PWM (control): the SAME run on S1 (a plain output pin) never connects the timer output (COM0A1 clear, OCR0A %s) while D6 is %s - the watch tells the two routes apart' % (w_s1.get('OCR0A'), 'high' if w_s1.get('PORTD', 0) & 64 else 'low'),
          not (w_s1.get('TCCR0A', 0) & com) and bool(w_s1.get('PORTD', 0) & 64) and bool(f_s1.get('led_on')), w_s1)
    from board.custom import press_latency as PL
    rec = PL.load('uno-light-slow-loop')
    fast = PL.load('uno-light')
    check('smp-1 F2 (record): the committed press-to-light record of the slow loop is over the Purpose\'s 100 ms (%s ms), the fast build\'s (S1, uno-light) is far under (%s ms)' % (rec and rec['worst_ms'], fast and fast['worst_ms']),
          bool(rec) and bool(fast) and rec['worst_ms'] > 100 and fast['worst_ms'] < 5)
    if rec:
        again = PL.measure('uno-light-slow-loop')
        check('smp-1 F2 (twin): measuring the slow loop AGAIN repeats the committed record - every press time within 1 ms (the twin is deterministic): %s vs %s' % ([r['latency_ms'] for r in again['runs']], [r['latency_ms'] for r in rec['runs']]),
              all(abs(a['latency_ms'] - b['latency_ms']) < 1.0 for a, b in zip(again['runs'], rec['runs'])) and again['worst_ms'] > 100)
    after = set(glob.glob(os.path.join(tempfile.gettempdir(), 'smp-*')))
    check('smp-1 TWIN: the sample runners leave no temp directory behind', after <= before, sorted(after - before))
