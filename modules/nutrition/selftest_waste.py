"""
@module nutrition.selftest_waste

mpb-4 selftest (waste half) — the waste ledger: grams resolve via
the priors, priced waste gets a labeled $ estimate, UNPRICED waste
counts in grams and is named (never valued at zero), grouping is
worst-first with reasons, and an empty ledger says what it can and
cannot know.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_waste
"""

from datetime import date
from types import SimpleNamespace

from nutrition.market_basis import (SEED_PRICE_OBSERVATIONS,
                                    SEED_SOURCE_LOCATIONS,
                                    SEED_UNIT_WEIGHTS)
from nutrition.waste_basis import SEED_WASTE_RECORDS
from nutrition.waste_analysis import waste_report

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


RECORDS = list(SEED_WASTE_RECORDS) + [
    # priced waste: 1 lb chicken, over-prepped
    {'name': 'w-chicken', 'household_name': 'demo-household',
     'food_name': 'chicken-breast-raw', 'quantity': 1.0,
     'unit': 'lb', 'reason': 'over-prepped', 'date': '2026-08-29',
     'pantry_item_name': '', 'is_prior': False},
    # unpriced waste: broccoli has no demo price
    {'name': 'w-broccoli', 'household_name': 'demo-household',
     'food_name': 'broccoli-raw', 'quantity': 1.0, 'unit': 'head',
     'reason': 'spoiled', 'date': '2026-08-28',
     'pantry_item_name': '', 'is_prior': False},
    # unresolvable unit
    {'name': 'w-mystery', 'household_name': 'demo-household',
     'food_name': 'cod-raw', 'quantity': 1.0, 'unit': 'fillet',
     'reason': 'spoiled', 'date': '2026-08-28',
     'pantry_item_name': '', 'is_prior': False},
]

MANAGER = SimpleNamespace(objectTables={
    'WasteRecord': _rows(RECORDS),
    'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS),
    'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
    'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS),
})
TODAY = date(2026, 9, 2)

print('mpb-4: waste ledger')

report = waste_report(MANAGER, 'demo-household', TODAY)
check('report computes over the ledger', report.get('ok')
      and report['records'] == 4)
chicken = [b for b in report['byFood']
           if b['food'] == 'chicken-breast-raw'][0]
check('priced waste valued at best observed $/kg '
      '(453.6 g × 13.21/kg)',
      abs(chicken['estValue'] - 0.453592 * 11.98 / 0.907184)
      < 0.05)
broccoli = [b for b in report['byFood']
            if b['food'] == 'broccoli-raw'][0]
check('unpriced waste counted in grams, never valued at zero-'
      'as-if-free',
      broccoli['priced'] is False and broccoli['grams'] == 608.0
      and report['unpricedG'] >= 608.0
      and 'never valued at zero' in report['honesty'])
check('reasons grouped per food',
      chicken['reasons'].get('over-prepped', 0) > 0)
check('unresolvable unit lands in unresolved, named',
      len(report['unresolved']) == 1
      and 'fillet' in report['unresolved'][0]['why'])
check('observations suggest levers, decisions stay the human\'s',
      report['observations']
      and all('your call' in o for o in report['observations']))
empty = waste_report(MANAGER, 'no-such-household', TODAY)
check('empty ledger says only the log knows',
      empty.get('ok') and 'only the log knows' in empty['note'])

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpb-4 waste ledger holds together')
