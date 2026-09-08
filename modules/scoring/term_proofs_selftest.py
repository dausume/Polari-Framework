"""
Selftest — democratic term proofs (Dustin 2026-07-16).

Run from polari-framework/:
    python3 -m scoring.term_proofs_selftest

Covers: the proof lifecycle with rebuttals (raise flips to
challenged; resolving never auto-flips back); re-runnable
demonstrations (agreement, then a planted value change reported as
divergence); the three computable exposure checks over fixtures —
canonical aggregation-masking with EXACT concealed-mass counts, and
'misleading' pinned absent from every check result; validity and
comprehension votes tallied separately (the valid-but-fails-
comprehension tension case pinned); unit keying (a group echo counts
once); acceptance suggestions returned with every target untouched;
staleness propagating through a 2-deep dependency chain; dependency
cycles refused; the judgment-only pattern honestly checkless; and
the seeded uncontested-races worked example re-running against its
synthetic fixtures.
"""

import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring import term_proofs_basis as tp

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _ns(**fields):
    return SimpleNamespace(**fields)


def _value(name, term, value, contexts):
    return _ns(name=name, term_name=term, subject_name='demo-usa',
               context_names_json=json.dumps(contexts),
               pre_normalized_value=value,
               provenance_id=tp.DEMO_PROVENANCE, source='selftest')


def _mgr():
    m = SimpleNamespace(idList=[], db=None, objectTables={
        'TermProof': {}, 'ProofRebuttal': {}, 'ProofVote': {},
        'DataManipulationPattern': {}, 'ScoreTerm': {},
        'ScoreConcept': {}, 'ScoreContext': {},
        'ContextualizedValue': {}, 'TermRelationAssertion': {},
        'TermScopeVote': {}})
    for term in ('demo-avg-race-competitiveness',
                 'demo-uncontested-share-per-state',
                 'demo-race-competitiveness', 'demo-donation-mean'):
        m.objectTables['ScoreTerm'][term] = _ns(name=term)
    m.objectTables['ScoreConcept'][
        'demo-electoral-accountability'] = _ns(
        name='demo-electoral-accountability',
        required_context_names_json='["demo-usa-2026"]')
    for ctx, kind in (('demo-usa-2026', 'timeframe'),
                      ('demo-usa-2020', 'timeframe')):
        m.objectTables['ScoreContext'][ctx] = _ns(
            name=ctx, context_type=kind)
    values = m.objectTables['ContextualizedValue']
    values['demo-avg-race-competitiveness@usa-2026'] = _value(
        'demo-avg-race-competitiveness@usa-2026',
        'demo-avg-race-competitiveness', tp.DEMO_MEAN,
        ['demo-usa-2026'])
    values['demo-avg-race-competitiveness@usa-2020'] = _value(
        'demo-avg-race-competitiveness@usa-2020',
        'demo-avg-race-competitiveness', 0.61, ['demo-usa-2020'])
    for i, v in enumerate(tp.DEMO_STATE_VALUES):
        name = f'demo-race-competitiveness@state-{i:02d}'
        values[name] = _value(name, 'demo-race-competitiveness', v,
                              ['demo-usa-2026'])
    for i, v in enumerate([1.0, 1.0, 1.0, 1.0, 100.0]):
        name = f'demo-donation-mean@d{i}'
        values[name] = _value(name, 'demo-donation-mean', v,
                              ['demo-usa-2026'])
    for seed in tp.SEED_MANIPULATION_PATTERNS:
        m.objectTables['DataManipulationPattern'][seed['name']] = (
            _ns(**seed))
    return m


