"""@module nutrition.objects.shoptrip._shared — what the shoptrip row classes share (constants, seeds, helpers); split from shoptrip_basis.py (sap-2c)."""
import json

_PROV = 'N3 shoptrip (HOUSEHOLD_APP_PAGES.md §3.3)'
DEFAULT_AISLE_ORDER = ['produce', 'bakery', 'dairy', 'meat', 'seafood',
                       'dry-goods', 'frozen', 'household']
UNKNOWN_AISLE = 'unknown'
SEED_STORE_AISLE_ORDERS = [
    {'name': 'demo-grocery-order', 'location_name': 'demo-grocery',
     'household_name': '', 'aisle_order_json': json.dumps(DEFAULT_AISLE_ORDER),
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'convention prior (perimeter-first US grocery layout) — '
              'reorder to match the real store'},
]
_AISLES = {
    'produce': ['apple-raw', 'avocado-raw', 'banana-raw', 'bell-pepper-red-raw',
                'blueberries-raw', 'broccoli-raw', 'carrot-raw', 'celery-raw',
                'cucumber-raw', 'garlic-raw', 'kale-raw', 'lettuce-romaine-raw',
                'mushroom-white-raw', 'onion-raw', 'orange-raw',
                'potato-russet-raw', 'spinach-raw', 'strawberries-raw',
                'sweet-potato-raw', 'tomato-raw', 'basil-leaf', 'kale-leaf'],
    'dairy': ['butter-unsalted', 'cheese-cheddar', 'egg-whole-raw', 'milk-whole',
              'yogurt-plain-whole', 'tofu-firm'],
    'meat': ['beef-chuck-raw', 'chicken-breast-raw', 'ground-beef-90-raw',
             'pork-loin-raw', 'turkey-ground-raw'],
    'seafood': ['cod-raw', 'salmon-atlantic-raw', 'tilapia-raw'],
    'dry-goods': ['almonds-raw', 'black-beans-dry', 'chickpeas-dry',
                  'flour-all-purpose', 'flour-whole-wheat', 'lentils-dry',
                  'oats-rolled', 'olive-oil', 'pasta-dry', 'quinoa-raw',
                  'rice-brown-raw', 'rice-white-raw', 'salt-iodized',
                  'sugar-white', 'walnuts-raw'],
}
SEED_FOOD_AISLE_CATEGORIES = [
    {'name': f'{food}-aisle', 'food_name': food, 'category': aisle,
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'US-grocery aisle convention — a labelled prior; edit to '
              'match where your store shelves it'}
    for aisle, foods in _AISLES.items() for food in foods
]
AISLE_STORAGE_PRIOR = {'produce': 'fridge', 'dairy': 'fridge', 'meat': 'fridge',
                       'seafood': 'fridge', 'frozen': 'freezer'}
