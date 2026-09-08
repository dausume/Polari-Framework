"""
@cross-cutting
@module nutrition.food_basis
@tags @xc:bindings

nut-2 — the FOOD side of the ledger: a harvest of a plant, and its
food-nutrition composition. Two treeObjects:

  FoodItem        an edible harvest product tied to an aqp-4
                  PlantDefinition + which PlantParts are eaten + how it
                  is prepared. Fermentation is how B12 legitimately
                  appears (honest — flagged on the item).
  NutrientContent the food-nutrition composition — RICHER than aqp-4's
                  ELEMENTAL composition_json (which exists for carbon
                  capture): vitamins + bioavailable minerals per 100 g
                  edible. One row per (food, nutrient) — a transparent,
                  tunable USDA-prior table.

Reuses the aquaponics self-watering-pot plant model: the same
sweet-basil PlantDefinition/PlantPart that grows in a flowing
self-watering pot (aqp-1/aqp-8) becomes a FoodItem here, so a plant
GROWN in the pot system yields a computable meal-nutrient harvest.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.harvest_analysis, nutrition.food_seed
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-2 + Appendix A
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/food/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.food._shared import PREPARATIONS  # noqa: F401
from nutrition.objects.food.FoodItem import FoodItem  # noqa: F401
from nutrition.objects.food.NutrientContent import NutrientContent  # noqa: F401