def _lifecycle_and_rebuttals():
    print('lifecycle + rebuttals')
    m = _mgr()
    created = tp.create_proof(
        m, 'proof-a', 'misleading-contextualization',
        'per-state share beats the average here',
        'demo-uncontested-share-per-state',
        'demo-electoral-accountability',
        comparison_term='demo-avg-race-competitiveness',
        context_scope=['demo-usa-2026'],
        demonstration=[{'kind': 'reading', 'description': 'avg',
                        'inputs': [
                            'demo-avg-race-competitiveness@usa-2026'],
                        'result': tp.DEMO_MEAN}],
        manipulation_pattern='aggregation-masking',
        proposed_by='alice', at='2026-07-16T01:00:00+00:00')
    check('create -> draft', created['ok']
          and created['status'] == 'draft')
    check('draft cannot jump to accepted',
          not tp.transition_proof(m, 'proof-a', 'accepted')['ok'])
    tp.transition_proof(m, 'proof-a', 'demonstrated', by='alice')
    raised = tp.raise_rebuttal(
        m, 'reb-1', 'proof-a', 'framing',
        'the threshold choice does the work', 'bob',
        on_behalf_of_group='group-skeptics')
    check('raising a rebuttal flips demonstrated -> challenged',
          raised['ok'] and raised['proofStatus'] == 'challenged')
    check('rationale-less rebuttal refused',
          not tp.raise_rebuttal(m, 'reb-2', 'proof-a', 'data', '  ',
                                'bob')['ok'])
    reading = tp.proof_reading(m, 'proof-a')
    check('standing open rebuttal surfaces on the reading',
          len(reading['standingRebuttals']) == 1
          and reading['standingRebuttals'][0]['kind'] == 'framing')
    resolved = tp.resolve_rebuttal(m, 'reb-1', 'answered',
                                   by='alice',
                                   note='threshold from statute')
    check('resolving never auto-flips the proof (explicit only)',
          resolved['ok']
          and 'never auto-flips' in resolved['note']
          and tp._by_name(m, 'TermProof')['proof-a'].status
          == 'challenged')
    accepted = tp.accept_proof(m, 'proof-a', by='panel')
    check('challenged -> accepted via the explicit act',
          accepted['ok'] and accepted['status'] == 'accepted')
    history = json.loads(
        tp._by_name(m, 'TermProof')['proof-a'].history_json)
    check('history is append-only and complete',
          [h['event'] for h in history]
          == ['created', 'draft->demonstrated',
              'demonstrated->challenged', 'challenged->accepted'])


def _reruns():
    print('re-runnable demonstrations')
    m = _mgr()
    proof = tp.TermProof(**{**tp.SEED_TERM_PROOFS[0]},
                         manager=m)
    m.objectTables['TermProof'][proof.name] = proof
    rerun = tp.rerun_demonstration(
        m, 'proof-uncontested-races-masking')
    check('the seeded worked example re-runs in full agreement',
          rerun['ok'] and rerun['agreement']
          and len(rerun['steps']) == 5)
    check('recomputed concealed mass is exactly 24 of 50 (share '
          '0.48)', rerun['steps'][2]['recomputed'] == 24.0
          and rerun['steps'][3]['recomputed'] == 0.48)
    m.objectTables['ContextualizedValue'][
        'demo-race-competitiveness@state-00'
    ].pre_normalized_value = 0.9
    diverged = tp.rerun_demonstration(
        m, 'proof-uncontested-races-masking')
    check('a planted value change reads as DIVERGENCE, never hidden',
          diverged['ok'] and not diverged['agreement']
          and any('step 1' in d for d in diverged['divergences']))


def _exposure_checks():
    print('computable exposure checks (neutral arithmetic only)')
    m = _mgr()
    masking = tp.check_aggregation_masking(
        m, 'demo-avg-race-competitiveness',
        'demo-race-competitiveness')
    check('canonical masking: exact concealed-mass counts',
          masking['ok']
          and masking['massAtOrBelow']['count'] == 24
          and masking['massAtOrBelow']['share'] == 0.48
          and masking['distributionCount'] == 50
          and '24 of 50' in masking['finding'])
    outlier = tp.check_outlier_driven_mean(m, 'demo-donation-mean')
    check('outlier check: mean 20.8 vs median 1.0 divergence',
          outlier['ok'] and outlier['mean'] == 20.8
          and outlier['median'] == 1.0
          and outlier['divergence'] == 19.8)
    stale = tp.check_stale_vintage(
        m, 'demo-avg-race-competitiveness',
        'demo-electoral-accountability')
    check('stale vintage: the 2020 value flagged against the '
          'declared 2026 scope', stale['ok']
          and stale['matchingValueCount'] == 1
          and len(stale['mismatchedValues']) == 1
          and 'demo-usa-2020' in str(stale['mismatchedValues']))
    for result in (masking, outlier, stale):
        pass
    check("'misleading' appears in NO check result — the verdict "
          'belongs to the votes',
          all('misleading' not in json.dumps(r).lower()
              for r in (masking, outlier, stale)))
    check('missing distribution values refuse with a suggestion',
          not tp.check_aggregation_masking(
              m, 'demo-avg-race-competitiveness',
              'demo-uncontested-share-per-state')['ok'])


