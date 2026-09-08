"""
@module household.objects.household.HouseholdMember

Row class HouseholdMember of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class HouseholdMember(treeObject):
    @treeObjectInit
    def __init__(self, name: str = '', household_name: str = '', person_name: str = '',
                 role: str = 'adult',
                 purchase_participation: str = 'always',   # always|rotate|never|driver-only
                 can_drive: bool = True, has_workplace_meals: bool = False,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.household_name = household_name
        self.person_name = person_name
        self.role = role
        self.purchase_participation = purchase_participation
        self.can_drive = can_drive
        self.has_workplace_meals = has_workplace_meals
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
