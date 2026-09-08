"""
@cross-cutting
@module nutrition.nutrient_basis
@tags @xc:bindings

nut-1 — the shared dietary-nutrient vocabulary + Recommended Daily
Allowance reference data. Two treeObjects (auto-CRUDE + persisted):

  DietaryNutrient    one nutrient a household must hit — its category,
                     unit, role, and whether plants can supply it
                     (honest-absence: B12 / iodine / sodium / chloride
                     are NOT plant-native).
  NutrientReference  the RDA/AI basis for a demographic band, keyed to a
                     DietaryNutrient BY NAME — so the person profiler
                     (nut-3) scales every need from ONE sourced table,
                     never magic numbers.

Standing principles: object-coherence (every nutrient + RDA is a
configurable row), knobs-and-suggestions, honest-absence (missing
plant-availability = a named flag), labels-travel-with-numbers (every
reference carries its source + prior flag).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.person_analysis (reads references), nutrition.nutrient_seed
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/nutrient/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.nutrient._shared import NUTRIENT_CATEGORIES, PLANT_AVAILABILITY  # noqa: F401
from nutrition.objects.nutrient.DietaryNutrient import DietaryNutrient  # noqa: F401
from nutrition.objects.nutrient.NutrientReference import NutrientReference  # noqa: F401
