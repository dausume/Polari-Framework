"""
@cross-cutting
@module nutrition.weight_basis
@tags @xc:bindings

nmp-6 — WeightObservation: one measured weight for a person. The
trajectory engine (weight_trajectory) projects; observations are
what actually happened — drift between the two is shown, and the
model's priors are tunable knobs, never silently recalibrated.

Q4 (Dustin default): trajectories are OWN-PROFILE ONLY by default —
household members see each other's only via explicit sharing (a
frontend/permission concern; the API serves per-person data and
says so).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.weight_trajectory
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-6
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/weight/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.weight._shared import SEED_WEIGHT_OBSERVATIONS  # noqa: F401
from nutrition.objects.weight.WeightObservation import WeightObservation  # noqa: F401
