"""
@cross-cutting
@module nutrition.pantry_analysis
@tags @xc:bindings

mpa-3 — plans vs the pantry vs the market (the "adjust plans based
on available food" + "minimizing cost" engines):

  pantry_stock            household pantry → grams per food (the
                          labeled weight priors resolve count units;
                          unresolvable lots are named, not dropped).
  plan_ingredient_demand  one MealPlan → grams per food (the same
                          per-meal portion arithmetic the rollup and
                          acidity use — one arithmetic, three
                          callers).
  plan_vs_pantry          demand − stock: covered / partial / to-buy
                          per food, coverage fraction per entry.
  shopping_list           the to-buy gap priced per geolocation:
                          per-food best store + one-store totals —
                          arithmetic shown, store choice is the
                          human's.
  plan_cost               demand × best observed $/kg → estimated
                          plan cost; unpriced foods NAMED (a cost
                          that silently skips foods is a lie).
  availability_suggestions  entries coverable now; variation swaps
                          that consume stock — SUGGESTIONS with the
                          numbers, never auto-applied (knobs-and-
                          suggestions).

@consumers
  - nutrition.mealplanning_api, tracking dashboards
  - nutrition.selftest_pantry
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-3
"""

import json

from nutrition.acidity_analysis import template_portions
from nutrition.market_analysis import (
    best_price_per_kg, normalized_prices, resolve_grams,
)
from nutrition.person_analysis import _f, _rows


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def pantry_stock(manager, household_name):
    """{food: grams} + per-lot detail for one household."""
    lots, unresolved = [], []
    totals = {}
    for item in _rows(manager, 'PantryItem'):
        if getattr(item, 'household_name', '') != household_name:
            continue
        food = getattr(item, 'food_name', '')
        grams = resolve_grams(manager, food,
                              _f(item, 'quantity', 0.0),
                              getattr(item, 'unit', ''),
                              household_name)
        if not grams.get('ok'):
            unresolved.append({'item': getattr(item, 'name', ''),
                               'food': food,
                               'why': grams.get('error')})
            continue
        totals[food] = totals.get(food, 0.0) + grams['grams']
        lots.append({'item': getattr(item, 'name', ''),
                     'food': food,
                     'grams': round(grams['grams'], 1),
                     'weightBasis': grams['basis'],
                     'storage': getattr(item, 'storage_state', ''),
                     'acquiredDate': getattr(item, 'acquired_date',
                                             '')})
    return {'ok': True, 'household': household_name,
            'stockG': {f: round(g, 1)
                       for f, g in sorted(totals.items())},
            'lots': lots, 'unresolved': unresolved}


def plan_ingredient_demand(manager, plan):
    """{food: grams} the whole plan needs (entries × per-meal
    portions, swaps + scale applied)."""
    entries = [e for e in _rows(manager, 'MealEntry')
               if getattr(e, 'plan_name', '')
               == getattr(plan, 'name', '')]
    if not entries:
        return {'ok': False, 'error': 'plan has no MealEntries'}
    demand, per_entry, problems = {}, [], []
    for entry in entries:
        template = _named(manager, 'MealTemplate',
                          getattr(entry, 'template_name', ''))
        if template is None:
            problems.append({'entry': getattr(entry, 'name', ''),
                             'why': 'no such MealTemplate'})
            continue
        variation = None
        if getattr(entry, 'variation_name', ''):
            variation = _named(manager, 'VariationDefinition',
                               entry.variation_name)
        portions = template_portions(manager, template, variation,
                                     _f(entry, 'scale', 1.0))
        entry_foods = {}
        for p in portions:
            demand[p['food_name']] = (demand.get(p['food_name'], 0.0)
                                      + p['grams'])
            entry_foods[p['food_name']] = (
                entry_foods.get(p['food_name'], 0.0) + p['grams'])
        per_entry.append({'entry': getattr(entry, 'name', ''),
                          'day': getattr(entry, 'day_index', 0),
                          'slot': getattr(entry, 'slot', ''),
                          'foodsG': {f: round(g, 1) for f, g
                                     in sorted(entry_foods.items())}})
    return {'ok': True, 'plan': getattr(plan, 'name', ''),
            'demandG': {f: round(g, 1)
                        for f, g in sorted(demand.items())},
            'entries': per_entry, 'problems': problems}


def plan_vs_pantry(manager, plan, household_name):
    """Demand − stock, per food and per entry."""
    demand = plan_ingredient_demand(manager, plan)
    if not demand.get('ok'):
        return demand
    stock = pantry_stock(manager, household_name)
    foods = []
    for food, need in demand['demandG'].items():
        have = stock['stockG'].get(food, 0.0)
        foods.append({
            'food': food, 'needG': need,
            'haveG': round(have, 1),
            'toBuyG': round(max(0.0, need - have), 1),
            'status': ('covered' if have >= need else
                       'partial' if have > 0 else 'missing'),
        })
    remaining = dict(stock['stockG'])
    entry_reports = []
    for entry in demand['entries']:
        coverable = True
        for food, need in entry['foodsG'].items():
            if remaining.get(food, 0.0) < need:
                coverable = False
        if coverable:
            for food, need in entry['foodsG'].items():
                remaining[food] = remaining.get(food, 0.0) - need
        entry_reports.append({**entry, 'coverableNow': coverable})
    return {'ok': True, 'schema': 'plan-availability/1',
            'plan': demand['plan'], 'household': household_name,
            'foods': foods,
            'entries': entry_reports,
            'entriesCoverableNow': sum(
                1 for e in entry_reports if e['coverableNow']),
            'pantryUnresolved': stock['unresolved'],
            'honesty': 'entry coverability walks entries in plan '
                       'order against a depleting pantry copy — an '
                       'allocation convention, not an optimum; the '
                       'per-food gap table is the ground truth'}


