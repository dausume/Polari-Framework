"""
@module nutrition.selftest_recipe

nmp-3 selftest — the recipe rollup engine: retention rows load and
apply per the USDA true-retention method (hand-computed cross-check
against the vendored R6 values), yields scale mass not nutrients,
macros keep raw values with the gap named, provenance labels travel,
missing pieces are honest errors.

Run from polari-framework/:  python3 -m nutrition.selftest_recipe
Stdlib-only; duck-typed manager over the seed lists.
"""

from types import SimpleNamespace

from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.recipe_basis import (SEED_COOKING_STEPS,
                                    SEED_INGREDIENT_LINES,
                                    SEED_RECIPES)
from nutrition.recipe_analysis import (recipe_nutrition,
                                       retention_candidates,
                                       retention_rows)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


MGR = SimpleNamespace(objectTables={
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
    'Recipe': _rows(SEED_RECIPES),
    'IngredientLine': _rows(SEED_INGREDIENT_LINES),
    'CookingStep': _rows(SEED_COOKING_STEPS),
})


def _content(food, nutrient):
    # 0.0 for absent rows — FDC honestly omits e.g. protein for
    # pure fats, and the rollup does the same
    return next((c['amount_per_100g']
                 for c in SEED_FDC_NUTRIENT_CONTENTS
                 if c['food_name'] == food
                 and c['nutrient_name'] == nutrient), 0.0)


def main():
    print('nmp-3 retention data')
    ret = retention_rows('0801')  # CHICKEN,BROILED
    check('R6 0801 (chicken broiled) has rows and sane values',
          len(ret) > 5 and all(0 <= v <= 100 for v in ret.values()))
    cands = retention_candidates('BROCCOLI')
    check('retention search finds nothing for BROCCOLI (R6 groups '
          'it under VEG) — honest empty', cands == [])
    check('retention search finds VEG steamed',
          any(c['code'] == '3784'
              for c in retention_candidates('VEG,OTHER')))

    print('nmp-3 rollup (hand-computed cross-checks)')
    recipe = SimpleNamespace(**SEED_RECIPES[0])  # chicken-rice-bowl
    r = recipe_nutrition(MGR, recipe)
    check('rollup ok, 2 servings', r['ok'] and r['servings'] == 2.0)
    # vitamin C: broccoli 200 g x per100 x R6-3784 retention; chicken
    # + rice contribute per their retention rows; olive oil has none.
    vc_raw_broccoli = _content('broccoli-raw', 'vitamin-c') * 2.0
    ret_veg = retention_rows('3784').get('401', 100.0)
    want_broccoli = vc_raw_broccoli * ret_veg / 100.0
    got_total = r['total'].get('vitamin-c', 0.0)
    other = 0.0
    for food, code, grams in (('chicken-breast-raw', '0801', 300.0),
                              ('rice-white-raw', '0432', 150.0)):
        try:
            per100 = _content(food, 'vitamin-c')
        except StopIteration:
            continue
        rr = retention_rows(code).get('401', 100.0)
        other += per100 * grams / 100.0 * rr / 100.0
    check('vitamin C total = broccoli x R6 retention (+ other '
          'lines), hand-computed',
          abs(got_total - (want_broccoli + other)) < 0.05,
          f'got {got_total} want {want_broccoli + other:.3f}')
    # protein is a macro — no retention; raw sum kept
    want_protein = (
        _content('chicken-breast-raw', 'protein') * 3.0
        + _content('rice-white-raw', 'protein') * 0.55
        + _content('broccoli-raw', 'protein') * 2.0
        + _content('olive-oil', 'protein') * 0.15)
    check('protein (macro) keeps the raw sum — no R6 rows',
          abs(r['total']['protein'] - round(want_protein, 3)) < 0.01)
    check('macro provenance says raw kept where cooked',
          'raw value kept' in r['perServing']['protein']['provenance']
          or r['perServing']['protein']['provenance'] == 'mixed')
    # yield scales MASS: 300x0.7 + 55x2.8 + 200x0.95 + 15 = 569
    check('cooked mass = sum of line yields (569 g)',
          abs(r['cookedMassG'] - 569.0) < 0.1, str(r['cookedMassG']))
    check('per-serving = total / servings',
          abs(r['perServing']['protein']['amount']
              - round(r['total']['protein'] / 2.0, 3)) < 0.01)
    check('line report names retention description',
          any('CHICKEN,BROILED' in l.get('retentionDescription', '')
              for l in r['lines']))
    check('honesty names the macro gap',
          'macros keep raw values' in r['honesty'])

    print('nmp-3 honest refusals')
    bad = recipe_nutrition(MGR, SimpleNamespace(name='no-such',
                                                servings=1.0))
    check('recipe without lines refuses', not bad['ok'])

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-3 recipe engine holds together')


if __name__ == '__main__':
    main()
