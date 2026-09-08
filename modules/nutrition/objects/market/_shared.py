"""@module nutrition.objects.market._shared — what the market row classes share (constants, seeds, helpers); split from market_basis.py (sap-2c)."""

LOCATION_KINDS = ('grocery', 'farmers-market', 'warehouse-club',
                  'online', 'garden', 'other')
EXACT_UNIT_GRAMS = {'g': 1.0, 'kg': 1000.0, 'lb': 453.592,
                    'oz': 28.3495}
_UW_CITE = ('FDC household-measure conventions, TRANSCRIBED '
            '(unverified this session) — a labeled prior, tunable '
            'per household; weigh once to override')
_PROV = 'mpa-2 (MEAL_PLANNING_APP_PLAN.md)'
def _uw(food, unit, grams, note=''):
    return {'name': f'{food}-{unit}', 'food_name': food,
            'unit_label': unit, 'grams': grams,
            'household_name': '', 'citation': _UW_CITE,
            'is_prior': True, 'provenance_id': _PROV, 'notes': note}
SEED_UNIT_WEIGHTS = [
    _uw('egg-whole-raw', 'each', 50.0, 'large egg, without shell'),
    _uw('banana-raw', 'each', 118.0, 'medium, peeled'),
    _uw('apple-raw', 'each', 182.0, 'medium, whole'),
    _uw('orange-raw', 'each', 131.0, 'medium, peeled'),
    _uw('onion-raw', 'each', 110.0, 'medium'),
    _uw('garlic-raw', 'clove', 3.0, ''),
    _uw('carrot-raw', 'each', 61.0, 'medium'),
    _uw('potato-russet-raw', 'each', 173.0, 'medium'),
    _uw('sweet-potato-raw', 'each', 130.0, 'medium'),
    _uw('tomato-raw', 'each', 62.0, 'roma (the vendored variety)'),
    _uw('bell-pepper-red-raw', 'each', 119.0, 'medium'),
    _uw('celery-raw', 'stalk', 40.0, ''),
    _uw('cucumber-raw', 'each', 201.0, ''),
    _uw('avocado-raw', 'each', 136.0, 'flesh of one medium'),
    _uw('lettuce-romaine-raw', 'head', 626.0, ''),
    _uw('kale-raw', 'bunch', 170.0, ''),
    _uw('spinach-raw', 'bunch', 340.0, ''),
    _uw('broccoli-raw', 'head', 608.0, 'medium head'),
    _uw('mushroom-white-raw', 'each', 18.0, 'medium'),
    _uw('blueberries-raw', 'cup', 148.0, ''),
    _uw('strawberries-raw', 'cup', 152.0, 'whole berries'),
    _uw('milk-whole', 'cup', 244.0, ''),
    _uw('yogurt-plain-whole', 'cup', 245.0, ''),
    _uw('butter-unsalted', 'tbsp', 14.2, ''),
    _uw('olive-oil', 'tbsp', 13.5, ''),
    _uw('cheese-cheddar', 'oz-slice', 28.35, 'one ounce slice'),
    _uw('rice-white-raw', 'cup', 185.0, 'dry'),
    _uw('rice-brown-raw', 'cup', 190.0, 'dry'),
    _uw('oats-rolled', 'cup', 81.0, 'dry'),
    _uw('quinoa-raw', 'cup', 170.0, 'dry'),
    _uw('flour-all-purpose', 'cup', 125.0, 'spooned + leveled'),
    _uw('flour-whole-wheat', 'cup', 120.0, 'spooned + leveled'),
    _uw('sugar-white', 'cup', 200.0, 'granulated'),
    _uw('black-beans-dry', 'cup', 194.0, 'dry'),
    _uw('chickpeas-dry', 'cup', 200.0, 'dry'),
    _uw('lentils-dry', 'cup', 192.0, 'dry'),
    _uw('almonds-raw', 'cup', 143.0, 'whole'),
    _uw('walnuts-raw', 'cup', 117.0, 'halves'),
    _uw('chicken-breast-raw', 'each', 174.0, 'one boneless breast'),
    _uw('egg-whole-raw', 'dozen', 600.0, '12 large, without shell'),
]
SEED_SOURCE_LOCATIONS = [
    {'name': 'demo-grocery', 'display_name': 'Demo Grocery (chain)',
     'kind': 'grocery', 'ownership_kind': 'chain',
     'chain_name': 'demo-chain',
     'latitude': 38.8951, 'longitude': -77.0364,
     'region_label': 'DMV (demo placeholder)', 'address': '',
     'household_name': '', 'is_prior': True, 'provenance_id': _PROV,
     'notes': 'demo row — replace with a real store'},
    {'name': 'demo-farmers-market',
     'display_name': 'Demo Farmers Market',
     'kind': 'farmers-market', 'ownership_kind': 'farmers-market',
     'chain_name': '',
     'latitude': 38.9847,
     'longitude': -77.0947, 'region_label': 'DMV (demo placeholder)',
     'address': '', 'household_name': '', 'is_prior': True,
     'provenance_id': _PROV,
     'notes': 'demo row — replace with a real market'},
    # mlg-1: the workplace as a LOCATED source so "shop on the way
    # home" (mlg-6) can use distance; PersonSchedule rows point here.
    {'name': 'demo-workplace', 'display_name': 'Demo workplace',
     'kind': 'workplace', 'ownership_kind': 'other', 'chain_name': '',
     'latitude': 38.9072, 'longitude': -77.0369,
     'region_label': 'DMV (demo placeholder)', 'address': '',
     'household_name': 'demo-household', 'is_prior': True,
     'provenance_id': 'mlg-1',
     'notes': 'demo row — where Alex and Sam work; not a store'},
    {'name': 'demo-warehouse', 'display_name': 'Demo warehouse club',
     'kind': 'warehouse-club', 'ownership_kind': 'warehouse-chain',
     'chain_name': 'demo-warehouse-chain',
     'latitude': 38.8339, 'longitude': -77.1194,
     'region_label': 'DMV (demo placeholder)', 'address': '',
     'household_name': '', 'is_prior': True, 'provenance_id': 'cal-4',
     'notes': 'demo row — a household\'s own BulkStaple offers may point here '
              '(the shipped mealoptions staples leave the pointer blank)'},
]
def _po(name, food, location, price, qty, unit, date, note=''):
    return {'name': name, 'food_name': food,
            'location_name': location, 'price': price,
            'currency': 'USD', 'package_quantity': qty,
            'package_unit': unit, 'observed_date': date,
            'is_prior': True, 'provenance_id': _PROV,
            'notes': note or 'demo observation — enter real prices'}
SEED_PRICE_OBSERVATIONS = [
    _po('demo-chicken-grocery', 'chicken-breast-raw', 'demo-grocery',
        11.98, 2.0, 'lb', '2026-09-01'),
    # mo-2: the market observations share the grocery's month so the
    # month-level references compare chain vs farmers market.
    _po('demo-chicken-market', 'chicken-breast-raw',
        'demo-farmers-market', 8.50, 1.0, 'lb', '2026-09-01'),
    _po('demo-rice-grocery', 'rice-white-raw', 'demo-grocery',
        12.99, 5.0, 'lb', '2026-09-01'),
    _po('demo-eggs-grocery', 'egg-whole-raw', 'demo-grocery',
        3.79, 1.0, 'dozen', '2026-09-01'),
    _po('demo-tomato-market', 'tomato-raw', 'demo-farmers-market',
        2.50, 1.0, 'lb', '2026-09-01'),
    _po('demo-spinach-grocery', 'spinach-raw', 'demo-grocery',
        2.99, 1.0, 'bunch', '2026-09-01'),
    _po('demo-oil-grocery', 'olive-oil', 'demo-grocery',
        11.49, 750.0, 'g', '2026-09-01',
        'demo: 750 ml bottle entered by mass-equivalent'),
]
