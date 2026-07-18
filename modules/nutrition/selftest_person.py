"""
Selftest — nut-1/3/4: nutrient vocabulary, person profiler (BMR/TDEE/
goal/needs), household aggregation.

Run from polari-framework/:
    python3 -m nutrition.selftest_person

Covers: vocabulary complete (all ~30, plant-unavailable flagged, every
nutrient has a reference); BMR matches hand-computed Mifflin-St Jeor;
Katch-McArdle engages when body fat is set + suggests it when absent;
higher activity -> higher TDEE; lose goal lowers the target but never
below the BMR floor (warns); metabolism_factor scales BMR; needs cover
all nutrients scaled to sex/age/period; household demand = sum of
members with per-member breakdown; missing member refuses.
"""

from types import SimpleNamespace

from nutrition.nutrient_seed import (
    SEED_DIETARY_NUTRIENTS, SEED_NUTRIENT_REFERENCES,
)
from nutrition.person_seed import SEED_HOUSEHOLDS, SEED_PERSONS
from nutrition.person_analysis import (
    bmr, calorie_target, nutrient_needs, tdee,
)
from nutrition.household_analysis import household_needs

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
        'NutrientReference': _rows(SEED_NUTRIENT_REFERENCES),
        'PersonProfile': _rows(SEED_PERSONS),
        'HouseholdProfile': _rows(SEED_HOUSEHOLDS),
    })


EXPECTED_NUTRIENTS = {
    'calories', 'carbohydrate', 'protein', 'healthy-fat', 'vitamin-a',
    'vitamin-b1', 'vitamin-b2', 'vitamin-b3', 'vitamin-b5', 'vitamin-b6',
    'vitamin-b7', 'vitamin-b9', 'vitamin-b12', 'vitamin-c', 'vitamin-d',
    'vitamin-e', 'vitamin-k', 'iron', 'calcium', 'magnesium', 'omega-3',
    'potassium', 'sodium', 'chloride', 'zinc', 'selenium', 'copper',
    'manganese', 'iodine', 'chromium', 'molybdenum', 'boron', 'silicon'}


