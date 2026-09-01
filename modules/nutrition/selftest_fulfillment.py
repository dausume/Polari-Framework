"""
@module nutrition.selftest_fulfillment

nmp-7 selftest (the nut-5 acceptance, meal-plan-aware): the demo
garden covers what it can, uncoverable nutrients (iodine/sodium/
chloride/B12) always point at their real source, removing a
planting opens a named gap with a counted planting suggestion, and
the demand source can be a MEAL PLAN's actual rollup (the nmp-7
upgrade) — labeled which.

Run from polari-framework/:  python3 -m nutrition.selftest_fulfillment
"""

import json
from types import SimpleNamespace

from nutrition.dri_seed import SEED_DRI_REFERENCES
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.food_seed import SEED_FOOD_ITEMS, SEED_NUTRIENT_CONTENTS
from nutrition.fulfillment_basis import SEED_GARDEN_PLANS
from nutrition.fulfillment_analysis import coverage, suggest_plantings
from nutrition.meal_basis import (SEED_MEAL_TEMPLATES,
                                  SEED_VARIATIONS)
from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
from nutrition.person_seed import SEED_HOUSEHOLDS, SEED_PERSONS
from nutrition.recipe_basis import (SEED_INGREDIENT_LINES,
                                    SEED_RECIPES)
from nutrition.threshold_basis import SEED_EATING_PATTERNS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


# the aqp plant stand-ins the nut-2 seeds reference (mature volumes
# big enough that the demo garden supplies real mass)
PLANT_PARTS = [
    {'name': 'sweet-basil-leaf', 'dry_matter_fraction': 0.1,
     'dry_density_g_cm3': 0.3, 'mature_volume_cm3': 40.0},
    {'name': 'kale-leaf', 'dry_matter_fraction': 0.12,
     'dry_density_g_cm3': 0.3, 'mature_volume_cm3': 120.0},
]

PLAN = {'name': 'test-week', 'person_name': 'demo-alex',
        'household_name': '', 'days': 1, 'start_date': ''}
ENTRIES = [
    {'name': 'tw-d1-dinner', 'plan_name': 'test-week', 'day_index': 1,
     'slot': 'dinner', 'template_name': 'chicken-bowl-dinner',
     'variation_name': '', 'scale': 1.0, 'time_hhmm': '',
     'serving_split_json': ''},
]


def _mgr(plantings=None, meal_plan=''):
    plans = [dict(SEED_GARDEN_PLANS[0])]
    if plantings is not None:
        plans[0]['plantings_json'] = json.dumps(plantings)
    if meal_plan:
        plans[0]['meal_plan_name'] = meal_plan
    return SimpleNamespace(objectTables={
        'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
        'NutrientReference': _rows(SEED_DRI_REFERENCES),
        'PersonProfile': _rows(SEED_PERSONS),
        'HouseholdProfile': _rows(SEED_HOUSEHOLDS),
        'FoodItem': _rows(SEED_FOOD_ITEMS + SEED_FDC_FOOD_ITEMS),
        'NutrientContent': _rows(SEED_NUTRIENT_CONTENTS
                                 + SEED_FDC_NUTRIENT_CONTENTS),
        'PlantPart': _rows(PLANT_PARTS),
        'GardenPlanDefinition': _rows(plans),
        'Recipe': _rows(SEED_RECIPES),
        'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
        'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows([PLAN]),
        'MealEntry': _rows(ENTRIES),
        'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
        'PersonThreshold': {},
    })


def main():
    m = _mgr()
    print('nmp-7 coverage (household demand)')
    c = coverage(m, 'starter-garden', 'week')
    check('coverage runs against household needs',
          c['ok'] and 'household' in c['demandSource'])
    check('statuses partition met/partial/gap/uncoverable',
          all(r['status'] in ('met', 'partial', 'gap', 'uncoverable')
              for r in c['coverage'].values()))
    for nut in ('iodine', 'sodium', 'chloride', 'vitamin-b12'):
        row = c['coverage'].get(nut)
        check(f'{nut} UNCOVERABLE, real source named',
              row is not None and row['status'] == 'uncoverable'
              and row.get('source'))
    check('limiting nutrient named (and not an uncoverable one)',
          c['limitingNutrient'] is not None
          and c['coverage'][c['limitingNutrient']]['status']
          != 'uncoverable')

    print('nmp-7 gaps + suggestions')
    ck = coverage(_mgr(plantings={'basil-leaf': 6}), 'starter-garden',
                  'week')
    k_before = c['coverage'].get('vitamin-k', {}).get('ratio', 0)
    k_after = ck['coverage'].get('vitamin-k', {}).get('ratio', 0)
    check('removing kale drops vitamin-k coverage',
          k_after < k_before, f'{k_after} !< {k_before}')
    sg = suggest_plantings(_mgr(plantings={'basil-leaf': 6}),
                           'starter-garden', 'week')
    vk = next((s for s in sg['suggestions']
               if s['nutrient'] == 'vitamin-k'), None)
    check('suggestion names the best food + a plant count, '
          'arithmetic shown',
          vk is not None and vk.get('morePlants', 0) >= 1
          and 'yields' in vk.get('evidence', ''))
    check('nothing is planted for you (suggestion wording)',
          vk is not None and 'nothing is planted' in vk['note'])
    check('uncoverable list rides the suggestions too',
          any(u['nutrient'] == 'iodine' for u in sg['uncoverable']))

    print('nmp-7 meal-plan demand (the upgrade)')
    cm = coverage(_mgr(meal_plan='test-week'), 'starter-garden',
                  'week')
    check('demand source = the meal plan, labeled',
          cm['ok'] and 'meal plan' in cm['demandSource'])
    check('meal-plan demand differs from household needs '
          '(it is the actual plan, not generic needs)',
          cm['coverage'].get('protein', {}).get('demand')
          != c['coverage'].get('protein', {}).get('demand'))
    bad = coverage(_mgr(meal_plan='no-such'), 'starter-garden')
    check('missing meal plan refuses honestly', not bad['ok'])
    bad2 = coverage(m, 'no-such-garden')
    check('missing garden plan refuses honestly', not bad2['ok'])

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-7 garden loop holds together')


if __name__ == '__main__':
    main()
