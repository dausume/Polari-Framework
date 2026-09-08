"""
@cross-cutting
@module nutrition.person_basis
@tags @xc:bindings

nut-3 — PersonProfile: body metrics + weight goal + the metabolism /
life-stage factors the user "may not know", surfaced as EXPLICIT tunable
knobs (knobs-and-suggestions — never hidden, honest defaults). The math
(BMR/TDEE/calorie target/per-nutrient needs) lives in person_analysis.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.person_analysis, nutrition.custom.household_analysis
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-3
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/person/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.person._shared import ACTIVITY_LEVELS, ACTIVITY_PAL, EATING_PATTERNS, LIFE_STAGES, WEIGHT_GOALS  # noqa: F401
from nutrition.objects.person.PersonProfile import PersonProfile  # noqa: F401
