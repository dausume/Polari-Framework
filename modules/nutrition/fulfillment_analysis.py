"""
@cross-cutting
@module nutrition.fulfillment_analysis
@tags @xc:bindings

nmp-7 — the coverage sim (nut-5, meal-plan-aware): SUPPLY = the
garden's realized harvest nutrients per period; DEMAND = the
household's needs (nut-4) or — the nmp-7 upgrade — a MealPlan's
ACTUAL rolled-up daily demand. Per nutrient: ratio + status
(met/partial/gap/uncoverable); 'none'-plant-availability nutrients
are UNCOVERABLE by design and point at their real source (the
saltwater food forest spec / fermentation) — honest absence, named.
suggest_plantings proposes counts that would close each gap
(knobs-and-suggestions: counts suggested, never applied).

@consumers
  - nutrition.nutrition_api
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-7
"""

import json

from nutrition.harvest_analysis import harvest_nutrients
from nutrition.household_analysis import household_needs
from nutrition.meal_analysis import _named, plan_rollup
from nutrition.person_analysis import _f, _rows

UNCOVERABLE_SOURCES = {
    'iodine': 'saltwater food forest (seaweed) — see the spec',
    'sodium': 'saltwater food forest (seaweed) — see the spec',
    'chloride': 'saltwater food forest (seaweed) — see the spec',
    'vitamin-b12': 'fermentation of plant foods, or animal/algae '
                   'sources',
}


def _demand(manager, plan_row, period):
    """{nutrient: amount-per-period} + a source label."""
    meal_plan = getattr(plan_row, 'meal_plan_name', '')
    if meal_plan:
        mp = _named(manager, 'MealPlanDefinition', meal_plan)
        if mp is None:
            return None, f'no MealPlanDefinition named "{meal_plan}"'
        roll = plan_rollup(manager, mp)
        if not roll.get('ok'):
            return None, roll.get('error', 'plan rollup failed')
        day_totals = {}
        ndays = max(1, len(roll['days']))
        for day in roll['days'].values():
            for nut, amt in day['totals'].items():
                day_totals[nut] = day_totals.get(nut, 0.0) + amt
        period_days = {'day': 1.0, 'week': 7.0, 'month': 30.44}[period]
        return ({n: v / ndays * period_days
                 for n, v in day_totals.items()},
                f'meal plan "{meal_plan}" (avg day x '
                f'{period_days:g})')
    hh = getattr(plan_row, 'household_name', '')
    needs = household_needs(manager, hh, period=period)
    if not needs.get('ok'):
        return None, needs.get('error', 'household needs failed')
    return ({n: d['amount'] for n, d in needs['totals'].items()},
            f'household "{hh}" needs')


def _supply(manager, plan_row, period):
    """{nutrient: amount-per-period} from the plantings + reports."""
    try:
        plantings = json.loads(
            getattr(plan_row, 'plantings_json', '{}') or '{}')
    except Exception:
        plantings = {}
    period_days = {'day': 1.0, 'week': 7.0, 'month': 30.44}[period]
    cadence = _f(plan_row, 'harvest_period_days', 30.0) or 30.0
    harvests_per_period = period_days / cadence
    supply, reports = {}, []
    for food_name, count in plantings.items():
        h = harvest_nutrients(manager, food_name)
        if not h.get('ok'):
            reports.append({'food': food_name,
                            'error': h.get('error')})
            continue
        for nut, entry in h['nutrients'].items():
            supply[nut] = supply.get(nut, 0.0) + (
                entry['amount'] * count * harvests_per_period)
        reports.append({'food': food_name, 'plants': count,
                        'perHarvestMassG': h.get('freshMassG', 0.0)})
    return supply, reports


