"""
@module nutrition.objects.shoptrip.FoodAisleCategory

Row class FoodAisleCategory of the nutrition module — one class per file (design §7), split
from shoptrip_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from nutrition.objects.shoptrip._shared import UNKNOWN_AISLE

class FoodAisleCategory(treeObject):
    """food → aisle category label (a labelled convention)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('<food>-aisle').
        name: str = '',
        # FoodMaterial/FoodItem slug.
        food_name: str = '',
        # aisle category label ('produce' | 'dairy' | 'meat' | …).
        category: str = UNKNOWN_AISLE,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.category = category
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
