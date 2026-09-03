"""
@cross-cutting
@module nutrition.shoptrip_basis
@tags @xc:bindings

N3 — the SHOPPING TRIP page as data (HOUSEHOLD_APP_PAGES.md §3.3:
"the purchase event's lines as a checklist by store aisle order,
prices editable in place → PriceObservation rows; 'bought' →
PantryItem lots"):

  StoreAisleOrder    ONE store's walk order — an ordered list of
                     aisle category labels for one SourceLocation
                     (per household when stated). The aisle-order
                     KNOB lives here, not on SourceLocation (that
                     class is owned elsewhere tonight).
  FoodAisleCategory  food → aisle category label ('produce',
                     'dairy', …). A labelled CONVENTION over the
                     fsp-1 roster: US-grocery layout priors, tunable
                     per row; a food with no row lands in the
                     'unknown' aisle, named, last.

Both are knobs with defaults; nothing here is a measurement.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.shoptrip_analysis, shoptrip_api, shoptrip_seed
@see AI-Notes/designs/HOUSEHOLD_APP_PAGES.md §3.3
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

_PROV = 'N3 shoptrip (HOUSEHOLD_APP_PAGES.md §3.3)'

#: The default walk order — a US-grocery layout CONVENTION (perimeter
#: first: produce → bakery → dairy → meat → seafood, then the centre
#: aisles, frozen last so it stays cold). A StoreAisleOrder row per
#: store overrides it.
DEFAULT_AISLE_ORDER = ['produce', 'bakery', 'dairy', 'meat', 'seafood',
                       'dry-goods', 'frozen', 'household']

#: The label a food gets when no FoodAisleCategory row names it.
UNKNOWN_AISLE = 'unknown'


class StoreAisleOrder(treeObject):
    """The order one store's aisles are walked — a per-store knob."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-grocery-order').
        name: str = '',
        # SourceLocation.name this order belongs to.
        location_name: str = '',
        # household that walks it this way ('' = shared/global).
        household_name: str = '',
        # JSON ordered list of aisle category labels.
        aisle_order_json: str = '[]',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.location_name = location_name
        self.household_name = household_name
        self.aisle_order_json = aisle_order_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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


SEED_STORE_AISLE_ORDERS = [
    {'name': 'demo-grocery-order', 'location_name': 'demo-grocery',
     'household_name': '', 'aisle_order_json': json.dumps(DEFAULT_AISLE_ORDER),
     'is_prior': True, 'provenance_id': _PROV,
     'notes': 'convention prior (perimeter-first US grocery layout) — '
              'reorder to match the real store'},
]

# fsp-1 roster (fdc_seed: 49 FDC foods) + the two nut-2 grown foods,
# each placed in a US-grocery aisle CONVENTION. Tofu rides the
# refrigerated case with dairy (a convention, not a food class).
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

#: The per-category storage state a fresh lot lands in (put-away
#: prior; the pantry page is where a household corrects it).
AISLE_STORAGE_PRIOR = {'produce': 'fridge', 'dairy': 'fridge', 'meat': 'fridge',
                       'seafood': 'fridge', 'frozen': 'freezer'}

SHOPTRIP_CLASSES = [StoreAisleOrder, FoodAisleCategory]
#: (name, class, seeds) — the HOUSEHOLD_SEED_PAIRS shape the server's
#: seed passes unpack (a 2-tuple crashed ensureDefinitionTables on the
#: 2026-09-03 night deploy and took every later seed with it).
SHOPTRIP_SEED_PAIRS = [
    ('StoreAisleOrder', StoreAisleOrder, SEED_STORE_AISLE_ORDERS),
    ('FoodAisleCategory', FoodAisleCategory, SEED_FOOD_AISLE_CATEGORIES),
]
