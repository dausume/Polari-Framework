"""
Selftest — scr-12a: survival-cost intake walkthrough.

Run from polari-framework/:
    python3 -m scoring.selftest_survival

Covers: the wizard generated FROM the editable CostCategory rows
(household knobs, bank-app method, per-category guidance; editing a
row edits the wizard); profile submission (validation refusals name
their knobs, skipped categories are honest completeness gaps,
amounts land as engine-native ContextualizedValues, overwrite is
explicit); the area report (per-category means/medians, subtotals by
kind, pseudo-tax share, small samples flagged).
"""

import json
from types import SimpleNamespace

from scoring.contributors import SEED_CONTRIBUTORS
from scoring.scoring_seed import (
    SEED_CONTEXTUALIZED_VALUES, SEED_SCORE_CONTEXTS,
    SEED_SCORE_SUBJECTS, SEED_SCORE_TERMS,
)
from scoring.survival_costs import (
    SEED_COST_CATEGORIES, SEED_COST_TERMS, SEED_SURVIVAL_PROFILES,
    submit_survival_profile, survival_report, survival_walkthrough,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**{'pre_normalized_value': None, **r})
            for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'ScoreTerm': _rows(SEED_SCORE_TERMS + SEED_COST_TERMS),
        'ScoreContext': _rows(SEED_SCORE_CONTEXTS),
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS),
        'ContextualizedValue': _rows(SEED_CONTEXTUALIZED_VALUES),
        'Contributor': _rows(SEED_CONTRIBUTORS),
        'CostCategory': _rows(SEED_COST_CATEGORIES),
        'SurvivalCostProfile': _rows(SEED_SURVIVAL_PROFILES),
    })


def _patch_factories(m):
    """treeObject construction needs a live manager — stand in."""
    import scoring.survival_costs as mod

    def _factory(class_name):
        def make(manager=None, **fields):
            row = SimpleNamespace(**fields)
            table = m.objectTables.setdefault(class_name, {})
            table[f'ing-{len(table)}'] = row
            return row
        return make
    originals = (mod.ScoreSubject, mod.ContextualizedValue,
                 mod.SurvivalCostProfile)
    mod.ScoreSubject = _factory('ScoreSubject')
    mod.ContextualizedValue = _factory('ContextualizedValue')
    mod.SurvivalCostProfile = _factory('SurvivalCostProfile')
    return mod, originals


