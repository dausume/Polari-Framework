"""
Selftest — system-choice implications (2026-07-14): Dustin's
"implications" ask — assert that a judicial system choice affects a
real-world score, review through history which systems work best.

Run from polari-framework/:
    python3 -m scoring.system_choice_implications_selftest

Covers: compare_outcomes_by_system_choice() correctly groups
jurisdictions by their in-force consent-determination-fork criterion
and computes honest per-group averages; the raw comparison note is
present (no implied causation); honest refusal for an unknown fork;
the two competing ScoreAssertions exist with correct direction/status
(deliberately under-review, not confidently confirmed); their
AssertionValidityVote tallies show genuine, non-unanimous disagreement
— the real epistemic state of a contested empirical question, not
manufactured consensus; the COMPARATIVE-WEIGHTING correction (Dustin:
"both are valid but should be weighted... weight them comparatively
to get a standard score democratically") — an approval-mode
WorldviewElection over the two explanations as candidates, reusing
mechanism B unchanged, produces a real 3/7-vs-4/7 blend (not a forced
single winner) that correctly reflects voters who approved BOTH.
"""

from types import SimpleNamespace

from scoring.assertions_basis import tally_validity
from scoring.scoring_seed import SEED_SCORE_CONTEXTS, SEED_SCORE_SUBJECTS
from scoring.system_choice_implications_basis import (
    SEED_IMPLICATION_ASSERTIONS, SEED_IMPLICATION_CONTEXTUALIZED_VALUES,
    SEED_IMPLICATION_SCORE_TERMS, SEED_IMPLICATION_SUBJECTS,
    SEED_IMPLICATION_VALIDITY_VOTES, SEED_INTERPRETATION_BALLOTS,
    SEED_INTERPRETATION_ELECTIONS, SEED_INTERPRETATION_SCORE_CONCEPTS,
    SEED_INTERPRETATION_SCORE_GROUPS, SEED_SYSTEM_CHOICES_IN_FORCE,
    compare_outcomes_by_system_choice,
)
from scoring.agreement_policy_basis import SEED_AGREEMENT_POLICIES
from scoring.worldview_elections_basis import apply_election, tally_election

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list, extra_defaults=None):
    defaults = {'pre_normalized_value': None}
    if extra_defaults:
        defaults.update(extra_defaults)
    return {i: SimpleNamespace(**{**defaults, **r})
            for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'ScoreTerm': _rows(SEED_IMPLICATION_SCORE_TERMS),
        'ScoreContext': _rows(SEED_SCORE_CONTEXTS),
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS + SEED_IMPLICATION_SUBJECTS),
        'ContextualizedValue': _rows(SEED_IMPLICATION_CONTEXTUALIZED_VALUES),
        'SystemChoiceInForce': _rows(SEED_SYSTEM_CHOICES_IN_FORCE),
        'ScoreAssertion': _rows(
            SEED_IMPLICATION_ASSERTIONS,
            {'status_history_json': '[]'}),
        'AssertionValidityVote': _rows(SEED_IMPLICATION_VALIDITY_VOTES),
        'AgreementPolicy': _rows(SEED_AGREEMENT_POLICIES),
        'ScoreConcept': _rows(SEED_INTERPRETATION_SCORE_CONCEPTS),
        'ScoreGroup': _rows(SEED_INTERPRETATION_SCORE_GROUPS),
        'WorldviewElection': _rows(SEED_INTERPRETATION_ELECTIONS),
        'WorldviewBallot': _rows(SEED_INTERPRETATION_BALLOTS),
    })


