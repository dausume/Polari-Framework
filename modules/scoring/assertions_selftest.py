"""
Selftest — scr-5: assertions + evidence + contributors + abstraction
+ specificity conformance + policy scoring.

Run from polari-framework/:
    python3 -m scoring.assertions_selftest

Covers: evidence-grade weighting off editable policy rows (strongest
citation wins, unevidenced labeled, dangling names surfaced);
assertion lifecycle (allowed/refused transitions, append-only
history); multi-round validity tallies through AgreementPolicy bands
with SUGGESTED transitions; abstraction matching (generic intent →
ranked term/concept suggestions, purpose-equivalence expansion, never
auto-bound); policy scoring parity (hand-computed), decorative/
unconfirmed/unbound exclusions all named, dependency carry-over +
cycle refusal; specificity conformance against the ENGINE's actual
selection; critical-context variance suggestions; contributor track
records (the lobby-accountability numbers).
"""

import json
from types import SimpleNamespace

from scoring.custom.abstraction import suggest_scores_for_assertion
from scoring.agreement_policy_basis import SEED_AGREEMENT_POLICIES
from scoring.assertion_seed import (
    SEED_MEDIA_EVIDENCE, SEED_POLICY_SUBJECTS, SEED_SCORE_ASSERTIONS,
    SEED_VALIDITY_VOTES,
)
from scoring.assertions_basis import tally_validity, transition_assertion
from scoring.contributors_basis import SEED_CONTRIBUTORS, contributor_record
from scoring.custom.data_ingestion import ingest_records
from scoring.evidence_basis import SEED_EVIDENCE_POLICIES, evidence_weight
from scoring.custom.policy_scoring import score_policy
from scoring.scoring_seed import (
    SEED_CONTEXTUALIZED_VALUES, SEED_SCORE_CONCEPTS,
    SEED_SCORE_CONTEXTS, SEED_SCORE_GROUPS, SEED_SCORE_SUBJECTS,
    SEED_SCORE_TERMS,
)
from scoring.custom.specificity import (
    check_concept_specificity, suggest_critical_contexts,
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
        'ScoreSubject': _rows(
            SEED_SCORE_SUBJECTS + SEED_POLICY_SUBJECTS),
        'ContextualizedValue': _rows(SEED_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_SCORE_CONCEPTS),
        'ScoreGroup': _rows(SEED_SCORE_GROUPS),
        'AgreementPolicy': _rows(SEED_AGREEMENT_POLICIES),
        'Contributor': _rows(SEED_CONTRIBUTORS),
        'EvidencePolicy': _rows(SEED_EVIDENCE_POLICIES),
        'MediaEvidence': _rows(SEED_MEDIA_EVIDENCE),
        'ScoreAssertion': _rows(SEED_SCORE_ASSERTIONS),
        'AssertionValidityVote': _rows(SEED_VALIDITY_VOTES),
        'FEMModelDefinition': {},
        'MaterialScaleDefinition': {},
    })


#: Hand-computed policy score for policy-fair-wage-act@labor-quality
#: (weights ×21 for exact fractions):
#:   min-wage:   +1 × (0.9 × 0.9 × 8)  = +6.48
#:   union-harm: −1 × (0.4 × 0.6 × 5)  = −1.20
#:   dependency: +1 × (0.5 × 0.9 × 21) = +9.45   (child stance +1)
#:   stance = 14.73/17.13 = 491/571; score = 531/571
EXPECTED_POLICY_SCORE = 531 / 571


