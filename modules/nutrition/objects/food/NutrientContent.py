"""
@module nutrition.objects.food.NutrientContent

Row class NutrientContent of the nutrition module — one class per file (design §7), split
from food_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class NutrientContent(treeObject):
    """One (food, nutrient) content value per 100 g edible."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('basil-leaf-vitamin-k').
        name: str = '',
        # The FoodItem (by name).
        food_name: str = '',
        # The DietaryNutrient (by name).
        nutrient_name: str = '',
        # Amount per 100 g edible, in the nutrient's unit.
        amount_per_100g: float = 0.0,
        unit: str = 'mg',
        # USDA FoodData Central value vs an estimate.
        is_prior: bool = True,
        source: str = 'USDA FDC',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.nutrient_name = nutrient_name
        self.amount_per_100g = amount_per_100g
        self.unit = unit
        self.is_prior = is_prior
        self.source = source
        self.provenance_id = provenance_id
        self.notes = notes
