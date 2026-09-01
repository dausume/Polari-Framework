"""
@module nutrition.selftest_condition

mpb-2 selftest — stated-condition steering: declarations resolve
their steering rows (unknown conditions get an honest note), a
fatty meal flags a stated reflux via the cited fat-load row, a
rice-heavy meal flags glycemic sensitivity via GL, FODMAP asks
land as NAMED data gaps (never guesses), nothing blocks, and the
ratified no-diagnosis posture rides every payload.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_condition
"""

from types import SimpleNamespace

from foodstate.food_ph_seed import SEED_FOOD_PH_CLAIMS
from nutrition.condition_basis import (
    POSTURE, SEED_CONDITION_STEERINGS, SEED_STATED_CONDITIONS,
)
from nutrition.condition_analysis import (
    meal_condition_report, person_conditions, plan_condition_report,
)
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.meal_basis import (SEED_MEAL_ENTRIES,
                                  SEED_MEAL_PLANS,
                                  SEED_MEAL_TEMPLATES,
                                  SEED_VARIATIONS)
from nutrition.person_seed import SEED_PERSONS
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from nutrition.tolerance_basis import SEED_TOLERANCE_THRESHOLDS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


# test recipes: a fat-bomb and a rice mountain (2 servings each so
# per-meal halves them).
TEST_RECIPES = list(SEED_RECIPES) + [
    {'name': 'fat-test', 'display_name': 'Fat test',
     'servings': 1.0, 'origin': 'test', 'is_prior': True,
     'provenance_id': 't', 'notes': ''},
    {'name': 'rice-test', 'display_name': 'Rice test',
     'servings': 1.0, 'origin': 'test', 'is_prior': True,
     'provenance_id': 't', 'notes': ''},
]
TEST_LINES = list(SEED_INGREDIENT_LINES) + [
    {'name': 'ft-1', 'recipe_name': 'fat-test',
     'food_name': 'chicken-breast-raw', 'grams': 200.0,
     'method': 'raw', 'yield_percent': 100.0,
     'retention_code': '', 'prep_note': '', 'order': 1},
    {'name': 'ft-2', 'recipe_name': 'fat-test',
     'food_name': 'olive-oil', 'grams': 60.0, 'method': 'raw',
     'yield_percent': 100.0, 'retention_code': '', 'prep_note': '',
     'order': 2},
    {'name': 'rt-1', 'recipe_name': 'rice-test',
     'food_name': 'rice-white-raw', 'grams': 300.0,
     'method': 'boiled', 'yield_percent': 280.0,
     'retention_code': '0432', 'prep_note': '', 'order': 1},
]
TEST_TEMPLATES = list(SEED_MEAL_TEMPLATES) + [
    {'name': 'fat-test-meal', 'display_name': 'Fat test meal',
     'description': '', 'recipe_names_json': '["fat-test"]',
     'slots_json': '["dinner"]', 'dish_base': '',
     'is_prior': True, 'provenance_id': 't', 'notes': ''},
    {'name': 'rice-test-meal', 'display_name': 'Rice test meal',
     'description': '', 'recipe_names_json': '["rice-test"]',
     'slots_json': '["dinner"]', 'dish_base': '',
     'is_prior': True, 'provenance_id': 't', 'notes': ''},
]
CONDITIONS = list(SEED_STATED_CONDITIONS) + [
    {'name': 'dana-glycemic', 'person_name': 'test-dana',
     'condition': 'glycemic-sensitive',
     'stated_reason': 'stated spike sensitivity',
     'declared_date': '2026-09-01', 'is_prior': False},
    {'name': 'dana-fodmap', 'person_name': 'test-dana',
     'condition': 'fodmap-sensitive',
     'stated_reason': 'stated FODMAP sensitivity',
     'declared_date': '2026-09-01', 'is_prior': False},
    {'name': 'lee-mystery', 'person_name': 'test-lee',
     'condition': 'chronic-mystery',
     'stated_reason': 'stated', 'declared_date': '', 'is_prior':
     False},
]

