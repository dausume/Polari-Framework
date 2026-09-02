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
  - nutrition.budget_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-3
"""

from objectTreeDecorators import treeObject, treeObjectInit

_PROV = 'mpb-3 (MEAL_PLANNING_APP_PLAN §3b)'


class PlanBudget(treeObject):
    """One weekly budget cap for a plan or a household."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-week-budget').
        name: str = '',
        # exactly one of these scopes the cap.
        plan_name: str = '',
        household_name: str = '',
        weekly_amount: float = 0.0,
        currency: str = 'USD',
        # the human's own framing ('groceries only, eating-out
        # excluded').
        scope_note: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.plan_name = plan_name
        self.household_name = household_name
        self.weekly_amount = weekly_amount
        self.currency = currency
        self.scope_note = scope_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


#: Demo cap so the planner page renders the envelope.
SEED_PLAN_BUDGETS = [
    {'name': 'demo-alex-week-budget', 'plan_name': 'demo-alex-week',
     'household_name': '', 'weekly_amount': 60.0,
     'currency': 'USD', 'scope_note': 'demo cap — set your own',
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo row'},
]
