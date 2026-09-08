"""
@module nutrition.objects.budget.PlanBudget

Row class PlanBudget of the nutrition module — one class per file (design §7), split
from budget_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
