"""
@cross-cutting
@module scoring.scoring_basis
@tags @xc:bindings

Context-based scoring BASIS — the Political Scorecard's proven object
graph (Term → ContextualizedTerm → TermContext → weighted aggregation)
generalized into Polari as first-class objects, so scores and score
concepts can be built over ARBITRARY data (Dustin 2026-07-07: "use
arbitrary data in the political scorecard, and plug it into polari …
an accountability framework for policies").

Four data classes:
  ScoreTerm           — one 0-1-normalizable metric concept ("Union
                        Participation"): what it measures, its unit,
                        whether higher is better, provenance.
  ScoreContext        — one scenario slice (location/timeframe/
                        economic/demographic/custom) with a specificity
                        rank so the engine prefers the most specific
                        value available (scorecard idiom: City > State
                        > Country > Region).
  ScoreSubject        — the entity being scored (policy, politician,
                        state, material — anything), optionally
                        anchored to a live Polari object.
  ContextualizedValue — one term measured for one subject under N
                        contexts: raw value + explicit normalization
                        spec (never hidden math), OR an objectRef
                        binding into any Polari object (the
                        arbitrary-data seam, same binding contract as
                        the engine models).

Aggregation definitions live in score_concept.py; the math in
scoring_engine.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.scoring_engine / scoring.scoring_api
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/scoring/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.scoring._shared import CONTEXT_TYPES, LOCATION_SPECIFICITY, VALUE_TYPES  # noqa: F401
from scoring.objects.scoring.ScoreTerm import ScoreTerm  # noqa: F401
from scoring.objects.scoring.ScoreContext import ScoreContext  # noqa: F401
from scoring.objects.scoring.ScoreSubject import ScoreSubject  # noqa: F401
from scoring.objects.scoring.ContextualizedValue import ContextualizedValue  # noqa: F401
