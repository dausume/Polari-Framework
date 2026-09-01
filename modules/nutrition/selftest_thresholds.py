"""
@module nutrition.selftest_thresholds

nmp-1 selftest — the threshold layer: obesity classification (BMI
band, body-fat override, waist flag), minutes-mode TDEE (decision 6),
the calorie envelope + per-slot bands (decision 7 / Q5 fractions),
per-person thresholds derived from the DRI life-stage rows (EAR/UL
sides, pregnancy rows, human override wins).

Run from polari-framework/:  python3 -m nutrition.selftest_thresholds
Stdlib-only; duck-typed manager over the seed lists.
"""

from types import SimpleNamespace

from nutrition.dri_seed import SEED_DRI_REFERENCES
from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
from nutrition.person_analysis import tdee
from nutrition.threshold_basis import SEED_EATING_PATTERNS
from nutrition.threshold_analysis import (calorie_envelope,
                                          obesity_classification,
                                          person_thresholds)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(extra=None):
    tables = {
        'DietaryNutrient': _rows(SEED_DIETARY_NUTRIENTS),
        'NutrientReference': _rows(SEED_DRI_REFERENCES),
        'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
        'PersonThreshold': _rows(extra or []),
    }
    return SimpleNamespace(objectTables=tables)


def _person(**kw):
    base = dict(name='t', sex='male', age_years=30.0, weight_kg=80.0,
                height_cm=180.0, activity_level='moderate',
                goal='maintain', goal_rate_kg_per_week=0.0,
                metabolism_factor=1.0, body_fat_fraction=0.0,
                pregnant_or_lactating=False, eating_pattern='3-meal',
                weekly_moderate_minutes=0.0,
                weekly_vigorous_minutes=0.0, life_stage='',
                waist_cm=0.0)
    base.update(kw)
    return SimpleNamespace(**base)


def main():
    print('nmp-1 obesity classification')
    o = obesity_classification(_person())  # BMI 24.7
    check('80kg/180cm male = normal band', o['bmiBand'] == 'normal'
          and o['classification'] == 'normal')
    o = obesity_classification(_person(weight_kg=100.0))  # 30.9
    check('100kg/180cm = obesity-class-1',
          o['bmiBand'] == 'obesity-class-1')
    o = obesity_classification(
        _person(weight_kg=100.0, body_fat_fraction=0.15))
    check('measured body fat 15% outranks the BMI band',
          o['basis'] == 'body-fat'
          and o['classification'] == 'not-obese-by-body-fat')
    o = obesity_classification(_person(waist_cm=110.0))
    check('waist 110cm male flags risk (cut 102)',
          o.get('waistRiskFlag') is True)
    o = obesity_classification(_person(height_cm=0.0))
    check('missing height refuses honestly', not o['ok'])

    print('nmp-1 minutes-mode TDEE (decision 6)')
    t_pal = tdee(_person())
    check('no minutes -> pal mode', t_pal['mode'] == 'pal')
    t_min = tdee(_person(weekly_moderate_minutes=150.0))
    check('minutes -> minutes mode, labeled',
          t_min['mode'] == 'minutes')
    # 150 min moderate: (4-1) x 80kg x 2.5h / 7d = 85.7 kcal/day
    check('exercise kcal math = (MET-1) x kg x h / 7',
          abs(t_min['exerciseKcalPerDay'] - 85.7) < 0.1,
          str(t_min['exerciseKcalPerDay']))

    print('nmp-1 calorie envelope (decision 7)')
    m = _mgr()
    e = calorie_envelope(m, _person())
    check('envelope ok with slots', e['ok'] and len(e['slots']) == 3)
    check('min >= BMR floor', e['minDailyKcal'] >= e['bmrFloor'])
    check('max = TDEE + 500', abs(
        e['maxDailyKcal'] - (e['tdee'] + 500.0)) < 0.1)
    check('3-meal fractions 25/35/40',
          [s['fraction'] for s in e['slots']] == [0.25, 0.35, 0.40])
    check('slot bands scale the daily band',
          abs(e['slots'][2]['maxKcal']
              - e['maxDailyKcal'] * 0.40) < 0.1)
    e2 = calorie_envelope(m, _person(eating_pattern='no-such'))
    check('unknown pattern -> honest slotsError',
          'slotsError' in e2)

    print('nmp-1 person thresholds')
    r = person_thresholds(m, _person(), period='day')
    check('ok + honesty line', r['ok'] and 'general-population'
          in r['honesty'])
    iron = r['thresholds']['iron']
    check('male iron: min=EAR 6, target=RDA 8, max=UL 45',
          (iron['min'], iron['target'], iron['max'])
          == (6.0, 8.0, 45.0))
    check('protein target scales per-kg (0.8 x 80 = 64 g)',
          r['thresholds']['protein']['target'] == 64.0)
    vk = r['thresholds']['vitamin-k']
    check('AI nutrient: no EAR -> min 0, basis says so',
          vk['min'] == 0.0 and 'no EAR' in vk['basis']['min'])
    week = person_thresholds(m, _person(), period='week')
    check('week scales x7',
          week['thresholds']['iron']['target'] == 56.0)
    preg = person_thresholds(
        m, _person(sex='female', life_stage='pregnancy'), 'day')
    check('pregnancy picks the transcribed row (iron RDA 27)',
          preg['thresholds']['iron']['target'] == 27.0
          and preg['thresholds']['iron']['basis']['lifeStage']
          == 'pregnancy')
    check('DGA limits materialized against kcal target',
          any(l['name'] == 'added-sugar-share'
              and l.get('kcalPerDay', 0) > 0 for l in r['dgaLimits']))
    check('AMDR bands in grams',
          any(a['nutrient'] == 'protein'
              and a['minGramsPerDay'] > 0 for a in r['amdr']))
    ov = [{'name': 't-iron-day', 'person_name': 't',
           'nutrient_name': 'iron', 'period': 'day',
           'min_amount': 0.0, 'target_amount': 12.0,
           'max_amount': 0.0, 'unit': 'mg',
           'reason': 'doctor said so', 'is_prior': False}]
    r_ov = person_thresholds(_mgr(ov), _person(), 'day')
    iron_ov = r_ov['thresholds']['iron']
    check('human override wins per side, reason carried',
          iron_ov['target'] == 12.0
          and iron_ov['basis']['target'] == 'human override'
          and iron_ov['override']['reason'] == 'doctor said so'
          and iron_ov['max'] == 45.0)
    bad = person_thresholds(m, _person(), 'meal')
    check('per-meal period refuses (nmp-2/4 territory)',
          not bad['ok'])

    print()
    total = len(failures)
    if total:
        print(f'{FAIL}: {total} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-1 threshold layer holds together')


if __name__ == '__main__':
    main()
