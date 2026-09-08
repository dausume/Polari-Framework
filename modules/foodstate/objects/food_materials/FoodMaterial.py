"""
@module foodstate.objects.food_materials.FoodMaterial

Row class FoodMaterial of the foodstate module — one class per file (design §7), split
from food_materials_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class FoodMaterial(treeObject):
    """One base-ingredient identity — the food-side material row
    whose name anchors '<name>#<state>' subjects."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case identity, = the vendor food_slug ('tomato-raw').
        name: str = '',
        display_name: str = '',
        # ROSTER_CATEGORIES entry.
        roster_category: str = '',
        # Pinned FDC id — filled FROM the vendor file at seed build
        # (0 = not resolved; coverage reports it as a gap).
        fdc_id: int = 0,
        # 'foundation' | 'sr-legacy' (vendor fdc_dataset column).
        fdc_dataset: str = '',
        # FDC's own description for the pinned row.
        fdc_description: str = '',
        # Optional nut-2 FoodItem.name link (harvest loop) — '' = none.
        food_item_name: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.roster_category = roster_category
        self.fdc_id = fdc_id
        self.fdc_dataset = fdc_dataset
        self.fdc_description = fdc_description
        self.food_item_name = food_item_name
        self.provenance_id = provenance_id
        self.notes = notes
