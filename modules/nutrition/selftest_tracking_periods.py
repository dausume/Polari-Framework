"""
@module nutrition.selftest_tracking_periods

mpt selftest — the per-person tracking condensation: week / month
buckets of means per logged day, verdicts against the person's own
lines, consistency across well-logged buckets, low-confidence
buckets named, gap days never counted as zero; the "log it" form
proposals (validated) and their solutions through the REAL engine
writing IntakeRecord / WeightObservation rows (dedupe by name).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_tracking_periods
"""

import json
import sys
from types import SimpleNamespace

from nutrition.calendar_seed import SEED_MEALPLAN_ANALYSES, SEED_MEALPLAN_SOLUTIONS
from nutrition.fdc_seed import SEED_FDC_FOOD_ITEMS, SEED_FDC_NUTRIENT_CONTENTS
from nutrition.intake_basis import SEED_INTAKE_RECORDS
from nutrition.meal_basis import SEED_MEAL_TEMPLATES, SEED_VARIATIONS
from nutrition.person_seed import SEED_HOUSEHOLDS, SEED_PERSONS
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from nutrition.threshold_basis import SEED_EATING_PATTERNS
from nutrition.tolerance_basis import SEED_TOLERANCE_THRESHOLDS
from nutrition.tracking_periods import (
    intake_proposal, period_summary, weight_proposal,
)
from nutrition.weight_basis import SEED_WEIGHT_OBSERVATIONS
from polariNoCode import graph_builder as gb

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {f'{i}': SimpleNamespace(id=f'{i}', **r) for i, r in enumerate(seed_list)}


class _DB:
    def saveInstanceInDB(self, inst):
        return True


def _manager():
    return SimpleNamespace(objectTables={
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS), 'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES), 'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES), 'VariationDefinition': _rows(SEED_VARIATIONS),
        'PersonProfile': _rows(SEED_PERSONS), 'HouseholdProfile': _rows(SEED_HOUSEHOLDS),
        'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
        'ToleranceThreshold': _rows(SEED_TOLERANCE_THRESHOLDS),
        'IntakeRecord': _rows(SEED_INTAKE_RECORDS), 'WeightObservation': _rows(SEED_WEIGHT_OBSERVATIONS),
        'NutrientReference': {}, 'DietaryNutrient': {}, 'PersonThreshold': {},
        'AnalysisDefinition': _rows(SEED_MEALPLAN_ANALYSES),
        'SolutionDefinition': _rows(SEED_MEALPLAN_SOLUTIONS),
        'EventTrigger': {}, 'TriggerFiring': {}, 'PeriodIntakeMetric': {},
    }, db=_DB())