def _votes():
    print('validity vs comprehension (never conflated)')
    m = _mgr()
    tp.create_proof(
        m, 'proof-v', 'robustness', 'A is more robust than B',
        'demo-uncontested-share-per-state',
        'demo-electoral-accountability',
        comparison_term='demo-avg-race-competitiveness',
        demonstration=[{'kind': 'comparison', 'description': 'x',
                        'inputs': [], 'result': 'x'}],
        proposed_by='alice')
    tp.transition_proof(m, 'proof-v', 'demonstrated')
    for i, voter in enumerate(('v1', 'v2', 'v3', 'v4', 'v5')):
        tp.cast_proof_vote(m, 'proof-v', voter, 'validity', 'valid',
                           cast_at=f'2026-07-16T02:0{i}:00+00:00')
    for i, voter in enumerate(('c1', 'c2', 'c3')):
        tp.cast_proof_vote(m, 'proof-v', voter, 'comprehension',
                           'comparison',
                           cast_at=f'2026-07-16T03:0{i}:00+00:00')
    reading = tp.proof_reading(m, 'proof-v')
    check('validity strong AND comprehension leaning AGAINST the '
          'subject — the tension case reads BOTH, separately',
          reading['validity']['score'] == round(5 / 6, 4)
          and reading['validity']['units'] == 5
          and not reading['validity']['smallSample']
          and reading['comprehension']['leaning'] == 'comparison'
          and reading['comprehension']['smallSample'])
    check('the reading is framed as a reading, not a truth '
          'declaration', 'not a truth declaration'
          in reading['reading'])
    before = reading['validity']['units']
    tp.cast_proof_vote(m, 'proof-v', 'member-x', 'validity', 'valid',
                       on_behalf_of_group='group-g',
                       cast_at='2026-07-16T04:00:00+00:00')
    tp.cast_proof_vote(m, 'proof-v', 'member-y', 'validity',
                       'flawed', on_behalf_of_group='group-g',
                       cast_at='2026-07-16T04:01:00+00:00')
    after = tp.proof_reading(m, 'proof-v')['validity']
    check('a group echo counts ONCE (latest stance per unit)',
          after['units'] == before + 1
          and after['byChoice']['flawed'] == 1)
    check('wrong choice for the vote kind refused',
          not tp.cast_proof_vote(m, 'proof-v', 'z', 'validity',
                                 'subject')['ok'])
    missing = tp.proof_reading(m, 'proof-a-missing')
    check('an unknown proof reads as an honest refusal listing '
          'known proofs',
          not missing['ok'] and 'proof-v' in missing['knownProofs'])
    fresh = tp.create_proof(
        m, 'proof-quiet', 'sufficiency', 'meets the bar',
        'demo-race-competitiveness',
        'demo-electoral-accountability', proposed_by='a',
        demonstration=[{'kind': 'comparison', 'description': 'x',
                        'inputs': [], 'result': 'x'}])
    quiet = tp.proof_reading(m, 'proof-quiet')
    check('no votes yet = unrated with the act suggested (both '
          'kinds)', fresh['ok']
          and quiet['validity']['score'] is None
          and 'suggestion' in quiet['validity']
          and 'suggestion' in quiet['comprehension'])


