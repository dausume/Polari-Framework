"""brd-1 PROBE — the UNO twin on the REAL simavr path (no UNO attached; the plan's brd-1 proof, run on the twin).

gen (pinned SimRigState v2 contract, target=avr) → build (avr-gcc through the engines ladder) → twin up (polari-avr-twin
in the prf-board-engines image, or a local binary) → the pty link read with the independent Python reference parser
(board.custom.packet_ref; the Java bridge reads the same link with source=serial) → a command frame
{led_on: true, pwm_duty: 42} written to the link → the firmware's echo + simavr's PORTB5 edge and OCR0A → twin down.
Skips HONESTLY (exit 0, every check listed as SKIP) when neither the image nor a local polari-avr-twin exists.

  PYTHONPATH=.:modules python3 tests/board_uno_twin_probe.py [--seconds 5] [--json out.json]     # from polari-framework/
"""
import json
import os
import select
import sys
import tempfile
import time
import tty

FRAMEWORK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, FRAMEWORK); sys.path.insert(0, os.path.join(FRAMEWORK, 'modules'))
os.chdir(FRAMEWORK)

from board.custom import board_engines as be, build, gen, packet_ref, twin  # noqa: E402

results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(('PASS' if cond else 'FAIL') + ': ' + label + (('  [%s]' % (extra,)) if extra else ''))


def read_frames(fd, parser, fmap, seconds, spec=None):
    """brd-wire: frames are wire v2 (prelude: index + presence) — decoded with the class's wire spec."""
    frames, t0 = [], time.time()
    while time.time() - t0 < seconds:
        r, _, _ = select.select([fd], [], [], 0.2)
        if fd in r:
            for mt, dev, seq, payload, ver in parser.feed(os.read(fd, 4096)):
                if mt == 1:
                    frames.append((time.time(), dev, seq, packet_ref.decode_any(fmap, payload, ver, spec)))
    return frames


