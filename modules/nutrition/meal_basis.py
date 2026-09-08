"""
@cross-cutting
@module nutrition.meal_basis
@tags @xc:bindings

nmp-4 — meals as data (decisions 1/2/4/5). mo-1
(MEAL_OPTIONS_MODULE_PLAN.md) MOVED the shareable half —
MealTemplate, VariationDefinition, MEAL_SLOTS and their seeds — to
mealoptions.meal_basis with names unchanged; this module RE-EXPORTS
them so every `from nutrition.meal_basis import X` keeps working,
and KEEPS the person-side half:

  MealPlanDefinition   a person's/household's plan over N days.
  MealEntry            pattern-consistent slot x template x chosen
                       variation x scale, on one day of the plan.

Slots (decision 5): breakfast, lunch, dinner, brunch, linner, snack
(+ snack-2 for the 5-slot pattern). Days are 1-based indexes — the
calendar mapping is presentation, not data.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.meal_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-4
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/meal/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from mealoptions.meal_basis import (  # noqa: F401
    MEAL_SLOTS, MealTemplate, VariationDefinition,
    SEED_MEAL_TEMPLATES, SEED_VARIATIONS,
)

from nutrition.objects.meal._shared import SEED_MEAL_ENTRIES, SEED_MEAL_PLANS  # noqa: F401
from nutrition.objects.meal.MealPlanDefinition import MealPlanDefinition  # noqa: F401
from nutrition.objects.meal.MealEntry import MealEntry  # noqa: F401
