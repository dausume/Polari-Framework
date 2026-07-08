"""
Selftest — context-based scoring (the Political Scorecard generalized).

Run from polari-framework/:
    python3 -m scoring.selftest_scoring

Covers: PARITY with the scorecard's Labor Quality spreadsheet sample
(same 2022 data, ranges, weights → same initialScores, same ranking,
DC on top at levelized 100); inversion for anti-competitive terms;
context matching by specificity; the arbitrary-data seam (objectRef
into another class's JSON blob resolves live; a dangling ref is an
honest absence, and missing terms stay in the denominator); honest
errors for unknown concepts and empty subject selections.
"""

from types import SimpleNamespace

from scoring.scoring_engine import (
    normalize_value, score_concept, select_value,
)
from scoring.scoring_seed import (
    SEED_CONTEXTUALIZED_VALUES, SEED_SCORE_CONCEPTS,
    SEED_SCORE_CONTEXTS, SEED_SCORE_SUBJECTS, SEED_SCORE_TERMS,
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


def _mgr(with_beeswax_result=True):
    tables = {
        'ScoreTerm': _rows(SEED_SCORE_TERMS),
        'ScoreContext': _rows(SEED_SCORE_CONTEXTS),
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS),
        'ContextualizedValue': _rows(SEED_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_SCORE_CONCEPTS),
        'MaterialScaleDefinition': {},
    }
    if with_beeswax_result:
        tables['MaterialScaleDefinition'] = {0: SimpleNamespace(
            name='beeswax@L1',
            parameters_json='{"engine": "fem.effective-conductivity",'
                            ' "result": {"effectiveK": 0.2593}}')}
    return SimpleNamespace(objectTables=tables)


#: Expected initialScores, hand-computed from the scorecard sample's
#: exact formula (weightedSum / 21).
EXPECTED = {
    'washington-dc': 0.924732,
    'california': 0.720064,
    'idaho': 0.438120,
    'texas': 0.157559,
    'alabama': 0.114809,
}


if __name__ == '__main__':
    print('\nContext-based scoring (scorecard generalization)\n')

    print('normalization')
    ok, v, spec = normalize_value(
        13.5, {'method': 'min-max', 'min': 5.0, 'max': 15.0}, False)
    check('anti-competitive inversion (13.5% poverty -> 0.15)',
          ok and abs(v - 0.15) < 1e-9, f'{v}')
    ok, v, spec = normalize_value(
        16.0, {'method': 'min-max', 'min': 7.25, 'max': 17.50}, True)
    check('min-max ($16 wage -> 0.853659)',
          ok and abs(v - 0.8536585) < 1e-6)
    ok, _, refusal = normalize_value(1.0, {'method': 'z-score'}, True)
    check('unknown method refused naming the knob',
          not ok and refusal['suggestion']['knob']
          == 'normalization_json')
    ok, _, refusal = normalize_value(
        1.0, {'method': 'min-max-auto'}, True, value_pool=[1.0])
    check('min-max-auto with a degenerate pool refused honestly',
          not ok and '>= 2 distinct' in refusal['error'])

    print('\nparity with the scorecard Labor Quality sample')
    report = score_concept(_mgr(), 'labor-quality')
    check('scores computed for all 5 states',
          report['ok'] and len(report['subjects']) == 5)
    by_name = {s['subject']: s for s in report['subjects']}
    for state, expected in EXPECTED.items():
        got = by_name[state]['initialScore']
        check(f'{state} initialScore parity ({expected})',
              abs(got - expected) < 1e-4, f'got {got}')
    ranking = [s['subject'] for s in report['subjects']]
    check('ranking DC > CA > ID > TX > AL',
          ranking == list(EXPECTED))
    check('DC levelized to 100',
          by_name['washington-dc']['levelizedScore'] == 100.0)
    check('total weight 21 + the count-divergence note travels',
          report['totalWeight'] == 21
          and 'divides by term count' in report['aggregationNote'])
    dc = by_name['washington-dc']
    check('breakdown carries raw + normalized + weighted + spec',
          all(('raw' in b and 'normalized' in b and 'weighted' in b
               and b['normalization']['method'] == 'min-max')
              for b in dc['breakdown'] if b['found']))
    check('no terms missing in the parity model',
          not dc['termsMissing'])

    print('\narbitrary-data seam (objectRef values)')
    report = score_concept(_mgr(), 'demo-material-conductivity')
    subjects = {s['subject']: s for s in report['subjects']}
    bee = subjects['beeswax-material']
    check('beeswax scores from the LIVE FEM result through the '
          'objectRef',
          not bee['termsMissing']
          and abs(bee['breakdown'][0]['raw'] - 0.2593) < 1e-9)
    check('objectRef source travels in the breakdown',
          'MaterialScaleDefinition/beeswax@L1'
          in bee['breakdown'][0]['source'])
    car = subjects['carnauba-material']
    check('carnauba honestly missing (no executed L1 row)',
          car['termsMissing'] == ['thermal-conductivity-score']
          and car['initialScore'] == 0.0)
    report = score_concept(_mgr(with_beeswax_result=False),
                           'demo-material-conductivity')
    bee = {s['subject']: s for s in report['subjects']}[
        'beeswax-material']
    check('dangling objectRef -> absence with the refusal, not a '
          'guess',
          bee['termsMissing'] and not bee['breakdown'][0]['found'])

    print('\ncontext selection')
    contexts = {getattr(r, 'name', ''): r
                for r in _mgr().objectTables['ScoreContext'].values()}
    broad = SimpleNamespace(context_names_json='["year-2022"]')
    specific = SimpleNamespace(
        context_names_json='["state-california", "year-2022"]')
    chosen = select_value([broad, specific], ['year-2022'], contexts)
    check('most specific value wins (state beats bare year)',
          chosen is specific)
    check('required context not held -> no match',
          select_value([broad], ['state-texas'], contexts) is None)

    print('\nhonest errors')
    bad = score_concept(_mgr(), 'no-such-concept')
    check('unknown concept named + known list',
          not bad['ok'] and 'labor-quality' in bad['knownConcepts'])

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} checks passed\n')
    raise SystemExit(1 if failed else 0)
