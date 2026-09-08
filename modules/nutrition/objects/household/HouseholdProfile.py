"""
@module nutrition.objects.household.HouseholdProfile

Row class HouseholdProfile of the nutrition module — one class per file (design §7), split
from household_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class HouseholdProfile(treeObject):
    """A household — a named set of member PersonProfiles."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('smith-household').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list of PersonProfile names.
        member_names_json: str = '[]',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.member_names_json = member_names_json
        self.provenance_id = provenance_id
        self.notes = notes
