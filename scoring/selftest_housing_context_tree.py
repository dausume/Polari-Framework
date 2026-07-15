"""
Selftest — Democratic Scorecard revamp Phase 2: the Housing
Affordability Context Tree (the first REAL, non-demo content exercising
mechanism B end-to-end).

Run from polari-framework/:
    python3 -m scoring.selftest_housing_context_tree

Covers: all three worldview concepts score every state honestly (no
missing terms — every state has all four ContextualizedValues seeded);
the ranked-condorcet election over the three worldviews produces the
real (uncontrived) Condorcet winner computed by hand when this seed was
authored (price-only beats both others pairwise); applying the closed
election writes vote-derived weights onto the assembly group with
provenance.
"""

from types import SimpleNamespace

from scoring.housing_affordability_seed import (
    SEED_HOUSING_BALLOTS, SEED_HOUSING_CONTEXTUALIZED_VALUES,
    SEED_HOUSING_CONTRIBUTORS, SEED_HOUSING_ELECTIONS,
    SEED_HOUSING_SCORE_CONCEPTS, SEED_HOUSING_SCORE_GROUPS,
    SEED_HOUSING_SCORE_TERMS,
)
from scoring.scoring_engine import score_concept
from scoring.scoring_seed import SEED_SCORE_CONTEXTS, SEED_SCORE_SUBJECTS
from scoring.worldview_elections import apply_election, tally_election

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
        'ScoreTerm': _rows(SEED_HOUSING_SCORE_TERMS),
        'ScoreContext': _rows(SEED_SCORE_CONTEXTS),
        'ScoreSubject': _rows(SEED_SCORE_SUBJECTS),
        'ContextualizedValue': _rows(SEED_HOUSING_CONTEXTUALIZED_VALUES),
        'ScoreConcept': _rows(SEED_HOUSING_SCORE_CONCEPTS),
        'ScoreGroup': _rows(SEED_HOUSING_SCORE_GROUPS),
        'Contributor': _rows(SEED_HOUSING_CONTRIBUTORS),
        'WorldviewElection': _rows(SEED_HOUSING_ELECTIONS),
        'WorldviewBallot': _rows(SEED_HOUSING_BALLOTS),
    })


PRICE_ONLY = 'housing-afford-price-only'
QUALITY_WEIGHTED = 'housing-afford-quality-weighted'
SUPPLY_FIRST = 'housing-afford-supply-first'
STATES = {'alabama', 'california', 'washington-dc', 'idaho', 'texas'}


if __name__ == '__main__':
    print('\nDemocratic Scorecard revamp Phase 2: Housing Affordability '
          'Context Tree\n')

    print('all three worldviews score every seeded state honestly')
    m = _mgr()
    for concept_name in (PRICE_ONLY, QUALITY_WEIGHTED, SUPPLY_FIRST):
        report = score_concept(m, concept_name)
        subjects = {s['subject'] for s in report.get('subjects', [])} \
            if report.get('ok') else set()
        all_missing = [s for s in report.get('subjects', [])
                       if s['termsMissing']] if report.get('ok') else []
        check(f"{concept_name}: scores all 5 states, no missing terms",
              report.get('ok') and subjects == STATES
              and not all_missing,
              extra=f"missing={[s['subject'] for s in all_missing]}"
              if all_missing else '')

    print('\nconstruction quality genuinely moves the ranking')
    m = _mgr()
    price_only = score_concept(m, PRICE_ONLY)
    quality = score_concept(m, QUALITY_WEIGHTED)
    price_only_best = max(price_only['subjects'],
                          key=lambda s: s['levelizedScore'])['subject']
    quality_best = max(quality['subjects'],
                       key=lambda s: s['levelizedScore'])['subject']
    check('price-only and quality-weighted disagree on the best state '
          "(construction quality isn't a no-op term)",
          price_only_best != quality_best,
          extra=f"price-only={price_only_best} "
          f"quality-weighted={quality_best}")

    print('\nranked-condorcet election: the real (uncontrived) outcome')
    m = _mgr()
    tally = tally_election(m, 'housing-affordability-election')
    check('election tallies ok, 5 ballots cast and counted',
          tally.get('ok') and tally['ballotsCast'] == 5
          and tally['ballotsCounted'] == 5
          and not tally['refusedBallots'])
    check('price-only is the Condorcet winner (beats both others '
          'pairwise, computed by hand when this seed was written)',
          tally.get('ok') and tally['winners'] == [PRICE_ONLY]
          and 'condorcet' in tally['note'])

    print('\napplying the closed election writes vote-derived weights')
    applied = apply_election(m, 'housing-affordability-election')
    check('closed election applies with provenance',
          applied.get('ok')
          and 'vote-derived' in applied['weightsProvenance']
          and 'ranked-condorcet' in applied['weightsProvenance'])
    check('applied weights favor price-only',
          applied.get('ok')
          and applied['appliedWeights'][PRICE_ONLY]
          > applied['appliedWeights'][QUALITY_WEIGHTED]
          and applied['appliedWeights'][PRICE_ONLY]
          > applied['appliedWeights'][SUPPLY_FIRST])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} passed')
    raise SystemExit(0 if passed == total else 1)