def coverage(manager, garden_plan_name, period='week'):
    if period not in ('day', 'week', 'month'):
        return {'ok': False,
                'error': "period must be day|week|month"}
    plan_row = _named(manager, 'GardenPlanDefinition',
                      garden_plan_name)
    if plan_row is None:
        return {'ok': False,
                'error': f'no GardenPlanDefinition named '
                         f'"{garden_plan_name}"'}
    demand, demand_source = _demand(manager, plan_row, period)
    if demand is None:
        return {'ok': False, 'error': demand_source}
    supply, harvest_reports = _supply(manager, plan_row, period)
    availability = {getattr(n, 'name', ''):
                    getattr(n, 'plant_availability', 'common')
                    for n in _rows(manager, 'DietaryNutrient')}
    rows, limiting = {}, None
    for nut, need in sorted(demand.items()):
        if need <= 0:
            continue
        have = supply.get(nut, 0.0)
        ratio = have / need
        if availability.get(nut) == 'none':
            status = 'uncoverable'
        elif ratio >= 1.0:
            status = 'met'
        elif ratio >= 0.25:
            status = 'partial'
        else:
            status = 'gap'
        row = {'demand': round(need, 2), 'supply': round(have, 2),
               'ratio': round(ratio, 3), 'status': status}
        if status == 'uncoverable':
            row['source'] = UNCOVERABLE_SOURCES.get(
                nut, 'not plant-native — needs an external source')
        rows[nut] = row
        if status != 'uncoverable' and (
                limiting is None
                or ratio < rows[limiting]['ratio']):
            limiting = nut
    result = {'ok': True, 'gardenPlan': garden_plan_name,
              'period': period, 'demandSource': demand_source,
              'coverage': rows, 'harvests': harvest_reports,
              'limitingNutrient': limiting,
              'honesty': 'uncoverable nutrients are named with '
                         'their real source, never averaged away'}
    # persist the snapshot (the scoring seam) when a real manager is
    # behind us; duck-typed selftest managers skip silently
    try:
        plan_row.coverage_result_json = json.dumps(
            {'period': period, 'limiting': limiting,
             'met': sum(1 for r in rows.values()
                        if r['status'] == 'met'),
             'total': len(rows)})
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(plan_row)
    except Exception:
        pass
    return result


def suggest_plantings(manager, garden_plan_name, period='week'):
    """For each gap/partial nutrient: which grown food yields it
    best, and how many MORE plants would close the gap."""
    cov = coverage(manager, garden_plan_name, period)
    if not cov.get('ok'):
        return cov
    plan_row = _named(manager, 'GardenPlanDefinition',
                      garden_plan_name)
    period_days = {'day': 1.0, 'week': 7.0, 'month': 30.44}[period]
    cadence = _f(plan_row, 'harvest_period_days', 30.0) or 30.0
    harvests = period_days / cadence
    grown = [f for f in _rows(manager, 'FoodItem')
             if getattr(f, 'plant_name', '')]
    suggestions = []
    for nut, row in cov['coverage'].items():
        if row['status'] not in ('gap', 'partial'):
            continue
        best, best_yield = None, 0.0
        for f in grown:
            h = harvest_nutrients(manager, getattr(f, 'name', ''))
            if not h.get('ok'):
                continue
            y = h['nutrients'].get(nut, {}).get('amount', 0.0)
            if y > best_yield:
                best, best_yield = getattr(f, 'name', ''), y
        if best is None or best_yield <= 0:
            suggestions.append({
                'nutrient': nut, 'status': row['status'],
                'note': 'no grown food in the roster yields this — '
                        'a pantry/purchase item for now'})
            continue
        missing = row['demand'] - row['supply']
        plants = missing / (best_yield * harvests)
        suggestions.append({
            'nutrient': nut, 'status': row['status'],
            'food': best,
            'morePlants': max(1, int(plants + 0.999)),
            'evidence': f'{best} yields {best_yield:g} per harvest; '
                        f'{missing:g} more needed per {period}',
            'note': 'a suggestion with the arithmetic shown — '
                    'nothing is planted for you'})
    uncoverable = [
        {'nutrient': n, 'source': r['source']}
        for n, r in cov['coverage'].items()
        if r['status'] == 'uncoverable']
    return {'ok': True, 'gardenPlan': garden_plan_name,
            'period': period, 'suggestions': suggestions,
            'uncoverable': uncoverable}
