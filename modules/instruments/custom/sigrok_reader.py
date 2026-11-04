"""
@module instruments.custom.sigrok_reader

msv-3 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md section 3, D-msv-1 as the user refined it on 2026-11-04: "anything with sigrok"): A METER READ BY
sigrok. sigrok is libsigrok + sigrok-cli, GPLv3; its per-device drivers decode the meter's protocol, so Polari writes none
([use-established-solvers]). The reader runs wherever the meter is plugged in and sigrok-cli is installed. Where it is absent, it refuses by
name; it never guesses a device path.

  capability()                       {available, binary, version | why}
  driver_for(instrument)             the sigrok driver id of an Instrument model (SIGROK_DRIVERS, read off `sigrok-cli -L`), or refused
  parse_line(line)                   '-O analog' output 'P1: 14.20 mA DC AUTO' -> {channel, value (SI), unit (V | A | Ohm | ...), flags, raw}
  read(resource, samples, timeout)   one sigrok-cli run -> {samples: [...], raw, argv}; resource = '<driver>[:conn=<port>]' (an InstrumentEndpoint's)
  steady(samples, resolution, n)     the value once the last n samples sit within one resolution of each other (D-msv-6: the device's data decides)

A stream is never stored. Only the steady value is kept, as a MeasurementReading (via usb-serial), and the raw lines' sha256 is its evidence.
"""
import hashlib
import os
import re
import shutil
import subprocess

#: Instrument model -> sigrok driver id, exactly as `sigrok-cli -L` prints it (sigrok-cli 0.7.2, libsigrok 0.5.2, the Debian trixie package; read
#: 2026-11-04 in a throwaway container). The case matters: the TP4000ZC's id ends in a capital ZC.
SIGROK_DRIVERS = {
    'tekpower-tp4000zc': {'driver': 'tekpower-tp4000ZC', 'listed_as': 'TekPower TP4000ZC', 'conn': 'serial (its RS232 / USB cable)'},
    'sigrok-demo': {'driver': 'demo', 'listed_as': 'Demo driver and pattern generator', 'conn': 'none (sigrok\'s own generator: for testing the path)'},
}
STEADY_N = 3          # KNOB: samples in a row within one resolution count that make a reading steady
TAKE_SAMPLES = 12     # KNOB: the most samples one take reads before it gives up as "not steady"
TAKE_TIMEOUT_S = 15   # KNOB: no line from the meter within this = "no data came through" (the probe, the cable or the port - not the circuit)

_PREFIX = {'': 1.0, 'p': 1e-12, 'n': 1e-9, 'u': 1e-6, 'µ': 1e-6, 'm': 1e-3, 'k': 1e3, 'M': 1e6, 'G': 1e9}
_UNITS = {'V': 'V', 'A': 'A', 'Ω': 'Ohm', 'Ohm': 'Ohm', 'ohm': 'Ohm', 'Hz': 'Hz', 'F': 'F', '°C': 'C', '%': '%'}
_LINE = re.compile(r'^\s*(?P<ch>[^:\s]+):\s+(?P<num>[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|[-+]?inf|nan)\s*(?P<unit>[pnuµmkMG]?(?:V|A|Ω|Ohm|ohm|Hz|F|°C|%))?(?P<flags>.*)$')


class SigrokRefused(Exception):
    def __init__(self, why, status=409):
        Exception.__init__(self, why)
        self.why, self.status = why, status


def binary():
    return os.environ.get('SIGROK_CLI') or shutil.which('sigrok-cli') or ''


def capability():
    b = binary()
    if not b:
        return {'available': False, 'binary': '', 'why': 'sigrok-cli is not installed on this node (GPLv3; Debian/Ubuntu: apt install sigrok-cli) - or set SIGROK_CLI'}
    try:
        out = subprocess.run([b, '--version'], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError) as e:
        return {'available': False, 'binary': b, 'why': 'sigrok-cli did not run: %s' % e}
    return {'available': True, 'binary': b, 'version': (out.strip().splitlines() or [''])[0]}


def driver_for(instrument):
    d = SIGROK_DRIVERS.get(instrument)
    if d is None:
        raise SigrokRefused('%r has no sigrok driver listed (SIGROK_DRIVERS: %s) - check `sigrok-cli -L` and the sigrok supported-hardware list first'
                            % (instrument, ', '.join(sorted(SIGROK_DRIVERS))), status=422)
    return d['driver']


def parse_line(line):
    m = _LINE.match(line or '')
    if not m:
        return None
    unit = m.group('unit') or ''
    pre = ''
    if unit and unit[0] in _PREFIX and unit[1:] in _UNITS:
        pre, unit = unit[0], unit[1:]
    if unit and unit not in _UNITS:
        return None
    num = m.group('num')
    value = float(num) * _PREFIX[pre]
    return {'channel': m.group('ch'), 'value': value, 'unit': _UNITS.get(unit, ''), 'flags': m.group('flags').split(), 'raw': line.rstrip('\n'),
            'overload': num.lstrip('+-') in ('inf', 'nan')}


def argv_for(resource, samples):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+(?::[a-z_]+=[^\s;|&`$]+)*', resource or ''):
        raise SigrokRefused('the sigrok resource %r is not <driver>[:conn=<port>] (no spaces or shell characters)' % resource, status=422)
    return [binary(), '--driver', resource, '--samples', str(int(samples)), '-O', 'analog']


def read(resource, samples=TAKE_SAMPLES, timeout=TAKE_TIMEOUT_S):
    cap = capability()
    if not cap['available']:
        raise SigrokRefused(cap['why'], status=409)
    argv = argv_for(resource, samples)
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raw = (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or '')
        return {'samples': [s for s in map(parse_line, raw.splitlines()) if s], 'raw': raw, 'argv': argv, 'timed_out': True, 'stderr': ''}
    got = [s for s in map(parse_line, p.stdout.splitlines()) if s]
    return {'samples': got, 'raw': p.stdout, 'argv': argv, 'timed_out': False, 'stderr': p.stderr.strip()[-400:], 'returncode': p.returncode}


def steady(samples, resolution, n=STEADY_N):
    """-> (value, the lines it rests on) once the last n non-overload samples sit within one resolution of each other, else (None, why)."""
    ok = [s for s in samples if not s['overload']]
    if ok:   # one channel only: the meter's (a multi-channel driver interleaves its channels - the demo prints A0..A3)
        ok = [s for s in ok if s['channel'] == ok[-1]['channel']]
    if len(ok) < n:
        return None, '%d sample(s), %d needed in a row' % (len(ok), n)
    for end in range(len(ok), n - 1, -1):
        win = ok[end - n:end]
        vals = [s['value'] for s in win]
        if max(vals) - min(vals) <= max(resolution, 0.0) + 1e-15:
            return win[-1]['value'], win
    return None, 'not steady: no %d samples in a row within %g' % (n, resolution)


def evidence(raw):
    return hashlib.sha256((raw or '').encode()).hexdigest()
