"""@module mealoptions.objects.staple._shared — what the staple row classes share (constants, seeds, helpers); split from staple_basis.py (sap-2c)."""

BULK_CADENCES = (1, 3, 6, 12)
FOODKEEPER = ('USDA FoodKeeper (FSIS/Cornell/FMI), pantry, unopened, '
              'best-quality window; public domain')
INSTANCE_POINTER_FIELDS = ('household_name', 'bulk_location_name',
                           'observed_date')
def _staple(food, cadence, shelf_days, qty, unit, price, weekly_g, note=''):
    # Seed names keep the cal-4 keys so the upsert converges on the
    # rows already live; the pointer fields are blank by the mo-1 line.
    return {'name': f'demo-household-bulk-{food}', 'household_name': '',
            'food_name': food, 'cadence_months': cadence, 'shelf_life_days': shelf_days,
            'storage_state': 'pantry', 'bulk_package_quantity': qty,
            'bulk_package_unit': unit, 'bulk_price': price, 'currency': 'USD',
            'bulk_location_name': '', 'observed_date': '',
            'weekly_demand_g': weekly_g, 'citation': FOODKEEPER,
            'confidence': 'transcribed', 'is_prior': True, 'provenance_id': 'cal-4',
            'notes': (note or 'demo bulk offer + FoodKeeper shelf life — a labeled prior')
                     + '; offer location lives on the instance'}
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
