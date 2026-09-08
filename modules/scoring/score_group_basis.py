"""
@cross-cutting
@module scoring.score_group_basis
@tags @xc:bindings

ScoreGroup — a named collection of member WORLDVIEWS (each member's
definition of a scored idea IS a ScoreConcept: their term weights +
stances). Groups are what agreement aggregation runs over (Dustin
2026-07-08: "(a) All groups - Consensus, (b) Political Groups,
(c) Professional Groups").

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - scoring.custom.group_aggregation / scoring.scoring_api
@see /OVERLAP_MAP.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/score_group/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from scoring.objects.score_group._shared import GROUP_TYPES  # noqa: F401
from scoring.objects.score_group.ScoreGroup import ScoreGroup  # noqa: F401
