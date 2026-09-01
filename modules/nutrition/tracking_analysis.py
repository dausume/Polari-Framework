"""
@cross-cutting
@module nutrition.tracking_analysis
@tags @xc:bindings

mpa-4 — per-person metrics OVER TIME (MEAL_PLANNING_APP_PLAN.md
§0.2: "tracking their nutrition, meal acidity, and other important
metrics, over time"), rolled up from IntakeRecord facts:

  resolve_me        Keycloak identity → UserAccountLink → person +
                    household (precedence sub > username > email;
                    unlinked logins get the fix named, never a
                    silent auto-provision — A4).
  intake_day        one person-day: per-meal nutrition (the nmp-4
                    rollup), GL, meal acidity, day totals vs the
                    person's thresholds + tolerance warnings.
  tracking_series   date-series of the day metrics + weight
                    observations — days with no records are NAMED
                    gaps (a flat-line chart through missing data is
                    a lie).

@consumers
  - nutrition.mealplanning_api (dashboard + trends pages)
  - nutrition.selftest_tracking
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-4
"""

from datetime import date, timedelta

from nutrition.acidity_analysis import template_acidity
from nutrition.meal_analysis import _named, template_rollup
from nutrition.person_analysis import _f, _rows
from nutrition.threshold_analysis import person_thresholds
from nutrition.tolerance_analysis import evaluate_tolerances

#: day-series nutrients the trends surface charts by default —
#: a selection knob, not a limit (the API takes ?nutrients=).
DEFAULT_SERIES_NUTRIENTS = ('calories', 'protein', 'fiber', 'sodium')


def resolve_me(manager, user_info):
    """Keycloak identity dict → the linked person, honestly."""
    if not user_info:
        return {'ok': False, 'authenticated': False,
                'error': 'no authenticated identity on this request '
                         '— log in via Keycloak (the /auth/me '
                         'surface shows what the backend sees)'}
    sub = user_info.get('sub') or ''
    username = user_info.get('username') or ''
    email = user_info.get('email') or ''
    links = _rows(manager, 'UserAccountLink')
    match = None
    for attr, value in (('keycloak_sub', sub),
                        ('keycloak_username', username),
                        ('keycloak_email', email)):
        if not value:
            continue
        for link in links:
            if getattr(link, attr, '') == value:
                match = (link, attr)
                break
        if match:
            break
    if match is None:
        return {'ok': False, 'authenticated': True,
                'username': username,
                'error': 'this login is not linked to a person yet '
                         '— add a UserAccountLink row (keycloak_sub '
                         f'"{sub or username}" → your PersonProfile '
                         'name); no profile is created silently '
                         '(A4)'}
    link, matched_by = match
    person_name = getattr(link, 'person_name', '')
    person = _named(manager, 'PersonProfile', person_name)
    return {'ok': True, 'authenticated': True,
            'matchedBy': matched_by,
            'person': person_name,
            'personExists': person is not None,
            'household': getattr(link, 'household_name', ''),
            'link': getattr(link, 'name', '')}


def intake_day(manager, person_name, day):
    """One person-day rolled up from IntakeRecords."""
    person = _named(manager, 'PersonProfile', person_name)
    records = sorted(
        [r for r in _rows(manager, 'IntakeRecord')
         if getattr(r, 'person_name', '') == person_name
         and getattr(r, 'date', '') == day],
        key=lambda r: (getattr(r, 'time_hhmm', ''),
                       getattr(r, 'slot', '')))
    if not records:
        return {'ok': False, 'date': day,
                'error': f'no IntakeRecords for {person_name} on '
                         f'{day} — an honest gap, not a zero'}
    meals, totals = [], {}
    for rec in records:
        template = _named(manager, 'MealTemplate',
                          getattr(rec, 'template_name', ''))
        if template is None:
            meals.append({'record': getattr(rec, 'name', ''),
                          'error': 'no such MealTemplate'})
            continue
        variation = None
        if getattr(rec, 'variation_name', ''):
            variation = _named(manager, 'VariationDefinition',
                               rec.variation_name)
        scale = _f(rec, 'scale', 1.0)
        roll = template_rollup(manager, template, variation, scale)
        acidity = template_acidity(manager, template, variation,
                                   scale, person=person)
        meal = {'record': getattr(rec, 'name', ''),
                'slot': getattr(rec, 'slot', ''),
                'template': getattr(rec, 'template_name', ''),
                'variation': getattr(rec, 'variation_name', ''),
                'source': getattr(rec, 'source', ''),
                'time': getattr(rec, 'time_hhmm', '')}
        if roll.get('ok'):
            for nut, entry in roll['perMeal'].items():
                totals[nut] = totals.get(nut, 0.0) + entry['amount']
            meal['calories'] = roll['perMeal'].get(
                'calories', {}).get('amount', 0.0)
            meal['glycemicLoad'] = roll['glycemicLoad']
        else:
            meal['rollupError'] = roll.get('error')
        if acidity.get('ok'):
            meal['acidMassShare'] = acidity['acidMassShare']
            meal['acidWarnings'] = [w['message'] for w in
                                    acidity['warnings']]
        meals.append(meal)
    day_report = {'ok': True, 'schema': 'intake-day/1',
                  'person': person_name, 'date': day,
                  'meals': meals,
                  'dayTotals': {n: round(v, 2)
                                for n, v in sorted(totals.items())}}
    if person is not None:
        th = person_thresholds(manager, person, 'day')
        if th.get('ok'):
            # thresholds is {nutrient: entry} (nmp-1 shape)
            vs = []
            for nut, row in sorted(th['thresholds'].items()):
                if nut in totals:
                    vs.append({'nutrient': nut,
                               'amount': round(totals[nut], 2),
                               'target': row.get('target'),
                               'max': row.get('max')})
            day_report['vsThresholds'] = vs
        tol = evaluate_tolerances(manager, totals, 'day',
                                  person=person)
        day_report['dayWarnings'] = tol['warnings']
    else:
        day_report['note'] = (f'no PersonProfile "{person_name}" — '
                              f'totals computed without thresholds')
    return day_report


