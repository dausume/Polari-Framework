"""
@module board.custom.light_twin

THE LIGHT TEST ON THE SIMAVR TWIN (slice ucd-light): builds the variant uno-light through the shipped pipeline (gen + build)
and drives it deterministically through firmwarefaults.custom.harness (cycle-scheduled, never real-time sleeps), decoding every
frame with the independent Python reference codec (board.custom.packet_ref / grpcbridge.custom.wire_ref):

  presses    N debounced presses on D2 (--pin-at) -> each flips led_on, toggles == presses, source == button
  commands   SET_LED 1 then SET_LED 0 injected over the serial link -> led_on follows, toggles counts both, source == command

`prove()` returns the {'ok', 'route', 'why', 'frames_compared'} shape cmod.custom.firmware.run() returns, so the acceptance
runner (firmwarefaults.custom.acceptance) can turn it into a ScenarioRun the same way it does for the other Purposes.
Refuses honestly (route 'refused') when no avr twin engine is reachable on this device.
"""
import shutil
import tempfile

VARIANT = 'uno-light'
N_PRESSES = 3
PRESS_GAP_CYCLES = 2400000     # 150 ms @ 16 MHz: >= 3 x the 30 ms debounce
PRESS_HOLD_CYCLES = 80000
START_CYCLE = 1600000          # 100 ms in, past the init at the top of main()
CMD_ON_CYCLE = 1600000
CMD_OFF_CYCLE = 8000000
RUN_TAIL = 1600000


def _spec():
    from board.custom import gen
    from board.custom.compat import wire_spec
    fmap = gen.pinned_contract('LightState')[0]['field_map']
    return fmap, wire_spec(None, 'LightState', fmap)


def cmd_frame(spec, seq, **vals):
    """A command frame PRESENCE-MASKED to exactly the fields given (SET_LED = led_on only)."""
    from board.custom import packet_ref
    from grpcbridge.custom import wire_ref
    payload = wire_ref.encode(spec, vals, present=list(vals))
    return packet_ref.frame(1, 0, seq, payload, version=spec['wire_version'])


def decode(uart):
    from board.custom import packet_ref
    fmap, spec = _spec()
    p = packet_ref.StreamParser()
    out = [packet_ref.decode_any(fmap, payload, ver, spec) for mt, dev, seq, payload, ver in p.feed(bytes(uart)) if mt == 1]
    return out, p.bad_crc


def press_pinat(n=N_PRESSES):
    out, c = [], START_CYCLE
    for _ in range(n):
        out += ['--pin-at', 'cycle=%d,pin=PD2,level=0' % c, '--pin-at', 'cycle=%d,pin=PD2,level=1' % (c + PRESS_HOLD_CYCLES)]
        c += PRESS_GAP_CYCLES
    return out, c


def _argv(seconds, extra):
    return ['--hex', 'firmware.hex', '--mcu', 'atmega328p', '--freq', '16000000', '--free', '--seconds', '%g' % seconds,
            '--status-ms', '0', '--uart-out', 'uart.bin'] + extra


def build(work, variant=VARIANT):
    from board.custom import gen, build as B
    gen.gen('uno', None, work, variant=variant)
    return B.build('uno', work)


def run_presses(hex_bytes, n=N_PRESSES):
    from firmwarefaults.custom import harness
    pinat, end = press_pinat(n)
    r = harness.run(_argv((end + RUN_TAIL) / 16000000.0, pinat), hex_bytes, timeout=120)
    frames, bad = decode(r['uart'])
    return r, frames, bad


def run_commands(hex_bytes):
    from firmwarefaults.custom import harness
    _, spec = _spec()
    files = {'on.bin': cmd_frame(spec, 1, led_on=True), 'off.bin': cmd_frame(spec, 2, led_on=False)}
    argv = _argv((CMD_OFF_CYCLE + 4 * RUN_TAIL) / 16000000.0, ['--inject', 'on.bin@%d' % CMD_ON_CYCLE, '--inject', 'off.bin@%d' % CMD_OFF_CYCLE])
    r = harness.run_files(argv, hex_bytes, files, timeout=120)
    frames, bad = decode(r['uart'])
    return r, frames, bad


def judge_presses(frames, n=N_PRESSES):
    """(ok, why): led_on flips with every press, toggles == presses, source == button, in the frames seen."""
    seen = [(f.get('toggles'), f.get('led_on')) for f in frames]
    last = frames[-1] if frames else {}
    flips = sorted({t: l for t, l in seen if t}.items())
    ok = (bool(frames) and last.get('toggles') == n and last.get('source') == 'button' and bool(last.get('led_on')) == bool(n % 2)
          and all(bool(l) == bool(t % 2) for t, l in flips))
    return ok, ('%d press(es): last frame toggles=%s led_on=%s source=%s; every state seen had led_on == (toggles odd): %s'
                % (n, last.get('toggles'), last.get('led_on'), last.get('source'), all(bool(l) == bool(t % 2) for t, l in flips)))


def judge_commands(frames):
    """(ok, why): after SET_LED 1 the frames say led_on with source=command; after SET_LED 0, off; toggles == 2."""
    mid = [f for f in frames if f.get('toggles') == 1]
    last = frames[-1] if frames else {}
    ok = (bool(mid) and all(f.get('led_on') and f.get('source') == 'command' for f in mid)
          and last.get('toggles') == 2 and not last.get('led_on') and last.get('source') == 'command')
    return ok, ('SET_LED 1 -> %d frame(s) with toggles=1 led_on=%s source=%s; SET_LED 0 -> last frame toggles=%s led_on=%s source=%s'
                % (len(mid), mid[-1].get('led_on') if mid else None, mid[-1].get('source') if mid else None,
                   last.get('toggles'), last.get('led_on'), last.get('source')))


def engine_ready():
    from board.custom import board_engines as be
    where = be.resolve('avr-twin')
    return where['how'] in ('local-binary', be.LOCAL_IMAGE), where['why']


def prove(which='both', mode='digital-twin', variant=VARIANT):
    if mode == 'hardware':
        return {'ok': False, 'route': 'refused', 'why': 'the light test --hardware is not wired yet (the UNO is not attached)'}
    ready, why = engine_ready()
    if not ready:
        return {'ok': False, 'route': 'refused', 'why': 'no simavr twin here: %s' % why}
    work = tempfile.mkdtemp(prefix='ucd-light-')
    try:
        return _prove_in(work, which, variant)
    finally:
        shutil.rmtree(work, ignore_errors=True)   # fsc-0b: the temp dir used to leak on every run (pol-core's disk is tight)


def _prove_in(work, which, variant=VARIANT):
    row = build(work, variant)
    if row.get('state') != 'built':
        return {'ok': False, 'route': 'digital-twin', 'why': '%s did not build: %s' % (variant, row.get('notes'))}
    hex_bytes = open(row['hex_path'], 'rb').read()
    ok, parts, seen = True, [], 0
    if which in ('both', 'button'):
        r, fr, bad = run_presses(hex_bytes)
        o, w = judge_presses(fr)
        ok, seen = ok and o and r['ok'] and bad == 0, seen + len(fr)
        parts.append('button: ' + w)
    if which in ('both', 'polari'):
        r, fr, bad = run_commands(hex_bytes)
        o, w = judge_commands(fr)
        ok, seen = ok and o and r['ok'] and bad == 0, seen + len(fr)
        parts.append('polari: ' + w)
    return {'ok': ok, 'route': 'digital-twin', 'why': '; '.join(parts), 'frames_compared': seen,
            'how': 'board.custom.light_twin (firmwarefaults.custom.harness, --pin-at / --inject, the Python wire reference decoder)'}