if __name__ == '__main__':
    print('\nscr-12a: survival-cost walkthrough\n')

    print('the wizard (generated from the vocabulary)')
    m = _mgr()
    wizard = survival_walkthrough(m)
    check('household knobs first (size, workers, cars NEEDED)',
          wizard['ok']
          and [k['knob'] for k in wizard['householdKnobs']]
          == ['household_size', 'workers', 'cars_needed'])
    check('the bank-app method is the instruction',
          'bank app' in wizard['method']
          and 'ONE month' in wizard['method'])
    steps = {s['category']: s for s in wizard['steps']}
    check('8 seeded steps in sort order, housing first',
          len(wizard['steps']) == 8
          and wizard['steps'][0]['category'] == 'housing')
    check('every step carries guidance + examples + kind',
          all(s['guidance'] and s['examples'] and s['kind']
              for s in wizard['steps']))
    check('uncancellable subscriptions seeded as pseudo-tax with '
          'the contestable framing in its description',
          steps['uncancellable-subscriptions']['kind'] == 'pseudo-tax'
          and 'contestable' in
          steps['uncancellable-subscriptions']['description'])
    for row in m.objectTables['CostCategory'].values():
        if row.name == 'housing':
            row.guidance = 'EDITED GUIDANCE'
    wizard = survival_walkthrough(m)
    check('editing a category row edits the wizard',
          wizard['steps'][0]['guidance'] == 'EDITED GUIDANCE')

    print('\nsubmission (validation, gaps, engine-native values)')
    m = _mgr()
    mod, originals = _patch_factories(m)
    try:
        result = mod.submit_survival_profile(m, {
            'contributor': 'demo-labor-lobby',
            'location': 'state-california', 'month': 'q2-2022',
            'household_size': 2, 'workers': 2, 'cars_needed': 1,
            'entries': {
                'housing': 2100, 'utilities': 240, 'food': 550,
                'transport-work': {'amount': 380, 'notes': '1 car'},
                'healthcare': 400,
                'uncancellable-subscriptions': 25,
            }})
        check('profile lands with total + honest gaps',
              result['ok'] and result['totalMonthly'] == 3695.0
              and 'childcare' in result['skipped']
              and result['requiredGaps'] == [])
        check('one engine-native value per entered category',
              len(result['valuesWritten']) == 6
              and 'cost-housing-monthly@household-demo-labor-lobby'
                  '-q2-2022' in result['valuesWritten'])
        row = next(
            r for r in m.objectTables['ContextualizedValue'].values()
            if getattr(r, 'term_name', '') == 'cost-housing-monthly')
        check('values carry contexts + contributor attribution',
              json.loads(row.context_names_json)
              == ['state-california', 'q2-2022']
              and row.contributed_by == 'demo-labor-lobby')
        again = mod.submit_survival_profile(m, {
            'contributor': 'demo-labor-lobby',
            'location': 'state-california', 'month': 'q2-2022',
            'entries': {'housing': 1}})
        check('re-submit refuses without the overwrite knob',
              not again['ok']
              and again['suggestion']['knob'] == 'overwrite')
        result = mod.submit_survival_profile(m, {
            'contributor': 'demo-labor-lobby',
            'location': 'state-california', 'month': 'q2-2022',
            'entries': {'housing': 100, 'rocket-fuel': 900}})
        check('unknown category refused with the vocabulary',
              not result['ok']
              and 'rocket-fuel' in result['error']
              and 'housing' in result['knownCategories'])
        result = mod.submit_survival_profile(m, {
            'contributor': 'nobody', 'location': 'state-texas',
            'month': 'q1-2022', 'entries': {'housing': 1}})
        check('unknown contributor refused pointing at pseudonyms',
              not result['ok']
              and 'pseudonym' in result['suggestion']['action'])
        result = mod.submit_survival_profile(m, {
            'contributor': 'demo-citizen-jane',
            'location': 'mars-colony', 'month': 'q1-2022',
            'entries': {'housing': 1}})
        check('unknown contexts refused (never auto-invented)',
              not result['ok'] and 'mars-colony' in result['error'])
        result = mod.submit_survival_profile(m, {
            'contributor': 'demo-citizen-jane',
            'location': 'state-texas', 'month': 'q2-2022',
            'entries': {'housing': 'lots', 'food': -5,
                        'utilities': 200}})
        check('bad amounts refused per-entry, good ones land',
              result['ok'] and len(result['refused']) == 2
              and result['entered'] == ['utilities'])
    finally:
        (mod.ScoreSubject, mod.ContextualizedValue,
         mod.SurvivalCostProfile) = originals

    print('\narea report (subtotals by kind, pseudo-tax share)')
    m = _mgr()
    report = survival_report(m, 'state-texas', 'q1-2022')
    check('2 seeded texas households, small sample flagged',
          report['ok'] and report['profiles'] == 2
          and report['smallSample'] is True)
    check('total stats (mean of 4295 + 2540 = 3417.5, median same)',
          report['totalMonthly']['mean'] == 3417.5
          and report['totalMonthly']['median'] == 3417.5)
    housing = next(c for c in report['categories']
                   if c['category'] == 'housing')
    check('per-category stats with entered-by counts',
          housing['mean'] == 1250.0 and housing['enteredBy'] == 2)
    subtotals = report['subtotalsByKind']
    check('subtotals split by kind knob (survival / work-required / '
          'pseudo-tax)',
          set(subtotals) == {'survival', 'work-required',
                             'pseudo-tax'}
          and subtotals['pseudo-tax'] == 37.5)
    check('pseudo-tax share computed against the mean total',
          abs(report['pseudoTaxShare']
              - 37.5 / sum(subtotals.values())) < 1e-4)
    check('the note names the classification knob',
          'CostCategory' in report['note'])
    report = survival_report(m, 'state-alabama')
    check('area without profiles refuses pointing at submit',
          not report['ok'] and 'submit' in
          report['suggestion']['knob'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
