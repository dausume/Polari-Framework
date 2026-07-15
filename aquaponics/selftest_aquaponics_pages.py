"""
Selftest — the aquaponics-pot-shape phase 2 DisplayDefinition page.

Run from polari-framework/:
    python3 -m aquaponics.selftest_aquaponics_pages

Covers: the page seed parses; the hosted componentName matches the
name the frontend registers (string-level contract, same idea as the
msci pages selftest); the page defaults to a REAL seeded pot.
"""

import json

from aquaponics.aquaponics_pages_seed import SEED_AQUAPONICS_PAGE_DISPLAYS
from aquaponics.pot_seed import SEED_POTS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []

# The names aquaponics-display-components.ts registers (string
# contract). sim-space-viewer (2026-07-14): the editor alone renders
# nothing — this bare viewer is what actually shows the re-derived
# scene next to it.
REGISTERED_COMPONENTS = {'pot-geometry-editor', 'sim-space-viewer'}


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _component_names(page):
    defn = json.loads(page['definition'])
    return [item['componentProps']['componentName']
            for row in defn['rows'] for item in row['items']
            if item.get('type') == 'component']


if __name__ == '__main__':
    print('\nAquaponics pages\n')
    names = [p['name'] for p in SEED_AQUAPONICS_PAGE_DISPLAYS]
    check('pot-geometry page seeded', names == ['pot-geometry'],
          f'names={names}')
    for page in SEED_AQUAPONICS_PAGE_DISPLAYS:
        json.loads(page['definition'])
    check('page definition parses', True)
    check('page is a page with a route',
          all(p['isPage'] and p['pageRoute']
              for p in SEED_AQUAPONICS_PAGE_DISPLAYS))
    hosted = {n for p in SEED_AQUAPONICS_PAGE_DISPLAYS
              for n in _component_names(p)}
    check('hosted componentNames match the registered set',
          hosted == REGISTERED_COMPONENTS, f'hosted={sorted(hosted)}')
    by_name = {p['name']: p for p in SEED_AQUAPONICS_PAGE_DISPLAYS}
    defn = json.loads(by_name['pot-geometry']['definition'])
    default_pot = (defn['rows'][0]['items'][0]['componentProps']
                   ['inputs']['potName'])
    seeded_pot_names = {p['name'] for p in SEED_POTS}
    check('page defaults to a REAL seeded pot, not a made-up name',
          default_pot in seeded_pot_names, f'default_pot={default_pot}')

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
