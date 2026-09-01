"""
@module nutrition.selftest_tracking

mpa-4 selftest — accounts + tracking over time: the Keycloak
identity resolves through UserAccountLink (precedence + honest
unlinked refusal), a person-day rolls up meals with GL + acidity +
day warnings, and the series names gap days instead of charting
zeros, with weight observations riding alongside.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_tracking
"""

from types import SimpleNamespace

from foodstate.food_ph_seed import SEED_FOOD_PH_CLAIMS
from nutrition.account_basis import SEED_USER_ACCOUNT_LINKS
from nutrition.dri_seed import SEED_DRI_REFERENCES
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.intake_basis import SEED_INTAKE_RECORDS
from nutrition.meal_basis import SEED_MEAL_TEMPLATES, SEED_VARIATIONS
from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
from nutrition.person_seed import SEED_PERSONS
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from nutrition.threshold_basis import SEED_EATING_PATTERNS
from nutrition.tolerance_basis import SEED_TOLERANCE_THRESHOLDS
from nutrition.tracking_analysis import (
    intake_day, resolve_me, tracking_series,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


WEIGHTS = [
    {'name': 'w1', 'person_name': 'demo-alex', 'date': '2026-08-30',
     'day_index': 0, 'weight_kg': 80.0, 'context': 'morning'},
    {'name': 'w2', 'person_name': 'demo-alex', 'date': '2026-09-01',
     'day_index': 2, 'weight_kg': 79.6, 'context': 'morning'},
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
    'UserAccountLink': _rows(SEED_USER_ACCOUNT_LINKS),
    'IntakeRecord': _rows(SEED_INTAKE_RECORDS),
    'WeightObservation': _rows(WEIGHTS),
})

print('mpa-4: accounts + tracking over time')

# ── resolve_me ────────────────────────────────────────────
me = resolve_me(MANAGER, {'sub': 'nope', 'username': 'demo-alex',
                          'email': ''})
check('username matches the demo link → demo-alex',
      me.get('ok') and me['person'] == 'demo-alex'
      and me['matchedBy'] == 'keycloak_username')
check('person existence is verified, household attached',
      me.get('personExists') is True
      and me['household'] == 'demo-household')
anon = resolve_me(MANAGER, None)
check('anonymous refuses naming the login path',
      not anon.get('ok') and not anon['authenticated'])
unlinked = resolve_me(MANAGER, {'sub': 'abc123',
                                'username': 'stranger',
                                'email': 's@x.invalid'})
check('unlinked login refuses with the fix named (no silent '
      'auto-provision)',
      not unlinked.get('ok') and unlinked['authenticated']
      and 'UserAccountLink' in unlinked['error'])

# ── one person-day ────────────────────────────────────────
day = intake_day(MANAGER, 'demo-alex', '2026-09-01')
check('day rolls up both logged meals', day.get('ok')
      and len(day['meals']) == 2)
check('meals carry GL + acid share',
      all('glycemicLoad' in m and 'acidMassShare' in m
          for m in day['meals']))
check('day totals accumulate (calories > one meal)',
      day['dayTotals'].get('calories', 0)
      > max(m.get('calories', 0) for m in day['meals']))
check('day compares against the person thresholds',
      isinstance(day.get('vsThresholds'), list)
      and len(day['vsThresholds']) > 0)
empty = intake_day(MANAGER, 'demo-alex', '2026-07-01')
check('a day without records is an honest gap, not zeros',
      not empty.get('ok') and 'gap' in empty['error'])

# ── the series over time ──────────────────────────────────
series = tracking_series(MANAGER, 'demo-alex',
                         start_date='2026-08-30',
                         end_date='2026-09-01')
check('series computes', series.get('ok'))
check('recorded days present, gap day NAMED (08-30 has no intake)',
      len(series['days']) == 2 and series['gapDays'] == ['2026-08-30'])
check('day entries carry the metric set',
      all(set(('calories', 'protein', 'maxMealGL',
               'maxMealAcidShare')) <= set(d)
          for d in series['days']))
check('weight observations ride the series',
      len(series['weightObservations']) == 2
      and series['weightObservations'][0]['date'] == '2026-08-30')
check('honesty names the gap policy',
      'NAMED gaps' in series['honesty'])
nobody = tracking_series(MANAGER, 'nobody')
check('unknown person refuses with the next step',
      not nobody.get('ok') and 'log a meal' in nobody['error'])

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpa-4 accounts + tracking holds together')
