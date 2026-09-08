"""
@cross-cutting
@module nutrition.tolerance_basis
@tags @xc:bindings

nmp-2 — the tolerance/adverse-effect table (the honest one): each
row is ONE literature-pinned threshold above which a named SYMPTOM
is associated, with its citation and a confidence grade. Evaluation
(tolerance_analysis) produces WARNINGS naming the symptom — never
silent clamps, never medical advice (decision 3: general-population
only, and the rows say so).

Confidence grades, honestly ranked:
  'ul-grade'  NASEM UL / CDRR quality evidence
  'moderate'  well-replicated feeding/tolerance studies
  'low'       weaker or heterogeneous evidence (the decision-9
              reflux/trigger rows live here, labeled)

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.tolerance_analysis, nmp-4 plan rollups
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-2
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/tolerance/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.tolerance._shared import CONFIDENCE_GRADES, SEED_TOLERANCE_THRESHOLDS, TOLERANCE_PERIODS, _t  # noqa: F401
from nutrition.objects.tolerance.ToleranceThreshold import ToleranceThreshold  # noqa: F401
