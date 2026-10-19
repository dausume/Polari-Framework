"""
@module board.custom.press_latency

smp-1: HOW LONG THE LIGHT TAKES TO FOLLOW A PRESS, MEASURED ON THE TWIN. The sample failure F2 (uno-light-slow-loop) misses a deadline that a Purpose states (ensure-button-controls-light: the light follows a press
inside max_latency_ms). The number has to be a measurement, not an estimate, so this is the measurement, in the style of cyc-0 (board.custom.cycle_measure): the config is built through the shipped pipeline,
driven deterministically by firmwarefaults.custom.harness (cycle-scheduled, never real-time sleeps), and its own record is committed with the inputs by sha256.

HOW IT IS SAMPLED. One debounced press (a falling edge on the button's own pin, from board.custom.light_button) is made at a known cycle P. The twin prints a `pb5` event, stamped with the core's own cycle
counter, every time the on-board L LED (D13, PB5) changes. In the button-clock firmware led_follow_state - the ONLY pin writer (scl) - writes D6 and then D13 in the same call, a few cycles apart, so the first
`pb5` event to the high level after P is the cycle the light followed the press. The latency is that cycle minus P: exact to the cycle (the D13 write follows the D6 write by a handful of cycles, said
here, not hidden). A press can land anywhere in a main-loop pass, and a slow pass makes the latency depend on where, so the press is made at PHASES different times spaced STEP_MS apart (across one pass of the
slowest build we measure, 250 ms) and the WORST of them is the number reported; all of them are kept in the record.

    python3 -m board.custom.press_latency measure <variant> [--save]    build, measure, print (and write the committed record press_records/<variant>.json)
    python3 -m board.custom.press_latency show <variant>               the committed record
    python3 -m board.custom.press_latency verify <variant>             re-measure and compare with the record (the twin is deterministic: the runs repeat exactly)
"""
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile

SCHEMA = 'press-latency/1'
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'press_records')
CPS = 16000000
PHASES = 5
STEP_MS = 50
FIRST_PRESS_MS = 100        # past the init at the top of main()
TAIL_MS = 600               # long enough for a 250 ms pass to finish after the press
_CACHE = {}


class PressRefused(RuntimeError):
    pass


def path(variant):
    return os.path.join(DIR, variant + '.json')


def load(variant):
    if variant in _CACHE:
        return _CACHE[variant]
    try:
        rec = json.load(open(path(variant)))
    except (OSError, ValueError):
        rec = None
    _CACHE[variant] = rec
    return rec


def seal(rec):
    body = {k: v for k, v in rec.items() if k not in ('record_sha256', 'recorded_at')}
    rec['record_sha256'] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return rec


def save(rec):
    os.makedirs(DIR, exist_ok=True)
    with open(path(rec['variant']), 'w') as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write('\n')
    _CACHE.pop(rec['variant'], None)
    return path(rec['variant'])


def latency_of(stdout, press_cycle):
    """(latency_ms, led_cycle) from the twin's `pb5` events: the first change of the L LED (D13) to high at or after `press_cycle`; (None, None) when the light never came on."""
    for line in (stdout or '').splitlines():
        if not line.startswith('{"t":"pb5"'):
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get('v') == 1 and e.get('cycle', 0) >= press_cycle:
            return (e['cycle'] - press_cycle) * 1000.0 / CPS, e['cycle']
    return None, None


