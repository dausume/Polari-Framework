"""
Selftest — the materials-science DisplayDefinition pages.

Run from polari-framework/:
    python3 -m materialsScience.selftest_msci_pages

Covers: both page seeds parse; componentNames match the names the
frontend registers (string-level contract, same idea as the periodic
selftest); routes are unique across ALL seeded pages; the workbench
seed points at the seeded search definition.
"""

import json

from materialsScience.msci_pages_seed import SEED_MSCI_PAGE_DISPLAYS
from materialsScience.periodic_table_seed import SEED_PERIODIC_DISPLAYS
from materialsScience.formulation_search_seed import (
    SEED_FORMULATION_SEARCHES,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []

# The names msci-display-components.ts registers (string contract).
REGISTERED_COMPONENTS = {
    'materials-basis-browser',
    'formulation-search-workbench',
}


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
    print('\nMaterials-science pages\n')
    names = [p['name'] for p in SEED_MSCI_PAGE_DISPLAYS]
    check('both pages seeded',
          names == ['materials-basis', 'formulation-search'])
    for page in SEED_MSCI_PAGE_DISPLAYS:
        json.loads(page['definition'])
    check('page definitions parse', True)
    check('pages are pages with routes',
          all(p['isPage'] and p['pageRoute']
              for p in SEED_MSCI_PAGE_DISPLAYS))
    all_pages = SEED_PERIODIC_DISPLAYS + SEED_MSCI_PAGE_DISPLAYS
    routes = [p['pageRoute'] for p in all_pages if p.get('isPage')]
    check('page routes unique across all seeded pages',
          len(routes) == len(set(routes)), f'routes={routes}')
    hosted = {n for p in SEED_MSCI_PAGE_DISPLAYS
              for n in _component_names(p)}
    check('hosted componentNames match the registered set',
          hosted == REGISTERED_COMPONENTS, f'hosted={sorted(hosted)}')
    wb = json.loads(SEED_MSCI_PAGE_DISPLAYS[1]['definition'])
    wb_inputs = wb['rows'][0]['items'][0]['componentProps']['inputs']
    check('workbench defaults to the seeded search definition',
          wb_inputs['defaultSearchRef']
          == SEED_FORMULATION_SEARCHES[0]['name'])

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
