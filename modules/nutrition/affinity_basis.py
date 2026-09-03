"""
@cross-cutting
@module nutrition.affinity_basis
@tags @xc:bindings

nmp-11 — the composition vocabulary (decision 11). mo-1
(MEAL_OPTIONS_MODULE_PLAN.md) MOVED DishBase / IngredientRole /
FoodRole / IngredientAffinity, DEFAULT_CONTEXT and the seeds to
mealoptions.affinity_basis with names unchanged; this module now
RE-EXPORTS them so every `from nutrition.affinity_basis import X`
keeps working. The composer (affinity_composer) stays here — it
reads the person's stated context.

@consumers
  - nutrition.affinity_composer, the selftests
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""

from mealoptions.affinity_basis import (  # noqa: F401
    DEFAULT_CONTEXT, DishBase, IngredientRole, FoodRole,
    IngredientAffinity, SEED_DISH_BASES, SEED_INGREDIENT_ROLES,
    SEED_FOOD_ROLES, SEED_INGREDIENT_AFFINITIES,
)