if __name__ == '__main__':
    manager = _mgr()

    print('nut-1 vocabulary + references')
    names = {n['name'] for n in SEED_DIETARY_NUTRIENTS}
    check('all ~30 canonical nutrients present',
          EXPECTED_NUTRIENTS <= names,
          extra=str(sorted(EXPECTED_NUTRIENTS - names)) or '')
    ref_nutrients = {r['nutrient_name'] for r in SEED_NUTRIENT_REFERENCES}
    check('every nutrient has >=1 reference row',
          names <= ref_nutrients,
          extra=str(sorted(names - ref_nutrients)) or '')
    unavailable = {n['name'] for n in SEED_DIETARY_NUTRIENTS
                   if n['plant_availability'] == 'none'}
    check('B12/iodine/sodium/chloride flagged plant-unavailable',
          unavailable == {'vitamin-b12', 'iodine', 'sodium', 'chloride'},
          extra=str(sorted(unavailable)))

    print('nut-3 BMR (Mifflin-St Jeor)')
    alex = next(SimpleNamespace(**p) for p in SEED_PERSONS
                if p['name'] == 'demo-alex')
    # 10*80 + 6.25*178 - 5*34 + 5 = 800 + 1112.5 - 170 + 5 = 1747.5
    check('BMR matches hand-computed Mifflin-St Jeor',
          abs(bmr(alex)['value'] - 1747.5) < 0.5,
          extra=str(bmr(alex)['value']))
    check('Mifflin path suggests body-fat knob',
          bmr(alex)['suggestion'] is not None
          and 'body_fat_fraction' in bmr(alex)['suggestion']['knob'])
    alex_bf = SimpleNamespace(**dict(
        next(p for p in SEED_PERSONS if p['name'] == 'demo-alex'),
        body_fat_fraction=0.2))
    # Katch: 370 + 21.6 * (80*0.8=64) = 370 + 1382.4 = 1752.4
    check('Katch-McArdle engages with body fat set',
          bmr(alex_bf)['formula'].startswith('Katch')
          and abs(bmr(alex_bf)['value'] - 1752.4) < 0.5)
    alex_slow = SimpleNamespace(**dict(
        next(p for p in SEED_PERSONS if p['name'] == 'demo-alex'),
        metabolism_factor=0.9))
    check('metabolism_factor scales BMR',
          abs(bmr(alex_slow)['value'] - 1747.5 * 0.9) < 0.5)

    print('nut-3 TDEE + calorie target')
    check('moderate activity PAL 1.55 applied',
          abs(tdee(alex)['value'] - 1747.5 * 1.55) < 1.0)
    cal = calorie_target(alex)
    check('lose goal lowers target below TDEE',
          cal['value'] < cal['tdee'] and cal['deltaKcal'] < 0)
    # An extreme pace should clamp to the BMR floor + warn.
    alex_crash = SimpleNamespace(**dict(
        next(p for p in SEED_PERSONS if p['name'] == 'demo-alex'),
        goal='lose', goal_rate_kg_per_week=2.0, activity_level='sedentary'))
    crash = calorie_target(alex_crash)
    check('unsafe pace clamps to BMR floor + warns',
          crash['warning'] is not None
          and abs(crash['value'] - crash['floor']) < 0.5)

    print('nut-3 per-nutrient needs')
    needs = nutrient_needs(manager, alex, period='day')
    check('needs ok + cover all nutrients',
          needs['ok'] and EXPECTED_NUTRIENTS <= set(needs['needs']))
    check('protein scales per-kg (0.8 g/kg × 80 = 64 g)',
          abs(needs['needs']['protein']['amount'] - 64.0) < 0.5)
    check('male iron = 8 mg (sex-specific reference)',
          abs(needs['needs']['iron']['amount'] - 8.0) < 0.01)
    sam = next(SimpleNamespace(**p) for p in SEED_PERSONS
               if p['name'] == 'demo-sam')
    sam_needs = nutrient_needs(manager, sam, period='day')
    check('female iron = 18 mg (sex-specific)',
          abs(sam_needs['needs']['iron']['amount'] - 18.0) < 0.01)
    week = nutrient_needs(manager, alex, period='week')
    check('weekly protein = 7× daily',
          abs(week['needs']['protein']['amount']
              - 7 * 64.0) < 0.5)
    check('calories in needs = calorie target',
          abs(needs['needs']['calories']['amount']
              - cal['value']) < 0.5)
    check('plant-unavailable carried onto needs',
          needs['needs']['iodine']['plantAvailability'] == 'none')

    print('nut-4 household aggregation')
    hh = household_needs(manager, 'demo-household', period='day')
    check('household ok + 2 members', hh['ok']
          and hh['memberCount'] == 2)
    check('household iron = alex + sam (8 + 18 = 26 mg)',
          abs(hh['totals']['iron']['amount'] - 26.0) < 0.02)
    check('per-member breakdown present',
          set(hh['perMember']) == {'demo-alex', 'demo-sam'})
    check('household calorie/day = sum of members',
          abs(hh['calorieTargetPerDay']
              - (calorie_target(alex)['value']
                 + calorie_target(sam)['value'])) < 1.0)
    week_hh = household_needs(manager, 'demo-household', period='week')
    check('weekly household iron = 7× daily',
          abs(week_hh['totals']['iron']['amount'] - 7 * 26.0) < 0.1)

    print('honest refusals')
    bad = SimpleNamespace(objectTables={
        'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
        'NutrientReference': _rows(SEED_NUTRIENT_REFERENCES),
        'PersonProfile': {},
        'HouseholdProfile': _rows(SEED_HOUSEHOLDS)})
    check('household with unresolvable members refuses',
          not household_needs(bad, 'demo-household').get('ok'))
    check('unknown household refuses',
          not household_needs(manager, 'nope').get('ok'))
    check('bad period refuses',
          not nutrient_needs(manager, alex, period='decade').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
