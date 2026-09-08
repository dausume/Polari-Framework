"""
Selftest — scr-16: per-group bias analysis.

Run from polari-framework/:
    python3 -m scoring.bias_selftest

Covers: stance skew vs the all-groups consensus (opposed stances
named); assertion direction one-sidedness per target kind (small
samples flagged, bands editable); the vote-alignment confirmation-
bias read (self-serving vs counter-stance votes — the lobby's
invalid vote on an unfavorable assertion reads self-serving, the
research group's valid vote on the same assertion reads
evidence-driven); source quality (grades + scr-15 outlet accuracy
over what the group cites); honest refusals.
"""

import json
from types import SimpleNamespace

from scoring.agreement_policy_basis import SEED_AGREEMENT_POLICIES
from scoring.assertion_seed import (
    SEED_MEDIA_EVIDENCE, SEED_POLICY_SUBJECTS, SEED_SCORE_ASSERTIONS,
    SEED_VALIDITY_VOTES,
)
from scoring.contributors_basis import SEED_CONTRIBUTORS
from scoring.evidence_basis import SEED_EVIDENCE_POLICIES
from scoring.group_bias_basis import SEED_BIAS_POLICIES, group_bias_report
from scoring.media_accuracy_basis import (
    SEED_ACCURACY_POLICIES, SEED_FACTUAL_CLAIMS, SEED_MEDIA_OUTLETS,
)
from scoring.policy_votes_basis import SEED_COHORT_GROUPS
from scoring.scoring_seed import (
    SEED_CONTEXTUALIZED_VALUES, SEED_SCORE_CONCEPTS,
    SEED_SCORE_CONTEXTS, SEED_SCORE_GROUPS, SEED_SCORE_SUBJECTS,
    SEED_SCORE_TERMS,
)
from scoring.worldview_elections_basis import SEED_ASSEMBLY_GROUPS

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
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS
                              + SEED_POLICY_SUBJECTS
                              + SEED_MEDIA_OUTLETS),
        'ContextualizedValue': _rows(SEED_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_SCORE_CONCEPTS),
        'ScoreGroup': _rows(SEED_SCORE_GROUPS + SEED_ASSEMBLY_GROUPS
                            + SEED_COHORT_GROUPS),
        'AgreementPolicy': _rows(SEED_AGREEMENT_POLICIES),
        'BiasPolicy': _rows(SEED_BIAS_POLICIES),
        'AccuracyPolicy': _rows(SEED_ACCURACY_POLICIES),
        'FactualClaim': _rows(SEED_FACTUAL_CLAIMS),
        'Contributor': _rows(SEED_CONTRIBUTORS),
        'EvidencePolicy': _rows(SEED_EVIDENCE_POLICIES),
        'MediaEvidence': _rows(SEED_MEDIA_EVIDENCE),
        'ScoreAssertion': _rows(SEED_SCORE_ASSERTIONS),
        'AssertionValidityVote': _rows(SEED_VALIDITY_VOTES),
        'FEMModelDefinition': {},
    })


if __name__ == '__main__':
    print('\nscr-16: per-group bias analysis\n')

    print('vote alignment (the confirmation-bias read)')
    m = _mgr()
    report = group_bias_report(m, 'demo-political-group')
    alignment = report['voteAlignment']
    check("lobby's invalid vote on an unfavorable assertion = "
          'self-serving (rate 1.0)',
          report['ok'] and alignment['alignmentRate'] == 1.0
          and alignment['selfServing'] == 1
          and alignment['votes'][0]['favorableToGroup'] is False)
    check('one decisive vote = small sample, flagged not over-read',
          alignment['smallSample'] is True
          and alignment['decisiveVotes'] == 1)
    check('abstentions carry no direction — not counted',
          all(v['castVote'] in ('valid', 'invalid')
              for v in alignment['votes']))
    report = group_bias_report(m, 'demo-professional-group')
    alignment = report['voteAlignment']
    check("research group's valid vote on the same unfavorable "
          'assertion = counter-stance (rate 0.0, evidence-driven)',
          alignment['alignmentRate'] == 0.0
          and alignment['counterStance'] == 1
          and alignment['band'] == 'balanced')
    report = group_bias_report(m, 'demo-town-assembly')
    alignment = report['voteAlignment']
    check('jane (assembly): two counter-stance votes, rate 0.0',
          alignment['decisiveVotes'] == 2
          and alignment['alignmentRate'] == 0.0)

    print('\nassertion one-sidedness')
    m = _mgr()
    report = group_bias_report(m, 'demo-political-group')
    kinds = {r['targetKind']: r for r in report['oneSidedness']}
    check('lobby asserts only supports on policies — echo-chamber '
          'band, small sample flagged',
          kinds['policy']['supports'] == 2
          and kinds['policy']['harms'] == 0
          and kinds['policy']['band'] == 'echo-chamber'
          and kinds['policy']['smallSample'] is True)
    check('the assertions behind the read are named',
          'assert-fair-wage-min-wage'
          in kinds['policy']['assertions'])

    print('\nstance skew vs consensus')
    m = _mgr()
    # A one-member group holding minimum-wage NEGATIVE (dan) opposes
    # the consensus positive stance.
    m.objectTables['ScoreGroup'][90] = SimpleNamespace(
        name='dan-group', display_name='Dan bloc',
        group_type='custom',
        member_concept_names_json=json.dumps(['member-labor-dan']),
        member_contributor_names_json=json.dumps(
            ['demo-citizen-jane']),
        member_subject_names_json='[]', member_weights_json='',
        weights_provenance='', pre_normalized_value=None)
    report = group_bias_report(m, 'dan-group')
    skew = {t['key']: t for t in report['stanceSkew']['terms']}
    check('dan bloc opposes consensus on minimum-wage',
          skew['minimum-wage']['reading'] == 'opposed'
          and skew['minimum-wage']['groupStance'] == -1
          and skew['minimum-wage']['consensusStance'] == 1
          and report['stanceSkew']['opposedTerms'] == 1)
    check('non-opposed terms read by emphasis band with both shares '
          'shown',
          all('groupShare' in t and 'consensusShare' in t
              for t in report['stanceSkew']['terms']))

    print('\nsource quality')
    m = _mgr()
    report = group_bias_report(m, 'demo-political-group')
    source = report['sourceQuality']
    check('grade distribution over cited evidence',
          source['gradeDistribution']
          == {'official-record': 1, 'contemporaneous-report': 1})
    check('unevidenced assertions counted',
          source['unevidencedAssertions'] == 1)
    signal = source['outletsCited'].get('demo-signal-times', {})
    check('cited outlet carries its scr-15 accuracy record '
          '(mean error ≈ 33.7%)',
          signal.get('citations') == 1
          and abs(signal.get('meanRelativeError') - 6.3 / 18.7)
          < 1e-6)

    print('\neditable bands + honest refusals')
    m = _mgr()
    for row in m.objectTables['BiasPolicy'].values():
        row.alignment_bands_json = json.dumps(
            [{'label': 'anything-goes', 'max': 1.0}])
    report = group_bias_report(m, 'demo-political-group')
    check('editing the BiasPolicy row recalibrates the alignment '
          'band',
          report['voteAlignment']['band'] == 'anything-goes')
    report = group_bias_report(m, 'demo-assembly-labor-committee')
    check('group without member contributors refuses naming the knob',
          not report['ok']
          and 'member_contributor_names_json'
          in report['suggestion']['knob'])
    report = group_bias_report(m, 'no-such')
    check('unknown group honest 404 with known list',
          not report['ok'] and 'knownGroups' in report)

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
