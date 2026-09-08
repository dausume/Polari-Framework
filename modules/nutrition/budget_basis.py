"""
@cross-cutting
@module nutrition.budget_basis
@tags @xc:bindings

mpb-3 — the budget envelope as data (MEAL_PLANNING_APP_PLAN §3b):

  PlanBudget   one plan's (or household's standing) weekly money
               cap — its own row rather than a new field on the
               frozen MealPlanDefinition schema (schema-
               stabilization discipline: extend by rows, not by
               widening existing classes). Evaluation shows spend
               vs cap and the biggest drivers; it never trims a
               plan silently (knobs-and-suggestions).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.custom.budget_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-3
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/budget/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.budget._shared import SEED_PLAN_BUDGETS, _PROV  # noqa: F401
from nutrition.objects.budget.PlanBudget import PlanBudget  # noqa: F401
