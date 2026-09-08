"""
@cross-cutting
@module nutrition.household_basis
@tags @xc:bindings

nut-4 — HouseholdProfile: a set of PersonProfiles whose nutrient needs
aggregate into the household's total demand (per day/week/month). The
demand the hydroponic fulfillment sim (nut-5) is solved against.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.household_analysis
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-4
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/household/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.household.HouseholdProfile import HouseholdProfile  # noqa: F401
