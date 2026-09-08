"""
@cross-cutting
@module scoring.score_concept_basis
@tags @xc:bindings

ScoreConcept — "concepts for scores that are more complicated": a
named, weighted bundle of ScoreTerms evaluated over subjects under
required contexts (the scorecard's WorldviewBallot generalized away
from voting — a ballot is ONE source of a concept, a policy
accountability framework is another).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.scoring_engine (the math) / scoring.scoring_api
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/score_concept/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.score_concept._shared import AGGREGATIONS  # noqa: F401
from scoring.objects.score_concept.ScoreConcept import ScoreConcept  # noqa: F401
