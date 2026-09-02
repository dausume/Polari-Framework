"""
@cross-cutting
@module nutrition.coverage_analysis
@tags @xc:bindings

mpb-6 — coverage steering over time: what has this person's LOGGED
intake actually covered over the last N days, which nutrients run
chronically under target, and what are the CHEAPEST closers that
exist at observed prices. Composition of three existing engines
(intake_day + person_thresholds + cheapest_closers) — no new
arithmetic, only honest joins:

  - averages are over DAYS WITH RECORDS ONLY; gap days are counted
    and named (an average diluted by unlogged days would fabricate
    a deficiency).
  - steering respects the person's declared exclusions (a milk-
    excluded person never gets cheddar as a calcium closer).
  - closers are price arithmetic; dish FIT stays the affinity
    composer's call (stated on the payload).

@consumers
  - nutrition.mealplanning_api (coverage route + dashboard)
  - nutrition.selftest_coverage
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-6
"""

from datetime import date, timedelta

from nutrition.budget_analysis import cheapest_closers
from nutrition.exclusion_analysis import screen_foods
from nutrition.meal_analysis import _named
from nutrition.person_analysis import _rows
from nutrition.threshold_analysis import person_thresholds
from nutrition.tracking_analysis import _date_range, intake_day


def _window_ending(end, days):
    """The last `days` calendar dates ending at `end` (inclusive) —
    unlogged days inside the window are REAL gap days."""
    y, m, d = (int(x) for x in end.split('-'))
    start = (date(y, m, d) - timedelta(days=days - 1)).isoformat()
    return _date_range(start, end)


def rolling_coverage(manager, person_name, days=7, end_date=None):
    """Average logged intake vs day targets over the window."""
    person = _named(manager, 'PersonProfile', person_name)
    if person is None:
        return {'ok': False,
                'error': f'no PersonProfile "{person_name}"'}
    record_dates = sorted({
        getattr(r, 'date', '') for r in
        _rows(manager, 'IntakeRecord')
        if getattr(r, 'person_name', '') == person_name
        and getattr(r, 'date', '')})
    if not record_dates:
        return {'ok': False,
                'error': f'no IntakeRecords for "{person_name}" — '
                         f'coverage needs logged days'}
    end = end_date or record_dates[-1]
    window = _window_ending(end, days)
    # nutrients the vendored per-100g data NEVER carries can never
    # show intake — reporting them "under target" would fabricate
    # a deficiency out of missing DATA. Split them out, named.
    measurable = {getattr(c, 'nutrient_name', '')
                  for c in _rows(manager, 'NutrientContent')}
    totals, logged, gaps = {}, 0, []
    for day in window:
        report = intake_day(manager, person_name, day)
        if not report.get('ok'):
            gaps.append(day)
            continue
        logged += 1
        for nutrient, amount in report['dayTotals'].items():
            totals[nutrient] = totals.get(nutrient, 0.0) + amount
    if logged == 0:
        return {'ok': False,
                'error': f'no logged days inside the {days}-day '
                         f'window ending {end} — gaps: {gaps}'}
    th = person_thresholds(manager, person, 'day')
    if not th.get('ok'):
        return {'ok': False, 'error': th.get('error')}
    under, over, on_track, no_data = [], [], [], []
    for nutrient, row in sorted(th['thresholds'].items()):
        target = row.get('target', 0.0) or 0.0
        maximum = row.get('max', 0.0) or 0.0
        if target <= 0:
            continue
        if nutrient not in measurable:
            no_data.append(nutrient)
            continue
        avg = totals.get(nutrient, 0.0) / logged
        entry = {'nutrient': nutrient,
                 'unit': row.get('unit', ''),
                 'avgPerLoggedDay': round(avg, 2),
                 'dayTarget': target,
                 'coverage': round(avg / target, 3)}
        if maximum > 0 and avg > maximum:
            entry['dayMax'] = maximum
            over.append(entry)
        elif avg < target * 0.8:
            entry['dailyGap'] = round(target - avg, 2)
            under.append(entry)
        else:
            on_track.append(entry)
    under.sort(key=lambda e: e['coverage'])
    return {'ok': True, 'schema': 'rolling-coverage/1',
            'person': person_name,
            'windowDays': days, 'end': end,
            'loggedDays': logged, 'gapDays': gaps,
            'underTarget': under, 'overMax': over,
            'onTrack': len(on_track),
            'noDataNutrients': no_data,
            'honesty': 'averages are over LOGGED days only — gap '
                       'days are named, never counted as zero '
                       'intake; under-target = below 80% of the '
                       'day target on average (a labeled '
                       'convention, not a diagnosis); nutrients '
                       'the vendored composition data never '
                       'carries are listed as NO-DATA, not as '
                       'deficiencies'}


def coverage_steering(manager, person_name, days=7, end_date=None,
                      today=None, closers_per_nutrient=3):
    """Chronic under-targets + the cheapest exclusion-safe
    closers — suggestions with arithmetic, yours to apply."""
    coverage = rolling_coverage(manager, person_name, days,
                                end_date)
    if not coverage.get('ok'):
        return coverage
    steered = []
    for gap in coverage['underTarget'][:5]:
        closers = cheapest_closers(
            manager, gap['nutrient'], gap['dailyGap'], today,
            limit=closers_per_nutrient * 2)
        entry = {'nutrient': gap['nutrient'],
                 'coverage': gap['coverage'],
                 'dailyGap': gap['dailyGap'],
                 'unit': gap['unit']}
        if not closers.get('ok') or not closers['closers']:
            entry['note'] = ('no priced closer exists yet — enter '
                             'prices for foods carrying this '
                             'nutrient and closers appear')
            steered.append(entry)
            continue
        screen = screen_foods(
            manager, person_name,
            [c['food'] for c in closers['closers']])
        blocked = {v['food'] for v in screen['violations']}
        safe = [c for c in closers['closers']
                if c['food'] not in blocked]
        entry['closers'] = safe[:closers_per_nutrient]
        if blocked:
            entry['excludedClosers'] = sorted(blocked)
            entry['exclusionNote'] = ('closers violating your '
                                      'declared exclusions were '
                                      'removed and are named here')
        steered.append(entry)
    return {'ok': True, 'schema': 'coverage-steering/1',
            'person': person_name,
            'windowDays': days,
            'loggedDays': coverage['loggedDays'],
            'gapDays': coverage['gapDays'],
            'steering': steered,
            'overMax': coverage['overMax'],
            'honesty': 'price arithmetic only — dish FIT is the '
                       'affinity composer\'s call; applying any '
                       'of this to a plan is yours'}
