"""
@module nutrition.selftest_quickadd

mpb-9 selftest — quick-add parsing: the three line kinds parse to
typed PROPOSALS (never writes), ambiguity refuses listing
candidates, unknown units/locations refuse by name, and a line
that tries to be both a price and a pantry lot refuses.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_quickadd
"""

from types import SimpleNamespace

from nutrition.fdc_seed import SEED_FDC_FOOD_ITEMS
from nutrition.market_basis import SEED_SOURCE_LOCATIONS
from nutrition.meal_basis import SEED_MEAL_TEMPLATES
from nutrition.quick_add import parse_quick_add

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


MANAGER = SimpleNamespace(objectTables={
    'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
    'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
    'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
})

print('mpb-9: quick-add parsing')

p = parse_quick_add(MANAGER,
                    '2 lb chicken breast 11.98 @ demo-grocery')
check('price line parses to a PriceObservation proposal',
      p.get('ok') and p['kind'] == 'price'
      and p['proposal']['food_name'] == 'chicken-breast-raw'
      and p['proposal']['price'] == 11.98
      and p['proposal']['location_name'] == 'demo-grocery')
check('proposals are applied by the human',
      'you' in p['appliedBy'])

p = parse_quick_add(MANAGER, '3 each banana fridge')
check('pantry line parses with storage',
      p.get('ok') and p['kind'] == 'pantry'
      and p['proposal']['food_name'] == 'banana-raw'
      and p['proposal']['storage_state'] == 'fridge')

p = parse_quick_add(MANAGER, '500 g spinach')
check('bare line defaults to pantry storage',
      p.get('ok') and p['kind'] == 'pantry'
      and p['proposal']['storage_state'] == 'pantry')

p = parse_quick_add(MANAGER,
                    'ate chicken bowl dinner on 2026-09-02')
check('intake line resolves the template + slot + date',
      p.get('ok') and p['kind'] == 'intake'
      and p['proposal']['template_name'] == 'chicken-bowl-dinner'
      and p['proposal']['slot'] == 'dinner'
      and p['proposal']['date'] == '2026-09-02')

check('ambiguous food refuses LISTING candidates ("rice" is '
      'brown or white)',
      not parse_quick_add(MANAGER, '1 kg rice').get('ok')
      and 'ambiguous' in parse_quick_add(MANAGER,
                                         '1 kg rice')['error'])
check('unknown unit refuses by name',
      'unknown unit' in parse_quick_add(
          MANAGER, '2 fistfuls spinach')['error'])
check('unknown location refuses (add the row first)',
      'unknown location' in parse_quick_add(
          MANAGER, '1 kg sugar 2.99 @ moon-mart')['error'])
check('price+storage on one line refuses (pick one)',
      not parse_quick_add(MANAGER,
                          '1 kg sugar 2.99 fridge').get('ok'))
check('unknown food refuses without guessing',
      'no food matches' in parse_quick_add(
          MANAGER, '1 kg dragonfruit')['error'])
check('empty line refuses',
      not parse_quick_add(MANAGER, ' ').get('ok'))

print(f'\n{"ALL PASS" if not failures else "FAILURES: " + str(failures)}'
      f' — {len(failures)} failed')
if failures:
    raise SystemExit(1)
print('PASS: mpb-9 quick-add holds together')
