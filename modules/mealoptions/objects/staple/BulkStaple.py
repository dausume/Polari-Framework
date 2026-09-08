"""
@module mealoptions.objects.staple.BulkStaple

Row class BulkStaple of the mealoptions module — one class per file (design §7), split
from staple_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BulkStaple(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        household_name: str = '',
        # FoodMaterial/FoodItem slug.
        food_name: str = '',
        # months between bulk buys (BULK_CADENCES entry) — the knob.
        cadence_months: int = 3,
        # cited prior; the analysis refuses a cadence that outlives it.
        shelf_life_days: int = 0,
        storage_state: str = 'pantry',
        # the bulk offer as observed (a warehouse-club sack, a 25 lb bag).
        bulk_package_quantity: float = 0.0,
        bulk_package_unit: str = 'lb',
        bulk_price: float = 0.0,
        currency: str = 'USD',
        bulk_location_name: str = '',
        observed_date: str = '',
        # weekly demand override in grams ('0' = derive from the plans).
        weekly_demand_g: float = 0.0,
        citation: str = '',
        confidence: str = 'transcribed',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.household_name = household_name
        self.food_name = food_name
        self.cadence_months = cadence_months
        self.shelf_life_days = shelf_life_days
        self.storage_state = storage_state
        self.bulk_package_quantity = bulk_package_quantity
        self.bulk_package_unit = bulk_package_unit
        self.bulk_price = bulk_price
        self.currency = currency
        self.bulk_location_name = bulk_location_name
        self.observed_date = observed_date
        self.weekly_demand_g = weekly_demand_g
        self.citation = citation
        self.confidence = confidence
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
