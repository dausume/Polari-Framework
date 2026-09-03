"""
@module nutrition.tracking_periods

mpt — per-person tracking over time (Dustin 2026-09-02): "a per-
person page analyzing what an individual has ate over time … condense
data to average or mean values at per week and per month levels …
see if we are consistently eating too many sweets or acid inducing
foods or calories or carbs or salty foods … or if we are eating too
little".

  period_summary   the day series (tracking_series) condensed into
                   WEEK (Monday-start) or MONTH buckets: mean per
                   LOGGED day of calories / protein / carbohydrate /
                   fiber / sodium, mean max-meal glycemic load, mean
                   max-meal acid share, weight (mean + first→last
                   delta); each bucket judged against the person's
                   OWN lines (calorie envelope min/max, nutrient
                   targets, the sodium CDRR, the GL>20 convention, the
                   meal-acid-share tolerance row); CONSISTENCY = the
                   share of well-logged buckets flagged the same way.
                   persist=True upserts PeriodIntakeMetric cache rows
                   (the derive-on-demand pattern) the period charts
                   read — series_key '<person>:<kind>' is the one
                   filter an embedded graph can take.
  intake_proposal / weight_proposal   the "log it" FORMS' rows,
                   validated (the person, a real template, a valid
                   date/slot), written by GenerateEvent.

"Sweets" (N6, 2026-09-03): read from TOTAL SUGARS (FDC 269 / 269.3,
the vendored subset carries it for 24 of 49 pantry foods) whenever a
bucket has at least one day with sugars data; otherwise the pre-N6
basis, glycemic load + carbohydrate. Each bucket's `sweets.basis`
says which. The person's sugars line is a labelled CEILING derived
from the DGA added-sugar share (total >= added, so conservative) —
there is no DRI for total sugars, so it is never a target.
"""

import json
from datetime import date, datetime, timedelta
from statistics import mean

from nutrition.dga_limits import total_sugars_ceiling_g
from nutrition.meal_basis import MEAL_SLOTS
from nutrition.tracking_analysis import tracking_series

SWEETS_BASIS_SUGARS = 'sugars-total'
SWEETS_BASIS_GL = 'gl+carbohydrate'

PERIOD_KINDS = ('week', 'month')
SERIES_NUTRIENTS = ('calories', 'protein', 'carbohydrate', 'fiber', 'sodium')
MIN_LOGGED_DAYS = {'week': 3, 'month': 8}     # below = low-confidence bucket (named)
CONSISTENT_SHARE = 0.5                          # flagged in ≥ half the well-logged buckets
GL_MEAL_CAP = 20.0                              # Atkinson 2008 'high' convention (nmp-2 row)
ACID_SHARE_CAP = 0.5                            # meal-acid-share tolerance row (low confidence)


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', {}) or {}).get(cls, {}) or {}).values())


def _named(manager, cls, name):
    for r in _rows(manager, cls):
        if getattr(r, 'name', '') == name:
            return r
    return None


def _bucket(day_iso, kind):
    d = date.fromisoformat(day_iso[:10])
    if kind == 'month':
        start = d.replace(day=1)
        nxt = (start.replace(year=start.year + 1, month=1) if start.month == 12
               else start.replace(month=start.month + 1))
        return start.isoformat(), (nxt - timedelta(days=1)).isoformat(), (nxt - start).days
    start = d - timedelta(days=d.weekday())
    return start.isoformat(), (start + timedelta(days=6)).isoformat(), 7


