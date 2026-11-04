"""
@module cmod.custom.measure_readings

msv-0 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md sections 2-4): BUILT UNITS, REAL READINGS, AND THEIR JUDGEMENT. A reading is kept as entered (never
edited; a later one of the same point supersedes it); whether it matches the simulation is DERIVED on read:

  add_unit(manager, bs, body)          body {name?, hex_sha256?, build_method?, built_by?, layout?, notes?} -> the BuiltUnit ('<bs>-unit-<n>' when unnamed)
  units(manager, bs)                   the Bench Solution's units
  add_reading(manager, unit, body)     body {point, value, unit?: V|mV|uV|A|mA|uA, via?: manual, instrument?, range_max?, who?, note?, evidence_sha256?}
                                       -> the reading + its judgement; the quantity's unit must match the point's (V vs A)
  readings(manager, unit)              every reading of the unit, judged, newest first; `current` = the newest of its point
  judge(manager, reading)              -> {nominal, delta, delta_pct, band, band_words, verdict, words}

Verdicts (msv-0: the instrument band only; msv-1 adds the tolerance band, msv-2 the rulings):
  in-band       |reading - nominal| <= the instrument's cited accuracy at the range used (pct of reading + counts x resolution)
  unexplained   outside it - a person's look is needed (no tolerance band or ruling exists yet to explain it)
  unjudged      the instrument has no cited InstrumentAccuracy row for this function / range (D-msv-2: the user's instruments are read first) - the delta
                is still given
  over-range    the value is beyond the range said
A reading on another build than the point's prediction says so (stale).
"""
import datetime
import re

from cmod.custom import config_rows as R

_SCALE = {'V': ('V', 1.0), 'mV': ('V', 1e-3), 'uV': ('V', 1e-6), 'µV': ('V', 1e-6),
          'A': ('A', 1.0), 'mA': ('A', 1e-3), 'uA': ('A', 1e-6), 'µA': ('A', 1e-6)}
VIAS = ('manual', 'usb-scpi', 'usb-serial', 'lan-scpi')


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def fmt(v, unit):
    a = abs(v)
    for p, k in (('', 1.0), ('m', 1e-3), ('u', 1e-6)):
        if a >= k or p == 'u':
            return '%.4g %s%s' % (v / k, p, unit)
    return '%g %s' % (v, unit)


def add_unit(manager, bs, body):
    if R.get(manager, 'BenchSolution', bs) is None:
        raise R.ConfigRefused('no Bench Solution %r' % bs, status=404)
    name = str(body.get('name') or '') or '%s-unit-%d' % (bs, len(R.rows(manager, 'BuiltUnit', bench_solution=bs)) + 1)
    method = str(body.get('build_method') or 'breadboard')
    if method not in ('breadboard', 'perfboard', 'wire-wrap', 'pcb', 'other'):
        raise R.ConfigRefused('build_method is breadboard | perfboard | wire-wrap | pcb | other, not %r' % method)
    old = R.get(manager, 'BuiltUnit', name)
    if old is not None and old['bench_solution'] != bs:
        raise R.ConfigRefused('unit %s belongs to %s' % (name, old['bench_solution']), status=409)
    return R.upsert(manager, 'BuiltUnit', name, bench_solution=bs, hex_sha256=str(body.get('hex_sha256') or (old or {}).get('hex_sha256') or ''),
                    layout=str(body.get('layout') or ''), build_method=method, built_by=str(body.get('built_by') or ''), notes=str(body.get('notes') or ''),
                    at=(old or {}).get('at') or _now())


def units(manager, bs):
    return sorted(R.rows(manager, 'BuiltUnit', bench_solution=bs), key=lambda u: (len(u['name']), u['name']))


def _parse(body, si_unit):
    """-> (SI value, entered words). `value` may carry its unit ('14.2 mA') or name it in `unit`."""
    raw = str(body.get('value', '')).strip()
    m = re.fullmatch(r'([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([a-zA-Zµ]*)', raw)
    if not m:
        raise R.ConfigRefused('the value %r is not a number (with an optional unit: V mV uV A mA uA)' % raw)
    unit = m.group(2) or str(body.get('unit') or '') or si_unit
    if unit not in _SCALE:
        raise R.ConfigRefused('the unit %r is not one of %s' % (unit, ' '.join(k for k in _SCALE if 'µ' not in k)))
    base, k = _SCALE[unit]
    if base != si_unit:
        raise R.ConfigRefused('the point measures %s; %s is a %s unit' % (si_unit, unit, base))
    return float(m.group(1)) * k, '%s %s' % (m.group(1), unit)