def shopping_list(manager, plan, household_name, today=None):
    """The to-buy gap, priced per location."""
    avail = plan_vs_pantry(manager, plan, household_name)
    if not avail.get('ok'):
        return avail
    to_buy = [f for f in avail['foods'] if f['toBuyG'] > 0]
    all_prices = normalized_prices(manager, None, today)['prices']
    by_food = {}
    for p in all_prices:
        by_food.setdefault(p['food'], []).append(p)
    lines, unpriced = [], []
    store_totals = {}
    for gap in to_buy:
        options = []
        for p in by_food.get(gap['food'], []):
            cost = p['pricePerKg'] * gap['toBuyG'] / 1000.0
            options.append({'location': p['location'],
                            'pricePerKg': p['pricePerKg'],
                            'estCost': round(cost, 2),
                            'ageDays': p['ageDays'],
                            'isDemo': p['isDemo']})
            store_totals.setdefault(p['location'], 0.0)
        options.sort(key=lambda o: o['estCost'])
        line = {'food': gap['food'], 'toBuyG': gap['toBuyG'],
                'options': options}
        if options:
            line['best'] = options[0]
        else:
            unpriced.append(gap['food'])
        lines.append(line)
    # one-store totals: only stores that price EVERY priced line
    for store in list(store_totals):
        total, complete = 0.0, True
        for line in lines:
            opts = [o for o in line['options']
                    if o['location'] == store]
            if not opts:
                complete = False
                break
            total += opts[0]['estCost']
        if complete and lines:
            store_totals[store] = round(total, 2)
        else:
            store_totals.pop(store, None)
    best_anywhere = round(
        sum(l['best']['estCost'] for l in lines if 'best' in l), 2)
    return {'ok': True, 'schema': 'shopping-list/1',
            'plan': avail['plan'], 'household': household_name,
            'lines': lines,
            'bestAnywhereTotal': best_anywhere,
            'oneStoreTotals': store_totals,
            'unpricedFoods': unpriced,
            'honesty': 'costs are estimates from user-entered price '
                       'observations × approximate weights; '
                       'unpriced foods are NAMED — the total only '
                       'covers priced lines'}


def plan_cost(manager, plan, today=None):
    """Estimated cost of the WHOLE plan at best observed prices
    (ignoring pantry — the what-would-this-week-cost number)."""
    demand = plan_ingredient_demand(manager, plan)
    if not demand.get('ok'):
        return demand
    lines, unpriced, total = [], [], 0.0
    for food, grams in demand['demandG'].items():
        price = best_price_per_kg(manager, food, today)
        if price is None:
            unpriced.append(food)
            continue
        cost = price['pricePerKg'] * grams / 1000.0
        total += cost
        lines.append({'food': food, 'gramsNeeded': grams,
                      'pricePerKg': price['pricePerKg'],
                      'location': price['location'],
                      'estCost': round(cost, 2)})
    lines.sort(key=lambda l: -l['estCost'])
    return {'ok': True, 'schema': 'plan-cost/1',
            'plan': demand['plan'],
            'estTotal': round(total, 2),
            'lines': lines,
            'unpricedFoods': unpriced,
            'honesty': 'best observed price per food × approximate '
                       'demand; unpriced foods NAMED and excluded '
                       'from the total'}


def availability_suggestions(manager, plan, household_name):
    """Swaps that consume stock — suggestions with numbers, never
    applied."""
    avail = plan_vs_pantry(manager, plan, household_name)
    if not avail.get('ok'):
        return avail
    stock = {f['food']: f['haveG'] for f in avail['foods']}
    stock_all = pantry_stock(manager, household_name)['stockG']
    missing = {f['food'] for f in avail['foods']
               if f['status'] == 'missing'}
    suggestions = []
    for entry in _rows(manager, 'MealEntry'):
        if getattr(entry, 'plan_name', '') != avail['plan']:
            continue
        tname = getattr(entry, 'template_name', '')
        current = getattr(entry, 'variation_name', '')
        for variation in _rows(manager, 'VariationDefinition'):
            if getattr(variation, 'template_name', '') != tname:
                continue
            vname = getattr(variation, 'name', '')
            if vname == current:
                continue
            try:
                swaps = json.loads(
                    getattr(variation, 'swaps_json', '[]') or '[]')
            except ValueError:
                continue
            for sw in swaps:
                frm, to = sw.get('from_food', ''), sw.get('to_food',
                                                          '')
                if frm in missing and stock_all.get(to, 0.0) > 0:
                    suggestions.append({
                        'entry': getattr(entry, 'name', ''),
                        'switchToVariation': vname,
                        'because': f'"{frm}" is not in the pantry; '
                                   f'"{to}" is '
                                   f'({stock_all[to]:g} g on hand)',
                        'appliedBy': 'you — suggestions never edit '
                                     'the plan',
                    })
    return {'ok': True, 'schema': 'availability-suggestions/1',
            'plan': avail['plan'], 'household': household_name,
            'suggestions': suggestions,
            'entriesCoverableNow': avail['entriesCoverableNow'],
            'honesty': 'knobs-and-suggestions: the plan is yours; '
                       'these are arithmetic-backed options, not '
                       'edits'}
