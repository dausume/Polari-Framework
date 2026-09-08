"""
@module nutrition.objects.meal.MealPlanDefinition

Row class MealPlanDefinition of the nutrition module — one class per file (design §7), split
from meal_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MealPlanDefinition(treeObject):
    """A plan: person or household x N days of MealEntries."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-week-1').
        name: str = '',
        display_name: str = '',
        # exactly one of these names the owner.
        person_name: str = '',
        household_name: str = '',
        days: int = 7,
        # presentation anchor ('' = unanchored day indexes).
        start_date: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.person_name = person_name
        self.household_name = household_name
        self.days = days
        self.start_date = start_date
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
