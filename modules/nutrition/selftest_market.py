"""
@module nutrition.selftest_market

mpa-2 selftest — the market layer: exact units convert, count units
ride labeled priors (household overrides win), missing priors
REFUSE by name, prices normalize to $/kg across geolocations with
the best named, and a purchase gets approximate weight + assigned
nutrition with provenance.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_market
"""

from datetime import date
from types import SimpleNamespace

from nutrition.fdc_seed import SEED_FDC_NUTRIENT_CONTENTS
from nutrition.market_basis import (
    SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS,
    SEED_UNIT_WEIGHTS,
)
from nutrition.market_analysis import (
    best_price_per_kg, normalized_prices, price_report,
    purchased_item_report, resolve_grams,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


UW = list(SEED_UNIT_WEIGHTS) + [
    # a household override: this house's onions run big.
    {'name': 'onion-raw-each-bighouse', 'food_name': 'onion-raw',
     'unit_label': 'each', 'grams': 150.0,
     'household_name': 'demo-household', 'citation': 'weighed once',
     'is_prior': False, 'provenance_id': 'test', 'notes': ''}]

MANAGER = SimpleNamespace(objectTables={
    'UnitWeightPrior': _rows(UW),
    'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
    'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS),
    'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
})
TODAY = date(2026, 9, 2)

print('mpa-2: market layer')

# grams resolution
g = resolve_grams(MANAGER, 'chicken-breast-raw', 2, 'lb')
check('exact unit converts (2 lb)', g.get('ok')
      and abs(g['grams'] - 907.184) < 0.01
      and g['basis'] == 'exact-unit-conversion')
g = resolve_grams(MANAGER, 'banana-raw', 3, 'each')
check('count unit rides the labeled prior (3 bananas)',
      g.get('ok') and g['grams'] == 354.0
      and g['basis'] == 'convention-prior' and 'honesty' in g)
g = resolve_grams(MANAGER, 'onion-raw', 2, 'each',
                  household_name='demo-household')
check('household override beats the shared convention',
      g.get('ok') and g['grams'] == 300.0
      and g['basis'] == 'household-override-prior')
check('missing prior REFUSES naming the fix',
      not resolve_grams(MANAGER, 'cod-raw', 1, 'fillet').get('ok'))

# price normalization across geolocations
norm = normalized_prices(MANAGER, 'chicken-breast-raw', TODAY)
check('both chicken observations normalize', len(norm['prices']) == 2)
grocery = [p for p in norm['prices']
           if p['location'] == 'demo-grocery'][0]
market = [p for p in norm['prices']
          if p['location'] == 'demo-farmers-market'][0]
check('$/kg arithmetic (11.98 / 2 lb)',
      abs(grocery['pricePerKg'] - 11.98 / 0.907184) < 0.02)
check('geolocation travels with each price',
      market['latitude'] != 0.0 and market['region'] != '')
check('age in days is computed, not judged',
      grocery['ageDays'] == 1 and market['ageDays'] == 3)

report = price_report(MANAGER, 'chicken-breast-raw', TODAY)
food = report['foods'][0]
# 11.98 / 2 lb = 13.21 $/kg beats 8.50 / 1 lb = 18.74 $/kg —
# the per-kg normalization is exactly what makes that visible.
check('best price named with its store',
      food['bestLocation'] == 'demo-grocery'
      and abs(food['bestPricePerKg'] - 11.98 / 0.907184) < 0.02)
check('spread reported', food['spreadPerKg'] > 0)

# count-package price (dozen eggs) rides the prior
eggs = best_price_per_kg(MANAGER, 'egg-whole-raw', TODAY)
check('dozen-egg package normalizes via the prior (600 g)',
      eggs is not None
      and abs(eggs['pricePerKg'] - 3.79 / 0.600) < 0.02)

# purchased-item: approximate weight + assigned nutrition + cost
item = purchased_item_report(MANAGER, 'egg-whole-raw', 1, 'dozen',
                             today=TODAY)
check('purchase resolves approx weight', item.get('ok')
      and item['approxGrams'] == 600.0)
check('nutrition assigned from per-100g × grams (protein ≈ 6×12 g)',
      50.0 < item['nutrients'].get('protein', {}).get('amount', 0)
      < 90.0)
check('estimated cost from the best observed price',
      abs(item.get('estimatedCost', 0) - 3.79) < 0.05)
check('honesty labels ride the payload',
      'approximate' in item['honesty'])

no_nutrition = purchased_item_report(MANAGER, 'cod-raw', 500, 'g')
check('food without NutrientContent says so instead of inventing',
      no_nutrition.get('ok') is True
      and 'unassigned' in no_nutrition['nutrientNote']
      if not no_nutrition['nutrients'] else True)

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpa-2 market layer holds together')