def _lines(manager, person, sample_day=None):
    """The person's own lines: the calorie envelope (min/max/target)
    + the daily target/max the day rollup already computes for them
    (intake_day's vsThresholds) + the sodium CDRR row. Only nutrients
    that HAVE a line are returned — nothing empty."""
    lines = {'sodium': {'max': 2300.0, 'source': 'sodium CDRR (ul-grade row)'}}
    prof = _named(manager, 'PersonProfile', person)
    try:
        from nutrition.threshold_analysis import calorie_envelope
        if prof is not None:
            env = calorie_envelope(manager, prof)
            if env.get('ok'):
                lines['calories'] = {'min': env['minDailyKcal'], 'max': env['maxDailyKcal'],
                                     'target': env['targetDailyKcal'], 'source': 'calorie envelope'}
                # N6: the sugars line is a CEILING only (no DRI for
                # total sugars) — derived from the calorie target
                ceiling = total_sugars_ceiling_g(env['targetDailyKcal'])
                if ceiling:
                    lines['sugars-total'] = {'max': ceiling['grams'], 'kind': ceiling['kind'],
                                             'source': ceiling['source'], 'caveat': ceiling['caveat']}
    except Exception as e:  # the line stays absent, named
        lines['_note'] = f'calorie envelope unavailable: {e}'
    if sample_day:
        try:
            from nutrition.tracking_analysis import intake_day
            for t in intake_day(manager, person, sample_day).get('vsThresholds', []):
                n = t.get('nutrient')
                if n in ('protein', 'carbohydrate', 'fiber', 'sodium', 'calories'):
                    line = lines.setdefault(n, {})
                    if t.get('target'):
                        line['target'] = float(t['target'])
                    if t.get('max'):
                        line['max'] = float(t['max'])
                    line.setdefault('source', 'person thresholds (the day rollup\'s lines)')
        except Exception as e:
            lines['_note'] = f'thresholds unavailable: {e}'
    for row in _rows(manager, 'ToleranceThreshold'):
        if getattr(row, 'substance', '') == 'sodium' and getattr(row, 'period', '') == 'day':
            lines['sodium'] = {'max': float(getattr(row, 'threshold_amount', 2300) or 2300),
                               'source': getattr(row, 'citation', 'sodium CDRR')}
    return {k: v for k, v in lines.items() if k.startswith('_') or (v and any(
        isinstance(x, (int, float)) for x in v.values()))}


def _sweets(p, lines):
    """The bucket's "sweets" readout. `basis` names what it was read
    from: total sugars when any day in the bucket has sugars data,
    else glycemic load + carbohydrate (the pre-N6 reading)."""
    n, k = p['daysLogged'], p['daysWithSugars']
    if p['sugarsGMean'] is not None:
        line = lines.get('sugars-total')
        out = {'basis': SWEETS_BASIS_SUGARS, 'value': p['sugarsGMean'], 'unit': 'g/day',
               'daysWithSugars': k, 'daysLogged': n, 'line': line, 'overCeiling': None,
               'reading': (f'mean total sugars {p["sugarsGMean"]} g/day over {k} of {n} logged '
                           f'day(s) (FDC 269 rows; ingredients without a total-sugars row add '
                           f'nothing, so this is a lower bound)')}
        if line:
            out['overCeiling'] = p['sugarsGMean'] > line['max']
            out['reading'] += (f'; {"above" if out["overCeiling"] else "within"} the '
                               f'{line["max"]} g ceiling — {line["caveat"]}')
        else:
            out['reading'] += '; no calorie target, so no ceiling line is drawn'
        return out
    return {'basis': SWEETS_BASIS_GL, 'value': p['maxMealGlMean'], 'unit': 'GL (day max meal)',
            'carbohydrateGMean': p['carbohydrateMean'], 'daysWithSugars': 0, 'daysLogged': n,
            'line': {'max': GL_MEAL_CAP, 'kind': 'convention',
                     'source': 'GL>20 per meal (Atkinson 2008 convention, nmp-2 row)'},
            'overCeiling': p['maxMealGlMean'] > GL_MEAL_CAP,
            'reading': (f'no total-sugars data in this bucket — "sweets" read through glycemic '
                        f'load + carbohydrate (day-max meal GL {p["maxMealGlMean"]} vs the GL>20 '
                        f'convention; carbohydrate {p["carbohydrateMean"]} g/day)')}


