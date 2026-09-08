"""
@module mealoptions.mealoptions_selftest

mo-1 selftest — the meal-options layer on its own (imports ONLY
mealoptions; no nutrition, no household, no server): every class
constructs with defaults, every seed row's keys are constructor
fields, seed names are unique per class, provenance ids are kept,
and the PRIVACY LINE holds — no class carries a person / household /
place / day field, except BulkStaple's declared compat pointers,
which every shipped seed leaves blank.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m mealoptions.mealoptions_selftest
"""

import inspect
import sys

from mealoptions import MEALOPTIONS_CLASSES, MEALOPTIONS_SEED_PAIRS
from mealoptions.staple_basis import INSTANCE_POINTER_FIELDS, BulkStaple

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []

#: Fields that name a person, a household, a place or a day — none
#: of them may exist on a published-module class.
PRIVATE_FIELDS = ('person_name', 'household_name', 'latitude', 'longitude',
                  'address', 'observed_date', 'location_name')


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _fields(cls):
    return [p for p in inspect.signature(cls.__init__).parameters
            if p not in ('self', 'manager')]


def main():
    print('mo-1 meal options layer')
    names = [n for n, _c, _s in MEALOPTIONS_SEED_PAIRS]
    check('MEALOPTIONS_SEED_PAIRS: 17 (name, class, seeds) triples (mo-2 adds PriceReference)',
          len(MEALOPTIONS_SEED_PAIRS) == 17 and len(MEALOPTIONS_CLASSES) == 17, str(names))
    check('pair names match their classes',
          all(n == c.__name__ for n, c, _s in MEALOPTIONS_SEED_PAIRS))
    check('no class registered twice', len(set(names)) == len(names))

    for cls_name, cls, seeds in MEALOPTIONS_SEED_PAIRS:
        fields = set(_fields(cls))
        try:
            obj = cls()
            constructed = all(hasattr(obj, f) for f in fields)
        except Exception as exc:  # noqa: BLE001 — a selftest reports, never hides
            constructed, obj = False, exc
        check(f'{cls_name} constructs with defaults and sets every field', constructed, str(obj))
        bad_keys = [(r.get('name'), k) for r in seeds for k in r if k not in fields]
        check(f'{cls_name}: every seed key is a constructor field ({len(seeds)} rows)',
              not bad_keys, str(bad_keys[:3]))
        seed_names = [r.get('name', '') for r in seeds]
        check(f'{cls_name}: seed names unique and non-empty',
              all(seed_names) and len(set(seed_names)) == len(seed_names),
              str([n for n in seed_names if seed_names.count(n) > 1][:3]))
        check(f'{cls_name}: every seed carries a provenance_id',
              all(r.get('provenance_id') for r in seeds))
        # the privacy line
        compat = set(INSTANCE_POINTER_FIELDS) if cls is BulkStaple else set()
        leaked = [f for f in fields if f in PRIVATE_FIELDS and f not in compat]
        check(f'{cls_name}: no person / household / place / day field', not leaked, str(leaked))
        if compat:
            filled = [(r['name'], f) for r in seeds for f in compat if r.get(f, '')]
            check(f'{cls_name}: compat pointer fields {sorted(compat)} blank in every seed',
                  not filled, str(filled[:3]))
            check(f'{cls_name}: seed notes say the offer location lives on the instance',
                  all('offer location lives on the instance' in r.get('notes', '') for r in seeds))

    # cross-row integrity inside the module (names only — no engine)
    seeds = {n: s for n, _c, s in MEALOPTIONS_SEED_PAIRS}
    recipes = {r['name'] for r in seeds['Recipe']}
    check('every ingredient line and cooking step names a seeded recipe',
          all(r['recipe_name'] in recipes for r in seeds['IngredientLine'] + seeds['CookingStep']))
    templates = {r['name'] for r in seeds['MealTemplate']}
    check('every variation names a seeded template',
          all(r['template_name'] in templates for r in seeds['VariationDefinition']))
    bases = {r['name'] for r in seeds['DishBase']}
    check('every template dish_base is a seeded DishBase',
          all(r['dish_base'] in bases for r in seeds['MealTemplate']))
    roles = {r['name'] for r in seeds['IngredientRole']}
    check('every FoodRole names a seeded role',
          all(r['role_name'] in roles for r in seeds['FoodRole']))
    tasks = {r['name'] for r in seeds['CookingTaskDefinition']}
    tools = {r['name'] for r in seeds['KitchenToolDefinition']} | {''}
    check('every StepMethod names a seeded task kind and tool ("" = hands)',
          all(r['task_kind'] in tasks and r['tool_name'] in tools for r in seeds['StepMethod']))
    check('every MealSituation container is a seeded tool or blank',
          all(r['needs_container'] in tools for r in seeds['MealSituation']))
    check('every BulkStaple cadence is 1/3/6/12 and within its shelf life',
          all(r['cadence_months'] in (1, 3, 6, 12) and r['cadence_months'] * 30 <= r['shelf_life_days']
              for r in seeds['BulkStaple']))

    # the module imports nothing person-side
    leaky = [m for m in sys.modules if m.split('.')[0] in ('nutrition', 'household')]
    check('mealoptions imported nothing from nutrition or household', not leaky, str(leaky))

    print(f'\n{len(failures)} failure(s)' if failures else '\nall mealoptions checks passed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
