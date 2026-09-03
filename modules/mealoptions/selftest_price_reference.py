"""
@module mealoptions.selftest_price_reference

mo-2 selftest — PriceReference aggregation + local-first advice on
their own (imports ONLY mealoptions; no nutrition, no household, no
server): aggregation strips every PRIVACY_STRIPPED_FIELDS key,
independents carry no chain name and say prices vary by vendor, the
month has no day, the local-first rule picks the market within the
10 % band, 0 % is strict cheapest, the chain is named in the ranking,
and the package imported nothing person-side.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m mealoptions.selftest_price_reference
"""

import inspect
import sys
from types import SimpleNamespace

from mealoptions.price_reference_analysis import (
    LOCAL_PREFERENCE_LABEL, aggregate_references, price_advice,
)
from mealoptions.price_reference_basis import (
    CHAIN_KINDS, LOCAL_KINDS, OWNERSHIP_KINDS, PRIVACY_STRIPPED_FIELDS,
    PriceReference, SEED_PRICE_REFERENCES, VARIES_BY_VENDOR_NOTE,
    reference_name, region_slug,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _entry(food, location, kind, chain, price_per_kg, day,
           basis='exact-unit-conversion', region='DMV', demo=False):
    """A normalized_prices-shaped entry, person / place / day INCLUDED
    so the strip is exercised."""
    return {'observation': f'{location}-{food}-{day}', 'food': food,
            'location': location, 'locationKind': 'grocery',
            'ownershipKind': kind, 'chainName': chain,
            'isLocal': kind in LOCAL_KINDS, 'region': region,
            'latitude': 38.9, 'longitude': -77.0, 'address': '1 Main St',
            'household_name': 'demo-household', 'purchaser': 'alex',
            'person_name': 'alex', 'location_name': location,
            'observed_date': day, 'price': 1.0, 'currency': 'USD',
            'package': '1 kg', 'packageG': 1000.0,
            'pricePerKg': price_per_kg, 'weightBasis': basis,
            'observedDate': day, 'ageDays': 1, 'isDemo': demo}


ENTRIES = [
    # a chain: three observations across the month at two branches.
    _entry('chicken-breast-raw', 'kroger-eastside', 'chain', 'kroger',
           13.20, '2026-09-01'),
    _entry('chicken-breast-raw', 'kroger-westside', 'chain', 'kroger',
           13.60, '2026-09-08'),
    _entry('chicken-breast-raw', 'kroger-eastside', 'chain', 'kroger',
           12.80, '2026-09-15'),
    # two different farmers-market vendors — ONE reference, no names.
    _entry('chicken-breast-raw', 'saturday-market-stall-3',
           'farmers-market', '', 14.00, '2026-09-06'),
    _entry('chicken-breast-raw', 'sunday-market-stall-9',
           'farmers-market', '', 14.40, '2026-09-13'),
    # a warehouse chain, cheapest of all.
    _entry('chicken-breast-raw', 'costco-north', 'warehouse-chain',
           'costco', 11.90, '2026-09-02'),
    # a previous month, same chain — must land in its own row.
    _entry('chicken-breast-raw', 'kroger-eastside', 'chain', 'kroger',
           12.00, '2026-08-20'),
    # an undated observation — no month, left out.
    _entry('chicken-breast-raw', 'kroger-eastside', 'chain', 'kroger',
           9.99, ''),
    # eggs via a dozen prior at an independent — prior-mixed basis.
    _entry('egg-whole-raw', 'corner-store', 'independent', '', 6.30,
           '2026-09-03', basis='convention-prior', region=''),
]

print('mo-2: price references + local-first advice')

# the class itself
fields = [p for p in inspect.signature(PriceReference.__init__).parameters
          if p not in ('self', 'manager')]
check('PriceReference constructs with defaults',
      all(hasattr(PriceReference(), f) for f in fields))
check('PriceReference carries NONE of the privacy-stripped fields',
      not set(fields) & set(PRIVACY_STRIPPED_FIELDS),
      str(set(fields) & set(PRIVACY_STRIPPED_FIELDS)))
check('references are exported, never hand-seeded (SEED_PRICE_REFERENCES empty)',
      SEED_PRICE_REFERENCES == [])
check('one ownership vocabulary: chain kinds + local kinds ⊂ OWNERSHIP_KINDS',
      set(CHAIN_KINDS) <= set(OWNERSHIP_KINDS)
      and set(LOCAL_KINDS) <= set(OWNERSHIP_KINDS)
      and not set(CHAIN_KINDS) & set(LOCAL_KINDS))
check('region slug: as typed → name-safe; blank → unstated',
      region_slug('DMV (demo placeholder)') == 'dmv-demo-placeholder'
      and region_slug('') == 'unstated')
check('reference name = <food>-<YYYY-MM>-<type>[-<chain>]-<region>',
      reference_name('rice', '2026-09', 'chain', 'kroger', 'DMV')
      == 'rice-2026-09-chain-kroger-dmv'
      and reference_name('rice', '2026-09', 'coop', '', '')
      == 'rice-2026-09-coop-unstated')

# aggregation
rows = aggregate_references(ENTRIES)
by_name = {r['name']: r for r in rows}
check('grouping: per (food, month, type, chain, region) → 5 rows',
      len(rows) == 5, str(sorted(by_name)))
kroger = by_name.get('chicken-breast-raw-2026-09-chain-kroger-dmv')
market = by_name.get('chicken-breast-raw-2026-09-farmers-market-dmv')
costco = by_name.get('chicken-breast-raw-2026-09-warehouse-chain-costco-dmv')
kroger_aug = by_name.get('chicken-breast-raw-2026-08-chain-kroger-dmv')
eggs = by_name.get('egg-whole-raw-2026-09-independent-unstated')
check('the four September chicken rows + one August row exist',
      all(r is not None for r in (kroger, market, costco, kroger_aug, eggs)))
check('aggregation strips EVERY privacy field from every row',
      not any(k in r for r in rows for k in PRIVACY_STRIPPED_FIELDS)
      and not any(k in r for r in rows
                  for k in ('location', 'latitude', 'longitude')))
check('no vendor name leaks (stall names absent from every value)',
      not any('stall' in str(v) or 'eastside' in str(v)
              for r in rows for v in r.values()))
check('month has no day (YYYY-MM only)',
      all(len(r['month']) == 7 and r['month'][4] == '-' for r in rows)
      and not any('2026-09-0' in str(v) for r in rows for v in r.values()))
check('undated observation left out (kroger Sept = 3 samples, not 4)',
      kroger and kroger['sample_count'] == 3)
check('chain row keeps the brand; median/min/max over its branches',
      kroger and kroger['chain_name'] == 'kroger'
      and kroger['price_per_kg_median'] == 13.2
      and kroger['price_per_kg_min'] == 12.8
      and kroger['price_per_kg_max'] == 13.6
      and kroger['varies_by_vendor'] is False)
check('two market vendors → ONE typed row, chain_name blank, varies_by_vendor',
      market and market['chain_name'] == ''
      and market['sample_count'] == 2
      and market['varies_by_vendor'] is True
      and market['price_per_kg_median'] == 14.2
      and VARIES_BY_VENDOR_NOTE in market['notes'])
check('independent with blank region → unstated, prior-mixed basis',
      eggs and eggs['region_label'] == 'unstated'
      and eggs['weight_basis'] == 'prior-mixed'
      and eggs['varies_by_vendor'] is True)
check('exact basis when every sample converted exactly',
      kroger['weight_basis'] == 'exact' and costco['weight_basis'] == 'exact')
check('every row keys are PriceReference constructor fields',
      all(k in fields for r in rows for k in r))
check('provenance says what was stripped',
      all('stripped' in r['provenance_id'] for r in rows))

# advice — the local-first rule and its knob
adv = price_advice(rows, 'chicken-breast-raw')
check('advice ok for the latest month', adv['ok'] and adv['month'] == '2026-09')
check('ranking is a flat record list with the chain NAMED',
      all(isinstance(rec, dict) and not any(isinstance(v, (dict, list))
                                             for v in rec.values())
          for rec in adv['ranking'])
      and any(rec['chainName'] == 'kroger' for rec in adv['ranking'])
      and any(rec['chainName'] == 'costco' for rec in adv['ranking']))
# cheapest chain = costco 11.90; band at 10 % = 13.09; the market's
# 14.20 is above it → strict cheapest wins at 10 %.
check('10 %: market (14.20) is outside costco\'s band (11.90 × 1.10 = '
      '13.09) → cheapest overall recommended, rule says so',
      adv['recommended']['sourceType'] == 'warehouse-chain'
      and 'cheapest overall' in adv['recommended']['rule']
      and 'no local source within 10 %' in adv['recommended']['rule'])
adv25 = price_advice(rows, 'chicken-breast-raw', local_preference_pct=25)
check('25 %: band = 14.88 → the farmers market is recommended FIRST',
      adv25['recommended']['sourceType'] == 'farmers-market'
      and adv25['recommended']['isLocal'] is True
      and 'within 25 %' in adv25['recommended']['rule'])
check('at a wider band the cheapest chain row says it anchored the band',
      any('anchor' in rec['rule'] for rec in adv25['ranking']
          if rec['sourceType'] == 'warehouse-chain'))
adv0 = price_advice(rows, 'chicken-breast-raw', local_preference_pct=0)
check('0 %: strict cheapest (costco), no local preference',
      adv0['recommended']['sourceType'] == 'warehouse-chain'
      and adv0['knob']['localPreferencePct'] == 0.0
      and adv0['recommended']['rule'] == 'recommended: cheapest overall')
check('the knob is labelled as a convention prior',
      adv['knob']['label'] == LOCAL_PREFERENCE_LABEL
      and 'Dustin 2026-09-03' in adv['knob']['label']
      and adv['knob']['localPreferencePct'] == 10.0)
check('every ranking row states which rule decided it',
      all(rec['rule'] for rec in adv['ranking']))
check('honesty says local rows vary by vendor',
      any(VARIES_BY_VENDOR_NOTE in line for line in adv['honesty']))
check('a month with no references refuses by name',
      price_advice(rows, 'chicken-breast-raw', month='2026-07')['ok'] is False
      and price_advice(rows, 'cod-raw')['ok'] is False)
adv_aug = price_advice(rows, 'chicken-breast-raw', month='2026-08')
check('explicit month ranks only that month (August: kroger alone)',
      adv_aug['ok'] and len(adv_aug['ranking']) == 1
      and adv_aug['recommended']['chainName'] == 'kroger')
check('advice accepts objects (live rows) as well as dicts',
      price_advice([SimpleNamespace(**r) for r in rows],
                   'chicken-breast-raw')['recommended']['sourceType']
      == 'warehouse-chain')

# the privacy line on imports
leaky = [m for m in sys.modules
         if m.split('.')[0] in ('nutrition', 'household')]
check('mealoptions imported nothing from nutrition or household',
      not leaky, str(leaky))

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mo-2 price references hold the privacy line')
