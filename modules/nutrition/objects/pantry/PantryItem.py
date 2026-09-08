"""
@module nutrition.objects.pantry.PantryItem

Row class PantryItem of the nutrition module — one class per file (design §7), split
from pantry_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PantryItem(treeObject):
    """One lot of available food in one household."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-household-rice-1').
        name: str = '',
        household_name: str = '',
        # FoodMaterial/FoodItem slug.
        food_name: str = '',
        # amount as the human states it; grams resolve via the
        # market weight priors ('g'/'kg'/'lb'/'oz' are exact).
        quantity: float = 0.0,
        unit: str = 'g',
        # STORAGE_STATES entry.
        storage_state: str = 'pantry',
        # ISO date acquired ('' = unstated; age reporting skips it).
        acquired_date: str = '',
        # SourceLocation.name it came from ('' = unstated/garden).
        source_location_name: str = '',
        # what this lot cost ('0' = unstated/grown).
        price_paid: float = 0.0,
        currency: str = 'USD',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.household_name = household_name
        self.food_name = food_name
        self.quantity = quantity
        self.unit = unit
        self.storage_state = storage_state
        self.acquired_date = acquired_date
        self.source_location_name = source_location_name
        self.price_paid = price_paid
        self.currency = currency
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
