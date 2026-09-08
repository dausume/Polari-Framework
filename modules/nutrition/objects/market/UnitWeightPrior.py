"""
@module nutrition.objects.market.UnitWeightPrior

Row class UnitWeightPrior of the nutrition module — one class per file (design §7), split
from market_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class UnitWeightPrior(treeObject):
    """'one <unit> of <food> ≈ N grams' — a labeled convention."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('banana-raw-each').
        name: str = '',
        food_name: str = '',
        # 'each' | 'medium' | 'large' | 'cup' | 'tbsp' | 'clove' |
        # 'stalk' | 'slice' | 'dozen' | 'bunch' … (free vocabulary).
        unit_label: str = 'each',
        grams: float = 0.0,
        # household override ('' = the shared convention row).
        household_name: str = '',
        citation: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.unit_label = unit_label
        self.grams = grams
        self.household_name = household_name
        self.citation = citation
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