def add_reading(manager, unit, body):
    u = R.get(manager, 'BuiltUnit', unit)
    if u is None:
        raise R.ConfigRefused('no built unit %r' % unit, status=404)
    p = R.get(manager, 'MeasurementPoint', str(body.get('point') or ''))
    if p is None:
        raise R.ConfigRefused('no measurement point %r' % body.get('point'), status=404)
    via = str(body.get('via') or 'manual')
    if via not in VIAS:
        raise R.ConfigRefused('via is %s, not %r' % (' | '.join(VIAS), via))
    inst = str(body.get('instrument') or '')
    if inst and R.rows(manager, 'Instrument', name=inst) == [] and not R.rows(manager, 'InstrumentAccuracy', instrument=inst):
        raise R.ConfigRefused('no instrument %r (an Instrument row, or its InstrumentAccuracy rows)' % inst, status=404)
    value, entered = _parse(body, p['si_unit'])
    rng = body.get('range_max')
    if rng not in (None, ''):
        rng = _parse({'value': rng, 'unit': body.get('unit') or ''}, p['si_unit'])[0]
    else:
        rng = -1.0
    n = len([r for r in R.rows(manager, 'MeasurementReading', unit=unit) if r['point'] == p['name']]) + 1
    row = R.upsert(manager, 'MeasurementReading', '%s:%s#r%d' % (unit, p['name'], n), unit=unit, point=p['name'], value=value, entered=entered, via=via,
                   instrument=inst, range_max=float(rng), who=str(body.get('who') or ''), at=_now(), hex_sha256=u['hex_sha256'],
                   evidence_sha256=str(body.get('evidence_sha256') or ''), evidence_path=str(body.get('evidence_path') or ''),
                   session=str(body.get('session') or ''), step=str(body.get('step') or ''), note=str(body.get('note') or ''))
    return dict(row, **judge(manager, row))


def band(manager, instrument, function, value, range_max=-1.0):
    """-> (band in SI or None, words, range used or None)."""
    if not instrument:
        return None, 'no instrument said: the instrument band is unmeasured', None
    rows = sorted((a for a in R.rows(manager, 'InstrumentAccuracy', instrument=instrument) if a['function'] == function), key=lambda a: float(a['range_max']))
    if not rows:
        return None, '%s has no cited accuracy for %s: the instrument band is unmeasured (read its datasheet first, D-msv-2)' % (instrument, function), None
    if range_max is not None and float(range_max) > 0:
        row = next((a for a in rows if abs(float(a['range_max']) - float(range_max)) <= 1e-12 + 1e-9 * float(range_max)), None)
        if row is None:
            return None, '%s has no %s range of %g (its ranges: %s)' % (instrument, function, range_max, ', '.join('%g' % float(a['range_max']) for a in rows)), None
    else:
        row = next((a for a in rows if float(a['range_max']) >= abs(value)), None)
        if row is None:
            return None, 'the value is beyond every %s range of %s' % (function, instrument), None
    if float(row['pct_reading']) < 0:
        return None, '%s %s range %g: the accuracy is unread (-1)' % (instrument, function, float(row['range_max'])), row
    b = float(row['pct_reading']) / 100.0 * abs(value) + int(row['counts']) * float(row['resolution'])
    return b, '%s %s on the %g range: +/-(%g %% of reading + %d counts of %g) (%s)' % (
        instrument, function, float(row['range_max']), float(row['pct_reading']), int(row['counts']), float(row['resolution']), row.get('cite') or 'uncited'), row


def judge(manager, reading):
    p = R.get(manager, 'MeasurementPoint', reading['point']) or {}
    nominal = float(p.get('nominal') or 0.0)
    unit = p.get('si_unit') or 'V'
    v = float(reading['value'])
    delta = v - nominal
    pct = (100.0 * delta / nominal) if nominal else None
    b, bw, row = band(manager, reading.get('instrument') or '', p.get('quantity') or 'V dc', v, reading.get('range_max'))
    if row is not None and abs(v) > float(row['range_max']):
        verdict = 'over-range'
    elif b is None:
        verdict = 'unjudged'
    else:
        verdict = 'in-band' if abs(delta) <= b else 'unexplained'
    stale = bool(reading.get('hex_sha256') and p.get('hex_sha256') and reading['hex_sha256'] != p['hex_sha256'])
    words = '%s read %s, predicted %s: %s%s; %s' % (
        p.get('quantity', ''), fmt(v, unit), fmt(nominal, unit), ('%+.4g %s' % (delta, unit)) if abs(delta) >= 1 else fmt(delta, unit),
        (' (%+.1f %%)' % pct) if pct is not None else '', bw if b is None else 'instrument band +/-%s (%s)' % (fmt(b, unit), bw))
    words += {'in-band': ' - IN BAND: it matches the simulation within the instrument',
              'unexplained': ' - UNEXPLAINED: outside the instrument band; no tolerance band (msv-1) or ruling (msv-2) explains it yet - a person\'s look is needed',
              'unjudged': ' - UNJUDGED: the delta stands, but without a cited accuracy it is neither a match nor a miss',
              'over-range': ' - OVER RANGE: the value is beyond the range said'}[verdict]
    if stale:
        words += '; STALE: read on build %s.., the prediction is for %s..' % (reading['hex_sha256'][:12], p['hex_sha256'][:12])
    return {'nominal': nominal, 'delta': delta, 'delta_pct': pct, 'band': b, 'band_words': bw, 'verdict': verdict, 'stale': stale, 'words': words,
            'quantity': p.get('quantity', ''), 'node': p.get('node', ''), 'where': p.get('where', '')}


def readings(manager, unit):
    if R.get(manager, 'BuiltUnit', unit) is None:
        raise R.ConfigRefused('no built unit %r' % unit, status=404)
    rows = sorted(R.rows(manager, 'MeasurementReading', unit=unit), key=lambda r: (r['at'], len(r['name']), r['name']), reverse=True)
    seen, out = set(), []
    for r in rows:
        out.append(dict(r, current=r['point'] not in seen, **judge(manager, r)))
        seen.add(r['point'])
    return out
