"""
@cross-cutting
@module scoring.assertions_basis
@tags @xc:bindings

ScoreAssertion + AssertionValidityVote (scr-5) — the seam that binds
POLICY TEXT to score concepts. Dustin 2026-07-08: "based on
highlighting and assertion that portions of policy impact a particular
concept … assign scores via assertions of generic intents and then
suggestions of scores that should apply".

Typed assertions (the scorecard's legislativecompetition README,
adopted):
  score-impact — a span supports/harms a concept or term.
  dependency   — score carry-over from another policy subject this
                 one depends on (a nested edge between policies).
  decorative   — a span asserted to carry NO score weight (preambles,
                 boilerplate) — exclusion is itself an assertion.

Lifecycle: asserted → under-review → confirmed | rejected (re-open to
under-review allowed). Every transition APPENDS to
status_history_json — accountability can't be quietly rewritten.
Multi-round validity VOTING (the scorecard's designed rounds) tallies
through the same AgreementPolicy bands as group agreement; the tally
SUGGESTS a transition, never applies one (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.policy_scoring / scoring.custom.abstraction / scoring.scoring_api
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/assertions/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from datetime import datetime, timezone
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.agreement_policy_basis import classify_max, policy_bands

from scoring.objects.assertions._shared import ALLOWED_TRANSITIONS, ASSERTION_TYPES, DIRECTIONS, STATUSES, _assertion, _persist, _rows, tally_validity, transition_assertion  # noqa: F401
from scoring.objects.assertions.ScoreAssertion import ScoreAssertion  # noqa: F401
from scoring.objects.assertions.AssertionValidityVote import AssertionValidityVote  # noqa: F401
