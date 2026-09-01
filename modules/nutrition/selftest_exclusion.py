"""
@module nutrition.selftest_exclusion

mpb-1 selftest — the exclusion safety filter: identity flags
resolve, declared hard exclusions catch template foods (through
swaps too), unverified foods are NAMED not passed, plan screening
counts violations without editing anything, safe-swap suggestions
find the clearing variation, and authoring validation demands one
target + the person's own reason.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_exclusion
"""

from types import SimpleNamespace

from nutrition.exclusion_basis import (
    SEED_FOOD_ALLERGEN_FLAGS, SEED_PERSON_EXCLUSIONS,
)
from nutrition.exclusion_analysis import (
    exclusion_safe_swaps, screen_foods, screen_plan,
    screen_template, validate_exclusion_row,
)
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


# a milk-hard + mushroom-soft person beside the seeded tree-nut demo
EXCLUSIONS = list(SEED_PERSON_EXCLUSIONS) + [
    {'name': 'test-dana-milk', 'person_name': 'test-dana',
     'allergen_class': 'milk', 'food_name': '',
     'severity': 'intolerance-hard',
     'stated_reason': 'dairy makes me ill', 'is_prior': False},
    {'name': 'test-dana-mushroom', 'person_name': 'test-dana',
     'allergen_class': '', 'food_name': 'mushroom-white-raw',
     'severity': 'preference-soft',
     'stated_reason': 'just dislike them', 'is_prior': False},
]

MANAGER = SimpleNamespace(objectTables={
    'FoodAllergenFlag': _rows(SEED_FOOD_ALLERGEN_FLAGS),
    'PersonExclusion': _rows(EXCLUSIONS),
    'Recipe': _rows(SEED_RECIPES),
    'IngredientLine': _rows(SEED_INGREDIENT_LINES),
    'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
    'VariationDefinition': _rows(SEED_VARIATIONS),
    'MealPlanDefinition': _rows(SEED_MEAL_PLANS),
    'MealEntry': _rows(SEED_MEAL_ENTRIES),
})

print('mpb-1: exclusion safety filter')

# food-level screening
scr = screen_foods(MANAGER, 'test-dana',
                   ['cheese-cheddar', 'spinach-raw',
                    'mushroom-white-raw', 'dragonfruit'])
check('milk exclusion catches cheddar by identity flag',
      any(v['food'] == 'cheese-cheddar'
          and v['matched'] == 'milk' for v in scr['violations']))
check('the person\'s own reason travels with the violation',
      scr['violations'][0]['statedReason'] == 'dairy makes me ill')
check('soft dislike lands as a note, never a violation',
      any(n['food'] == 'mushroom-white-raw'
          for n in scr['softNotes'])
      and not any(v['food'] == 'mushroom-white-raw'
                  for v in scr['violations']))
# mushroom carries no allergen flag either — it lands in BOTH the
# unflagged list (allergen screening unverified) and the soft
# notes (declared dislike); both facts are true independently.
check('unflagged foods NAMED as unverified',
      set(scr['unflaggedFoods'])
      == {'dragonfruit', 'spinach-raw', 'mushroom-white-raw'})
check('boundary text rides the payload',
      'never' in scr['boundary'] and 'diagnosed' in scr['boundary'])

# template screening — the tofu swap matters: base bowl has no
# soy; the tofu VARIATION introduces soybean.
soy_person = SimpleNamespace(objectTables={
    **MANAGER.objectTables,
    'PersonExclusion': _rows([
        {'name': 't-soy', 'person_name': 'test-soy',
         'allergen_class': 'soybean', 'food_name': '',
         'severity': 'allergy-hard',
         'stated_reason': 'declared soy allergy',
         'is_prior': False}])})
base = screen_template(soy_person, 'test-soy',
                       'chicken-bowl-dinner',
                       'chicken-bowl-dinner-base')
tofu = screen_template(soy_person, 'test-soy',
                       'chicken-bowl-dinner',
                       'chicken-bowl-dinner-tofu')
check('base bowl clears a soy allergy', base['safeForPerson'])
check('the tofu VARIATION is caught (swap-aware screening)',
      not tofu['safeForPerson']
      and tofu['violations'][0]['food'] == 'tofu-firm')

# plan screening + safe swaps: give the demo plan's owner the soy
# allergy — d2 dinner (tofu variation) must violate; the base
# variation is the suggested clearing swap.
plan_mgr = SimpleNamespace(objectTables={
    **MANAGER.objectTables,
    'PersonExclusion': _rows([
        {'name': 'alex-soy', 'person_name': 'demo-alex',
         'allergen_class': 'soybean', 'food_name': '',
         'severity': 'allergy-hard',
         'stated_reason': 'declared soy allergy',
         'is_prior': False}])})
plan = SimpleNamespace(**SEED_MEAL_PLANS[0])
screen = screen_plan(plan_mgr, plan)
check('plan screen counts exactly the tofu entry as violating',
      screen.get('ok') and screen['entriesViolating'] == 1)
check('verdict says swap-or-replan, nothing auto-edited',
      'auto-edited' in screen['verdict'])
swaps = exclusion_safe_swaps(plan_mgr, plan)
check('safe-swap suggestion points at the base variation',
      any(s['switchToVariation'] == 'chicken-bowl-dinner-base'
          for s in swaps['suggestions']))
check('suggestions applied by the human',
      all('you' in s['appliedBy'] for s in swaps['suggestions']))

# tree-nut demo person: current demo plan has no nuts → all clear
clear = screen_plan(MANAGER, plan)
check('demo tree-nut person clears the nut-free demo plan',
      clear['entriesViolating'] == 0)

# authoring validation
check('row with BOTH targets refuses',
      not validate_exclusion_row(SimpleNamespace(
          allergen_class='milk', food_name='milk-whole',
          stated_reason='x'))['ok'])
check('unknown class refuses naming the vocabulary',
      not validate_exclusion_row(SimpleNamespace(
          allergen_class='gluten', food_name='',
          stated_reason='x'))['ok'])
check('missing stated reason refuses (the declaration is theirs)',
      not validate_exclusion_row(SimpleNamespace(
          allergen_class='milk', food_name='',
          stated_reason=''))['ok'])
check('valid row passes',
      validate_exclusion_row(SimpleNamespace(
          allergen_class='milk', food_name='',
          stated_reason='dairy makes me ill'))['ok'])

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpb-1 exclusion filter holds together')
