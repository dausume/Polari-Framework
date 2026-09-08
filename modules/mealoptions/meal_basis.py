"""
@cross-cutting
@module mealoptions.meal_basis
@tags @xc:bindings

nmp-4 — meals as data (decisions 1/2/4/5), the shareable half (mo-1):

  MealTemplate         ONE meal as a template: a set of base recipes
                       plus allowed variations. HARD-bounded at
                       authoring: the gate (nutrition.custom.meal_analysis.
                       validate_template) computes EVERY variation's
                       rollup and REFUSES the template if any
                       nutrient spikes past the average-person
                       per-meal caps — refusal with named reasons,
                       distinct from the soft warnings on intake.
  VariationDefinition  an allowed variation: food swaps + a portion
                       scale range. A variation is valid only inside
                       the template's bounds.

MealPlanDefinition and MealEntry (a person's/household's week) stay
in nutrition.meal_basis — they name people.

Slots (decision 5): breakfast, lunch, dinner, brunch, linner, snack
(+ snack-2 for the 5-slot pattern). Days are 1-based indexes — the
calendar mapping is presentation, not data.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.meal_analysis (via nutrition.meal_basis re-export)
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/meal/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from mealoptions.objects.meal._shared import MEAL_SLOTS, SEED_MEAL_TEMPLATES, SEED_VARIATIONS  # noqa: F401
from mealoptions.objects.meal.MealTemplate import MealTemplate  # noqa: F401
from mealoptions.objects.meal.VariationDefinition import VariationDefinition  # noqa: F401
