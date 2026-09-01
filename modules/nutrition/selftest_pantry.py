"""
@module nutrition.selftest_pantry

mpa-3 selftest — pantry vs plan vs market: stock resolves through
the weight priors, demand matches the rollup arithmetic, the gap
table splits covered/partial/missing, the shopping list prices the
gap per store (unpriced foods NAMED), plan cost excludes-and-names
unpriced foods, and availability suggestions cite stock without
ever editing the plan.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_pantry
"""

from datetime import date
from types import SimpleNamespace

from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.market_basis import (
    SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS,
    SEED_UNIT_WEIGHTS,
)
from nutrition.meal_basis import SEED_MEAL_TEMPLATES, SEED_VARIATIONS
from nutrition.pantry_basis import SEED_PANTRY_ITEMS
from nutrition.pantry_analysis import (
    availability_suggestions, pantry_stock, plan_cost,
    plan_ingredient_demand, plan_vs_pantry, shopping_list,
)
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


# 4 dinners: chicken demand 4 × 150 g = 600 g vs the 1 lb
# (453.6 g) freezer lot → genuinely PARTIAL; broccoli is missing
# AND unpriced → exercises the honest-naming paths.
PLAN = SimpleNamespace(name='test-week', person_name='',
                       household_name='demo-household', days=4)
ENTRIES = [
    {'name': f'test-week-d{i}-dinner', 'plan_name': 'test-week',
     'day_index': i, 'slot': 'dinner',
     'template_name': 'chicken-bowl-dinner',
     'variation_name': 'chicken-bowl-dinner-base', 'scale': 1.0}
    for i in (1, 2, 3, 4)
]

MANAGER = SimpleNamespace(objectTables={
    'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS),
    'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
    'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS),
    'PantryItem': _rows(SEED_PANTRY_ITEMS),
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
    'Recipe': _rows(SEED_RECIPES),
    'IngredientLine': _rows(SEED_INGREDIENT_LINES),
    'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
    'VariationDefinition': _rows(SEED_VARIATIONS),
    'MealEntry': _rows(ENTRIES),
    'MealPlanDefinition': _rows([vars(PLAN)]),
})
TODAY = date(2026, 9, 2)

print('mpa-3: pantry / availability / cost')

stock = pantry_stock(MANAGER, 'demo-household')
check('stock resolves count units through priors (8 eggs = 400 g)',
      abs(stock['stockG'].get('egg-whole-raw', 0) - 400.0) < 0.1)
check('exact units pass through (2 kg rice)',
      abs(stock['stockG'].get('rice-white-raw', 0) - 2000.0) < 0.1)
check('lots carry storage + weight basis',
      all('storage' in l and 'weightBasis' in l for l in
          stock['lots']))

demand = plan_ingredient_demand(MANAGER, PLAN)
check('demand computes per food', demand.get('ok')
      and demand['demandG'].get('chicken-breast-raw', 0) > 0)
check('four identical dinners quadruple the demand',
      abs(demand['demandG']['chicken-breast-raw']
          - 4 * demand['entries'][0]['foodsG']['chicken-breast-raw'])
      < 0.1)

avail = plan_vs_pantry(MANAGER, PLAN, 'demo-household')
check('gap table splits statuses', avail.get('ok') and
      {f['status'] for f in avail['foods']} <=
      {'covered', 'partial', 'missing'})
rice = [f for f in avail['foods']
        if f['food'] == 'rice-white-raw'][0]
check('rice fully covered by the 2 kg lot (toBuy 0)',
      rice['status'] == 'covered' and rice['toBuyG'] == 0)
chicken = [f for f in avail['foods']
           if f['food'] == 'chicken-breast-raw'][0]
check('chicken partial: 454 g on hand vs 600 g 4-dinner demand',
      chicken['status'] == 'partial'
      and abs(chicken['toBuyG'] - (600.0 - 453.592)) < 0.5)
broccoli = [f for f in avail['foods']
            if f['food'] == 'broccoli-raw'][0]
check('broccoli missing entirely',
      broccoli['status'] == 'missing')

slist = shopping_list(MANAGER, PLAN, 'demo-household', TODAY)
check('shopping list prices the gap', slist.get('ok')
      and any(l['food'] == 'chicken-breast-raw' and 'best' in l
              for l in slist['lines']))
check('unpriced foods are NAMED (broccoli has no observation)',
      'broccoli-raw' in slist['unpricedFoods']
      and 'NAMED' in slist['honesty'])
chicken_line = [l for l in slist['lines']
                if l['food'] == 'chicken-breast-raw'][0]
check('gap cost = toBuy grams × best $/kg',
      abs(chicken_line['best']['estCost']
          - chicken['toBuyG'] / 1000.0 * 11.98 / 0.907184) < 0.05)

cost = plan_cost(MANAGER, PLAN, TODAY)
check('plan cost totals priced lines, names the rest',
      cost.get('ok') and cost['estTotal'] > 0
      and isinstance(cost['unpricedFoods'], list))
check('cost lines sorted by impact',
      cost['lines'] == sorted(cost['lines'],
                              key=lambda l: -l['estCost']))

sugg = availability_suggestions(MANAGER, PLAN, 'demo-household')
check('suggestions engine runs and never edits (appliedBy = you)',
      sugg.get('ok') and all('you' in s['appliedBy']
                             for s in sugg['suggestions']))

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpa-3 pantry/availability/cost holds together')