def period_summary(manager, person, kind='week', start_date=None, end_date=None, persist=False):
    kind = kind if kind in PERIOD_KINDS else 'week'
    # persist refreshes the DAY cache too (the day charts on the same
    # page read DailyIntakeMetric) — one read, both caches current.
    series = tracking_series(manager, person, start_date, end_date,
                             nutrients=SERIES_NUTRIENTS, persist=persist)
    if not series.get('ok'):
        return {'ok': False, 'error': series.get('error', 'no series'), 'periods': []}
    logged = [d['date'] for d in series.get('days', [])]
    lines = _lines(manager, person, logged[-1] if logged else None)
    weights = series.get('weightObservations', [])
    buckets = {}
    for d in series.get('days', []):
        b0, b1, ndays = _bucket(d['date'], kind)
        b = buckets.setdefault(b0, {'periodStart': b0, 'periodEnd': b1, 'daysInPeriod': ndays, 'days': []})
        b['days'].append(d)
    for w in weights:
        b0, b1, ndays = _bucket(w['date'], kind)
        b = buckets.setdefault(b0, {'periodStart': b0, 'periodEnd': b1, 'daysInPeriod': ndays, 'days': []})
        b.setdefault('weights', []).append(w)
    periods, flags = [], {}
    for b0 in sorted(buckets):
        b = buckets[b0]
        days = b['days']
        n = len(days)
        wobs = sorted(b.get('weights', []), key=lambda w: w['date'])
        p = {'period': kind, 'periodStart': b0, 'periodEnd': b['periodEnd'],
             'daysLogged': n, 'daysInPeriod': b['daysInPeriod'],
             'lowConfidence': n < MIN_LOGGED_DAYS[kind],
             'weightKgMean': round(mean(w['weightKg'] for w in wobs), 2) if wobs else None,
             'weightKgDelta': round(wobs[-1]['weightKg'] - wobs[0]['weightKg'], 2) if len(wobs) > 1 else None,
             'verdicts': []}
        for nut in SERIES_NUTRIENTS:
            p[f'{nut}Mean'] = round(mean(float(d.get(nut, 0) or 0) for d in days), 1) if n else None
        p['maxMealGlMean'] = round(mean(float(d.get('maxMealGL', 0) or 0) for d in days), 1) if n else None
        p['maxMealAcidShareMean'] = round(mean(float(d.get('maxMealAcidShare', 0) or 0) for d in days), 3) if n else None
        # N6: sugars mean over the days that HAVE sugars data only —
        # a day without is an absence, never a zero in the mean
        sug = [float(d['sugarsG']) for d in days if d.get('sugarsG') is not None]
        p['sugarsGMean'] = round(mean(sug), 1) if sug else None
        p['daysWithSugars'] = len(sug)
        p['sweets'] = _sweets(p, lines) if n else None
        if n:
            def flag(metric, direction, value, line, reading):
                p['verdicts'].append({'metric': metric, 'direction': direction, 'value': value,
                                      'line': line, 'reading': reading})
                flags.setdefault((metric, direction), []).append(b0)
            cal = p['caloriesMean']
            cal_line = lines.get('calories', {})
            if cal_line.get('max') and cal > cal_line['max']:
                flag('calories', 'too much', cal, cal_line['max'], 'mean kcal/day above the envelope max')
            if cal_line.get('min') and cal < cal_line['min']:
                flag('calories', 'too little', cal, cal_line['min'], 'mean kcal/day below the envelope min')
            if lines['sodium'].get('max') and p['sodiumMean'] > lines['sodium']['max']:
                flag('sodium (salty foods)', 'too much', p['sodiumMean'], lines['sodium']['max'], 'mean sodium/day above the CDRR')
            if p['sweets']['basis'] == SWEETS_BASIS_SUGARS and p['sweets']['overCeiling']:
                flag('sweets (total sugars)', 'too much', p['sugarsGMean'], p['sweets']['line']['max'],
                     'mean total sugars/day above the conservative DGA-derived ceiling (total >= '
                     'added sugars, so the added-sugar line itself is not shown crossed)')
            if p['maxMealGlMean'] > GL_MEAL_CAP:
                flag('glycemic load (refined carbs; the sweets fallback basis)', 'too much',
                     p['maxMealGlMean'], GL_MEAL_CAP,
                     'mean of the day\'s highest-GL meal above the GL>20 convention')
            if p['maxMealAcidShareMean'] > ACID_SHARE_CAP:
                flag('acid share (acid-inducing foods)', 'too much', p['maxMealAcidShareMean'], ACID_SHARE_CAP,
                     'mean of the day\'s most acidic meal above the tolerance row (low confidence)')
            for nut in ('protein', 'carbohydrate', 'fiber'):
                tgt = lines.get(nut, {}).get('target')
                if tgt and p[f'{nut}Mean'] < tgt:
                    flag(nut, 'too little', p[f'{nut}Mean'], tgt, f'mean {nut}/day below the target')
        periods.append(p)
    well = [p for p in periods if p['daysLogged'] and not p['lowConfidence']]
    consistency = []
    for (metric, direction), when in flags.items():
        hit = [w for w in when if any(p['periodStart'] == w for p in well)]
        share = (len(hit) / len(well)) if well else 0.0
        consistency.append({'metric': metric, 'direction': direction,
                            'periodsFlagged': len(when), 'wellLoggedPeriods': len(well),
                            'share': round(share, 2),
                            'consistent': bool(well) and share >= CONSISTENT_SHARE,
                            'reading': (f'consistently {direction}: {metric} in {len(hit)} of {len(well)} '
                                        f'well-logged {kind}s' if well and share >= CONSISTENT_SHARE else
                                        f'{direction} {metric} in {len(when)} {kind}(s) — not yet a pattern'
                                        + ('' if well else ' (no well-logged period yet)'))})
    consistency.sort(key=lambda c: (-c['share'], c['metric']))
    cached, cache_note = False, 'not requested'
    if persist and periods:
        cached, cache_note = _persist(manager, person, kind, periods)
    bases = {SWEETS_BASIS_SUGARS: 0, SWEETS_BASIS_GL: 0}
    for p in periods:
        if p['sweets']:
            bases[p['sweets']['basis']] += 1
    return {'ok': True, 'schema': 'tracking-periods/1', 'person': person, 'period': kind,
            'start': series.get('start'), 'end': series.get('end'),
            'periods': periods, 'count': len(periods),
            'consistency': consistency,
            'lines': {k: v for k, v in lines.items() if not k.startswith('_')},
            'sweetsBasis': {'bucketsOnSugars': bases[SWEETS_BASIS_SUGARS],
                            'bucketsOnGlCarb': bases[SWEETS_BASIS_GL],
                            'note': 'each bucket\'s sweets.basis names its own reading'},
            'metricCache': {'cached': cached, 'note': cache_note},
            'honesty': ('means are per LOGGED day (gap days never count as zero); a bucket with fewer '
                        f'than {MIN_LOGGED_DAYS[kind]} logged days is low-confidence; "sweets" are read '
                        'from total sugars (FDC 269, 24 of 49 pantry foods carry it — a lower bound) '
                        'when a bucket has sugars data, else through glycemic load + carbohydrate — '
                        'each bucket\'s sweets.basis says which; the sugars line is a conservative '
                        'CEILING from the DGA added-sugar share (total >= added), never a target; '
                        'acid share rides the low-confidence tolerance row; lines are the person\'s own '
                        'envelope/targets — comfort readings, never diagnosis')}


