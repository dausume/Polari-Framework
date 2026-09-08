"""
@cross-cutting
@module nutrition.exclusion_basis
@tags @xc:bindings

mpb-1 — allergen/intolerance exclusions as data (MEAL_PLANNING_APP_
PLAN §3b, ratified 2026-09-01: a SAFETY FILTER, never diagnosis):

  FoodAllergenFlag   one roster food × one FDA major-9 allergen
                     class it contains BY IDENTITY (cheddar IS
                     milk; pasta IS wheat). Identity facts, not
                     lab analysis — cross-contact/processing
                     contamination is explicitly OUT (named).
  PersonExclusion    one person's declared exclusion: an allergen
                     class or a single food, with THEIR stated
                     reason and severity. Declared, never
                     inferred; 'allergy-hard' excludes absolutely,
                     'preference-soft' ranks down with a note.

FDA major-9 vocabulary: milk, egg, fish, crustacean-shellfish,
tree-nut, peanut, wheat, soybean, sesame (FASTER Act 2021 added
sesame). Roster foods that carry none of these seed no row —
absence of a flag row for an exotic future food is NOT evidence of
safety; the report says so.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.exclusion_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-1
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/exclusion/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.exclusion._shared import ALLERGEN_CLASSES, EXCLUSION_SEVERITIES, SEED_FOOD_ALLERGEN_FLAGS, SEED_PERSON_EXCLUSIONS, _PROV, _flag  # noqa: F401
from nutrition.objects.exclusion.FoodAllergenFlag import FoodAllergenFlag  # noqa: F401
from nutrition.objects.exclusion.PersonExclusion import PersonExclusion  # noqa: F401
