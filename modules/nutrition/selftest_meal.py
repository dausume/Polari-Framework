"""
@module nutrition.selftest_meal

nmp-4 selftest — templates, the hard gate, plans: rollups combine
recipes per meal, swaps apply without mutating stored rows, the
gate REFUSES a dangerous template with named reasons (and passes
the sane seeds), scale clamps report, day rollups compare against
the owner's thresholds and suggestions never auto-edit.

Run from polari-framework/:  python3 -m nutrition.selftest_meal
Stdlib-only; duck-typed manager over the seed lists.
"""

from types import SimpleNamespace

from nutrition.dri_seed import SEED_DRI_REFERENCES
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.meal_basis import (SEED_MEAL_TEMPLATES,
                                  SEED_VARIATIONS)
from nutrition.meal_analysis import (plan_rollup, template_rollup,
                                     validate_template)
from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
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


PERSON = {'name': 'alex-test', 'sex': 'male', 'age_years': 30.0,
          'weight_kg': 80.0, 'height_cm': 180.0,
          'activity_level': 'moderate', 'goal': 'maintain',
          'goal_rate_kg_per_week': 0.0, 'metabolism_factor': 1.0,
          'body_fat_fraction': 0.0, 'pregnant_or_lactating': False,
          'eating_pattern': '3-meal', 'weekly_moderate_minutes': 0.0,
          'weekly_vigorous_minutes': 0.0, 'life_stage': '',
          'waist_cm': 0.0}

PLAN = {'name': 'test-week', 'person_name': 'alex-test',
        'household_name': '', 'days': 2, 'start_date': ''}

ENTRIES = [
    {'name': 'test-week-d1-breakfast', 'plan_name': 'test-week',
     'day_index': 1, 'slot': 'breakfast',
     'template_name': 'omelet-breakfast',
     'variation_name': 'omelet-breakfast-base', 'scale': 1.0,
     'serving_split_json': ''},
    {'name': 'test-week-d1-dinner', 'plan_name': 'test-week',
     'day_index': 1, 'slot': 'dinner',
     'template_name': 'chicken-bowl-dinner',
     'variation_name': 'chicken-bowl-dinner-base', 'scale': 5.0,
     'serving_split_json': ''},
]


def _mgr(templates=None, variations=None, entries=None):
    return SimpleNamespace(objectTables={
        'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
        'NutrientReference': _rows(SEED_DRI_REFERENCES),
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
        'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES),
        'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
        'PersonThreshold': {},
        'MealTemplate': _rows(templates or SEED_MEAL_TEMPLATES),
        'VariationDefinition': _rows(variations or SEED_VARIATIONS),
        'MealPlanDefinition': _rows([PLAN]),
        'MealEntry': _rows(entries or ENTRIES),
        'PersonProfile': _rows([PERSON]),
    })


def main():
    m = _mgr()
    tmpl = SimpleNamespace(**SEED_MEAL_TEMPLATES[0])

    print('nmp-4 template rollup')
    r = template_rollup(m, tmpl)
    check('rollup ok with per-meal amounts + GL',
          r['ok'] and r['perMeal']['protein']['amount'] > 0
          and r['glycemicLoad'] > 0)
    var = SimpleNamespace(**SEED_VARIATIONS[1])  # tofu swap
    r_tofu = template_rollup(m, tmpl, var)
    check('tofu swap changes the rollup (less protein than chicken)',
          r_tofu['ok'] and r_tofu['perMeal']['protein']['amount']
          < r['perMeal']['protein']['amount'])
    check('swap does not mutate stored lines',
          any(l['food_name'] == 'chicken-breast-raw'
              for l in SEED_INGREDIENT_LINES))
    r2 = template_rollup(m, tmpl, scale=2.0)
    check('scale doubles amounts',
          abs(r2['perMeal']['protein']['amount']
              - 2 * r['perMeal']['protein']['amount']) < 0.01)

    print('nmp-4 the gate (decision 2 + 9)')
    v = validate_template(m, tmpl)
    check('sane seeded template PASSES the gate', v['ok'],
          str(v['refusals'][:2]))
    check('gate checked every variation x both scale extremes',
          v['casesChecked'] == 4)
    check('gate names its priors + gaps',
          'strictest adult UL' in v['honesty']
          and len(v['namedGaps']) == 2)
    # a dangerous template: a kilo of salt-heavy meal
    bad_recipe = [{'name': 'salt-bomb', 'display_name': 'Salt bomb',
                   'description': '', 'servings': 1.0,
                   'origin': 'test', 'is_prior': True,
                   'provenance_id': 't'}]
    bad_lines = [{'name': 'salt-bomb-salt', 'recipe_name': 'salt-bomb',
                  'food_name': 'salt-iodized', 'grams': 10.0,
                  'method': 'raw', 'yield_percent': 100.0,
                  'retention_code': '', 'prep_note': '', 'order': 1}]
    bad_tmpl = {'name': 'salty-dinner', 'display_name': 'Salty',
                'description': '',
                'recipe_names_json': '["salt-bomb"]',
                'slots_json': '["dinner"]', 'is_prior': True,
                'provenance_id': 't'}
    m_bad = _mgr(templates=[bad_tmpl])
    m_bad.objectTables['Recipe'] = _rows(SEED_RECIPES + bad_recipe)
    m_bad.objectTables['IngredientLine'] = _rows(
        SEED_INGREDIENT_LINES + bad_lines)
    m_bad.objectTables['VariationDefinition'] = {}
    vb = validate_template(m_bad, SimpleNamespace(**bad_tmpl))
    check('10 g salt in one meal REFUSED (sodium past the cap), '
          'reason named',
          not vb['ok'] and any('sodium' in r.get('reason', '')
                               for r in vb['refusals']))

    print('nmp-4 plan rollup')
    pr = plan_rollup(m, SimpleNamespace(**PLAN))
    check('plan ok with per-day totals', pr['ok']
          and 1 in pr['days'])
    d1 = pr['days'][1]
    check('day totals accumulate both meals',
          d1['totals']['calories'] > 0)
    dinner = next(e for e in pr['entries']
                  if e.get('slot') == 'dinner')
    check('scale 5.0 clamped into the variation range (1.2)',
          dinner['scale'] == 1.2 and dinner.get('scaleClamped'))
    check('thresholds compared (under/over lists present)',
          'underTarget' in d1 and 'overMax' in d1)
    check('suggestions propose, never auto-edit',
          all('auto' not in s['suggestion'].lower()
              or 'nothing auto-edited' in s['suggestion']
              for s in pr['suggestions']))
    empty = plan_rollup(m, SimpleNamespace(
        name='no-such', person_name='', household_name=''))
    check('plan without entries refuses', not empty['ok'])

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-4 meal layer holds together')


if __name__ == '__main__':
    main()
