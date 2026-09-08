"""
@cross-cutting
@module scoring.system_choice_implications_basis
@tags @xc:bindings

System-choice implications (2026-07-14, Democratic Scorecard revamp):
Dustin — "have an 'implications' portion, where people can assert
that particular system choices in judicial rulings have real world
effects on scores. One would be rape occurrence in the area compared
to other areas... assert for judicial solutions to crimes, that those
solutions should have associated scores that they can impact which we
can review through history to see which systems work best."

Two real gaps this module fills, both reusing EXISTING Polari
machinery rather than reinventing it:

1. Which criterion is actually DEPLOYED where, over time. A
   `LogicForkVote`'s `elected_criterion_name` (`logic_fork_vote.py`)
   is a single global resolution — real criminal law varies by
   jurisdiction and changes over time (each US state has its own
   code, amended on its own schedule). `SystemChoiceInForce` is the
   ground-truth record: "in jurisdiction J, fork F is/was configured
   to criterion C, from date X (to date Y, or still in force)."

2. The actual causal/correlational CLAIM. Reuses `ScoreAssertion`
   (`assertions.py`) directly, unchanged — it already models exactly
   this shape ("a claim binds a target to a score concept/term, with
   direction/strength/evidence/an accountable asserter, through a
   full asserted→under-review→confirmed/rejected lifecycle, group-
   agreement-classified multi-round voting"). The target is a
   `SystemChoiceInForce` or `LogicForkCriterion` row via
   `target_ref_json`'s standard objectRef binding — the SAME seam
   `ContextualizedValue.data_ref_json` uses everywhere else in this
   codebase. No new assertion class needed.

Honesty note this domain specifically demands (not a caveat to skip):
reported-rate metrics conflate TRUE INCIDENCE with REPORTING
PROPENSITY — more survivor-friendly evidentiary/consent standards can
raise REPORTED rates even as true incidence falls, because people
trust the system more to report. `compare_outcomes_by_system_choice()`
below returns a raw grouped comparison and explicitly says so — it
does NOT control for this confound, does NOT claim causation.

Correction (Dustin, same session, right after this module first
shipped): the two competing explanations (safety-improvement vs.
reporting-propensity) were originally ONLY modeled via
`AssertionValidityVote` — a binary valid/invalid lens that forces an
implicit XOR ("which one is true"). Dustin's point: that's the wrong
lens for two explanations that can BOTH be real simultaneously —
"people can just as easily say both are valid but should be weighted
... you can consider both to be important metrics and weight them
comparatively to get a standard score democratically." That's
mechanism B (`worldview_elections.py`), already fully built —
reused here unchanged, not reinvented: `SEED_INTERPRETATION_*` below
seeds the two explanations as WorldviewElection CANDIDATES under
APPROVAL mode specifically (a voter can approve BOTH on one ballot —
literally "both are valid"), and `apply_election()`'s derived weights
ARE the comparative democratic blend ("weight them comparatively"),
not a forced single winner. The `AssertionValidityVote` machinery
stays too, for a genuinely different question it's actually suited to
("is this methodological consideration credible reasoning at all") —
the two mechanisms now answer two different questions, not one
question through the wrong lens.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.scoring_api (system-choice-implication endpoints)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/system_choice_implications/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.custom.scoring_engine import (
    _by_name, _rows, resolve_raw_value, select_value,
)

from scoring.objects.system_choice_implications._shared import SEED_IMPLICATION_ASSERTIONS, SEED_IMPLICATION_CONTEXTUALIZED_VALUES, SEED_IMPLICATION_SCORE_TERMS, SEED_IMPLICATION_SUBJECTS, SEED_IMPLICATION_VALIDITY_VOTES, SEED_INTERPRETATION_BALLOTS, SEED_INTERPRETATION_ELECTIONS, SEED_INTERPRETATION_SCORE_CONCEPTS, SEED_INTERPRETATION_SCORE_GROUPS, SEED_SYSTEM_CHOICES_IN_FORCE, _RATE_DATA, _RATE_PROV, compare_outcomes_by_system_choice  # noqa: F401
from scoring.objects.system_choice_implications.SystemChoiceInForce import SystemChoiceInForce  # noqa: F401