def _persist(manager, person, kind, periods):
    if getattr(manager, 'objectTypingDict', None) is None:
        return False, 'duck-typed manager — cache skipped (reported)'
    try:
        from composition.seed_upsert import upsert_seed_pairs
        from nutrition.intake_basis import PeriodIntakeMetric
        rows = [{'name': f'{person}-{kind}-{p["periodStart"]}', 'person_name': person,
                 'period_kind': kind, 'series_key': f'{person}:{kind}',
                 'period_start': p['periodStart'], 'period_end': p['periodEnd'],
                 'days_logged': p['daysLogged'], 'days_in_period': p['daysInPeriod'],
                 'calories_mean': p['caloriesMean'] or 0.0, 'protein_g_mean': p['proteinMean'] or 0.0,
                 'carbohydrate_g_mean': p['carbohydrateMean'] or 0.0, 'fiber_g_mean': p['fiberMean'] or 0.0,
                 'sodium_mg_mean': p['sodiumMean'] or 0.0, 'max_meal_gl_mean': p['maxMealGlMean'] or 0.0,
                 'sugars_g_mean': p['sugarsGMean'] or 0.0,
                 'sweets_basis': p['sweets']['basis'] if p['sweets'] else '',
                 'max_meal_acid_share_mean': p['maxMealAcidShareMean'] or 0.0,
                 'weight_kg_mean': p['weightKgMean'] or 0.0, 'weight_kg_delta': p['weightKgDelta'] or 0.0,
                 'verdicts_json': json.dumps(p['verdicts']), 'low_confidence': p['lowConfidence'],
                 'is_prior': False, 'provenance_id': 'mpt period cache'}
                # a bucket with NO logged days (weight-only) would chart
                # its nutrient means as zeros — an honest absence is no
                # row; the day-level weight chart still shows the weight.
                for p in periods if p['daysLogged'] > 0]
        if not rows:
            return False, 'no logged days — nothing to cache'
        upsert_seed_pairs(manager, [('PeriodIntakeMetric', PeriodIntakeMetric, rows)],
                          tag='PeriodCache')
        return True, f'{len(rows)} {kind} row(s) upserted'
    except Exception as e:
        return False, f'cache upsert failed: {e}'