def run_once(variant, hex_bytes, press_ms):
    """One press at `press_ms` -> {press_cycle, led_cycle, latency_ms}."""
    from board.custom import light_button as LB
    from board.custom import variant_twin as VT
    from firmwarefaults.custom import harness
    press_cycle = int(press_ms * CPS / 1000)
    pl = LB.plan(variant)
    if pl['route'] == 'adc':
        raise PressRefused('%s reads its button as a voltage: this measurement drives a pin edge' % variant)
    pinat, _end = LB.press_pinat(pl, 1, press_cycle, VT.PRESS_HOLD_CYCLES, VT.PRESS_GAP_CYCLES)
    argv = VT._argv((press_ms + TAIL_MS) / 1000.0, pinat)
    r = harness.run(argv, hex_bytes, timeout=120)
    if not r['ok']:
        raise PressRefused('the twin run failed: %s' % ((r.get('stderr') or r.get('stdout') or '')[-300:]))
    ms, led_cycle = latency_of(r['stdout'], press_cycle)
    return {'press_ms': press_ms, 'press_cycle': press_cycle, 'led_cycle': led_cycle, 'latency_ms': None if ms is None else round(ms, 3)}


def measure(variant, work=None):
    """Build `variant` and measure it -> the sealed record (not saved)."""
    from board.custom import board_engines as be
    from board.custom import build as B
    from board.custom import engine_run, gen
    from board.custom import light_twin as LT
    ready, why = LT.engine_ready()
    if not ready:
        raise PressRefused('no simavr twin here: %s' % why)
    own = work is None
    work = work or tempfile.mkdtemp(prefix='smp-press-')
    try:
        gen.gen('uno', None, work, variant=variant)
        row = B.build('uno', work)
        if row.get('state') != 'built':
            raise PressRefused('%s did not build: %s' % (variant, row.get('notes')))
        hex_bytes = open(row['hex_path'], 'rb').read()
        runs = [run_once(variant, hex_bytes, FIRST_PRESS_MS + i * STEP_MS) for i in range(PHASES)]
        vals = [r['latency_ms'] for r in runs]
        if any(v is None for v in vals):
            raise PressRefused('the light never followed a press in a run of %s: %s' % (variant, runs))
        rec = {'schema': SCHEMA, 'variant': variant, 'mcu': 'atmega328p', 'clock_hz': CPS,
               'what': 'press-to-light latency: one debounced press on the config\'s own button pin, then the cycle of the first L LED (D13) change to high, which led_follow_state writes right after D6',
               'stimulus': {'phases': PHASES, 'first_press_ms': FIRST_PRESS_MS, 'step_ms': STEP_MS, 'tail_ms': TAIL_MS},
               'runs': runs, 'worst_ms': max(vals), 'best_ms': min(vals), 'resolution': 'one core cycle (D13 is written a few cycles after D6)',
               'inputs': {'hex_sha256': row['artifact_sha256'], 'source_sha': row['source_sha']},
               'tools': {'image': {'name': be.image_name(), 'id': be.local_image()}, 'avr-gcc': engine_run.version('avr-gcc')},
               'rule': 'the number is the WORST of the %d presses; a press at another time in the pass can give a smaller or (up to one pass) a larger value, so it is a measured value, not a bound' % PHASES,
               'recorded_at': datetime.datetime.now().isoformat(timespec='seconds')}
        return seal(rec)
    finally:
        if own:
            shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) < 2 or a[0] not in ('measure', 'show', 'verify'):
        print(__doc__)
        return 2
    verb, variant = a[0], a[1]
    if verb == 'show':
        rec = load(variant)
        print(json.dumps(rec, indent=1, sort_keys=True) if rec else 'no committed record for %s' % variant)
        return 0 if rec else 1
    rec = measure(variant)
    print('%s: worst press-to-light latency %.1f ms over %d presses %s (best %.1f ms); record %s' % (
        variant, rec['worst_ms'], PHASES, [r['latency_ms'] for r in rec['runs']], rec['best_ms'], rec['record_sha256'][:12]))
    if verb == 'measure' and '--save' in a:
        print('saved', save(rec))
    if verb == 'verify':
        old = load(variant)
        same = bool(old) and old['record_sha256'] == rec['record_sha256']
        print('matches the committed record' if same else 'DIFFERS from the committed record (%s)' % (old['record_sha256'][:12] if old else 'none'))
        return 0 if same else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
