"""
@module nutrition.selftest_acidity

mpa-1 selftest — meal acidity: pH claims resolve per ingredient,
the acid mass share uses the FDA 4.6 boundary, unknowns are named
(never guessed), the decision-9 tolerance row fires past a half-
acid meal, straddling ranges are flagged, and NO combined meal pH
exists anywhere in the payload.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_acidity
"""

from types import SimpleNamespace

from foodstate.food_ph_seed import SEED_FOOD_PH_CLAIMS
from nutrition.acidity_analysis import (
    HIGH_ACID_PH_BOUNDARY, food_ph_claims, meal_acidity,
    template_acidity,
)
from nutrition.meal_basis import SEED_MEAL_TEMPLATES, SEED_VARIATIONS
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


MANAGER = SimpleNamespace(objectTables={
    'PropertyClaim': _rows(SEED_FOOD_PH_CLAIMS),
    'ToleranceThreshold': _rows(SEED_TOLERANCE_THRESHOLDS),
    'Recipe': _rows(SEED_RECIPES),
    'IngredientLine': _rows(SEED_INGREDIENT_LINES),
    'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
    'VariationDefinition': _rows(SEED_VARIATIONS),
})

print('mpa-1: meal acidity')

claims = food_ph_claims(MANAGER)
check('pH claims resolve by slug (tomato present)',
      'tomato-raw' in claims and claims['tomato-raw']['ph'] == 4.6)
check('ranges ride the claims', claims['tomato-raw']['range']
      == [4.30, 4.90])
check('boundary is the FDA 21 CFR 114 line',
      HIGH_ACID_PH_BOUNDARY == 4.6)

# a half-acid meal: 200 g strawberries + 200 g chicken
report = meal_acidity(MANAGER, [
    {'food_name': 'strawberries-raw', 'grams': 200},
    {'food_name': 'chicken-breast-raw', 'grams': 200},
])
check('meal acidity ok', report.get('ok'))
check('acid share = strawberry half of the mass',
      abs(report['acidMassShare'] - 0.5) < 1e-9)
check('no combined meal pH anywhere (pH does not average)',
      'mealPh' not in report and 'ph' not in report)
check('honesty says why', 'logarithmic' in report['honesty'])

# crossing the seeded meal-acid-share row (threshold 0.5) fires
over = meal_acidity(MANAGER, [
    {'food_name': 'strawberries-raw', 'grams': 300},
    {'food_name': 'chicken-breast-raw', 'grams': 100},
])
check('decision-9 warning fires past the seeded share row',
      any(w['substance'] == 'meal-acidity' for w in over['warnings'])
      and over['warnings'][0]['confidence'] == 'low')
check('under-threshold meal carries no acid warning',
      not any(w['substance'] == 'meal-acidity'
              for w in report['warnings']))

# unknowns are named, never guessed
unk = meal_acidity(MANAGER, [
    {'food_name': 'olive-oil', 'grams': 30},
    {'food_name': 'tomato-raw', 'grams': 100},
])
check('foods without pH claims land in unknownPh (olive oil)',
      unk['unknownPh'] == ['olive-oil'])
check('unknown mass still counts in the denominator (share '
      'honest-low, not inflated)',
      abs(unk['acidMassShare'] - 100.0 / 130.0) < 1e-3)

# straddling ranges are flagged
tom = [i for i in unk['ingredients'] if i['food'] == 'tomato-raw']
check('tomato straddle (4.30-4.90) is flagged with the midpoint '
      'classification note',
      tom and 'straddles' in tom[0].get('note', ''))

# per-template acidity
template = SimpleNamespace(**[t for t in SEED_MEAL_TEMPLATES
                              if t['name'] == 'chicken-bowl-dinner'][0])
ta = template_acidity(MANAGER, template)
check('template acidity computes over per-meal portions',
      ta.get('ok') and ta['template'] == 'chicken-bowl-dinner'
      and ta['totalMassG'] > 0)
check('unverified transcriptions carry their label',
      any('TRANSCRIBED' in (c.get('provenance_id', '')
                            + c.get('confidence_json', ''))
          for c in SEED_FOOD_PH_CLAIMS
          if c['subject_state_key'].startswith('chicken-')))

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpa-1 meal acidity holds together')
