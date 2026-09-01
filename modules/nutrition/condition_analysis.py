"""
@cross-cutting
@module nutrition.condition_analysis
@tags @xc:bindings

mpb-2 — "try to make meals that do not make this condition worse"
(the ratified posture, and ONLY that): evaluate a meal's computable
aggravator metrics against the person's STATED conditions, flag
likely aggravators with the evidence grade, name the substances we
CANNOT compute (data gaps, never guesses), and rank — never block,
never diagnose, never treat.

Computable today (per meal): meal-acidity (acid mass share, mpa-1),
meal-fat-load (healthy-fat grams from the rollup), sodium (rollup),
glycemic-load (rollup). NOT computable from the FDC subset:
fructans / lactose-as-FODMAP / sugar alcohols — those report as
NAMED data gaps when a steering row asks for them.

@consumers
  - nutrition.mealplanning_api (condition routes + planner flags)
  - nutrition.selftest_condition
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-2
"""

import json

from nutrition.acidity_analysis import template_acidity
from nutrition.condition_basis import POSTURE
from nutrition.meal_analysis import _named, template_rollup
from nutrition.person_analysis import _f, _rows

#: substance → how one meal's value for it is computed ('' = not
#: computable from the vendored data — a NAMED gap).
_MEAL_METRIC_SOURCES = {
    'meal-acidity': 'acid mass share (mpa-1 pH claims)',
    'meal-fat-load': 'rollup healthy-fat grams',
    'sodium': 'rollup sodium mg',
    'glycemic-load': 'rollup GL (published GI values)',
    'reflux-trigger-categories': 'trigger-category flags '
                                 '(carbonation/caffeine/mint/'
                                 'chocolate — none in the base '
                                 'roster; flags appear when such '
                                 'foods join it)',
}


def person_conditions(manager, person_name):
    """The person's stated declarations + their steering rows."""
    steerings = {getattr(s, 'condition', ''): s
                 for s in _rows(manager, 'ConditionSteering')}
    out = []
    for row in _rows(manager, 'StatedCondition'):
        if getattr(row, 'person_name', '') != person_name:
            continue
        condition = getattr(row, 'condition', '')
        steer = steerings.get(condition)
        entry = {'condition': condition,
                 'statedReason': getattr(row, 'stated_reason', ''),
                 'declaredDate': getattr(row, 'declared_date', '')}
        if steer is None:
            entry['steering'] = None
            entry['note'] = (f'no ConditionSteering row for '
                             f'"{condition}" — declared but not '
                             f'steerable yet; adding the mapping '
                             f'row is the fix')
        else:
            try:
                substances = json.loads(getattr(
                    steer, 'aggravator_substances_json', '[]')
                    or '[]')
            except ValueError:
                substances = []
            entry['steering'] = {
                'displayName': getattr(steer, 'display_name', ''),
                'aggravatorSubstances': substances,
                'guidance': getattr(steer, 'guidance', ''),
                'citation': getattr(steer, 'citation', ''),
                'confidence': getattr(steer, 'confidence', ''),
            }
        out.append(entry)
    return out


def _meal_metrics(manager, template, variation, scale, person):
    """The computable per-meal aggravator metrics."""
    roll = template_rollup(manager, template, variation, scale)
    acidity = template_acidity(manager, template, variation, scale,
                               person=person)
    metrics, gaps = {}, []
    if roll.get('ok'):
        metrics['meal-fat-load'] = roll['perMeal'].get(
            'healthy-fat', {}).get('amount', 0.0)
        metrics['sodium'] = roll['perMeal'].get(
            'sodium', {}).get('amount', 0.0)
        metrics['glycemic-load'] = roll['glycemicLoad']
    else:
        gaps.append(f'rollup failed: {roll.get("error")}')
    if acidity.get('ok'):
        metrics['meal-acidity'] = acidity['acidMassShare']
    else:
        gaps.append(f'acidity failed: {acidity.get("error")}')
    # trigger categories: no base-roster food carries one — an
    # honest constant-for-now that flips when such foods exist.
    metrics['reflux-trigger-categories'] = 0.0
    return metrics, gaps


def _threshold_rows(manager):
    return {getattr(t, 'substance', ''): t
            for t in _rows(manager, 'ToleranceThreshold')
            if getattr(t, 'period', '') in ('meal', 'day')}


