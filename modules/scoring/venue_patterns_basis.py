"""
@cross-cutting
@module scoring.venue_patterns_basis
@tags @xc:bindings

Venue-mismatch analysis (Dustin 2026-07-16): "analyze different
devious strategies … where and how people address different issues
in different places potentially when they technically are not
supposed to. Like cramming what should be a legislated policy into a
budget instead of passing a policy first … Or the opposite …
a ballot initiative passes and then a politician actively tries to
suppress it by never budgeting it."

The model, honestly framed:
  * `VenueActionRecord` — one observed action on an ISSUE in a VENUE
    (statute, budget, ballot initiative, regulation, executive
    order, court), with actor, fiscal period, date, and evidence.
  * `VenueMismatchPattern` — THE CATALOG AS EDITABLE ROWS. What
    counts as a suspect sequence is a CONTESTABLE FRAMING, so
    patterns are content (proposed_by, votable like any other
    criterion), never baked-in judgment. Each row carries a small
    declarative `sequence_rule_json` the detector interprets.
  * `detect_patterns` — findings say a record sequence MATCHES a
    pattern, with the matched records and actors as evidence. It
    never declares wrongdoing.
  * `file_pattern_assertion` — a finding becomes a REAL
    ScoreAssertion (status 'asserted', NEVER auto-confirmed) against
    the implicated actor; the scr-6 validity-vote machinery is the
    adjudicator. That is the honest road into politician
    accountability.

sequence_rule_json shapes (interpreted by _apply_rule):
  {"requires": [{"venue": V, "action": A | "action_in": [..]}],
   "absentBefore": [{"venue": V, "action": A}],
   "starvation": {"after": {"venue": V, "action": A},
                  "venue": "budget-appropriation",
                  "starvingActions": [..], "reliefAction": "funded",
                  "minPeriods": N}}
  * requires: every entry must match >=1 record (chronological).
  * absentBefore: NO matching record may exist at-or-before the
    LAST matched `requires` record (the legitimate-sequence guard:
    a statute enacted BEFORE a budget rider is not a mismatch).
  * starvation: after the anchor record, walk fiscal periods that
    carry records in the given venue chronologically; count
    consecutive periods containing a starving action and NO relief
    action; >= minPeriods matches. Any relief period resets/clears.

@consumers
  - scoring.custom.politician_scoring (assertions land on actor subjects)
  - polariServer.defClassList (auto-CRUDE + persistence)
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/venue_patterns/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from scoring.assertions_basis import ScoreAssertion
from scoring.worldview_elections_basis import _by_name, _rows

from scoring.objects.venue_patterns._shared import ACTIONS, SEED_VENUE_PATTERNS, VENUES, _apply_rule, _record_matches, _record_summary, _validate_rule, detect_patterns, file_pattern_assertion  # noqa: F401
from scoring.objects.venue_patterns.VenueActionRecord import VenueActionRecord  # noqa: F401
from scoring.objects.venue_patterns.VenueMismatchPattern import VenueMismatchPattern  # noqa: F401
