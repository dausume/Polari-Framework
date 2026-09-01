"""
@cross-cutting
@module nutrition.pantry_basis
@tags @xc:bindings

mpa-3 — the pantry as data (MEAL_PLANNING_APP_PLAN.md §0.1: "being
able to adjust plans based on available food"):

  PantryItem   one lot of food a household actually HAS: food ×
               quantity (any unit the weight priors can resolve) ×
               storage state × where/when it was acquired and what
               it cost. Approximate by design — the same labeled
               weight priors as purchases; a kitchen scale beats
               the prior any day (enter grams directly).

Storage states align with the nmp-10 StorageActionDefinition
vocabulary (pantry / fridge / freezer); food-safety windows stay
nmp-10's concern — v1 reports age, not verdicts (named gap).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.pantry_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-3
"""

from objectTreeDecorators import treeObject, treeObjectInit

STORAGE_STATES = ('pantry', 'fridge', 'freezer')

_PROV = 'mpa-3 (MEAL_PLANNING_APP_PLAN.md)'


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


def _pi(name, food, qty, unit, storage, date='', note=''):
    return {'name': name, 'household_name': 'demo-household',
            'food_name': food, 'quantity': qty, 'unit': unit,
            'storage_state': storage, 'acquired_date': date,
            'source_location_name': '', 'price_paid': 0.0,
            'currency': 'USD', 'is_prior': True,
            'provenance_id': _PROV,
            'notes': note or 'demo pantry row — replace with yours'}


#: Demo pantry so the pages + availability reports render before
#: real data lands.
SEED_PANTRY_ITEMS = [
    _pi('demo-pantry-rice', 'rice-white-raw', 2.0, 'kg', 'pantry',
        '2026-08-20'),
    _pi('demo-pantry-eggs', 'egg-whole-raw', 8.0, 'each', 'fridge',
        '2026-08-28'),
    _pi('demo-pantry-spinach', 'spinach-raw', 1.0, 'bunch', 'fridge',
        '2026-08-31'),
    _pi('demo-pantry-chicken', 'chicken-breast-raw', 1.0, 'lb',
        'freezer', '2026-08-15'),
    _pi('demo-pantry-oil', 'olive-oil', 400.0, 'g', 'pantry',
        '2026-07-01'),
]
