"""
@cross-cutting
@module mealoptions.affinity_basis
@tags @xc:bindings

nmp-11 — the composition vocabulary (decision 11), moved here in
mo-1 with names unchanged:

  DishBase           the meal FAMILY a template instantiates
                     (omelet, salad, pasta, stir-fry, soup, bowl…).
  IngredientRole     groupings a food can carry several of
                     (diced-protein, leafy-green, fruit-topping…).
  FoodRole           one (food, role) membership row.
  IngredientAffinity (role-or-food x DishBase x context) -> WEIGHT.
                     A NORM, NEVER a restriction: low affinity ranks
                     suggestions lower and earns at most a gentle
                     "unusual for this dish" note — banana-on-pasta
                     is allowed (unique/cultural tastes always are).
                     Contexts are cuisine/regional frames; the
                     person's preferred context is a STATED
                     PersonProfile knob, never inferred.

Seeds: hand-curated norms (labeled), with the Ahn et al. 2011
flavor-network paper as the citable aggregate backdrop for shared-
compound pairings; the license-blocked recipe corpora stay
untouched. All extendable per household (decision 13 spirit).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.affinity_composer
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/affinity/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mealoptions.objects.affinity._shared import DEFAULT_CONTEXT, SEED_DISH_BASES, SEED_FOOD_ROLES, SEED_INGREDIENT_AFFINITIES, SEED_INGREDIENT_ROLES, _aff, _base, _fr, _role  # noqa: F401
from mealoptions.objects.affinity.DishBase import DishBase  # noqa: F401
from mealoptions.objects.affinity.IngredientRole import IngredientRole  # noqa: F401
from mealoptions.objects.affinity.FoodRole import FoodRole  # noqa: F401
from mealoptions.objects.affinity.IngredientAffinity import IngredientAffinity  # noqa: F401
