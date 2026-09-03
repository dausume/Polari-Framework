"""
@cross-cutting
@module nutrition.recipe_basis
@tags @xc:bindings

nmp-3 — recipes as data. mo-1 (MEAL_OPTIONS_MODULE_PLAN.md) MOVED
Recipe / IngredientLine / CookingStep, COOKING_METHODS and the seeds
to mealoptions.recipe_basis with names unchanged; this module now
RE-EXPORTS them so every `from nutrition.recipe_basis import X`
keeps working. The nutrition ROLLUP (recipe_analysis) stays here.

@consumers
  - nutrition.recipe_analysis, nmp-4 meal templates, the selftests
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""

from mealoptions.recipe_basis import (  # noqa: F401
    COOKING_METHODS, Recipe, IngredientLine, CookingStep,
    SEED_RECIPES, SEED_INGREDIENT_LINES, SEED_COOKING_STEPS,
)