if __name__ == '__main__':
    print('\nscr-5: assertions + evidence + policy accountability\n')

    print('evidence weighting (editable policy rows)')
    m = _mgr()
    w, detail = evidence_weight(
        m, ['evidence-fair-wage-hearing-record',
            'evidence-fair-wage-news'])
    check('strongest citation wins (official-record 0.9)',
          abs(w - 0.9) < 1e-9 and detail['grade'] == 'official-record')
    w, detail = evidence_weight(m, [])
    check("citing nothing = the policy's 'unevidenced' weight, "
          'labeled',
          abs(w - 0.1) < 1e-9 and detail['grade'] == 'unevidenced')
    w, detail = evidence_weight(
        m, ['evidence-fair-wage-news', 'no-such-evidence'])
    check('dangling evidence names surfaced, never silently ignored',
          detail['dangling'] == ['no-such-evidence']
          and abs(w - 0.6) < 1e-9)
    empty = SimpleNamespace(objectTables={'EvidencePolicy': {},
                                          'MediaEvidence': {}})
    w, detail = evidence_weight(empty, ['x'])
    check('no policy rows → weighting inactive (1.0) with a note',
          w == 1.0 and 'inactive' in detail['note'])

    print('\nassertion lifecycle (append-only history)')
    m = _mgr()
    r = transition_assertion(m, 'assert-fair-wage-generic',
                             'under-review', by='demo-research-group',
                             note='opening review')
    check('asserted → under-review allowed, history appended',
          r['ok'] and r['historyLength'] == 1
          and r['transition']['from'] == 'asserted')
    r = transition_assertion(m, 'assert-fair-wage-generic',
                             'asserted')
    check('under-review → asserted refused (no back-transition)',
          not r['ok'] and 'not allowed' in r['error'])
    r = transition_assertion(m, 'assert-fair-wage-generic',
                             'confirmed', by='demo-research-group')
    check('under-review → confirmed allowed, history grows',
          r['ok'] and r['historyLength'] == 2)
    r = transition_assertion(m, 'assert-fair-wage-min-wage',
                             'rejected')
    check("confirmed can only re-open via 'under-review' "
          '(suggestion names it)',
          not r['ok'] and 'under-review' in
          r['suggestion']['action'])
    r = transition_assertion(m, 'assert-fair-wage-min-wage',
                             'nonsense')
    check('unknown status refused with the vocabulary',
          not r['ok'] and 'asserted' in r['statuses'])
    r = transition_assertion(m, 'no-such-assertion', 'confirmed')
    check('unknown assertion honest 404', not r['ok'])

    print('\nvalidity voting (multi-round, banded, suggestions only)')
    m = _mgr()
    tally = tally_validity(m, 'assert-fair-wage-union-harm')
    check('two rounds tallied in order',
          tally['ok'] and [r['round'] for r in tally['rounds']]
          == [1, 2])
    r1 = tally['rounds'][0]
    check('round 1 exact tie = divisive, leaning tied',
          r1['valid'] == 1 and r1['invalid'] == 1
          and r1['band'] == 'divisive' and r1['leaning'] == 'tied')
    r2 = tally['rounds'][1]
    check('round 2: 2 valid, 1 abstain → consensus among decisive '
          'voters',
          r2['valid'] == 2 and r2['abstain'] == 1
          and r2['band'] == 'consensus')
    check("tally SUGGESTS 'confirmed', names the status knob",
          "'confirmed'" in tally['suggestion']['action']
          and tally['suggestion']['knob'] == 'ScoreAssertion.status')
    check('the note says suggestions never auto-apply',
          'SUGGEST' in tally['note'])

    print('\nabstraction matching (generic intent → suggestions)')
    m = _mgr()
    report = suggest_scores_for_assertion(m,
                                          'assert-fair-wage-generic')
    names = {(s['kind'], s['name']) for s in report['suggestions']}
    check('generic wage/labor intent finds the minimum-wage term',
          report['ok'] and ('term', 'minimum-wage') in names)
    check('…and the labor-quality concept',
          ('concept', 'labor-quality') in names)
    scores = [s['matchScore'] for s in report['suggestions']]
    check('suggestions ranked by match score',
          scores == sorted(scores, reverse=True))
    check('every suggestion names its binding knob',
          all(s['knob'] in ('ScoreAssertion.term_name',
                            'ScoreAssertion.concept_name')
              for s in report['suggestions']))
    check('the note says binding is never automatic',
          'never' in report['note'])
    # Purpose-equivalence: minimum-wage vouches for a declared
    # equivalent the intent never names.
    terms = m.objectTables['ScoreTerm']
    for row in terms.values():
        if row.name == 'minimum-wage':
            row.equivalent_terms_json = json.dumps(['living-wage'])
    terms[99] = SimpleNamespace(
        name='living-wage', display_name='Living Wage',
        description='', abstract_tags_json='[]',
        equivalent_terms_json='[]', pre_normalized_value=None)
    report = suggest_scores_for_assertion(m,
                                          'assert-fair-wage-generic')
    living = next((s for s in report['suggestions']
                   if s['name'] == 'living-wage'), None)
    check('purpose-equivalent term suggested with the vouching edge',
          living is not None
          and living['evidence'] == [{'equivalent-to': 'minimum-wage'}])
    bad = SimpleNamespace(name='assert-blank', intent='',
                          pre_normalized_value=None)
    m.objectTables['ScoreAssertion'][99] = bad
    report = suggest_scores_for_assertion(m, 'assert-blank')
    check('empty intent refused naming the intent knob',
          not report['ok']
          and report['suggestion']['knob'] == 'ScoreAssertion.intent')

    print('\npolicy scoring (assertion-weighted composition)')
    m = _mgr()
    report = score_policy(m, 'policy-fair-wage-act', 'labor-quality')
    check('hand-computed parity (531/571 ≈ 0.929947)',
          report['ok']
          and abs(report['score'] - EXPECTED_POLICY_SCORE) < 1e-4,
          f"got {report.get('score')}")
    check('three assertions used (supports + harms + dependency)',
          len(report['assertionsUsed']) == 3)
    used_by_name = {u['assertion']: u for u in report['assertionsUsed']}
    dep = used_by_name.get('assert-fair-wage-dependency', {})
    check('dependency carries the child policy score',
          dep.get('dependsOn') == 'policy-labor-standards-2020'
          and dep.get('childScore') == 1.0)
    harm = used_by_name.get('assert-fair-wage-union-harm', {})
    check('harms assertion contributes negative stance × term share',
          harm.get('stance') == -1
          and abs(harm.get('termShare', 0) - 5 / 21) < 1e-6)
    reasons = {e['assertion']: e['reason']
               for e in report['excluded']}
    check('decorative span excluded BY assertion',
          'decorative' in reasons.get('assert-fair-wage-preamble', ''))
    check('unconfirmed assertion excluded with its status named',
          "'asserted'" in reasons.get('assert-fair-wage-poverty', ''))
    check('unbound assertion excluded pointing at /suggestions',
          'unbound' in reasons.get('assert-fair-wage-generic', ''))
    check('every used entry carries quote + evidence grade',
          all(u.get('quote') and u.get('evidence', {}).get('grade')
              for u in report['assertionsUsed']))
    report = score_policy(m, 'policy-fair-wage-act', 'labor-quality',
                          include_statuses=('confirmed', 'asserted'))
    check('statuses knob widens inclusion explicitly (4 used)',
          len(report['assertionsUsed']) == 4)
    report = score_policy(m, 'alabama', 'labor-quality')
    check('subject with no assertions refuses with a suggestion',
          not report['ok'] and 'suggestion' in report)
    report = score_policy(m, 'policy-fair-wage-act', 'no-such')
    check('unknown concept honest error with known list',
          not report['ok'] and 'knownConcepts' in report)
    # Self-dependency: cycle refused, surfaced on the excluded list.
    m.objectTables['ScoreAssertion'][98] = SimpleNamespace(
        name='assert-self-loop',
        subject_name='policy-labor-standards-2020',
        assertion_type='dependency', direction='supports',
        strength=0.5,
        depends_on_subject='policy-labor-standards-2020',
        status='confirmed', pre_normalized_value=None)
    report = score_policy(m, 'policy-labor-standards-2020',
                          'labor-quality')
    loop = next((e for e in report['excluded']
                 if e['assertion'] == 'assert-self-loop'), None)
    check('dependency cycle refused, named on the excluded list',
          report['ok'] and loop is not None
          and 'cycle' in loop.get('error', ''))

    print('\nspecificity conformance (engine as oracle)')
    m = _mgr()
    report = check_concept_specificity(m, 'labor-quality')
    check('the parity concept is clean (year-grain data, year-grain '
          'ask)',
          report['ok'] and report['clean'], str(report['findings'][:2]))
    m.objectTables['ScoreConcept'][97] = SimpleNamespace(
        name='q1-labor', subject_kind='state',
        term_weights_json=json.dumps(
            [{'term': 'labor-force-participation-rate', 'weight': 1}]),
        required_context_names_json=json.dumps(['q1-2022']),
        subject_names_json='[]', pre_normalized_value=None)
    report = check_concept_specificity(m, 'q1-labor')
    kinds = {}
    for f in report['findings']:
        kinds.setdefault(f['kind'], []).append(f)
    coarse_subjects = {f['subject']
                       for f in kinds.get('less-time-specific', [])}
    check('quarter-grain ask: year-served states flagged '
          'less-time-specific',
          'alabama' in coarse_subjects and len(coarse_subjects) == 4)
    check('texas (measured quarterly) NOT flagged',
          'texas' not in coarse_subjects)
    check('uneven grain across subjects = specificity-imbalance',
          'specificity-imbalance' in kinds)
    check('findings diagnose, never block (note says so)',
          'never block' in report['note'])
    report = check_concept_specificity(m, 'no-such')
    check('unknown concept honest error', not report['ok'])

    print('\ncritical contexts (variance-scan suggestions)')
    m = _mgr()
    report = suggest_critical_contexts(m, 'labor-quality')
    year = [s for s in report['suggestions']
            if s['context'] == 'year-2022']
    check('year-2022 carries the full spread (states diverge '
          'within it)',
          report['ok'] and year
          and year[0]['divergenceRatio'] == 1.0)
    check('low-divergence slices filtered (texas quarterly LFPR)',
          not any(s['context'] == 'state-texas'
                  for s in report['suggestions']))
    check('suggestions name the required-contexts knob',
          all(s['knob'] == 'ScoreConcept.required_context_names_json'
              for s in report['suggestions']))

    print('\ncontributor track records (lobby accountability)')
    m = _mgr()
    record = contributor_record(m, 'demo-labor-lobby')
    check('lobby: 2 assertions, 1 reviewed, confirmationRate 1.0',
          record['ok']
          and record['assertions']['total'] == 2
          and record['assertions']['reviewed'] == 1
          and record['assertions']['confirmationRate'] == 1.0)
    check('lobby: votes + evidence attributed',
          record['validityVotesCast'] == 2
          and 'evidence-fair-wage-hearing-record'
          in record['evidenceSubmitted'])
    record = contributor_record(m, 'demo-citizen-jane')
    check('pseudonymous individual: record accrues to the pseudonym',
          record['ok'] and record['pseudonymous']
          and record['assertions']['total'] == 3)
    record = contributor_record(m, 'nobody')
    check('unknown contributor honest 404 with known list',
          not record['ok'] and 'demo-labor-lobby'
          in record['knownContributors'])
    # In-memory factory stand-in (the selftest_scoring idiom) —
    # real treeObject construction needs a live manager.
    import scoring.custom.data_ingestion as ingestion_mod

    def _factory(class_name, mgr):
        def make(manager=None, **fields):
            row = SimpleNamespace(**fields)
            table = mgr.objectTables.setdefault(class_name, {})
            table[f'ing-{len(table)}'] = row
            return row
        return make

    orig = ingestion_mod.ContextualizedValue
    ingestion_mod.ContextualizedValue = _factory(
        'ContextualizedValue', m)
    try:
        result = ingest_records(m, {
            'term': 'minimum-wage',
            'records': [{'subject': 'texas', 'value': 7.25,
                         'contexts': ['state-texas']}],
            'contexts': ['year-2022'],
            'contributed_by': 'demo-research-group',
            'source': 'selftest'})
    finally:
        ingestion_mod.ContextualizedValue = orig
    record = contributor_record(m, 'demo-research-group')
    check('ingested values attribute to their contributor',
          result['ok'] and record['valuesContributed'] == 1)

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
