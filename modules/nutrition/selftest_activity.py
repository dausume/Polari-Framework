"""
@module nutrition.selftest_activity

nmp-5/5b selftest — activity + timing: the curated seed carries
verbatim Compendium values with real codes, kcal = MET x kg x h
(hand-computed), intensity bands follow the 3/6 cutoffs, the weekly
summary suggests (never applies) profile updates, the day timeline
interleaves by clock and fires the comfort-window / fasted /
chrono evaluations with confidence labels, and the fasted-exercise
facts stay honest (no weight multiplier anywhere).

Run from polari-framework/:  python3 -m nutrition.selftest_activity
"""

from types import SimpleNamespace

from nutrition.activity_basis import (SEED_ACTIVITY_DEFINITIONS,
                                      intensity_band)
from nutrition.activity_analysis import (activity_kcal, day_timeline,
                                         fasted_exercise_facts,
                                         weekly_summary)
from nutrition.fdc_seed import (SEED_FDC_FOOD_ITEMS,
                                SEED_FDC_NUTRIENT_CONTENTS)
from nutrition.meal_basis import (SEED_MEAL_TEMPLATES,
                                  SEED_VARIATIONS)
from nutrition.recipe_basis import (SEED_INGREDIENT_LINES,
                                    SEED_RECIPES)
from nutrition.vendor_data import compendium_mets

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


PERSON = SimpleNamespace(name='alex-test', weight_kg=80.0,
                         weekly_moderate_minutes=150.0,
                         weekly_vigorous_minutes=0.0)

LOGS = [
    {'name': 'run-1', 'person_name': 'alex-test',
     'activity_name': 'running-6mph', 'activity_code': '',
     'duration_min': 30.0, 'date': '', 'start_hhmm': '19:00',
     'day_index': 1, 'perceived_intensity_factor': 1.0,
     'fasted': False},
    {'name': 'walk-1', 'person_name': 'alex-test',
     'activity_name': 'walking-25mph-level', 'activity_code': '',
     'duration_min': 60.0, 'date': '', 'start_hhmm': '',
     'day_index': 0, 'perceived_intensity_factor': 1.0,
     'fasted': False},
    {'name': 'fasted-run', 'person_name': 'alex-test',
     'activity_name': '', 'activity_code': '12050',
     'duration_min': 50.0, 'date': '', 'start_hhmm': '06:30',
     'day_index': 2, 'perceived_intensity_factor': 1.0,
     'fasted': True},
]

PLAN = {'name': 'test-week', 'person_name': 'alex-test',
        'household_name': '', 'days': 2, 'start_date': ''}

ENTRIES = [
    {'name': 'd1-dinner', 'plan_name': 'test-week', 'day_index': 1,
     'slot': 'dinner', 'template_name': 'chicken-bowl-dinner',
     'variation_name': '', 'scale': 2.0, 'time_hhmm': '18:00',
     'serving_split_json': ''},
    {'name': 'd1-late', 'plan_name': 'test-week', 'day_index': 1,
     'slot': 'snack', 'template_name': 'chicken-bowl-dinner',
     'variation_name': '', 'scale': 2.0, 'time_hhmm': '21:30',
     'serving_split_json': ''},
]


def _mgr():
    return SimpleNamespace(objectTables={
        'ActivityDefinition': _rows(SEED_ACTIVITY_DEFINITIONS),
        'ActivityLog': _rows(LOGS),
        'PersonProfile': _rows([{
            'name': 'alex-test', 'weight_kg': 80.0,
            'weekly_moderate_minutes': 150.0,
            'weekly_vigorous_minutes': 0.0}]),
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
        'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES),
        'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
        'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows([PLAN]),
        'MealEntry': _rows(ENTRIES),
    })


def main():
    m = _mgr()
    print('nmp-5 seed integrity')
    check('29 curated activities',
          len(SEED_ACTIVITY_DEFINITIONS) == 29)
    by_code = {r['activity_code']: r for r in compendium_mets()}
    check('every seeded MET verbatim from the vendored CSV',
          all(d['met_value'] == float(by_code[d['activity_code']]
                                      ['met_value'])
              for d in SEED_ACTIVITY_DEFINITIONS))
    check('bands follow the 3/6 cutoffs',
          intensity_band(2.9) == 'light'
          and intensity_band(3.0) == 'moderate'
          and intensity_band(6.0) == 'vigorous')
    check('attribution rides every row',
          all('Compendium' in d['source']
              for d in SEED_ACTIVITY_DEFINITIONS))

    print('nmp-5 kcal math')
    r = activity_kcal(m, PERSON, SimpleNamespace(**LOGS[0]))
    # running-6mph = 9.3 MET x 80 kg x 0.5 h = 372
    check('kcal = MET x kg x h (9.3 x 80 x 0.5 = 372)',
          r['ok'] and abs(r['kcal'] - 372.0) < 0.1, str(r.get('kcal')))
    r2 = activity_kcal(m, PERSON, SimpleNamespace(**{
        **LOGS[0], 'perceived_intensity_factor': 2.0}))
    check('felt-intensity knob clamps to 1.3 and labels',
          r2['perceivedIntensityFactor'] == 1.3 and 'note' in r2)
    bad = activity_kcal(m, PERSON, SimpleNamespace(**{
        **LOGS[0], 'activity_name': 'no-such', 'activity_code': ''}))
    check('unknown activity refuses honestly', not bad['ok'])

    print('nmp-5 weekly summary')
    w = weekly_summary(m, PERSON)
    check('minutes bucketed by band (30+50 vig, 60 mod)',
          w['minutesByBand']['vigorous'] == 80.0
          and w['minutesByBand']['moderate'] == 60.0)
    check('divergence from stated minutes SUGGESTS, never applies',
          len(w['suggestions']) == 1
          and 'nothing auto-applied' in
          w['suggestions'][0]['suggestion'])

    print('nmp-5b timeline + timing (decision 14)')
    t = day_timeline(m, SimpleNamespace(**PLAN), 1)
    check('timeline sorted by clock (18:00 dinner first)',
          t['ok'] and t['timeline'][0]['time'] == '18:00')
    kinds = {e['kind'] for e in t['evaluations']}
    check('comfort-window fires (vigorous run 1 h after dinner), '
          'low confidence',
          'comfort-window' in kinds
          and all(e['confidence'] == 'low'
                  for e in t['evaluations']
                  if e['kind'] == 'comfort-window'))
    check('late large meal flagged as chrononutrition (low, '
          'small-effect wording)',
          any(e['kind'] == 'chrononutrition'
              and 'small effects' in e['note']
              for e in t['evaluations']))
    t2 = day_timeline(m, SimpleNamespace(**PLAN), 2)
    check('fasted vigorous session noted on day 2',
          any(e['kind'] == 'fasted-vigorous'
              for e in t2['evaluations']))
    check('long fasted run with no meal gets the performance note',
          any(e['kind'] == 'performance' for e in t2['evaluations']))
    check('honesty: trajectory stays energy-balance-driven',
          'energy-balance' in t['honesty'])

    print('nmp-5b fasted-exercise facts')
    f = fasted_exercise_facts()
    check('does/does-not/caveats/citations all present',
          f['doesDo'] and f['doesNotDo'] and f['caveats']
          and len(f['citations']) == 2)
    check('no weight multiplier promised anywhere',
          any('no timing multiplier' in d for d in f['doesNotDo']))

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-5/5b activity + timing hold together')


if __name__ == '__main__':
    main()