def _date_range(start, end):
    y, m, d = (int(x) for x in start.split('-'))
    cur = date(y, m, d)
    y, m, d = (int(x) for x in end.split('-'))
    stop = date(y, m, d)
    out = []
    while cur <= stop:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def tracking_series(manager, person_name, start_date=None,
                    end_date=None, nutrients=None, persist=False):
    """Date-series of day metrics + weight, gaps named.

    persist=True upserts each computed day as a DailyIntakeMetric
    cache row (derive-on-demand, the D5 precedent) so class-backed
    charts can render the series — only on a real manager (the
    duck-typed selftest managers skip it, reported)."""
    nutrients = tuple(nutrients or DEFAULT_SERIES_NUTRIENTS)
    record_dates = sorted({
        getattr(r, 'date', '') for r in _rows(manager, 'IntakeRecord')
        if getattr(r, 'person_name', '') == person_name
        and getattr(r, 'date', '')})
    if not record_dates and not start_date:
        return {'ok': False,
                'error': f'no IntakeRecords for "{person_name}" — '
                         f'nothing to chart yet (log a meal or '
                         f'confirm a plan entry)'}
    start = start_date or record_dates[0]
    end = end_date or (record_dates[-1] if record_dates else start)
    days, gaps, metric_rows = [], [], []
    for day in _date_range(start, end):
        report = intake_day(manager, person_name, day)
        if not report.get('ok'):
            gaps.append(day)
            continue
        entry = {'date': day,
                 'mealsLogged': len(report['meals'])}
        for nut in nutrients:
            entry[nut] = report['dayTotals'].get(nut, 0.0)
        gls = [m.get('glycemicLoad', 0.0) for m in report['meals']
               if 'glycemicLoad' in m]
        acids = [m.get('acidMassShare') for m in report['meals']
                 if m.get('acidMassShare') is not None]
        entry['maxMealGL'] = round(max(gls), 1) if gls else 0.0
        entry['maxMealAcidShare'] = (round(max(acids), 3)
                                     if acids else 0.0)
        entry['dayWarningCount'] = len(report.get('dayWarnings', []))
        days.append(entry)
        totals = report['dayTotals']
        metric_rows.append({
            'name': f'{person_name}-{day}',
            'person_name': person_name, 'date': day,
            'calories': round(totals.get('calories', 0.0), 1),
            'protein_g': round(totals.get('protein', 0.0), 1),
            'fiber_g': round(totals.get('fiber', 0.0), 1),
            'sodium_mg': round(totals.get('sodium', 0.0), 1),
            'max_meal_gl': entry['maxMealGL'],
            'max_meal_acid_share': entry['maxMealAcidShare'],
            'meals_logged': entry['mealsLogged'],
            'day_warning_count': entry['dayWarningCount'],
            'is_prior': False, 'provenance_id': 'mpa-8 series cache',
        })
    cached = False
    cache_note = 'not requested'
    if persist and metric_rows:
        if getattr(manager, 'objectTypingDict', None) is None:
            cache_note = ('skipped — no typing dict on this manager '
                          '(selftest/duck manager); cache rows need '
                          'the live server')
        else:
            try:
                from composition.seed_upsert import upsert_seed_pairs
                from nutrition.intake_basis import DailyIntakeMetric
                upsert_seed_pairs(
                    manager,
                    [('DailyIntakeMetric', DailyIntakeMetric,
                      metric_rows)],
                    tag='IntakeMetricCache')
                cached = True
                cache_note = (f'{len(metric_rows)} DailyIntakeMetric '
                              f'cache rows upserted (charts read '
                              f'these)')
            except Exception as exc:
                cache_note = f'cache upsert failed: {exc}'
    weights = sorted(
        [{'date': getattr(w, 'date', ''),
          'weightKg': _f(w, 'weight_kg', 0.0),
          'context': getattr(w, 'context', '')}
         for w in _rows(manager, 'WeightObservation')
         if getattr(w, 'person_name', '') == person_name
         and getattr(w, 'date', '')],
        key=lambda w: w['date'])
    return {'ok': True, 'schema': 'tracking-series/1',
            'person': person_name,
            'start': start, 'end': end,
            'nutrients': list(nutrients),
            'days': days,
            'gapDays': gaps,
            'metricCache': {'cached': cached, 'note': cache_note},
            'weightObservations': weights,
            'honesty': 'days without records are NAMED gaps, never '
                       'zeros; per-meal GL and acid share chart '
                       'their day MAX (a spike metric, not an '
                       'average); comfort thresholds stay '
                       'general-population heuristics, not medical '
                       'advice'}
