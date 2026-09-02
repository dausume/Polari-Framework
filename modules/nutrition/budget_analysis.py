"""
@cross-cutting
@module nutrition.budget_analysis
@tags @xc:bindings

mpb-3 — nutrient value per dollar + the budget envelope (the PANTS
pattern, built on OUR price observations + FDC rows):

  nutrient_value_report   per food with an observed price: grams
                          (or the nutrient's unit) per dollar —
                          the "protein per $" ranking. Unpriced
                          foods and foods without the nutrient are
                          NAMED, never dropped silently.
  cheapest_closers        given a nutrient gap, the cheapest foods
                          that close it: $ to buy the closing
                          grams at the best observed price —
                          arithmetic shown.
  plan_budget_report      plan cost vs the PlanBudget cap: spend,
                          headroom/overrun, the biggest cost
                          drivers, and cheaper-protein-style
                          nudges — suggestions with numbers, the
                          plan stays the human's.

@consumers
  - nutrition.mealplanning_api, coverage steering (mpb-6)
  - nutrition.selftest_budget
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-3
"""

from nutrition.market_analysis import best_price_per_kg
from nutrition.pantry_analysis import plan_cost
from nutrition.person_analysis import _f, _rows


def _nutrient_per_100g(manager, nutrient):
    """{food: (amount_per_100g, unit)} for one nutrient."""
    out = {}
    for c in _rows(manager, 'NutrientContent'):
        if getattr(c, 'nutrient_name', '') != nutrient:
            continue
        out[getattr(c, 'food_name', '')] = (
            _f(c, 'amount_per_100g', 0.0), getattr(c, 'unit', ''))
    return out


def nutrient_value_report(manager, nutrient, today=None):
    """Amount-of-nutrient per dollar, per priced food, ranked."""
    contents = _nutrient_per_100g(manager, nutrient)
    if not contents:
        return {'ok': False,
                'error': f'no NutrientContent rows for '
                         f'"{nutrient}" — is it one of the nut-1 '
                         f'nutrient names?'}
    ranked, unpriced, zero = [], [], []
    unit = ''
    for food, (per100, food_unit) in sorted(contents.items()):
        unit = unit or food_unit
        if per100 <= 0:
            zero.append(food)
            continue
        price = best_price_per_kg(manager, food, today)
        if price is None:
            unpriced.append(food)
            continue
        # per kg: per100 × 10; per dollar: /$-per-kg.
        per_dollar = per100 * 10.0 / price['pricePerKg']
        ranked.append({
            'food': food,
            'perDollar': round(per_dollar, 2),
            'unit': food_unit,
            'per100g': per100,
            'pricePerKg': price['pricePerKg'],
            'priceLocation': price['location'],
            'priceAgeDays': price['ageDays'],
        })
    ranked.sort(key=lambda e: -e['perDollar'])
    return {'ok': True, 'schema': 'nutrient-value/1',
            'nutrient': nutrient, 'unit': unit,
            'ranked': ranked,
            'unpricedFoods': unpriced,
            'foodsWithoutNutrient': zero,
            'honesty': 'value-per-dollar exists ONLY for foods '
                       'with an observed price — enter prices and '
                       'the ranking grows; unpriced foods are '
                       'NAMED, never assumed cheap or dear'}


def cheapest_closers(manager, nutrient, gap_amount, today=None,
                     limit=5):
    """Cheapest ways to close a nutrient gap, arithmetic shown."""
    value = nutrient_value_report(manager, nutrient, today)
    if not value.get('ok'):
        return value
    if gap_amount <= 0:
        return {'ok': False,
                'error': 'gap_amount must be positive'}
    closers = []
    for entry in value['ranked']:
        grams_needed = gap_amount / entry['per100g'] * 100.0
        cost = grams_needed / 1000.0 * entry['pricePerKg']
        closers.append({
            'food': entry['food'],
            'gramsToClose': round(grams_needed, 1),
            'estCost': round(cost, 2),
            'at': entry['priceLocation'],
            'arithmetic': f'{gap_amount:g} {value["unit"]} ÷ '
                          f'{entry["per100g"]:g}/100g = '
                          f'{grams_needed:.0f} g × '
                          f'${entry["pricePerKg"]:g}/kg',
        })
    closers.sort(key=lambda e: e['estCost'])
    return {'ok': True, 'schema': 'cheapest-closers/1',
            'nutrient': nutrient, 'gapAmount': gap_amount,
            'unit': value['unit'],
            'closers': closers[:limit],
            'consideredFoods': len(value['ranked']),
            'unpricedFoods': value['unpricedFoods'],
            'honesty': 'a single-food arithmetic answer — real '
                       'meals mix foods; the affinity composer '
                       'decides FIT, this decides PRICE'}


def _budget_for(manager, plan):
    plan_name = getattr(plan, 'name', '')
    household = getattr(plan, 'household_name', '')
    plan_row = household_row = None
    for row in _rows(manager, 'PlanBudget'):
        if getattr(row, 'plan_name', '') == plan_name:
            plan_row = row
        elif household and getattr(row, 'household_name', '') \
                == household:
            household_row = row
    return plan_row or household_row


def plan_budget_report(manager, plan, today=None):
    """Spend vs cap for one plan."""
    cost = plan_cost(manager, plan, today)
    if not cost.get('ok'):
        return cost
    budget = _budget_for(manager, plan)
    days = max(1, int(getattr(plan, 'days', 7) or 7))
    report = {'ok': True, 'schema': 'plan-budget/1',
              'plan': cost['plan'],
              'estTotal': cost['estTotal'],
              'days': days,
              'estPerDay': round(cost['estTotal'] / days, 2),
              'topDrivers': cost['lines'][:5],
              'unpricedFoods': cost['unpricedFoods']}
    if budget is None:
        report['budget'] = None
        report['note'] = ('no PlanBudget row for this plan or its '
                          'household — add one to get the '
                          'envelope (a knob, not a requirement)')
        return report
    weekly = _f(budget, 'weekly_amount', 0.0)
    cap = weekly / 7.0 * days
    report['budget'] = {
        'name': getattr(budget, 'name', ''),
        'weeklyAmount': weekly,
        'capForPlanDays': round(cap, 2),
        'scopeNote': getattr(budget, 'scope_note', ''),
    }
    headroom = cap - cost['estTotal']
    report['headroom'] = round(headroom, 2)
    report['withinBudget'] = headroom >= 0
    if headroom >= 0:
        report['verdict'] = (f'within budget: ${headroom:.2f} '
                             f'headroom on the '
                             f'${cap:.2f} cap for {days} days')
    else:
        drivers = ', '.join(
            f"{l['food']} (${l['estCost']:.2f})"
            for l in cost['lines'][:3])
        report['verdict'] = (
            f'over budget by ${-headroom:.2f} — biggest drivers: '
            f'{drivers}. Swapping or shrinking those is YOUR '
            f'call; nothing is trimmed silently')
    report['honesty'] = ('estimates from observed prices × '
                         'approximate weights; unpriced foods are '
                         'excluded from the total AND named — the '
                         'real bill can be higher')
    return report