def meal_condition_report(manager, person_name, template_name,
                          variation_name='', scale=1.0):
    """One meal vs one person's stated conditions."""
    template = _named(manager, 'MealTemplate', template_name)
    if template is None:
        return {'ok': False,
                'error': f'no MealTemplate "{template_name}"'}
    variation = (_named(manager, 'VariationDefinition',
                        variation_name) if variation_name else None)
    person = _named(manager, 'PersonProfile', person_name)
    conditions = person_conditions(manager, person_name)
    if not conditions:
        return {'ok': True, 'schema': 'meal-condition/1',
                'template': template_name, 'person': person_name,
                'conditions': [],
                'verdict': 'no stated conditions — nothing to '
                           'steer against',
                'posture': POSTURE}
    metrics, metric_gaps = _meal_metrics(
        manager, template, variation, scale, person)
    thresholds = _threshold_rows(manager)
    reports = []
    for cond in conditions:
        steer = cond.get('steering')
        report = {'condition': cond['condition'],
                  'statedReason': cond['statedReason']}
        if steer is None:
            report['note'] = cond['note']
            reports.append(report)
            continue
        aggravators, gaps = [], []
        for substance in steer['aggravatorSubstances']:
            if substance not in _MEAL_METRIC_SOURCES:
                gaps.append({'substance': substance,
                             'why': 'not computable from the '
                                    'vendored data — a NAMED gap, '
                                    'never a guess'})
                continue
            value = metrics.get(substance)
            row = thresholds.get(substance)
            threshold = _f(row, 'threshold_amount', 0.0) \
                if row is not None else 0.0
            over = (value is not None and threshold > 0
                    and value > threshold)
            entry = {'substance': substance,
                     'value': (round(value, 3)
                               if value is not None else None),
                     'threshold': threshold,
                     'unit': getattr(row, 'unit', '')
                     if row is not None else '',
                     'likelyAggravating': bool(over),
                     'evidence': getattr(row, 'citation', '')
                     if row is not None else '',
                     'confidence': getattr(row, 'confidence', '')
                     if row is not None else steer['confidence'],
                     'source': _MEAL_METRIC_SOURCES[substance]}
            aggravators.append(entry)
        flagged = [a for a in aggravators if a['likelyAggravating']]
        report.update({
            'guidance': steer['guidance'],
            'aggravators': aggravators,
            'dataGaps': gaps,
            'likelyAggravating': bool(flagged),
            'verdict': (f'this meal would likely aggravate your '
                        f'stated {cond["condition"]}: '
                        + ', '.join(
                            f'{a["substance"]} {a["value"]:g}'
                            f' > {a["threshold"]:g} {a["unit"]}'
                            for a in flagged)
                        if flagged else
                        f'no computable aggravator of your stated '
                        f'{cond["condition"]} crosses its cited '
                        f'threshold in this meal'),
        })
        reports.append(report)
    if metric_gaps:
        for report in reports:
            report.setdefault('dataGaps', []).extend(
                {'substance': '(meal metrics)', 'why': g}
                for g in metric_gaps)
    return {'ok': True, 'schema': 'meal-condition/1',
            'template': template_name,
            'variation': variation_name, 'scale': scale,
            'person': person_name,
            'conditions': reports,
            'anyLikelyAggravating': any(
                r.get('likelyAggravating') for r in reports),
            'posture': POSTURE}


def plan_condition_report(manager, plan, person_name=None):
    """Every plan entry vs the owner's stated conditions — flags
    for the planner page; ranking input, never a block."""
    person = person_name or getattr(plan, 'person_name', '')
    if not person:
        return {'ok': False,
                'error': 'no person to steer for'}
    entries = sorted(
        [e for e in _rows(manager, 'MealEntry')
         if getattr(e, 'plan_name', '')
         == getattr(plan, 'name', '')],
        key=lambda e: (getattr(e, 'day_index', 0),
                       getattr(e, 'slot', '')))
    if not entries:
        return {'ok': False, 'error': 'plan has no MealEntries'}
    reports, flagged = [], 0
    for entry in entries:
        r = meal_condition_report(
            manager, person, getattr(entry, 'template_name', ''),
            getattr(entry, 'variation_name', ''),
            _f(entry, 'scale', 1.0))
        row = {'entry': getattr(entry, 'name', ''),
               'day': getattr(entry, 'day_index', 0),
               'slot': getattr(entry, 'slot', '')}
        if not r.get('ok'):
            row['error'] = r.get('error')
        else:
            row['likelyAggravating'] = r['anyLikelyAggravating']
            row['conditions'] = [
                {'condition': c['condition'],
                 'verdict': c.get('verdict', c.get('note', ''))}
                for c in r['conditions']]
            if r['anyLikelyAggravating']:
                flagged += 1
        reports.append(row)
    return {'ok': True, 'schema': 'plan-condition/1',
            'plan': getattr(plan, 'name', ''), 'person': person,
            'entries': reports,
            'entriesLikelyAggravating': flagged,
            'verdict': ('no entry crosses a cited aggravator '
                        'threshold for your stated conditions'
                        if flagged == 0 else
                        f'{flagged} entries would likely aggravate '
                        f'a stated condition — flagged for YOUR '
                        f'call, never blocked'),
            'posture': POSTURE}
