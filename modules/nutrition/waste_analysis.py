"""
@cross-cutting
@module nutrition.waste_analysis
@tags @xc:bindings

mpb-4 (waste half) — what waste actually costs: grams via the
labeled weight priors, dollars via the best observed price
(estimate, labeled; unpriced waste is counted in grams and NAMED
as unpriced rather than valued at zero), grouped by food and
reason, worst first. Suggestions stay observations ("spinach
spoils on you — smaller bunches or freeze half"), never edits.

@consumers
  - nutrition.mealplanning_api, tracking dashboards
  - nutrition.selftest_waste
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-4
"""

from nutrition.market_analysis import (best_price_per_kg,
                                       resolve_grams)
from nutrition.person_analysis import _f, _rows


def waste_report(manager, household_name, today=None):
    """The household's waste ledger, priced where prices exist."""
    records = [r for r in _rows(manager, 'WasteRecord')
               if getattr(r, 'household_name', '')
               == household_name]
    if not records:
        return {'ok': True, 'schema': 'waste-report/1',
                'household': household_name,
                'records': 0, 'totalG': 0.0,
                'estValue': 0.0, 'byFood': [],
                'note': 'no waste logged — either a tight kitchen '
                        'or an unlogged leak; only the log knows'}
    by_food, unresolved = {}, []
    total_g = total_value = unpriced_g = 0.0
    for rec in records:
        food = getattr(rec, 'food_name', '')
        grams = resolve_grams(manager, food,
                              _f(rec, 'quantity', 0.0),
                              getattr(rec, 'unit', ''),
                              household_name)
        if not grams.get('ok'):
            unresolved.append({'record': getattr(rec, 'name', ''),
                               'why': grams.get('error')})
            continue
        g = grams['grams']
        total_g += g
        price = best_price_per_kg(manager, food, today)
        value = None
        if price is not None:
            value = g / 1000.0 * price['pricePerKg']
            total_value += value
        else:
            unpriced_g += g
        bucket = by_food.setdefault(food, {
            'food': food, 'grams': 0.0, 'estValue': 0.0,
            'priced': price is not None, 'reasons': {}})
        bucket['grams'] += g
        if value is not None:
            bucket['estValue'] += value
        reason = getattr(rec, 'reason', 'other')
        bucket['reasons'][reason] = (
            bucket['reasons'].get(reason, 0.0) + g)
    foods = sorted(by_food.values(),
                   key=lambda b: -(b['estValue'] or b['grams']))
    for b in foods:
        b['grams'] = round(b['grams'], 1)
        b['estValue'] = round(b['estValue'], 2)
        b['reasons'] = {k: round(v, 1)
                        for k, v in b['reasons'].items()}
    observations = []
    for b in foods[:3]:
        if b['grams'] <= 0:
            continue
        top_reason = max(b['reasons'], key=b['reasons'].get)
        observations.append(
            f'{b["food"]}: {b["grams"]:g} g wasted, mostly '
            f'{top_reason}'
            + (f' (~${b["estValue"]:.2f})' if b['priced'] else
               ' (no observed price — grams only)')
            + ' — smaller purchases, earlier freezing, or a '
              'use-it-up meal are the usual levers; your call')
    return {'ok': True, 'schema': 'waste-report/1',
            'household': household_name,
            'records': len(records),
            'totalG': round(total_g, 1),
            'estValue': round(total_value, 2),
            'unpricedG': round(unpriced_g, 1),
            'byFood': foods,
            'unresolved': unresolved,
            'observations': observations,
            'honesty': 'value = grams × best OBSERVED price '
                       '(estimate, labeled); unpriced waste is '
                       'counted in grams and NAMED, never valued '
                       'at zero as if it were free'}