def main():
    mgr = _manager()
    print('mpt — tracking over time')
    wk = period_summary(mgr, 'demo-alex', 'week')
    check('week buckets: the 2 logged days (Aug 31, Sep 1) fall in ONE Monday-start week; means are '
          'per logged day; the bucket is low-confidence (< 3 days) and says so',
          wk['ok'] and wk['count'] >= 1 and wk['periods'][-1]['daysLogged'] == 2
          and wk['periods'][-1]['periodStart'] == '2026-08-31' and wk['periods'][-1]['lowConfidence'],
          f"{[(p['periodStart'], p['daysLogged'], p['lowConfidence']) for p in wk['periods']]}")
    p = wk['periods'][-1]
    check('the bucket carries calories / protein / carbohydrate / fiber / sodium means, max-GL and acid-share means',
          all(p.get(k) is not None for k in ('caloriesMean', 'proteinMean', 'carbohydrateMean',
                                              'fiberMean', 'sodiumMean', 'maxMealGlMean', 'maxMealAcidShareMean')),
          str({k: p.get(k) for k in ('caloriesMean', 'sodiumMean', 'maxMealGlMean')}))
    check('~580 kcal/day logged is judged "too little" against Alex\'s calorie envelope (his own line)',
          any(v['metric'] == 'calories' and v['direction'] == 'too little' for v in p['verdicts']),
          str(p['verdicts']))
    check('weight: the observations in the bucket give a mean and a first→last delta',
          any(q.get('weightKgMean') for q in wk['periods']) and any(q.get('weightKgDelta') is not None
                                                                     for q in wk['periods']))
    check('consistency: with no well-logged bucket yet, nothing is called a pattern (said plainly)',
          all(not c['consistent'] and 'not yet a pattern' in c['reading'] for c in wk['consistency']),
          str(wk['consistency'][:2]))
    mo = period_summary(mgr, 'demo-alex', 'month')
    check('month buckets: Aug and Sep separate; days in period = the month length',
          mo['ok'] and {q['periodStart'] for q in mo['periods']} >= {'2026-08-01', '2026-09-01'}
          and any(q['daysInPeriod'] == 31 for q in mo['periods']), str([(q['periodStart'], q['daysInPeriod']) for q in mo['periods']]))
    check('"sweets" are read through GL + carbohydrate and the payload SAYS there is no sugars column',
          'no sugars column' in wk['honesty'])
    check('a duck-typed manager skips the cache and REPORTS it',
          period_summary(mgr, 'demo-alex', 'week', persist=True)['metricCache']['cached'] is False)

    # --- a consistent pattern: 3 weeks of salty days -----------------
    salty = _manager()
    salty.objectTables['ToleranceThreshold'] = _rows([
        {'name': 'sodium-cdrr-day', 'substance': 'sodium', 'period': 'day', 'threshold_amount': 50.0,
         'unit': 'mg', 'per_kg_body_mass': False, 'symptom': '', 'citation': 'test: a 50 mg line',
         'confidence': 'test', 'qualifier': '', 'is_prior': True, 'provenance_id': '', 'notes': ''}])
    recs = []
    for i, d in enumerate(['2026-08-10', '2026-08-11', '2026-08-12', '2026-08-17', '2026-08-18', '2026-08-19',
                           '2026-08-24', '2026-08-25', '2026-08-26']):
        recs.append({'name': f'r{i}', 'person_name': 'demo-alex', 'date': d, 'slot': 'dinner',
                     'template_name': 'chicken-bowl-dinner', 'variation_name': 'chicken-bowl-dinner-base',
                     'scale': 1.0, 'time_hhmm': '', 'source': 'logged', 'plan_entry_name': '',
                     'is_prior': False, 'provenance_id': '', 'notes': ''})
    salty.objectTables['IntakeRecord'] = _rows(recs)
    s = period_summary(salty, 'demo-alex', 'week')
    sod = [c for c in s['consistency'] if c['metric'].startswith('sodium')]
    check('three well-logged weeks all over a (test) sodium line → "consistently too much: sodium (salty foods)"',
          sod and sod[0]['consistent'] and sod[0]['wellLoggedPeriods'] == 3 and 'consistently' in sod[0]['reading'],
          str(sod))

    # --- the log forms ------------------------------------------------
    ip = intake_proposal(mgr, 'demo-alex', '2026-09-02', 'lunch', 'chicken-bowl-dinner', '', 1.0, '12:30')
    check('intake proposal: validated row named person-date-slot with the base variation filled in',
          ip['ok'] and ip['proposals'][0]['name'] == 'demo-alex-2026-09-02-lunch'
          and ip['proposals'][0]['variation_name'] == 'chicken-bowl-dinner-base', str(ip))
    bad = intake_proposal(mgr, 'nobody', 'yesterday', 'tea', 'nope')
    check('a bad log refuses with EVERY problem named', not bad['ok'] and bad['error'].count(';') >= 3, bad['error'])
    wp = weight_proposal(mgr, 'demo-alex', '', 79.6, 'morning')
    check('weight proposal: blank date = today; 20–400 kg guard', wp['ok'] and wp['proposals'][0]['weight_kg'] == 79.6
          and not weight_proposal(mgr, 'demo-alex', '', 5)['ok'])
    sol = [x for x in SEED_MEALPLAN_SOLUTIONS if x['name'] == 'mealplan-log-intake'][0]
    n0 = len(mgr.objectTables['IntakeRecord'])
    t = gb.execute(json.loads(sol['definition']), manager=mgr,
                   params={'person': 'demo-alex', 'date': '2026-09-02', 'slot': 'lunch',
                           'template': 'chicken-bowl-dinner', 'variation': '', 'scale': 1, 'time': '12:30'})
    check('the "Log what I ate" form solution writes ONE IntakeRecord through the real engine and asks the page to refresh',
          t.status == 'completed' and len(mgr.objectTables['IntakeRecord']) == n0 + 1, f'{t.status} {t.error_summary}')
    t2 = gb.execute(json.loads(sol['definition']), manager=mgr,
                    params={'person': 'demo-alex', 'date': '2026-09-02', 'slot': 'lunch',
                            'template': 'chicken-bowl-dinner', 'variation': '', 'scale': 1, 'time': '12:30'})
    check('logging the same slot again reuses the row (dedupe by name)', t2.status == 'completed'
          and len(mgr.objectTables['IntakeRecord']) == n0 + 1)
    solw = [x for x in SEED_MEALPLAN_SOLUTIONS if x['name'] == 'mealplan-log-weight'][0]
    w0 = len(mgr.objectTables['WeightObservation'])
    tw = gb.execute(json.loads(solw['definition']), manager=mgr,
                    params={'person': 'demo-alex', 'date': '2026-09-02', 'weight_kg': 79.6, 'context': 'morning'})
    check('the "Log my weight" form solution writes a WeightObservation', tw.status == 'completed'
          and len(mgr.objectTables['WeightObservation']) == w0 + 1, f'{tw.status} {tw.error_summary}')
    wk2 = period_summary(mgr, 'demo-alex', 'week')
    check('the new log shows up in the week means (3 logged days now)',
          wk2['periods'][-1]['daysLogged'] == 3, str(wk2['periods'][-1]['daysLogged']))

    print(f'\n{len(failures)} failure(s)')
    for f in failures:
        print('  -', f)
    print('PASS: mpt tracking over time holds together' if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
