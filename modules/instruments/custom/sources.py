"""
@module instruments.custom.sources

osc-2: the SIGNAL SOURCES an emulated channel is fed from — pure functions of a spec and a time axis (seconds, relative to the trigger), so
an emulated capture is reproducible from its stored spec (`WaveformCapture.source_ref`).

  spec kinds (every field a number, every default named here, nothing hidden):
    sine    {kind, freq_hz, amp_v, offset_v, phase_deg}
    square  {kind, freq_hz, amp_v, offset_v, duty, phase_deg}                      duty 0..1 (default 0.5)
    ramp    {kind, freq_hz, amp_v, offset_v}                                        a rising sawtooth over one period
    triangle {kind, lo_v, hi_v, period_s}                                           lo -> hi -> lo over one period (the AVR twin's --adc0-ramp)
    dc      {kind, offset_v}
    noise   {kind, rms_v, offset_v, seed}                                           deterministic per (seed, acquisition number)
    pulses  {kind, edges: [[t_s, level_v], ...], initial_v}                         a step trace: level after each edge (osc-4's device feed)
    replay  {kind, t_s: [...], v: [...]}                                            interpolated onto the emulator's axis (a stored capture)
    digital {kind, bits: [0/1, ...], bit_period_s, hi_v, lo_v}                      osc-6: a logic-level pattern (a UART frame, a clock) at two levels, repeating
  default_source(channel) -> a 1 kHz sine of 1 V amplitude on channel 1, square on 2, ramp on 3, dc 0.5 V on 4 (so four channels differ on sight)
  validate(spec) -> the spec with defaults filled (raises ValueError naming the field)
  evaluate(spec, t, acquisition_no) -> volts (numpy array, same length as t)
  describe(spec) -> plain words for the capture's source_ref
"""
import json

import numpy as np

_DEFAULTS = {
    'sine': {'freq_hz': 1000.0, 'amp_v': 1.0, 'offset_v': 0.0, 'phase_deg': 0.0},
    'square': {'freq_hz': 1000.0, 'amp_v': 1.0, 'offset_v': 0.0, 'duty': 0.5, 'phase_deg': 0.0},
    'ramp': {'freq_hz': 1000.0, 'amp_v': 1.0, 'offset_v': 0.0},
    'triangle': {'lo_v': 0.0, 'hi_v': 1.0, 'period_s': 1.0},           # the AVR twin's --adc0-ramp lo,hi,period_ms (a triangle, polari_avr_twin.c)
    'dc': {'offset_v': 0.0},
    'noise': {'rms_v': 0.1, 'offset_v': 0.0, 'seed': 1},
    'pulses': {'edges': [], 'initial_v': 0.0},
    'replay': {'t_s': [], 'v': []},
    'digital': {'bits': [], 'bit_period_s': 1e-3, 'hi_v': 3.3, 'lo_v': 0.0},   # a digital SIGNAL is still volts on the wire: two levels, a bit time
}


def default_source(channel):
    return [{'kind': 'sine', 'freq_hz': 1000.0, 'amp_v': 1.0},
            {'kind': 'square', 'freq_hz': 1000.0, 'amp_v': 1.0, 'duty': 0.5},
            {'kind': 'ramp', 'freq_hz': 1000.0, 'amp_v': 1.0},
            {'kind': 'dc', 'offset_v': 0.5}][(int(channel) - 1) % 4] | {}


def validate(spec):
    if not isinstance(spec, dict) or spec.get('kind') not in _DEFAULTS:
        raise ValueError('a source spec is {kind: %s, ...}' % ' | '.join(_DEFAULTS))
    out = dict(_DEFAULTS[spec['kind']])
    for k, v in spec.items():
        if k == 'kind':
            continue
        if k not in out:
            raise ValueError('source %s has no field %r (fields: %s)' % (spec['kind'], k, ', '.join(out)))
        if k in ('edges', 't_s', 'v'):
            out[k] = [list(map(float, e)) for e in v] if k == 'edges' else [float(x) for x in v]
        elif k == 'bits':
            out[k] = [1 if int(x) else 0 for x in v]
        else:
            out[k] = float(v)
    if spec['kind'] == 'square' and not 0 < out['duty'] < 1:
        raise ValueError('duty must be between 0 and 1')
    if spec['kind'] == 'replay' and len(out['t_s']) != len(out['v']):
        raise ValueError('replay t_s and v must be the same length')
    if spec['kind'] == 'digital' and (not out['bits'] or out['bit_period_s'] <= 0):
        raise ValueError('digital needs at least one bit and a positive bit_period_s')
    out['kind'] = spec['kind']
    return out


def evaluate(spec, t, acquisition_no=1):
    s = validate(spec)
    t = np.asarray(t, dtype=np.float64)
    k = s['kind']
    if k == 'sine':
        return s['offset_v'] + s['amp_v'] * np.sin(2 * np.pi * s['freq_hz'] * t + np.deg2rad(s['phase_deg']))
    if k == 'square':
        phase = (s['freq_hz'] * t + s['phase_deg'] / 360.0) % 1.0
        return s['offset_v'] + np.where(phase < s['duty'], s['amp_v'], -s['amp_v'])
    if k == 'ramp':
        phase = (s['freq_hz'] * t) % 1.0
        return s['offset_v'] + s['amp_v'] * (2 * phase - 1)
    if k == 'triangle':
        phase = (t / s['period_s']) % 1.0
        return s['lo_v'] + (s['hi_v'] - s['lo_v']) * (1.0 - np.abs(2 * phase - 1.0))
    if k == 'dc':
        return np.full_like(t, s['offset_v'])
    if k == 'noise':
        rng = np.random.default_rng(int(s['seed']) * 1000003 + int(acquisition_no))
        return s['offset_v'] + rng.normal(0.0, s['rms_v'], size=t.shape)
    if k == 'pulses':
        v = np.full_like(t, s['initial_v'])
        for at, level in sorted(s['edges']):
            v[t >= at] = level
        return v
    if k == 'replay':
        if not s['t_s']:
            return np.zeros_like(t)
        return np.interp(t, np.asarray(s['t_s']), np.asarray(s['v']), left=s['v'][0], right=s['v'][-1])
    if k == 'digital':
        idx = (np.floor(t / s['bit_period_s']).astype(np.int64)) % len(s['bits'])
        return np.where(np.asarray(s['bits'])[idx] == 1, s['hi_v'], s['lo_v'])
    raise ValueError(k)


def describe(spec):
    s = validate(spec)
    k = s['kind']
    if k in ('sine', 'square', 'ramp'):
        return '%s %g Hz, %g V amplitude, %g V offset%s' % (k, s['freq_hz'], s['amp_v'], s['offset_v'], (', duty %g' % s['duty']) if k == 'square' else '')
    if k == 'triangle':
        return 'triangle %g..%g V over %g s' % (s['lo_v'], s['hi_v'], s['period_s'])
    if k == 'dc':
        return 'dc %g V' % s['offset_v']
    if k == 'noise':
        return 'noise %g V rms, seed %d' % (s['rms_v'], int(s['seed']))
    if k == 'pulses':
        return 'pulses: %d edges from %g V' % (len(s['edges']), s['initial_v'])
    if k == 'digital':
        return 'digital: %d bits at %g s each, %g / %g V' % (len(s['bits']), s['bit_period_s'], s['hi_v'], s['lo_v'])
    return 'replay of %d points' % len(s['t_s'])


def to_json(spec):
    return json.dumps(validate(spec), sort_keys=True)
