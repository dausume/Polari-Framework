"""
@module nutrition.selftest_weight

nmp-6 selftest — the Hall/Chow trajectory against the published
behavior: steady state stays flat; a deficit loses less than the
naive 3500-rule says (the model's core correction); the small-
deficit steady state approaches the Lancet ~22 kcal/day per kg
rule-of-thumb at long horizons; Forbes partitioning sends a fatter
body's imbalance more to fat; observations report drift with a
suggestion (never a silent recalibration); timing has no term.

Run from polari-framework/:  python3 -m nutrition.selftest_weight
"""

from types import SimpleNamespace

from nutrition.weight_trajectory import (observed_vs_projected,
                                         project_weight)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _person(**kw):
    base = dict(name='t', sex='male', age_years=30.0, weight_kg=90.0,
                height_cm=180.0, activity_level='moderate',
                goal='lose', goal_rate_kg_per_week=0.5,
                metabolism_factor=1.0, body_fat_fraction=0.25,
                pregnant_or_lactating=False,
                weekly_moderate_minutes=0.0,
                weekly_vigorous_minutes=0.0)
    base.update(kw)
    return SimpleNamespace(**base)


def main():
    p = _person()
    from nutrition.person_analysis import tdee
    maintenance = tdee(p)['value']

    print('nmp-6 model behavior')
    flat = project_weight(p, maintenance, 12)
    check('maintenance intake -> flat weight (<0.2 kg drift)',
          flat['ok'] and abs(flat['projectedKg'][-1]
                             - flat['projectedKg'][0]) < 0.2,
          str(flat['projectedKg'][-1]))
    cut = project_weight(p, maintenance - 500.0, 12,
                         include_naive=True)
    lost = cut['projectedKg'][0] - cut['projectedKg'][-1]
    naive_lost = cut['projectedKg'][0] - cut['naive3500Kg'][-1]
    check('-500 kcal/day x 12 wk loses a plausible 3.5-6 kg',
          3.5 <= lost <= 6.0, f'{lost:.2f}')
    check('Hall loses LESS than the naive 3500 rule (the core '
          'correction)', lost < naive_lost,
          f'hall {lost:.2f} vs naive {naive_lost:.2f}')
    check('naive curve carries its over-prediction label',
          'over-predicts' in cut['naive3500Label'])
    # Lancet rule-of-thumb: a small permanent deficit settles near
    # deltaEI/~22 kcal/kg/day eventually; at 3 years most of the way
    long = project_weight(p, maintenance - 220.0, 156)
    eventual = long['projectedKg'][0] - long['projectedKg'][-1]
    check('-220 kcal/day for 3 years -> ~7-11 kg (Lancet ~22 '
          'kcal/day/kg rule, 95%-by-3-years shape)',
          7.0 <= eventual <= 11.0, f'{eventual:.2f}')
    half = project_weight(p, maintenance - 220.0, 52)
    year1 = half['projectedKg'][0] - half['projectedKg'][-1]
    check('~half the eventual change lands in year 1',
          0.35 * eventual <= year1 <= 0.75 * eventual,
          f'y1 {year1:.2f} of {eventual:.2f}')

    print('nmp-6 partitioning + bands')
    lean = project_weight(_person(body_fat_fraction=0.12),
                          maintenance - 500.0, 12)
    fat = project_weight(_person(body_fat_fraction=0.40),
                         maintenance - 500.0, 12)
    check('Forbes: leaner body loses MORE total mass on the same '
          'deficit (lean tissue is energetically cheaper)',
          (lean['projectedKg'][0] - lean['projectedKg'][-1])
          > (fat['projectedKg'][0] - fat['projectedKg'][-1]))
    check('band brackets the projection',
          all(lo <= mid <= hi for lo, mid, hi in zip(
              cut['bandLowKg'], cut['projectedKg'],
              cut['bandHighKg'])))
    check('goal line present for a lose goal',
          'goalLineKg' in cut
          and cut['goalLineKg'][-1] < cut['goalLineKg'][0])
    noBf = project_weight(_person(body_fat_fraction=0.0),
                          maintenance, 4)
    check('missing body fat -> Deurenberg prior, labeled',
          'Deurenberg' in noBf['fatMassBasis'])
    check('timing has no term (honesty line, decision 14)',
          'timing' in cut['honesty'])

    print('nmp-6 observed vs projected')
    mgr = SimpleNamespace(objectTables={'WeightObservation': {
        0: SimpleNamespace(name='o1', person_name='t',
                           date='', day_index=28, weight_kg=93.0,
                           context='morning'),
        1: SimpleNamespace(name='o2', person_name='t',
                           date='', day_index=56, weight_kg=92.5,
                           context='morning'),
    }})
    r = observed_vs_projected(mgr, p, maintenance - 500.0, 12)
    check('observations joined with per-point drift',
          len(r['observations']) == 2
          and all('driftKg' in o for o in r['observations']))
    check('large drift -> suggestion, never silent recalibration',
          'driftSuggestion' in r
          and 'nothing recalibrates silently'
          in r['driftSuggestion'])
    bad = project_weight(p, 0.0, 12)
    check('zero intake refuses honestly', not bad['ok'])
    bad2 = project_weight(p, 2000.0, 0)
    check('zero horizon refuses honestly', not bad2['ok'])

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-6 weight trajectory holds together')


if __name__ == '__main__':
    main()
