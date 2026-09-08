"""
@cross-cutting
@module nutrition.threshold_basis
@tags @xc:bindings

nmp-1 — the threshold layer's objects:

  EatingPatternDefinition  one eating pattern (decision 4) with its
                           per-slot calorie FRACTIONS (decision 7 /
                           Q5) — labeled convention priors: the
                           meal-distribution literature is thin, and
                           these rows say so. Tunable per household.
  PersonThreshold          ONE overridden threshold knob. Derived
                           thresholds are computed on demand from the
                           DRI/UL + DGA seeds (threshold_analysis) —
                           only a HUMAN override materializes a row
                           (knobs-and-suggestions: the derivation is
                           the suggestion, this row is the knob).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.threshold_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/threshold/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.threshold._shared import SEED_EATING_PATTERNS, THRESHOLD_PERIODS  # noqa: F401
from nutrition.objects.threshold.EatingPatternDefinition import EatingPatternDefinition  # noqa: F401
from nutrition.objects.threshold.PersonThreshold import PersonThreshold  # noqa: F401
