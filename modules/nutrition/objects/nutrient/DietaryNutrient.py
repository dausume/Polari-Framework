"""
@module nutrition.objects.nutrient.DietaryNutrient

Row class DietaryNutrient of the nutrition module — one class per file (design §7), split
from nutrient_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DietaryNutrient(treeObject):
    """One nutrient the household nutrition ledger tracks."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('vitamin-c').
        name: str = '',
        display_name: str = '',
        # NUTRIENT_CATEGORIES entry.
        category: str = 'vitamin',
        # Reporting unit ('mg' / 'ug' / 'g' / 'kcal' / 'IU').
        unit: str = 'mg',
        # Free-text physiological role ('immunity & collagen').
        role: str = '',
        # PLANT_AVAILABILITY entry — the honesty seam.
        plant_availability: str = 'common',
        # For a 'none'/'hard' nutrient, WHERE it actually comes from.
        alternate_source: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.category = category
        self.unit = unit
        self.role = role
        self.plant_availability = plant_availability
        self.alternate_source = alternate_source
        self.provenance_id = provenance_id
        self.notes = notes
