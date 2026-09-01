"""
@cross-cutting
@module nutrition.fulfillment_basis
@tags @xc:bindings

nmp-7 — GardenPlanDefinition (BUILDS nut-5 in its meal-plan-aware
form): one runnable garden config — a household (or a MealPlan) x
{grown FoodItem: plant count} x harvest cadence. The coverage sim
(fulfillment_analysis) matches DEMAND (household needs, or the
upgraded nmp-7 source: a MealPlan's actual rolled-up demand)
against SUPPLY (realized harvest nutrients, nut-2/aqp-8) — per
nutrient: met/partial/gap/uncoverable, gaps NAMED, uncoverable
nutrients pointed at their real source (saltwater food forest /
fermentation) per the honest-absence rule.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.fulfillment_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-7;
     /HOUSEHOLD_NUTRITION_PLAN.md §nut-5
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


SEED_GARDEN_PLANS = [
    {'name': 'starter-garden', 'display_name': 'Starter garden',
     'household_name': 'demo-household', 'meal_plan_name': '',
     'plantings_json': '{"basil-leaf": 6, "kale-leaf": 8}',
     'harvest_period_days': 30.0,
     'is_prior': True, 'provenance_id': 'nmp-7',
     'notes': 'the nut-2 basil+kale pot roster as a coverage demo'},
]