if __name__ == '__main__':
    print('\nSystem-choice implications: judicial system choices vs. '
          'real-world outcome scores\n')

    print('compare_outcomes_by_system_choice(): groups states by '
          'in-force consent-determination criterion')
    m = _mgr()
    report = compare_outcomes_by_system_choice(
        m, 'consent-determination-fork', 'rape-occurrence-rate')
    check('ok, 2 groups (affirmative-consent, force-based)',
          report.get('ok') and len(report['groups']) == 2,
          extra=f"groups={[g['criterion'] for g in report.get('groups', [])]}")

    by_criterion = {g['criterion']: g for g in report.get('groups', [])}
    afc = by_criterion.get('affirmative-consent-standard', {})
    fbc = by_criterion.get('force-based-consent-standard', {})
    check('affirmative-consent group: CA + DC, avg = (27.4+45.3)/2 = '
          '36.35',
          afc.get('jurisdictionCount') == 2
          and abs((afc.get('averageValue') or 0) - 36.35) < 1e-6)
    check('force-based group: TX + AL + ID, avg = '
          '(41.8+38.2+33.6)/3 ≈ 37.8667',
          fbc.get('jurisdictionCount') == 3
          and abs((fbc.get('averageValue') or 0) - 37.866667) < 1e-4)
    check('the response explicitly disclaims causation (no implied '
          'settled finding)',
          'not a controlled-for' in report.get('note', '')
          and 'CAUSED' in report.get('note', ''))

    print('\nhonest refusal for an unknown fork')
    report = compare_outcomes_by_system_choice(
        m, 'no-such-fork', 'rape-occurrence-rate')
    check('unknown fork 404 with known list',
          not report['ok'] and 'knownForks' in report)

    print('\nthe two competing assertions exist, deliberately '
          'under-review (not confidently confirmed)')
    assertions = m.objectTables['ScoreAssertion']
    safety = next(a for a in assertions.values()
                 if a.name == 'assert-affirmative-consent-safety-improvement')
    confound = next(a for a in assertions.values()
                    if a.name == 'assert-reporting-propensity-rival-explanation')
    check("safety-improvement assertion: direction='supports', "
          "status='under-review' (not overclaimed as settled)",
          safety.direction == 'supports' and safety.status == 'under-review')
    check("reporting-propensity assertion: direction='harms' (raises "
          "the raw metric), status='under-review'",
          confound.direction == 'harms' and confound.status == 'under-review')

    print('\nAssertionValidityVote tallies show genuine, non-'
          'unanimous disagreement — not manufactured consensus')
    safety_tally = tally_validity(
        m, 'assert-affirmative-consent-safety-improvement')
    check('safety-improvement: 1 valid, 1 invalid, 1 abstain in round '
          "1 — a real, tied-leaning split, not unanimous",
          safety_tally.get('ok')
          and safety_tally['rounds'][0]['valid'] == 1
          and safety_tally['rounds'][0]['invalid'] == 1
          and safety_tally['rounds'][0]['abstain'] == 1)
    confound_tally = tally_validity(
        m, 'assert-reporting-propensity-rival-explanation')
    check('reporting-propensity: 2 valid, 0 invalid — the '
          'methodological confound itself is uncontested even by the '
          'coalition that disagrees with its POLICY implication',
          confound_tally.get('ok')
          and confound_tally['rounds'][0]['valid'] == 2
          and confound_tally['rounds'][0]['invalid'] == 0)

    print('\nCOMPARATIVE WEIGHTING correction (Dustin): both '
          'explanations can be valid, weighted democratically — NOT '
          'a forced single winner via mechanism B, approval mode')
    SAFETY = 'interpretation-safety-improvement-effect'
    REPORTING = 'interpretation-reporting-propensity-effect'
    tally = tally_election(m, 'rape-occurrence-interpretation-election')
    check('5 ballots cast/counted, none refused',
          tally.get('ok') and tally['ballotsCast'] == 5
          and tally['ballotsCounted'] == 5 and not tally['refusedBallots'])
    check('2 voters approved BOTH candidates on one ballot — the '
          'literal mechanism for "both are valid"',
          tally.get('ok')
          and next(r['approvals'] for r in tally['results']
                   if r['candidate'] == SAFETY) == 3
          and next(r['approvals'] for r in tally['results']
                   if r['candidate'] == REPORTING) == 4)
    check('derived weights: safety=3/7, reporting=4/7 — a genuine '
          'comparative BLEND, not a 100/0 single-winner verdict',
          tally.get('ok')
          and abs(tally['electedWeights'][SAFETY] - 3 / 7) < 1e-6
          and abs(tally['electedWeights'][REPORTING] - 4 / 7) < 1e-6)

    applied = apply_election(m, 'rape-occurrence-interpretation-election')
    check('apply writes the comparative weights onto the assembly '
          'group with provenance — the "standard score, weighted '
          'comparatively, democratically" Dustin described',
          applied.get('ok')
          and abs(applied['appliedWeights'][SAFETY] - 3 / 7) < 1e-6
          and abs(applied['appliedWeights'][REPORTING] - 4 / 7) < 1e-6
          and 'vote-derived' in applied['weightsProvenance'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
