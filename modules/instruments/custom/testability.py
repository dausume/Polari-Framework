"""
@module instruments.custom.testability

osc-6 (OSCILLOSCOPE_PLAN.md §2b): TESTABILITY - can the instruments on a bench measure what a test needs, adapting to each instrument's kind and
capabilities, and does putting several cheap ones side by side stand in for one expensive one? His question 2026-10-27: "Perhaps using multiple in
parallel to feed polari and deriving data that way instead of buying more expensive ones? Not sure if that would work." The honest answer, as rules:

  ADDS UP across units        channels (analog, digital) - with ONE caveat: the units must share a trigger (one unit's trigger-out, or the signal itself,
                              into every unit) and their captures are aligned only to +/- one sample of the SLOWEST unit plus the trigger jitter (-1 until
                              measured on the bench); memory depth per channel is each unit's own.
  NEVER adds up               bandwidth (the analog front end of each unit bounds every signal it sees: N slow scopes never see a fast edge); vertical
                              resolution (bits are the ADC's); sample rate per channel ACROSS units (interleaving two scopes needs their sample clocks
                              phase-aligned to a fraction of a sample - independent units are not: NOT claimed).
  HELPS, with conditions      noise: N units on the SAME signal (or N captures) average uncorrelated noise down by sqrt(N) - not bandwidth, not accuracy;
                              repetitive signals: a unit that states equivalent-time sampling (ETS) reaches its ETS rate on its own - for REPETITIVE signals only.
  DIGITAL on an ANALOG channel: a spare analog channel reads a digital signal (and shows its edges); a logic input never reads an analog one.
  DIFFERENTIAL                one native differential input, else TWO analog channels + A - B (common mode costs range; skew costs timing).

needs = {analog: n, digital: n, differential: n, bandwidth_hz, sample_rate_sps, bits, repetitive: bool, same_instant: bool}  (every field optional; -1 / 0 = not needed)
units = the bench's instruments (model rows x count).  coverage(needs, units) -> {rows[] (one per need, verdict ok | caveat | no, with why), verdict, cost, options[]}
Every number comes from the Instrument rows (cited there) or is -1; the rules above are stated in each row's `why`.
"""
import json

from instruments.custom import catalog as C

_NEED_KEYS = ('analog', 'digital', 'differential', 'bandwidth_hz', 'sample_rate_sps', 'bits')


def parse_needs(body):
    """A tolerant reader of the door's body / query (strings allowed; blanks = not needed)."""
    out = {}
    for k in _NEED_KEYS:
        v = (body or {}).get(k, -1)
        try:
            out[k] = float(v) if k in ('bandwidth_hz', 'sample_rate_sps') else int(float(v))
        except (TypeError, ValueError):
            out[k] = -1
        if v in (None, ''):
            out[k] = -1
    out['repetitive'] = str((body or {}).get('repetitive', '')).lower() in ('1', 'true', 'yes', 'on')
    out['same_instant'] = str((body or {}).get('same_instant', 'true')).lower() not in ('0', 'false', 'no', 'off')
    return out


def _num(m, key):
    try:
        v = float(m.get(key, -1))
    except (TypeError, ValueError):
        return -1.0
    return v


def units_on_bench(bench, manager=None):
    """[{model, title, count, analog, digital, differential, bandwidth_hz, sample_rate_by_channels, ets, bits, price, ...}] from the bench's instruments_json."""
    by = {m['name']: m for m in C.models(manager)}
    out = []
    for e in C._j((bench or {}).get('instruments_json'), []):
        m = by.get(e.get('model', ''))
        if m is None:
            continue
        out.append({'model': m['name'], 'title': '%s %s' % (m.get('vendor', ''), m.get('model', '')), 'count': int(e.get('count') or 1),
                    'analog': int(m.get('channels', -1) or -1), 'digital': int(m.get('digital_channels', -1) or -1), 'differential': int(m.get('differential_inputs', -1) or -1),
                    'bandwidth_hz': _num(m, 'bandwidth_hz'), 'srate': {int(k): float(v) for k, v in C._j(m.get('sample_rate_by_channels_json'), {}).items()},
                    'srate_1ch': _num(m, 'sample_rate_sps'), 'ets': _num(m, 'ets_sample_rate_sps'), 'bits': int(m.get('resolution_bits', -1) or -1),
                    'price': _num(m, 'price_usd'), 'data_access': m.get('data_access', 'unverified'), 'openness': m.get('openness', 'unverified')})
    return out


def _n(x):
    return x if x >= 0 else 0


