"""
@module nutrition.purchase_basis

cal-4 (Dustin 2026-09-02): "periodic in bulk purchase events at 1
month, 3 month, 6 month, and yearly periods that can serve as ways
to buy stuff like rice or grains in bulk that last very long periods
without decay, and can act as a means to save money over time."

BulkStaple = one long-shelf-life food a household is willing to buy
in bulk: its CADENCE (months between bulk buys — the knob: 1, 3, 6
or 12), its shelf life (a CITED prior — a cadence longer than the
shelf life is refused by name), and the bulk offer observed (package
+ price + where), which the analysis compares against the best
retail $/kg to state the savings. Every number here is a labeled
prior a household overrides on its own row.

Shelf lives are TRANSCRIBED from the USDA FoodKeeper app (USDA FSIS /
Cornell / FMI; U.S. government work — public domain), pantry
storage, unopened, "best quality" figures; confidence 'transcribed'
means read from the table, not re-verified against the source this
session — verify before quoting.
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: the cadences the arc ships (months) — his four.
BULK_CADENCES = (1, 3, 6, 12)
FOODKEEPER = ('USDA FoodKeeper (FSIS/Cornell/FMI), pantry, unopened, '
              'best-quality window; public domain')


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


def _staple(food, cadence, shelf_days, qty, unit, price, weekly_g, note=''):
    return {'name': f'demo-household-bulk-{food}', 'household_name': 'demo-household',
            'food_name': food, 'cadence_months': cadence, 'shelf_life_days': shelf_days,
            'storage_state': 'pantry', 'bulk_package_quantity': qty,
            'bulk_package_unit': unit, 'bulk_price': price, 'currency': 'USD',
            'bulk_location_name': 'demo-warehouse', 'observed_date': '2026-09-01',
            'weekly_demand_g': weekly_g, 'citation': FOODKEEPER,
            'confidence': 'transcribed', 'is_prior': True, 'provenance_id': 'cal-4',
            'notes': note or 'demo bulk offer + FoodKeeper shelf life — a labeled prior'}


#: Demo household: the four cadences populated. Bulk prices are DEMO
#: observations (is_prior) — a household replaces them with what it
#: actually sees.
SEED_BULK_STAPLES = [
    # yearly — grains that keep for years
    _staple('rice-white-raw', 12, 730, 25, 'lb', 21.99, 500,
            'FoodKeeper: white rice, pantry 2 years'),
    _staple('pasta-dry', 12, 730, 12, 'lb', 13.49, 250,
            'FoodKeeper: dry pasta, pantry 2 years'),
    _staple('sugar-white', 12, 730, 10, 'lb', 6.99, 100,
            'FoodKeeper: granulated sugar, pantry 2 years (keeps indefinitely)'),
    # every 6 months
    _staple('lentils-dry', 6, 365, 10, 'lb', 12.99, 300,
            'FoodKeeper: dried lentils/beans, pantry 1 year'),
    _staple('black-beans-dry', 6, 365, 10, 'lb', 11.49, 250,
            'FoodKeeper: dried beans, pantry 1 year'),
    _staple('chickpeas-dry', 6, 365, 10, 'lb', 12.49, 250,
            'FoodKeeper: dried beans, pantry 1 year'),
    # quarterly
    _staple('oats-rolled', 3, 365, 10, 'lb', 9.99, 400,
            'FoodKeeper: rolled oats, pantry 1 year'),
    _staple('quinoa-raw', 3, 730, 4, 'lb', 12.99, 150,
            'FoodKeeper: quinoa, pantry 2-3 years'),
    _staple('rice-brown-raw', 3, 180, 10, 'lb', 11.99, 300,
            'FoodKeeper: brown rice, pantry 6 months (bran oils go rancid) — '
            'the cadence is capped BY the shelf life'),
    # monthly
    _staple('flour-all-purpose', 1, 240, 10, 'lb', 5.49, 400,
            'FoodKeeper: all-purpose flour, pantry 6-8 months'),
    _staple('flour-whole-wheat', 1, 90, 5, 'lb', 4.99, 200,
            'FoodKeeper: whole-wheat flour, pantry 1-3 months'),
    _staple('olive-oil', 1, 365, 2.76, 'kg', 24.99, 250,
            'FoodKeeper: olive oil, pantry 6-12 months unopened'),
]