MANAGER = SimpleNamespace(objectTables={
    'ConditionSteering': _rows(SEED_CONDITION_STEERINGS),
    'StatedCondition': _rows(CONDITIONS),
    'PersonProfile': _rows(SEED_PERSONS),
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
    'Recipe': _rows(TEST_RECIPES),
    'IngredientLine': _rows(TEST_LINES),
    'MealTemplate': _rows(TEST_TEMPLATES),
    'VariationDefinition': _rows(SEED_VARIATIONS),
    'MealPlanDefinition': _rows(SEED_MEAL_PLANS),
    'MealEntry': _rows(SEED_MEAL_ENTRIES),
    'ToleranceThreshold': _rows(SEED_TOLERANCE_THRESHOLDS),
    'PropertyClaim': _rows(SEED_FOOD_PH_CLAIMS),
})

print('mpb-2: stated-condition steering')

# declarations resolve
conds = person_conditions(MANAGER, 'demo-alex')
check('demo reflux declaration resolves its steering row',
      len(conds) == 1 and conds[0]['steering'] is not None
      and 'meal-acidity' in
      conds[0]['steering']['aggravatorSubstances'])
lee = person_conditions(MANAGER, 'test-lee')
check('unknown condition gets the honest not-steerable note',
      lee[0]['steering'] is None
      and 'not steerable' in lee[0]['note'])

# the fat bomb flags stated reflux via the cited fat-load row
fat = meal_condition_report(MANAGER, 'demo-alex', 'fat-test-meal')
check('fatty meal flags stated reflux (fat-load > 40 g row)',
      fat['ok'] and fat['anyLikelyAggravating']
      and any(a['substance'] == 'meal-fat-load'
              and a['likelyAggravating']
              for a in fat['conditions'][0]['aggravators']))
check('the flag carries evidence + confidence, and the wording '
      'is do-not-worsen (never diagnosis)',
      'aggravate your stated reflux' in
      fat['conditions'][0]['verdict']
      and all(a['confidence'] for a in
              fat['conditions'][0]['aggravators']))
check('posture rides the payload',
      fat['posture'] == POSTURE and 'never diagnosed' in POSTURE)

# a normal bowl does not flag
bowl = meal_condition_report(MANAGER, 'demo-alex',
                             'chicken-bowl-dinner',
                             'chicken-bowl-dinner-base')
check('the ordinary bowl does not aggravate stated reflux',
      bowl['ok'] and not bowl['anyLikelyAggravating'])

# glycemic + FODMAP for test-dana on the rice mountain
rice = meal_condition_report(MANAGER, 'test-dana', 'rice-test-meal')
glyc = [c for c in rice['conditions']
        if c['condition'] == 'glycemic-sensitive'][0]
fod = [c for c in rice['conditions']
       if c['condition'] == 'fodmap-sensitive'][0]
check('rice mountain flags stated glycemic sensitivity (GL row)',
      glyc['likelyAggravating']
      and any(a['substance'] == 'glycemic-load'
              and a['likelyAggravating']
              for a in glyc['aggravators']))
check('FODMAP substances land as NAMED data gaps, not guesses',
      len(fod['dataGaps']) >= 3
      and all('NAMED gap' in g['why'] for g in fod['dataGaps']
              if g['substance'] != '(meal metrics)'))
check('no-stated-conditions person gets nothing-to-steer',
      meal_condition_report(MANAGER, 'nobody-here',
                            'chicken-bowl-dinner')['verdict']
      .startswith('no stated conditions'))

# plan-level flags: demo plan for demo-alex (reflux) — ordinary
# meals, nothing flagged; verdict language never blocks.
plan = SimpleNamespace(**SEED_MEAL_PLANS[0])
pr = plan_condition_report(MANAGER, plan)
check('plan report runs per entry', pr['ok']
      and len(pr['entries']) == len(SEED_MEAL_ENTRIES))
check('flags are for YOUR call — nothing blocked',
      'never blocked' in pr['verdict']
      or pr['entriesLikelyAggravating'] == 0)
check('plan posture present', pr['posture'] == POSTURE)

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpb-2 condition steering holds together')