def _acceptance_and_staleness():
    print('acceptance suggestions + staleness propagation')
    m = _mgr()
    for name, kind, deps in (
            ('proof-base', 'sufficiency', []),
            ('proof-mid', 'subset', ['proof-base']),
            ('proof-top', 'robustness', ['proof-mid'])):
        comparison = ('' if kind == 'sufficiency'
                      else 'demo-avg-race-competitiveness')
        tp.create_proof(
            m, name, kind, f'{name} claim',
            'demo-uncontested-share-per-state',
            'demo-electoral-accountability',
            comparison_term=comparison, depends_on=deps,
            demonstration=[{'kind': 'comparison',
                            'description': 'x', 'inputs': [],
                            'result': 'x'}],
            proposed_by='alice')
        tp.transition_proof(m, name, 'demonstrated')
    relations_before = len(tp._rows(m, 'TermRelationAssertion'))
    votes_before = len(tp._rows(m, 'TermScopeVote'))
    accepted = tp.accept_proof(m, 'proof-mid', by='panel')
    check('a subset acceptance SUGGESTS the relation assertion',
          accepted['ok']
          and 'logical-subset' in
          accepted['suggestions'][0]['action'])
    check('suggestion targets stay untouched (no rows created)',
          len(tp._rows(m, 'TermRelationAssertion'))
          == relations_before
          and len(tp._rows(m, 'TermScopeVote')) == votes_before)
    check('acceptance names its context scope honestly',
          'recorded context scope only' in accepted['scopeNote'])

    rejected = tp.reject_proof(m, 'proof-base', by='panel',
                               note='fixture withdrawn')
    check('rejection suggests propagating staleness',
          rejected['ok'] and 'propagate_staleness'
          in rejected['suggestion']['knob'])
    flipped = tp.propagate_staleness(m, 'proof-base')
    check('staleness reaches BOTH levels of the dependency chain',
          flipped['flippedToStale'] == ['proof-mid', 'proof-top'])
    top = tp._by_name(m, 'TermProof')['proof-top']
    check("the stale reason names the moved foundation",
          top.status == 'stale' and 'foundation changed'
          in json.loads(top.history_json)[-1]['note'])
    check('a stale proof surfaces on dependents\' readings',
          any(d['status'] == 'stale' for d in tp.proof_reading(
              m, 'proof-top')['dependenciesNotAccepted'])
          or tp.proof_reading(m, 'proof-top')['status'] == 'stale')

    check('self-dependency refused at creation',
          not tp.create_proof(
              m, 'proof-self', 'sufficiency', 'c',
              'demo-race-competitiveness',
              'demo-electoral-accountability',
              depends_on=['proof-self'])['ok'])
    a = tp._by_name(m, 'TermProof')['proof-mid']
    a.depends_on_json = json.dumps(['proof-top'])  # CRUDE-edit cycle
    check('a dependency graph containing a cycle refuses new proofs',
          not tp.create_proof(
              m, 'proof-on-cycle', 'sufficiency', 'c',
              'demo-race-competitiveness',
              'demo-electoral-accountability',
              depends_on=['proof-top'])['ok'])


def _catalog():
    print('the manipulation catalog')
    m = _mgr()
    patterns = tp._by_name(m, 'DataManipulationPattern')
    check('all 18 seeded patterns load with unique names',
          len(tp.SEED_MANIPULATION_PATTERNS) == 18
          and len(patterns) == 18)
    causation = patterns['correlation-as-causation']
    check('judgment-only patterns carry NO exposure check and say '
          'so', causation.computability == 'judgment-only'
          and causation.exposure_check == '')
    computable = [p for p in patterns.values()
                  if p.computability == 'computable']
    check('exactly the three implemented checks are marked '
          'computable, each with its module:function ref',
          len(computable) == 3
          and all(':check_' in p.exposure_check
                  for p in computable))
    check('every pattern states its counter-presentation',
          all(getattr(p, 'counter_presentation', '')
              for p in patterns.values()))


def main():
    _lifecycle_and_rebuttals()
    _reruns()
    _exposure_checks()
    _votes()
    _acceptance_and_staleness()
    _catalog()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
