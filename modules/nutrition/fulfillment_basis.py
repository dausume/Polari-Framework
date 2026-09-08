"""
@cross-cutting
@module nutrition.fulfillment_basis
@tags @xc:bindings

nmp-7 — GardenPlanDefinition (BUILDS nut-5 in its meal-plan-aware
form): one runnable garden config — a household (or a MealPlan) x
{grown FoodItem: plant count} x harvest cadence. The coverage sim
(fulfillment_analysis) matches DEMAND (household needs, or the
upgraded nmp-7 source: a MealPlan's actual rolled-up demand)
against SUPPLY (realized harvest nutrients, nut-2/aqp-8) — per
nutrient: met/partial/gap/uncoverable, gaps NAMED, uncoverable
nutrients pointed at their real source (saltwater food forest /
fermentation) per the honest-absence rule.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.fulfillment_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-7;
     /HOUSEHOLD_NUTRITION_PLAN.md §nut-5
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/fulfillment/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.fulfillment._shared import SEED_GARDEN_PLANS  # noqa: F401
from nutrition.objects.fulfillment.GardenPlanDefinition import GardenPlanDefinition  # noqa: F401
