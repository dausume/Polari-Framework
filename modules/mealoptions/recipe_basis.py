"""
@cross-cutting
@module mealoptions.recipe_basis
@tags @xc:bindings

nmp-3 — recipes as data (moved here in mo-1, names unchanged):
Recipe (serves N), IngredientLine (a FoodItem, an amount, its
cooking transform), CookingStep (ordered instructions with a method
+ duration). The nutrition ROLLUP (nutrition.custom.recipe_analysis) is the
build-ourselves engine: per-ingredient FDC per-100g x amount x YIELD
factor x per-nutrient RETENTION factor, summed to per-serving
RecipeNutrition with raw-vs-cooked provenance labels.

Decision 8 rides here: ingredient lines reference whole FoodItems
(base ingredients + meats) — no packaged products. Q3 (Dustin
default): recipes are hand-authored first; the recipe-scrapers URL
import lands later (the dausume fork-pin already exists).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.recipe_analysis, nmp-4 meal templates
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/recipe/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mealoptions.objects.recipe._shared import COOKING_METHODS, SEED_COOKING_STEPS, SEED_INGREDIENT_LINES, SEED_RECIPES, _line  # noqa: F401
from mealoptions.objects.recipe.Recipe import Recipe  # noqa: F401
from mealoptions.objects.recipe.IngredientLine import IngredientLine  # noqa: F401
from mealoptions.objects.recipe.CookingStep import CookingStep  # noqa: F401
