"""
@module nutrition.selftest_tolerance

nmp-2 selftest — the tolerance table + evaluation: rows are shaped
and cited, warnings fire at documented doses with the symptom named,
per-kg rows scale with the person (and are honestly skipped without
one), nothing clamps, GL math matches hand-computation, and the
decision-9 rows carry their LOWER confidence labels.

Run from polari-framework/:  python3 -m nutrition.selftest_tolerance
Stdlib-only; duck-typed manager over the seed lists.
"""

from types import SimpleNamespace

from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.tolerance_basis import (CONFIDENCE_GRADES,
                                       SEED_TOLERANCE_THRESHOLDS,
                                       TOLERANCE_PERIODS)
from nutrition.tolerance_analysis import (evaluate_tolerances,
                                          meal_glycemic_load)

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
    'ToleranceThreshold': _rows(SEED_TOLERANCE_THRESHOLDS),
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
})
PERSON = SimpleNamespace(name='t', weight_kg=80.0)


def main():
    print('nmp-2 table shape')
    check('16 seeded rows', len(SEED_TOLERANCE_THRESHOLDS) == 16,
          str(len(SEED_TOLERANCE_THRESHOLDS)))
    check('every row cited + symptom named',
          all(r['citation'] and r['symptom']
              for r in SEED_TOLERANCE_THRESHOLDS))
    check('valid periods + confidence grades',
          all(r['period'] in TOLERANCE_PERIODS
              and r['confidence'] in CONFIDENCE_GRADES
              for r in SEED_TOLERANCE_THRESHOLDS))
    check('decision-9 reflux rows carry LOW confidence',
          all(r['confidence'] == 'low'
              for r in SEED_TOLERANCE_THRESHOLDS
              if r['substance'] in ('meal-acidity', 'meal-fat-load',
                                    'reflux-trigger-categories')))
    check('protein row is labeled utilization NOT toxicity',
          any(r['substance'] == 'protein'
              and 'NOT toxicity' in r['qualifier']
              for r in SEED_TOLERANCE_THRESHOLDS))
    check('fiber row says no UL exists',
          any('no NASEM UL' in r['qualifier']
              for r in SEED_TOLERANCE_THRESHOLDS
              if r['substance'] == 'inulin-type-fiber'))

    print('nmp-2 evaluation')
    r = evaluate_tolerances(MGR, {'inulin-type-fiber': 15.0}, 'dose')
    check('15 g fermenting fiber/dose warns with the symptom',
          len(r['warnings']) == 1
          and 'bloating' in r['warnings'][0]['symptom'])
    r = evaluate_tolerances(MGR, {'inulin-type-fiber': 8.0}, 'dose')
    check('8 g stays under the 10 g row (no warning)',
          len(r['warnings']) == 0)
    r = evaluate_tolerances(MGR, {'protein': 40.0}, 'meal',
                            person=PERSON)
    check('40 g protein/meal at 80 kg (cap 32) warns, qualifier '
          'carried', len(r['warnings']) == 1
          and 'NOT toxicity' in r['warnings'][0]['qualifier'])
    r = evaluate_tolerances(MGR, {'protein': 40.0}, 'meal')
    check('per-kg row without a person is SKIPPED and reported',
          len(r['warnings']) == 0 and len(r['skipped']) == 1)
    r = evaluate_tolerances(MGR, {'sodium': 3000.0,
                                  'glycemic-load': 5.0}, 'day')
    check('sodium 3000/day warns; GL row is meal-period (no '
          'cross-period firing)', len(r['warnings']) == 1
          and r['warnings'][0]['substance'] == 'sodium')
    r = evaluate_tolerances(
        MGR, {'reflux-trigger-categories': 1.0}, 'meal')
    check('presence-flag row warns on any presence',
          len(r['warnings']) == 1)
    r = evaluate_tolerances(
        MGR, {'sodium': 999999.0}, 'day')
    check('warnings never clamp — the amount stays the person\'s',
          r['warnings'][0]['amount'] == 999999.0)

    print('nmp-2 glycemic load (decision 9)')
    # 150 g white rice: carbs 80.34 g/100g -> 120.5 g x GI 73 / 100
    gl = meal_glycemic_load(
        MGR, [{'food_name': 'rice-white-raw', 'grams': 150.0}])
    rice_carbs = next(
        c['amount_per_100g'] for c in SEED_FDC_NUTRIENT_CONTENTS
        if c['name'] == 'rice-white-raw-carbohydrate')
    want = 73.0 * (rice_carbs * 1.5) / 100.0
    check('GL math = GI x carbs/100 (hand-computed)',
          abs(gl['glycemicLoad'] - round(want, 1)) < 0.05,
          f"got {gl['glycemicLoad']} want {round(want, 1)}")
    gl2 = meal_glycemic_load(
        MGR, [{'food_name': 'chicken-breast-raw', 'grams': 200.0},
              {'food_name': 'no-such-food', 'grams': 10.0}])
    check('no-GI and unknown foods reported, never guessed',
          gl2['glycemicLoad'] == 0.0 and len(gl2['unknown']) == 2)
    check('source cites the paper, not the Sydney database',
          'Atkinson' in gl['source'])

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-2 tolerance table holds together')


if __name__ == '__main__':
    main()
