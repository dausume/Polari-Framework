"""
@module scoring.objects.survival_costs.SurvivalCostProfile

Row class SurvivalCostProfile of the scoring module — one class per file (design §7), split
from survival_costs_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class SurvivalCostProfile(treeObject):
    """One household's entered month of survival costs."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('household-<contributor>-<month>').
        name: str = '',
        # Contributor row (pseudonymous by its own knob).
        contributed_by: str = '',
        # ScoreContext names: where + when.
        location_context: str = '',
        month_context: str = '',
        # Household knobs.
        household_size: int = 1,
        workers: int = 1,
        cars_needed: int = 0,
        # {category: {'amount': $/month, 'notes': str}} (JSON).
        entries_json: str = '{}',
        # Category names skipped (JSON list) — honest gaps.
        skipped_json: str = '[]',
        total_monthly: float = None,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.contributed_by = contributed_by
        self.location_context = location_context
        self.month_context = month_context
        self.household_size = household_size
        self.workers = workers
        self.cars_needed = cars_needed
        self.entries_json = entries_json
        self.skipped_json = skipped_json
        self.total_monthly = total_monthly
        self.notes = notes
