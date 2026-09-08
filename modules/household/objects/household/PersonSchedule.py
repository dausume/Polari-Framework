"""
@module household.objects.household.PersonSchedule

Row class PersonSchedule of the household module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PersonSchedule(treeObject):
    """A recurring commitment: when and WHERE a person is."""

    @treeObjectInit
    def __init__(self, name: str = '', person_name: str = '', kind: str = 'work',
                 display_name: str = '',
                 # `schedule` (semantic type applied at registration).
                 recurrence: str = '{}',
                 location_kind: str = 'workplace', location_name: str = '',
                 # minutes the block may move (0 = fixed).
                 flexibility_min: int = 0,
                 is_prior: bool = True, provenance_id: str = '', notes: str = '',
                 manager=None):
        self.name = name
        self.person_name = person_name
        self.kind = kind
        self.display_name = display_name
        self.recurrence = recurrence
        self.location_kind = location_kind
        self.location_name = location_name
        self.flexibility_min = flexibility_min
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