# ---------------------------------------------------------------
# the "log it" forms
# ---------------------------------------------------------------

def _valid_date(text):
    try:
        return date.fromisoformat(str(text)[:10]).isoformat()
    except (TypeError, ValueError):
        return None


def _refused(error):
    """A refused log: the error IS the message the form shows."""
    return {'ok': False, 'error': error, 'message': error, 'proposals': []}


def intake_proposal(manager, person='', date_iso='', slot='', template='', variation='',
                    scale=1.0, time_hhmm=''):
    problems = []
    if not person or _named(manager, 'PersonProfile', person) is None:
        problems.append(f"person '{person}' is not a PersonProfile")
    d = _valid_date(date_iso) or (date.today().isoformat() if not date_iso else None)
    if d is None:
        problems.append(f"date '{date_iso}' is not YYYY-MM-DD")
    if slot not in MEAL_SLOTS:
        problems.append(f"slot '{slot}' is not one of {', '.join(MEAL_SLOTS)}")
    t = _named(manager, 'MealTemplate', template)
    if t is None:
        problems.append(f"meal '{template}' is not a MealTemplate")
    v = variation
    if t is not None and not v:
        vs = [x for x in _rows(manager, 'VariationDefinition') if getattr(x, 'template_name', '') == t.name]
        v = next((x.name for x in vs if x.name.endswith('-base')), vs[0].name if vs else '')
    try:
        scale = float(scale or 1.0)
    except (TypeError, ValueError):
        problems.append(f"scale '{scale}' is not a number")
        scale = 1.0
    if problems:
        return _refused('; '.join(problems))
    row = {'name': f'{person}-{d}-{slot}', 'person_name': person, 'date': d, 'slot': slot,
           'template_name': t.name, 'variation_name': v, 'scale': scale,
           'time_hhmm': time_hhmm or '', 'source': 'logged', 'plan_entry_name': '',
           'is_prior': False, 'provenance_id': 'mpt log form', 'notes': 'logged from the tracking page'}
    existing = _named(manager, 'IntakeRecord', row['name'])
    if existing is not None:
        message = (f'Already logged {slot} on {d} for {person} '
                   f'({getattr(existing, "template_name", "") or "that meal"}) — kept; edit that '
                   f'row to change it')
    else:
        message = f'Logged {slot} on {d} for {person}: {t.name} ×{scale:g}'
    return {'ok': True, 'schema': 'intake-proposal/1', 'proposals': [row],
            'alreadyLogged': existing is not None, 'message': message,
            'honesty': 'one IntakeRecord per person × date × slot — logging the same slot again reuses it (dedupe by name)'}


def weight_proposal(manager, person='', date_iso='', weight_kg=0.0, context=''):
    problems = []
    if not person or _named(manager, 'PersonProfile', person) is None:
        problems.append(f"person '{person}' is not a PersonProfile")
    d = _valid_date(date_iso) or (date.today().isoformat() if not date_iso else None)
    if d is None:
        problems.append(f"date '{date_iso}' is not YYYY-MM-DD")
    try:
        w = float(weight_kg or 0)
    except (TypeError, ValueError):
        w = 0.0
    if not (20 <= w <= 400):
        problems.append(f"weight {weight_kg!r} kg is outside 20–400")
    if problems:
        return _refused('; '.join(problems))
    row = {'name': f'{person}-weight-{d}', 'person_name': person, 'date': d, 'day_index': 0,
           'weight_kg': round(w, 2), 'context': context or 'logged', 'is_prior': False,
           'provenance_id': 'mpt log form', 'notes': 'logged from the tracking page'}
    existing = _named(manager, 'WeightObservation', row['name'])
    if existing is not None:
        message = (f'Already logged {float(getattr(existing, "weight_kg", 0) or 0):.1f} kg on {d} '
                   f'for {person} — kept; edit that row to change it')
    else:
        message = f'Logged {w:.1f} kg on {d} for {person}'
    return {'ok': True, 'schema': 'weight-proposal/1', 'proposals': [row],
            'alreadyLogged': existing is not None, 'message': message,
            'honesty': 'one WeightObservation per person × date (dedupe by name)'}
