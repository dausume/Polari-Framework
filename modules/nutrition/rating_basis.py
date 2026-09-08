"""
@cross-cutting
@module nutrition.rating_basis
@tags @xc:bindings

mpb-8 — meal ratings as data: the person's own verdict on a meal
they actually ate. Ratings feed suggestion RANKING (the nmp-11
affinity overlay's "household accept/reject history", now with a
number) — they never gate, never block, and a low rating never
deletes anything (tastes change; the history stays).

  MealRating   person × template (× variation) × 1-5 stars ×
               their words, dated. One rating per eating is the
               intent (link the IntakeRecord when there is one).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.rating_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-8
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/rating/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.rating._shared import SEED_MEAL_RATINGS, _PROV  # noqa: F401
from nutrition.objects.rating.MealRating import MealRating  # noqa: F401