def _row(need, value, offered, verdict, why):
    return {'need': need, 'value': value, 'offered': offered, 'verdict': verdict, 'why': why}


def _srate_at(u, channels):
    """The unit's sample rate with `channels` of its analog channels on (its own per-channel-count table; the headline when the table is empty)."""
    if not u['srate']:
        return u['srate_1ch']
    keys = sorted(k for k in u['srate'] if k >= max(1, channels))
    return u['srate'][keys[0]] if keys else -1.0


def coverage(needs, units):
    rows = []
    n_units = sum(u['count'] for u in units)
    analog_total = sum(_n(u['analog']) * u['count'] for u in units)
    digital_total = sum(_n(u['digital']) * u['count'] for u in units)
    diff_native = sum(_n(u['differential']) * u['count'] for u in units)
    biggest = max((_n(u['analog']) for u in units), default=0)
    shared = ('%d units: they must share a trigger (one unit\'s trigger-out or the signal itself into every unit); alignment = +/- one sample of the slowest unit '
              '+ trigger jitter (-1: not measured on this bench)' % n_units) if n_units > 1 else ''
    # analog channels first (differential may consume the spare ones)
    analog_need = _n(needs['analog'])
    spare_analog = analog_total - analog_need
    if needs['analog'] > 0:
        if analog_total < analog_need:
            rows.append(_row('analog channels', analog_need, analog_total, 'no', 'the bench offers %d analog channel(s) in all' % analog_total))
        elif needs['same_instant'] and biggest < analog_need:
            rows.append(_row('analog channels', analog_need, analog_total, 'caveat', 'channels ADD UP across units, but no single unit has %d: %s' % (analog_need, shared)))
        else:
            rows.append(_row('analog channels', analog_need, analog_total, 'ok', 'one unit holds them all (same shot)' if biggest >= analog_need else 'enough channels; same_instant not asked'))
    # differential: native inputs, else two spare analog channels each
    if needs['differential'] > 0:
        need = needs['differential']
        by_math = max(0, spare_analog) // 2
        if diff_native >= need:
            rows.append(_row('differential signals', need, diff_native, 'ok', '%d native differential input(s) on the bench' % diff_native))
        elif diff_native + by_math >= need:
            used = (need - diff_native) * 2
            spare_analog -= used
            rows.append(_row('differential signals', need, diff_native + by_math, 'caveat', '%d native + %d by the math A - B on two analog channels each (%d analog channels used: common mode costs range, '
                             'channel skew costs timing)' % (diff_native, by_math, used)))
        else:
            rows.append(_row('differential signals', need, diff_native + by_math, 'no', 'needs a differential probe / input or two spare analog channels per signal (%d spare)' % max(0, spare_analog)))
    # digital: logic inputs, then spare analog channels
    if needs['digital'] > 0:
        need = needs['digital']
        if digital_total >= need:
            rows.append(_row('digital channels', need, digital_total, 'ok', '%d logic input(s) on the bench%s' % (digital_total, ('; ' + shared) if n_units > 1 and max(_n(u['digital']) for u in units) < need else '')))
        elif digital_total + max(0, spare_analog) >= need:
            rows.append(_row('digital channels', need, digital_total + max(0, spare_analog), 'caveat', '%d logic input(s) + %d spare analog channel(s) reading levels by a threshold (an analog channel '
                             'takes a digital signal and shows its edges)' % (digital_total, max(0, spare_analog))))
        else:
            rows.append(_row('digital channels', need, digital_total + max(0, spare_analog), 'no', 'not enough logic inputs or spare analog channels'))
    # bandwidth: the best single unit; never a sum
    if needs['bandwidth_hz'] > 0:
        best = max((u['bandwidth_hz'] for u in units), default=-1.0)
        ok = [u['title'] for u in units if u['bandwidth_hz'] >= needs['bandwidth_hz']]
        rows.append(_row('bandwidth (Hz)', needs['bandwidth_hz'], best, 'ok' if ok else 'no',
                         ('every signal needs ONE channel with this bandwidth: %s' % ', '.join(ok)) if ok else
                         'bandwidth NEVER adds up across units (the analog front end bounds each one): the best unit here is %s Hz' % ('%g' % best if best > 0 else 'unverified')))
    # sample rate: per unit at the needed analog channel count; ETS for repetitive signals; no cross-unit interleaving
    if needs['sample_rate_sps'] > 0:
        per_unit = {u['title']: (_srate_at(u, max(1, min(analog_need, _n(u['analog'])))), max(1, min(analog_need, _n(u['analog'])))) for u in units}
        ok = ['%s (%d ch on)' % (t, n) for t, (r, n) in per_unit.items() if r >= needs['sample_rate_sps']]
        ets = [u['title'] for u in units if u['ets'] >= needs['sample_rate_sps']]
        best = max((r for r, _n_ in per_unit.values()), default=-1.0)
        if ok:
            rows.append(_row('sample rate (Sa/s)', needs['sample_rate_sps'], best, 'ok', 'real-time per unit: %s (a rate is each unit\'s own at its channel count; never summed)' % ', '.join(ok)))
        elif needs['repetitive'] and ets:
            rows.append(_row('sample rate (Sa/s)', needs['sample_rate_sps'], max(u['ets'] for u in units), 'caveat',
                             'by equivalent-time sampling on %s - REPETITIVE signals only (the shape is rebuilt over many triggers)' % ', '.join(ets)))
        else:
            rows.append(_row('sample rate (Sa/s)', needs['sample_rate_sps'], best, 'no', 'the best unit gives %s Sa/s at that channel count; interleaving two units is NOT claimed (their sample clocks are not '
                             'phase-aligned)%s' % ('%g' % best if best > 0 else 'unverified', '' if needs['repetitive'] else '; if the signal repeats, say so: a unit with ETS may reach it')))
    # bits: the ADC's; averaging is an info row
    if needs['bits'] > 0:
        best = max((u['bits'] for u in units), default=-1)
        rows.append(_row('vertical resolution (bits)', needs['bits'], best, 'ok' if best >= needs['bits'] else 'no',
                         'bits are each unit\'s ADC; %d unit(s) on the SAME signal (or N captures) average uncorrelated noise by sqrt(N) - about %.2g bit(s) of noise, not accuracy, not bandwidth'
                         % (n_units, (0.5 * (n_units.bit_length() - 1)) if n_units > 1 else 0.0)))
    verdict = 'no' if any(r['verdict'] == 'no' for r in rows) else ('caveat' if any(r['verdict'] == 'caveat' for r in rows) else ('ok' if rows else 'nothing asked'))
    known = [u['price'] * u['count'] for u in units if u['price'] > 0]
    cost = {'usd': sum(known), 'units_priced': len(known), 'units': n_units, 'basis': 'the Instrument rows\' price_usd x count where known (-1 rows not summed)'}
    return {'needs': needs, 'units': units, 'rows': rows, 'verdict': verdict, 'cost': cost, 'options': options(needs, units),
            'basis': 'instruments.custom.testability: channels add up (shared trigger); bandwidth, bits and per-channel sample rate never do; ETS for repetitive signals; '
                     'noise averages by sqrt(N); a spare analog channel reads a digital signal'}