def main(argv):
    seconds = float(argv[argv.index('--seconds') + 1]) if '--seconds' in argv else 5.0
    out_json = argv[argv.index('--json') + 1] if '--json' in argv else ''
    where = be.resolve('avr-twin')
    if where['how'] not in ('local-binary', be.LOCAL_IMAGE):
        print('SKIP: no simavr twin on this device (%s) — build the image: docker compose -f polari-rf-node/docker-compose.board-engines.yml build' % where['why'])
        return 0
    work = tempfile.mkdtemp(prefix='uno-twin-probe-')
    link = os.path.join(work, 'uart')
    fmap = gen.pinned_contract('SimRigState')[0]['field_map']
    from board.custom.compat import wire_spec
    spec = wire_spec(None, 'SimRigState', fmap)   # brd-wire: one unbound instance — width 0, the status enum
    row = gen.gen('uno', ['SimRigState'], work, rig_name='uno-twin')
    check('gen: the project holds only main.c (the uno-sim-rig app), hal.c/hal.h, Makefile, board_config.h, simrigstate_packets.h (RULE 2)',
          sorted(os.listdir(row['project_dir'])) == ['Makefile', 'board_config.h', 'hal.c', 'hal.h', 'main.c', 'simrigstate_packets.h'])
    row = build.build('uno', work)
    check('build: avr-gcc through the ladder (%s) → state built, sizes measured, under the cited limits' % json.loads(row['engines_json'])['avr-gcc']['how'],
          row['state'] == 'built' and row['size_text'] > 0 and row['flash_bytes'] <= 32256 and row['ram_bytes'] <= 2048,
          '.text %s .data %s .bss %s' % (row['size_text'], row['size_data'], row['size_bss']))
    report = {'build': {k: row[k] for k in ('name', 'size_text', 'size_data', 'size_bss', 'flash_bytes', 'ram_bytes', 'artifact_sha256')}}
    s = twin.up('uno', work, tcp=int(os.environ.get('UNO_TWIN_TCP', '9839')), link=link, adc0_mv=750)
    try:
        check('twin up: %s, the UART at a pty link' % s['how'], s['alive'] and os.path.islink(link), s.get('container') or s.get('pid'))
        fd = os.open(link, os.O_RDWR | os.O_NOCTTY)
        tty.setraw(fd)
        parser = packet_ref.StreamParser()
        frames = read_frames(fd, parser, fmap, seconds, spec)
        n = len(frames)
        span = frames[-1][0] - frames[0][0] if n > 1 else 0
        rate = (n - 1) / span if span else 0
        ups = [f[3]['uptime_ms'] for f in frames]
        steps = sorted(set(b - a for a, b in zip(ups, ups[1:])))
        last = frames[-1][3] if frames else {}
        check('telemetry: %d SimRigState frames in %.1f s of wall time = %.2f Hz (10 Hz expected), CRC-valid, %d bad CRC'
              % (n, span, rate, parser.bad_crc), n >= 5 * seconds and 9.0 <= rate <= 11.0 and parser.bad_crc == 0)
        check('uptime_ms advances 100 ms per frame (Timer2 1 ms tick)', steps and all(90 <= d <= 110 for d in steps), steps)
        check('temp_c from the TMP36 formula at the 750 mV stimulus: ADC 153 → 747.07 mV → 24.71 °C (binary32 on the wire as binary64)',
              abs(last.get('temp_c', 0) - 24.70703125) < 1e-3, last.get('temp_c'))
        check('identity + status: name uno-twin, device_id 3, status ok after 1 s', last.get('name') == 'uno-twin' and frames[-1][1] == 3 and last.get('status') == 'ok',
              (last.get('name'), frames[-1][1], last.get('status')))
        before = dict(last)
        from grpcbridge.custom import wire_ref
        cmd = packet_ref.frame(1, 0, 7, wire_ref.encode(spec, {'name': 'uno-twin', 'led_on': True, 'pwm_duty': 42, 'status': '', 'temp_c': 0.0, 'uptime_ms': 0}),
                               version=spec['wire_version'])
        os.write(fd, b'\x00\xffjunk' + cmd)   # garbage first: the firmware's parser must resync
        t_cmd = time.time()
        after = read_frames(fd, parser, fmap, 1.5, spec)
        echoed = [f for f in after if f[3]['status'] == 'commanded']
        e = echoed[0][3] if echoed else {}
        check('PUT echo: {led_on: true, pwm_duty: 42} → the next frames carry status=commanded, led_on=true, pwm_duty=42 (after leading garbage)',
              bool(echoed) and e['led_on'] is True and e['pwm_duty'] == 42, e)
        check('sensors + identity stay the firmware\'s own (command carried temp 0 / uptime 0)', bool(echoed) and e['uptime_ms'] > before['uptime_ms'] and e['temp_c'] > 20)
        time.sleep(1.2)   # one status line later
        log = [json.loads(l) for l in open(s['log']) if l.startswith('{')]
        pb5 = [x for x in log if x.get('t') == 'pb5' and x.get('v') == 1]
        st = [x for x in log if x.get('t') == 'status']
        check('simavr saw PORTB5 (D13) go high after the command', bool(pb5), pb5[:1])
        check('simavr saw OCR0A = 42 % of 255 = 107 (Timer0 fast PWM on D6)', bool(st) and st[-1]['ocr0a'] == 107, st[-1]['ocr0a'] if st else None)
        os.close(fd)
        report['twin'] = {'how': s['how'], 'frames': n, 'wall_s': round(span, 3), 'rate_hz': round(rate, 3), 'uptime_steps_ms': steps,
                          'last_frame': before, 'echo_frame': e, 'echo_latency_s': round(echoed[0][0] - t_cmd, 3) if echoed else None,
                          'pb5_high_event': pb5[:1], 'last_status': st[-1] if st else None, 'bad_crc': parser.bad_crc}
    finally:
        d = twin.down('uno', work)
    check('twin down: the twin and the pty pump stopped, the link removed', d['state'] == 'down' and not os.path.islink(link))
    if out_json:
        json.dump(report, open(out_json, 'w'), indent=1)
    print('\n%d/%d probe checks passed' % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
