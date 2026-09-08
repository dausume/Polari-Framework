"""
@module nutrition.objects.market.PriceObservation

Row class PriceObservation of the nutrition module — one class per file (design §7), split
from market_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PriceObservation(treeObject):
    """One observed price for one food at one location."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('eastside-chicken-2026-09-01').
        name: str = '',
        # FoodMaterial/FoodItem slug ('chicken-breast-raw').
        food_name: str = '',
        # SourceLocation.name.
        location_name: str = '',
        # price of ONE package as bought.
        price: float = 0.0,
        currency: str = 'USD',
        # what the package holds: quantity in package_unit —
        # exact mass units (g/kg/lb/oz) convert directly; count
        # units ('each', 'dozen', 'bunch'…) resolve via
        # UnitWeightPrior (approximate, labeled).
        package_quantity: float = 1.0,
        package_unit: str = 'kg',
        # ISO date observed ('' = undated, reported as such).
        observed_date: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.food_name = food_name
        self.location_name = location_name
        self.price = price
        self.currency = currency
        self.package_quantity = package_quantity
        self.package_unit = package_unit
        self.observed_date = observed_date
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
