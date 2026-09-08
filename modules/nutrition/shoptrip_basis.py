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
  - nutrition.custom.shoptrip_analysis, shoptrip_api, shoptrip_seed
@see AI-Notes/designs/HOUSEHOLD_APP_PAGES.md §3.3
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/shoptrip/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.objects.shoptrip._shared import AISLE_STORAGE_PRIOR, DEFAULT_AISLE_ORDER, SEED_FOOD_AISLE_CATEGORIES, SEED_STORE_AISLE_ORDERS, UNKNOWN_AISLE, _AISLES, _PROV  # noqa: F401
from nutrition.objects.shoptrip.StoreAisleOrder import StoreAisleOrder  # noqa: F401
from nutrition.objects.shoptrip.FoodAisleCategory import FoodAisleCategory  # noqa: F401


SHOPTRIP_CLASSES = [StoreAisleOrder, FoodAisleCategory]
SHOPTRIP_SEED_PAIRS = [
    ('StoreAisleOrder', StoreAisleOrder, SEED_STORE_AISLE_ORDERS),
    ('FoodAisleCategory', FoodAisleCategory, SEED_FOOD_AISLE_CATEGORIES),
]
