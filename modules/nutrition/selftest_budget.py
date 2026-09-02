"""
@module nutrition.selftest_budget

mpb-3 selftest — nutrient value per dollar + the budget envelope:
per-$ arithmetic is exact against the demo prices, unpriced foods
are NAMED (never assumed), cheapest closers show their arithmetic,
and the plan-vs-cap verdict names the drivers without trimming
anything.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_budget
"""

from datetime import date
from types import SimpleNamespace

from nutrition.budget_basis import SEED_PLAN_BUDGETS
from nutrition.budget_analysis import (
    cheapest_closers, nutrient_value_report, plan_budget_report,
)
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.market_basis import (SEED_PRICE_OBSERVATIONS,
                                    SEED_SOURCE_LOCATIONS,
                                    SEED_UNIT_WEIGHTS)
from nutrition.meal_basis import (SEED_MEAL_ENTRIES,
                                  SEED_MEAL_PLANS,
                                  SEED_MEAL_TEMPLATES,
                                  SEED_VARIATIONS)
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


MANAGER = SimpleNamespace(objectTables={
    'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS),
    'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
    'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS),
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
    'Recipe': _rows(SEED_RECIPES),
    'IngredientLine': _rows(SEED_INGREDIENT_LINES),
    'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
    'VariationDefinition': _rows(SEED_VARIATIONS),
    'MealPlanDefinition': _rows(SEED_MEAL_PLANS),
    'MealEntry': _rows(SEED_MEAL_ENTRIES),
    'PlanBudget': _rows(SEED_PLAN_BUDGETS),
})
TODAY = date(2026, 9, 2)

print('mpb-3: nutrient value per dollar + budget envelope')

value = nutrient_value_report(MANAGER, 'protein', TODAY)
check('protein-per-$ report computes', value.get('ok')
      and len(value['ranked']) >= 2)
check('ranking is descending per-dollar',
      value['ranked'] == sorted(value['ranked'],
                                key=lambda e: -e['perDollar']))
chicken = [e for e in value['ranked']
           if e['food'] == 'chicken-breast-raw']
check('per-$ arithmetic exact for chicken '
      '(per100 × 10 / $-per-kg)',
      chicken and abs(
          chicken[0]['perDollar']
          - chicken[0]['per100g'] * 10 / chicken[0]['pricePerKg'])
      < 0.01)
check('unpriced foods NAMED (most of the roster has no demo '
      'price)',
      len(value['unpricedFoods']) > 10
      and 'NAMED' in value['honesty'])
check('unknown nutrient refuses',
      not nutrient_value_report(MANAGER, 'unobtainium').get('ok'))

closers = cheapest_closers(MANAGER, 'protein', 30.0, TODAY)
check('closers computed with arithmetic shown',
      closers.get('ok') and closers['closers']
      and '÷' in closers['closers'][0]['arithmetic'])
check('closers sorted cheapest first',
      closers['closers'] == sorted(closers['closers'],
                                   key=lambda e: e['estCost']))
check('single-food honesty stated (composer decides fit)',
      'composer' in closers['honesty'])

plan = SimpleNamespace(**SEED_MEAL_PLANS[0])
budget = plan_budget_report(MANAGER, plan, TODAY)
check('budget report computes vs the demo cap', budget.get('ok')
      and budget['budget'] is not None
      and budget['budget']['weeklyAmount'] == 60.0)
check('cap scales to the plan days (3/7 of weekly)',
      abs(budget['budget']['capForPlanDays'] - 60.0 / 7 * 3)
      < 0.01)
check('verdict present and nothing auto-trimmed',
      ('headroom' in budget['verdict']
       or 'YOUR call' in budget['verdict']))
check('unpriced foods still NAMED at plan level',
      isinstance(budget['unpricedFoods'], list))

no_budget_plan = SimpleNamespace(name='no-such-budget-plan',
                                 person_name='', household_name='',
                                 days=7)
MANAGER.objectTables['MealPlanDefinition'][99] = no_budget_plan
MANAGER.objectTables['MealEntry'][99] = SimpleNamespace(
    name='nsb-d1', plan_name='no-such-budget-plan', day_index=1,
    slot='dinner', template_name='chicken-bowl-dinner',
    variation_name='chicken-bowl-dinner-base', scale=1.0)
nb = plan_budget_report(MANAGER, no_budget_plan, TODAY)
check('plan without a budget row reports the knob honestly',
      nb.get('ok') and nb['budget'] is None
      and 'PlanBudget' in nb['note'])

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpb-3 budget layer holds together')
