"""
@module nutrition.selftest_coverage

mpb-6 selftest — coverage steering over time: averages ride LOGGED
days only (gap days named, never zeros), under-target uses the
labeled 80% convention, steering finds priced closers with their
arithmetic, declared exclusions remove closers BY NAME, and
nutrients without priced closers say so instead of vanishing.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_coverage
"""

from datetime import date
from types import SimpleNamespace

from foodstate.food_ph_seed import SEED_FOOD_PH_CLAIMS
from nutrition.coverage_analysis import (coverage_steering,
                                         rolling_coverage)
from nutrition.dri_seed import SEED_DRI_REFERENCES
from nutrition.exclusion_basis import SEED_FOOD_ALLERGEN_FLAGS
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.intake_basis import SEED_INTAKE_RECORDS
from nutrition.market_basis import (SEED_PRICE_OBSERVATIONS,
                                    SEED_SOURCE_LOCATIONS,
                                    SEED_UNIT_WEIGHTS)
from nutrition.meal_basis import SEED_MEAL_TEMPLATES, SEED_VARIATIONS
from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
from nutrition.person_seed import SEED_PERSONS
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from nutrition.threshold_basis import SEED_EATING_PATTERNS
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


EXCLUSIONS = [
    # exclude fish → salmon can never be an omega-3/protein closer
    {'name': 'alex-fish', 'person_name': 'demo-alex',
     'allergen_class': 'fish', 'food_name': '',
     'severity': 'allergy-hard',
     'stated_reason': 'declared fish allergy', 'is_prior': False},
]

MANAGER = SimpleNamespace(objectTables={
    'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
    'NutrientReference': _rows(SEED_DRI_REFERENCES),
    'PersonProfile': _rows(SEED_PERSONS),
    'PersonThreshold': {},
    'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
    'Recipe': _rows(SEED_RECIPES),
    'IngredientLine': _rows(SEED_INGREDIENT_LINES),
    'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
    'VariationDefinition': _rows(SEED_VARIATIONS),
    'ToleranceThreshold': _rows(SEED_TOLERANCE_THRESHOLDS),
    'PropertyClaim': _rows(SEED_FOOD_PH_CLAIMS),
    'IntakeRecord': _rows(SEED_INTAKE_RECORDS),
    'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS),
    'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
    'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS),
    'FoodAllergenFlag': _rows(SEED_FOOD_ALLERGEN_FLAGS),
    'PersonExclusion': _rows(EXCLUSIONS),
})
TODAY = date(2026, 9, 2)

print('mpb-6: coverage steering over time')

cov = rolling_coverage(MANAGER, 'demo-alex', days=3,
                       end_date='2026-09-01')
check('coverage computes over the demo window', cov.get('ok'))
check('averages over LOGGED days only (2 logged in a 3-day '
      'window, gap named)',
      cov['loggedDays'] == 2 and len(cov['gapDays']) == 1)
check('under-target list carries coverage fraction + daily gap',
      cov['underTarget'] and all(
          'coverage' in e and 'dailyGap' in e
          for e in cov['underTarget']))
check('under-target sorted worst first',
      cov['underTarget'] == sorted(cov['underTarget'],
                                   key=lambda e: e['coverage']))
check('the 80% convention is labeled, not silent',
      '80%' in cov['honesty'] and 'not a diagnosis'
      in cov['honesty'])
check('unknown person refuses',
      not rolling_coverage(MANAGER, 'nobody').get('ok'))
check('nutrients absent from the vendored data land in NO-DATA, '
      'never as deficiencies (boron/chloride…)',
      'boron' in cov['noDataNutrients']
      and not any(e['nutrient'] == 'boron'
                  for e in cov['underTarget']))

steer = coverage_steering(MANAGER, 'demo-alex', days=3,
                          end_date='2026-09-01', today=TODAY)
check('steering computes', steer.get('ok')
      and len(steer['steering']) > 0)
priced = [s for s in steer['steering'] if s.get('closers')]
unpriced = [s for s in steer['steering'] if 'note' in s]
check('nutrients without priced closers SAY so (most demo '
      'nutrients have no priced source)',
      all('enter prices' in s['note'] for s in unpriced))
if priced:
    check('priced closers carry arithmetic',
          all('arithmetic' in c for s in priced
              for c in s['closers']))
    check('declared fish exclusion removes fish closers BY NAME '
          'wherever they ranked',
          all('salmon-atlantic-raw' not in
              [c['food'] for c in s.get('closers', [])]
              for s in steer['steering']))
else:
    check('at least one nutrient found a priced closer '
          '(protein has demo prices)', False,
          str([s.get('nutrient') for s in steer['steering']]))
check('fit stays the composer\'s call (stated)',
      'composer' in steer['honesty'])

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpb-6 coverage steering holds together')
