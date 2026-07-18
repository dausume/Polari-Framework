"""
Selftest — credibility bases: professional / impact / methodological
/ locality standing per domain, affiliations disclosed inline,
kinds never collapsed, relevance-ordered readings that exclude
nobody.

Run from polari-framework/:
    python3 -m scoring.selftest_credibility_bases

THE FIXTURE IS DUSTIN'S SCENARIO: a logically-valid proof; an
IMPACTED resident rebuts from lived experience (attested impact
claim); a company scientist counters professionally WITH her
employer disclosed inline; an independent mathematician — attested
absence of ties — weighs in methodologically with a competing-term
relation assertion. The reading lists all three DISTINCTLY, the
relevance votes rank impact first for this context, and the
prioritized reading surfaces it first while dropping NO ONE.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring import credibility_bases as cb
from scoring.assertion_credibility import cast_credibility_vote
from scoring.term_competition import assert_term_relation
from scoring.term_proofs import (cast_proof_vote, proof_reading,
                                 raise_rebuttal)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    m = SimpleNamespace(idList=[], db=None, objectTables={
        'Contributor': {}, 'ScoreContext': {}, 'ScoreAssertion': {},
        'TermProof': {}, 'ProofRebuttal': {}, 'ProofVote': {},
        'TermRelationAssertion': {}, 'TermScopeVote': {},
        'AssertionCredibilityVote': {}, 'CredibilityClaim': {},
        'ClaimAttestation': {}, 'StanceBasis': {},
        'QualificationRelevanceVote': {}})
    for person in ('resident-rita', 'dr-acme-alice',
                   'prof-indy-ivan', 'neighbor-ned', 'neighbor-nora',
                   'quant-quinn', 'quant-quill', 'observer-omar',
                   'epi-erin'):
        m.objectTables['Contributor'][person] = SimpleNamespace(
            name=person)
    for name, parent in (('dmv-region', ''),
                         ('md-montgomery', 'dmv-region'),
                         ('state-texas', ''),
                         ('tx-travis', 'state-texas'),
                         ('housing-displacement', ''),
                         ('epidemiology-domain', '')):
        m.objectTables['ScoreContext'][name] = SimpleNamespace(
            name=name, parent_name=parent, context_type='any',
            value_json='{}', notes='')
    m.objectTables['TermProof']['proof-risk-model'] = (
        SimpleNamespace(
            name='proof-risk-model', proof_kind='robustness',
            claim='the exposure risk model holds',
            subject_term='modeled-exposure-risk',
            comparison_term='reported-exposure-events',
            for_concept_name='housing-displacement',
            context_scope_json='["md-montgomery"]',
            demonstration_json='[]', manipulation_pattern='',
            depends_on_json='[]', status='demonstrated',
            history_json='[]', proposed_by='dr-acme-alice',
            on_behalf_of_group='', notes=''))
    m.objectTables['ScoreAssertion']['assert-risk-low'] = (
        SimpleNamespace(name='assert-risk-low', status='asserted'))
    return m


def _claims(m):
    cb.create_claim(
        m, 'rita-impact', 'resident-rita', 'impact',
        'twelve years living beside the site; documented recurring '
        'flooding the model calls negligible',
        qualifier='displaced-tenant',
        domain_scope=['md-montgomery'])
    cb.create_claim(
        m, 'alice-professional', 'dr-acme-alice', 'professional',
        'PhD toxicology; fifteen years exposure modeling',
        qualifier='exposure-modeling',
        domain_scope=['dmv-region'],
        affiliations=[{'org': 'AcmeChem', 'relation': 'employer',
                       'since': '2019'}])
    cb.create_claim(
        m, 'ivan-methodological', 'prof-indy-ivan', 'methodological',
        'professor of applied statistics; no work related to this '
        'issue or industry',
        qualifier='statistics',
        domain_scope=['md-montgomery'],
        independence_note='no professional or financial background '
                          'related to housing-displacement')
    cb.create_claim(
        m, 'erin-epi', 'epi-erin', 'professional',
        'epidemiologist', domain_scope=['epidemiology-domain'])
    cb.create_claim(
        m, 'rita-locality', 'resident-rita', 'locality',
        'resident of Montgomery County', qualifier='resident',
        domain_scope=['md-montgomery'])


def _claims_and_attestations():
    print('claims + attestations')
    m = _mgr()
    bad = cb.create_claim(m, 'x', 'resident-rita', 'astrological',
                          'stars')
    check('unknown basis kind refused listing kinds incl. locality',
          not bad['ok'] and 'locality' in bad['kinds'])
    check('non-Contributor refused with registration suggestion',
          not cb.create_claim(m, 'x', 'nobody', 'impact',
                              's')['ok'])
    _claims(m)
    check("a claim cannot attest itself",
          not cb.attest_claim(m, 'a0', 'rita-impact',
                              'resident-rita', True, 'me')['ok'])
    cb.attest_claim(m, 'a1', 'rita-impact', 'neighbor-ned', True,
                    'we lived it too', cast_at='t1')
    cb.attest_claim(m, 'a2', 'rita-impact', 'neighbor-nora', True,
                    'confirmed', cast_at='t2')
    verdict = cb.apply_attestation_verdict(m, 'rita-impact')
    check("majority support -> 'attested' via the explicit act",
          verdict['ok'] and verdict['status'] == 'attested')
    cb.attest_claim(m, 'a3', 'ivan-methodological', 'quant-quinn',
                    True, 'his record is public',
                    on_behalf_of_group='math-guild', cast_at='t1')
    cb.attest_claim(m, 'a4', 'ivan-methodological', 'quant-quill',
                    True, 'agreed', on_behalf_of_group='math-guild',
                    cast_at='t2')
    tally = cb.attestation_tally(m, 'ivan-methodological')
    check('a group echo counts ONCE (unit keying)',
          tally['units'] == 1 and tally['smallSample'])
    cb.attest_claim(m, 'a5', 'ivan-methodological', 'neighbor-ned',
                    True, 'checked', cast_at='t3')
    cb.apply_attestation_verdict(m, 'ivan-methodological')
    cb.attest_claim(m, 'a6', 'erin-epi', 'neighbor-ned', False,
                    'credential not shown', cast_at='t1')
    cb.attest_claim(m, 'a7', 'erin-epi', 'neighbor-nora', False,
                    'same', cast_at='t2')
    disputed = cb.apply_attestation_verdict(m, 'erin-epi')
    check("majority opposition flips 'disputed' visibly",
          disputed['ok'] and disputed['status'] == 'disputed')
    tie = cb.apply_attestation_verdict(m, 'alice-professional')
    check('tied/empty attestation refuses with the tally',
          not tie['ok'] and 'tally' in tie)
    return m


def _scenario(m):
    print("Dustin's scenario (the three actors)")
    raise_rebuttal(m, 'rita-rebuts', 'proof-risk-model',
                   'generality',
                   'the model holds on paper; the flooding it calls '
                   'negligible put my family out twice',
                   'resident-rita', at='t1')
    check('impact basis attaches to the rebuttal',
          cb.attach_basis(m, 'proof-rebuttal', 'rita-rebuts',
                          'rita-impact')['ok'])
    cast_proof_vote(m, 'proof-risk-model', 'dr-acme-alice',
                    'validity', 'valid',
                    rationale='the stated issue does not translate '
                              'to modeled risk', cast_at='t1')
    alice_vote = [v.name for v in
                  m.objectTables['ProofVote'].values()
                  if v.voter == 'dr-acme-alice'][0]
    cb.attach_basis(m, 'proof-vote', alice_vote,
                    'alice-professional')
    assert_term_relation(
        m, 'ivan-competing-term', 'reported-exposure-events',
        'modeled-exposure-risk', 'logically-exclusive-competing',
        'prof-indy-ivan',
        rationale='the modeled term understates tail events the '
                  'reported-events term captures; averaging masks '
                  'them')
    cb.attach_basis(m, 'term-relation-assertion',
                    'ivan-competing-term', 'ivan-methodological')
    cast_proof_vote(m, 'proof-risk-model', 'observer-omar',
                    'validity', 'valid', cast_at='t2')

    check("speaking from another's claim refused plainly",
          not cb.attach_basis(m, 'proof-vote', alice_vote,
                              'rita-impact')['ok'])
    check('unknown stance kind refused listing kinds',
          not cb.attach_basis(m, 'tweet', 'x', 'rita-impact')['ok'])
    check('unknown stance row refused listing knowns',
          not cb.attach_basis(m, 'proof-rebuttal', 'nope',
                              'rita-impact')['ok'])

    reading = cb.proof_reading_by_basis(m, 'proof-risk-model')
    labels = sorted(reading['byBasis'])
    check('per-basis breakdown lists the kinds distinctly',
          labels == ['impact:displaced-tenant',
                     'professional:exposure-modeling'], f'{labels}')
    alice_entry = reading['byBasis'][
        'professional:exposure-modeling'][0]
    check("the company scientist's employer shows INLINE",
          'AcmeChem' in alice_entry['basis'], alice_entry['basis'])
    rita_entry = reading['byBasis']['impact:displaced-tenant'][0]
    check('the impact basis reads attested',
          'attested' in rita_entry['basis'])
    check('NO combined cross-basis score exists (kinds never '
          'collapsed)',
          'score' not in reading['byBasis']
          and all('score' not in e
                  for grp in reading['byBasis'].values()
                  for e in grp))
    check("the unattributed voter appears as 'unattributed', "
          'never hidden',
          any(e['actor'] == 'observer-omar'
              for e in reading['unattributed']))

    base = proof_reading(m, 'proof-risk-model')
    check('base proof_reading fields IDENTICAL for consumers not '
          'asking for bases',
          all(reading[k] == base[k] for k in base))

    relation_reading = cb._group_by_basis(
        m, {'term-relation-assertion':
            [cb._by_name(m, 'TermRelationAssertion')[
                'ivan-competing-term']]})[0]
    ivan_entry = relation_reading['methodological:statistics'][0]
    check("the independent mathematician reads 'independent — "
          "attested absence of ties'",
          'independent — attested absence of ties'
          in ivan_entry['basis'], ivan_entry['basis'])
    return reading


def _scope(m):
    print('domain scope (per-context standing)')
    erin_vote = cast_credibility_vote(
        m, 'assert-risk-low', 'epi-erin', 'credible',
        rationale='consistent with cohort studies')
    vote_name = [v.name for v in
                 m.objectTables['AssertionCredibilityVote'].values()
                 if v.voter == 'epi-erin'][0]
    check('setup: credibility vote cast', erin_vote['ok'])
    cb.attach_basis(m, 'assertion-credibility-vote', vote_name,
                    'erin-epi')
    reading = cb.assertion_reading_by_basis(m, 'assert-risk-low')
    entry = reading['byBasis']['professional'][0]
    check('a DISPUTED claim reads DISPUTED inline',
          'DISPUTED' in entry['basis'], entry['basis'])

    claims = cb._by_name(m, 'CredibilityClaim')
    check('locality claim in-scope for its jurisdiction (chain '
          'covers md-montgomery)',
          cb._scope_covers(m, claims['rita-locality'],
                           ['md-montgomery']) is True)
    check('and in-scope for the parent region (hierarchy-aware)',
          cb._scope_covers(m, claims['rita-locality'],
                           ['dmv-region']) is True)
    check('but out-of-scope for another geography',
          cb._scope_covers(m, claims['rita-locality'],
                           ['tx-travis']) is False)
    check('undeterminable scope reads None, not False',
          cb._scope_covers(m, claims['rita-locality'], []) is None)
    epi_covered = cb._scope_covers(m, claims['erin-epi'],
                                   ['md-montgomery'])
    check('out-of-domain professional basis marked, not blocked',
          epi_covered is False)


def _relevance(m):
    print('relevance votes + prioritized reading (anti-drowning = '
          'ordering, never exclusion)')
    ctx = 'housing-displacement'
    for i, voter in enumerate(('neighbor-ned', 'neighbor-nora',
                               'observer-omar')):
        cb.cast_relevance_vote(
            m, f'rv-impact-{i}', ctx, 'impact', voter, True,
            'those living it see what models miss',
            qualifier='displaced-tenant', cast_at=f't{i}')
    cb.cast_relevance_vote(m, 'rv-prof-1', ctx, 'professional',
                           'quant-quinn', True, 'method matters',
                           on_behalf_of_group='math-guild',
                           cast_at='t1')
    cb.cast_relevance_vote(m, 'rv-prof-2', ctx, 'professional',
                           'quant-quill', True, 'agreed',
                           on_behalf_of_group='math-guild',
                           cast_at='t2')
    relevance = cb.qualification_relevance(m, ctx)
    top = relevance['ranking'][0]
    check('impact ranked above professional for this context',
          top['basisKind'] == 'impact' and top['supportUnits'] == 3)
    prof = next(e for e in relevance['ranking']
                if e['basisKind'] == 'professional')
    check('relevance group echo counts once + small-sample flagged',
          prof['supportUnits'] == 1 and prof['smallSample'])
    check('empty-context relevance suggests the vote knob',
          'suggestion' in cb.qualification_relevance(m, 'elsewhere'))

    prioritized = cb.prioritized_stances(m, 'proof-risk-model')
    order = [g['basis'] for g in prioritized['prioritized']]
    check('prioritized reading surfaces the impact group FIRST',
          order[0].startswith('impact'), f'{order}')
    check('the professional group follows — present, not dropped',
          any(g.startswith('professional') for g in order))
    plain = cb.proof_reading_by_basis(m, 'proof-risk-model')
    plain_stances = sorted(
        e['stance'] for grp in plain['byBasis'].values()
        for e in grp) + sorted(e['stance']
                               for e in plain['unattributed'])
    prio_stances = sorted(
        e['stance'] for g in prioritized['prioritized']
        for e in g['stances']) + sorted(
        e['stance'] for e in prioritized['unattributed'])
    check('COMPLETENESS: every stance in the plain reading appears '
          'in the prioritized one (ordering, never exclusion)',
          plain_stances == prio_stances)
    check('the ordering note says exactly that',
          'excluded' in prioritized['orderingNote'])


def _standing(m):
    print('the accountability card')
    card = cb.contributor_standing(m, 'resident-rita')
    kinds = sorted(c['basisKind'] for c in card['claims'])
    check('contributor standing composes kinds + attestations',
          kinds == ['impact', 'locality']
          and card['claims'][0]['attestations']['units'] >= 1)
    scoped = cb.contributor_standing(m, 'epi-erin',
                                     domain='md-montgomery')
    check('domain-scoped card omits out-of-domain claims',
          scoped['claims'] == [])
    check('no-claims contributor reads the citizen-first note',
          'never gated'
          in cb.contributor_standing(m, 'quant-quinn')['note'])


def main():
    m = _claims_and_attestations()
    _scenario(m)
    _scope(m)
    _relevance(m)
    _standing(m)
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
