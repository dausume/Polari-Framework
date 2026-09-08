"""
@module cntfet.objects.cnt_targets.DesignTarget

Row class DesignTarget of the cntfet module — one class per file (design §7), split
from cnt_targets_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DesignTarget(treeObject):
    """What a device / library is engineered FOR, as a row: the
    PowerBudget rows (by name) and other criteria that apply."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # PowerBudget names this target enforces (by scope)
        budgets_json: str = '[]',
        # non-power criteria (informational for now, data for later)
        criteria_json: str = '[]',
        # 'switching' | 'signal' | 'any' — the optimization class it
        # belongs with
        optimization: str = 'switching',
        notes: str = '',
        is_prior: bool = True,
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.budgets_json = budgets_json
        self.criteria_json = criteria_json
        self.optimization = optimization
        self.notes = notes
        self.is_prior = is_prior
