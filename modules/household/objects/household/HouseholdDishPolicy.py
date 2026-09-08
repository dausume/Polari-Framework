"""
@module household.objects.household.HouseholdDishPolicy

Row class HouseholdDishPolicy of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class HouseholdDishPolicy(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '',
                 preprep_strategy: str = 'wash-as-you-go',
                 meal_strategy: str = 'batch-after-meal',
                 cooldown_after_eating_min: float = 10.0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.preprep_strategy = preprep_strategy
        self.meal_strategy = meal_strategy
        self.cooldown_after_eating_min = cooldown_after_eating_min
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
