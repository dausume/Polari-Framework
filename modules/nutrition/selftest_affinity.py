"""
@module nutrition.selftest_affinity

nmp-11 selftest — the composer: affinity resolution (direct food
beats role, context falls back to general-western, unknown ranks
low but is never refused), placements are affinity-ranked DIFF
proposals, banana-on-pasta is ALLOWED with a gentle note, the
cuisine context is a stated knob, and counterbalance suggestions
are filtered by fit to the week's dishes.

Run from polari-framework/:  python3 -m nutrition.selftest_affinity
"""

from types import SimpleNamespace

from nutrition.affinity_basis import (SEED_DISH_BASES,
                                      SEED_FOOD_ROLES,
                                      SEED_INGREDIENT_AFFINITIES,
                                      SEED_INGREDIENT_ROLES)
from nutrition.affinity_composer import (affinity_for, compose,
                                         counterbalance)
from nutrition.dri_seed import SEED_DRI_REFERENCES
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.meal_basis import (SEED_MEAL_TEMPLATES,
                                  SEED_VARIATIONS)
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
          'waist_cm': 0.0, 'cooking_skill': 'intermediate',
          'cuisine_context': 'japanese'}

PLAN = {'name': 'test-week', 'person_name': 'alex-test',
        'household_name': '', 'days': 3, 'start_date': ''}
ENTRIES = [
    {'name': 'tw-d1-breakfast', 'plan_name': 'test-week',
     'day_index': 1, 'slot': 'breakfast',
     'template_name': 'omelet-breakfast', 'variation_name': '',
     'scale': 1.0, 'time_hhmm': '', 'serving_split_json': ''},
    {'name': 'tw-d1-dinner', 'plan_name': 'test-week',
     'day_index': 1, 'slot': 'dinner',
     'template_name': 'chicken-bowl-dinner', 'variation_name': '',
     'scale': 1.0, 'time_hhmm': '', 'serving_split_json': ''},
    {'name': 'tw-d2-dinner', 'plan_name': 'test-week',
     'day_index': 2, 'slot': 'dinner',
     'template_name': 'chicken-bowl-dinner', 'variation_name': '',
     'scale': 1.0, 'time_hhmm': '', 'serving_split_json': ''},
]


def _mgr():
    return SimpleNamespace(objectTables={
        'DishBase': _rows(SEED_DISH_BASES),
        'IngredientRole': _rows(SEED_INGREDIENT_ROLES),
        'FoodRole': _rows(SEED_FOOD_ROLES),
        'IngredientAffinity': _rows(SEED_INGREDIENT_AFFINITIES),
        'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
        'NutrientReference': _rows(SEED_DRI_REFERENCES),
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
        'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES),
        'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
        'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows([PLAN]),
        'MealEntry': _rows(ENTRIES),
        'PersonProfile': _rows([PERSON]),
        'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
        'PersonThreshold': {},
    })


def main():
    m = _mgr()
    print('nmp-11 affinity resolution')
    a = affinity_for(m, 'tomato-raw', 'pasta')
    check('direct food row outranks the role (tomato-pasta 0.95)',
          a['weight'] == 0.95 and 'food row' in a['basis'])
    a2 = affinity_for(m, 'chicken-breast-raw', 'bowl')
    check('role resolution (diced-protein x bowl 0.95)',
          a2['weight'] == 0.95 and 'role' in a2['basis'])
    a3 = affinity_for(m, 'rice-white-raw', 'bowl',
                      context='japanese')
    check('context row wins in its context (rice x bowl japanese '
          '1.0)', a3['weight'] == 1.0 and 'japanese' in a3['basis'])
    a4 = affinity_for(m, 'chicken-breast-raw', 'bowl',
                      context='japanese')
    check('missing context falls back to general-western',
          a4['weight'] == 0.95 and 'general-western' in a4['basis'])
    a5 = affinity_for(m, 'salt-iodized', 'omelet')
    check('unknown food ranks LOW, never refused',
          a5['weight'] == 0.1 and 'never refused' in a5['basis'])

    print('nmp-11 the composer')
    c = compose(m, SimpleNamespace(**PLAN), 'chicken-breast-raw',
                meals_count=2)
    check('placements ranked by affinity (bowl 0.95 above omelet '
          '0.8)', c['ok']
          and c['ranked'][0]['dishBase'] == 'bowl'
          and c['ranked'][0]['affinity'] >= c['ranked'][-1]['affinity'])
    check('the person\'s stated context knob is used (japanese)',
          c['context'] == 'japanese')
    check('placements are DIFF proposals through the gate',
          all('gate' in p['proposal'] for p in c['placements']))
    b = compose(m, SimpleNamespace(**PLAN), 'banana-raw',
                slot='dinner')
    check('banana-on-bowl allowed; low affinity earns at most a '
          'gentle note', b['ok'] and len(b['placements']) == 1)
    check('honesty: nothing written, nothing blocked',
          'never blocks' in b['honesty'])
    bad = compose(m, SimpleNamespace(**PLAN), 'no-such-food')
    check('unknown FoodItem refuses honestly', not bad['ok'])

    print('nmp-11 counterbalance (filtered by fit)')
    cb = counterbalance(m, SimpleNamespace(**PLAN))
    check('under-target nutrients get fit-filtered suggestions',
          cb['ok'] and len(cb['suggestions']) > 0
          and all(s['suggestedFoods'] for s in cb['suggestions']
                  if s['suggestedFoods']))
    one = next((s for s in cb['suggestions']
                if s['suggestedFoods']), None)
    check('suggestions ranked by affinity then richness, dish '
          'named', one is not None
          and one['suggestedFoods'][0]['affinity']
          >= one['suggestedFoods'][-1]['affinity']
          and one['suggestedFoods'][0]['bestDish'])
    check('norms rank, people decide (the wording)',
          all('people decide' in s['note']
              for s in cb['suggestions']))

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-11 affinity composer holds together')


if __name__ == '__main__':
    main()
