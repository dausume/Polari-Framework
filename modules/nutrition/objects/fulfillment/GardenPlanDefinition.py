"""
@module nutrition.objects.fulfillment.GardenPlanDefinition

Row class GardenPlanDefinition of the nutrition module — one class per file (design §7), split
from fulfillment_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class GardenPlanDefinition(treeObject):
    """One garden configuration to simulate coverage for."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('starter-garden').
        name: str = '',
        display_name: str = '',
        # demand source: a household... or (nmp-7) a MealPlan —
        # exactly one set; the meal plan wins when both are.
        household_name: str = '',
        meal_plan_name: str = '',
        # JSON {food_name: plant_count} — GROWN FoodItems only
        # (plant-linked, nut-2); pantry foods are not growable.
        plantings_json: str = '{}',
        # days between harvests of the roster.
        harvest_period_days: float = 30.0,
        # persisted snapshot of the last coverage run (scoring seam).
        coverage_result_json: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.household_name = household_name
        self.meal_plan_name = meal_plan_name
        self.plantings_json = plantings_json
        self.harvest_period_days = harvest_period_days
        self.coverage_result_json = coverage_result_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
