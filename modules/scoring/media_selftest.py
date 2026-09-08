"""
Selftest — scr-15: media accountability for accuracy to data.

Run from polari-framework/:
    python3 -m scoring.media_selftest

Covers: claim checking against engine-resolved measurements (exact /
accurate / wrong bands, hand-computed relative errors, provenance of
the measured value travels); 'unverifiable' honesty (missing term,
missing data — the refusal names what's absent, outlets are never
penalized for what the data cannot check); editable AccuracyPolicy
bands actually recalibrate verdicts; outlet accuracy records (band
distribution, mean error, per-term breakdown).
"""

import json
from types import SimpleNamespace

from scoring.agreement_policy_basis import SEED_AGREEMENT_POLICIES
from scoring.media_accuracy_basis import (
    SEED_ACCURACY_POLICIES, SEED_FACTUAL_CLAIMS, SEED_MEDIA_OUTLETS,
    check_claim, outlet_accuracy,
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


def _mgr():
    return SimpleNamespace(objectTables={
        'ScoreTerm': _rows(SEED_SCORE_TERMS),
        'ScoreContext': _rows(SEED_SCORE_CONTEXTS),
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS + SEED_MEDIA_OUTLETS),
        'ContextualizedValue': _rows(SEED_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_SCORE_CONCEPTS),
        'AgreementPolicy': _rows(SEED_AGREEMENT_POLICIES),
        'AccuracyPolicy': _rows(SEED_ACCURACY_POLICIES),
        'FactualClaim': _rows(SEED_FACTUAL_CLAIMS),
        'FEMModelDefinition': {},
    })


if __name__ == '__main__':
    print('\nscr-15: media accuracy against the data\n')

    print('claim checking (banded relative error)')
    m = _mgr()
    result = check_claim(m, 'claim-ledger-texas-lfpr')
    check('exact claim: 63.2 vs measured 63.2, error 0',
          result['ok'] and result['verdict'] == 'exact'
          and result['measuredValue'] == 63.2
          and result['relativeError'] == 0.0)
    check('measured value provenance travels',
          'valueRow' in result['measuredSource'])
    result = check_claim(m, 'claim-ledger-dc-wage')
    check('17.00 vs 17.50 ≈ 2.86% = accurate (hand-computed)',
          result['verdict'] == 'accurate'
          and abs(result['relativeError'] - 0.5 / 17.5) < 1e-6,
          f"got {result['relativeError']}")
    result = check_claim(m, 'claim-signal-dc-union')
    check('25 vs 18.7 ≈ 33.7% = wrong',
          result['verdict'] == 'wrong'
          and abs(result['relativeError'] - 6.3 / 18.7) < 1e-6)
    check('both numbers stay shown with the band',
          result['claimedValue'] == 25.0
          and result['measuredValue'] == 18.7)

    print('\nunverifiable honesty')
    result = check_claim(m, 'claim-signal-childcare')
    check('unknown term = unverifiable naming the missing vocabulary',
          result['ok'] and result['verdict'] == 'unverifiable'
          and 'childcare-cost-index' in result['reason'])
    m.objectTables['FactualClaim'][90] = SimpleNamespace(
        name='claim-no-data', outlet_name='demo-signal-times',
        statement='x', term_name='minimum-wage',
        subject_name='texas',
        context_names_json=json.dumps(['q1-2022']),
        claimed_value=7.25, evidence_names_json='[]',
        pre_normalized_value=None)
    # q1-2022 IS servable (year full-covers) — so pick a frame with
    # no coverage instead: a 2030 context.
    m.objectTables['ScoreContext'][90] = SimpleNamespace(
        name='year-2030', context_type='timeframe', parent_name='',
        value_json=json.dumps(
            {'start': '2030-01-01', 'end': '2030-12-31'}),
        pre_normalized_value=None)
    m.objectTables['FactualClaim'][90].context_names_json = \
        json.dumps(['year-2030'])
    result = check_claim(m, 'claim-no-data')
    check('no data for the frame = unverifiable with the engine '
          'refusal',
          result['verdict'] == 'unverifiable' and result['reason'])
    result = check_claim(m, 'no-such-claim')
    check('unknown claim honest 404 with known list',
          not result['ok'] and 'knownClaims' in result)
    m.objectTables['FactualClaim'][91] = SimpleNamespace(
        name='claim-no-value', outlet_name='demo-signal-times',
        statement='x', term_name='minimum-wage',
        subject_name='texas', context_names_json='[]',
        claimed_value=None, pre_normalized_value=None)
    result = check_claim(m, 'claim-no-value')
    check('missing claimed_value refused naming the knob',
          not result['ok']
          and result['suggestion']['knob']
          == 'FactualClaim.claimed_value')

    print('\neditable accuracy bands')
    m = _mgr()
    for row in m.objectTables['AccuracyPolicy'].values():
        row.error_bands_json = json.dumps([
            {'label': 'spot-on', 'max': 0.001},
            {'label': 'off', 'max': 1e9}])
    result = check_claim(m, 'claim-ledger-dc-wage')
    check('editing the policy row recalibrates the verdict '
          '(accurate → off)',
          result['verdict'] == 'off')

    print('\noutlet accuracy records')
    m = _mgr()
    record = outlet_accuracy(m, 'demo-daily-ledger')
    check('ledger: 2 checked, exact + accurate, mean error '
          '≈ 1.43%',
          record['ok'] and record['checked'] == 2
          and record['verdicts'] == {'exact': 1, 'accurate': 1}
          and abs(record['meanRelativeError']
                  - (0.5 / 17.5) / 2) < 1e-6)
    record = outlet_accuracy(m, 'demo-signal-times')
    check('signal: wrong + unverifiable both counted, unverifiable '
          'not averaged in',
          record['verdicts'].get('wrong') == 1
          and record['unverifiable'] == 1
          and abs(record['meanRelativeError'] - 6.3 / 18.7) < 1e-6)
    check('per-term breakdown travels',
          record['perTerm']['union-participation']['claims'] == 1)
    check('the note says outlets are not penalized for unverifiable',
          'not penalized' in record['note'])
    record = outlet_accuracy(m, 'alabama')
    check('subject with no claims refuses with the FactualClaim knob',
          not record['ok']
          and record['suggestion']['knob'] == 'FactualClaim')
    record = outlet_accuracy(m, 'no-such')
    check('unknown outlet honest 404', not record['ok'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