def options(needs, units, manager=None):
    """What ONE more unit of each known model would add - the cheap way to make a 'no' an 'ok' when the rule allows it (channels), with the price beside it."""
    out = []
    for m in C.models(manager):
        if m.get('kind') != 'oscilloscope':
            continue
        price = _num(m, 'price_usd')
        out.append({'model': m['name'], 'title': '%s %s' % (m.get('vendor', ''), m.get('model', '')), 'adds_analog': int(m.get('channels', -1) or -1),
                    'adds_digital': int(m.get('digital_channels', -1) or -1), 'bandwidth_hz': _num(m, 'bandwidth_hz'), 'bits': int(m.get('resolution_bits', -1) or -1),
                    'price_usd': price, 'openness': m.get('openness', 'unverified'), 'data_access': m.get('data_access', 'unverified'),
                    'helps': 'channels only (never bandwidth / bits / rate)' if units else 'the first unit sets bandwidth, bits and rate'})
    return sorted(out, key=lambda o: (o['price_usd'] < 0, o['price_usd']))


def door(manager, bench_name, body):
    from board.custom import bench as BENCH
    b = BENCH.bench(bench_name, manager)
    if b is None:
        return 404, {'ok': False, 'error': 'no bench named %r' % bench_name}
    if not isinstance(body, dict):
        return 400, {'ok': False, 'error': 'the body must be a JSON object of needs'}
    cov = coverage(parse_needs(body), units_on_bench(b, manager))
    rows = cov['rows'] or [_row('(nothing asked)', '', '', 'nothing asked', 'give at least one need: analog, digital, differential, bandwidth_hz, sample_rate_sps, bits')]
    return 200, dict(cov, ok=True, bench=bench_name, rows=rows, units=[{k: v for k, v in u.items() if k != 'srate'} for u in cov['units']])


def to_json(x):
    return json.dumps(x, sort_keys=True, default=str)
