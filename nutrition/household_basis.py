"""
@cross-cutting
@module nutrition.household_basis
@tags @xc:bindings

nut-4 — HouseholdProfile: a set of PersonProfiles whose nutrient needs
aggregate into the household's total demand (per day/week/month). The
demand the hydroponic fulfillment sim (nut-5) is solved against.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.household_analysis
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-4
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
