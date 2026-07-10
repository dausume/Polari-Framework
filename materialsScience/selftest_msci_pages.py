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
    'fem-model-config',
    'dft-model-config',
    'md-model-config',
    'meso-model-config',
    'materials-home',
    'material-level-page',
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
    check('all twelve msci pages seeded (home + 6 tools + 5 levels)',
          names == ['materials', 'materials-basis', 'fem-models',
                    'dft-models', 'md-models', 'meso-models',
                    'formulation-search',
                    'materials-level-0', 'materials-level-1',
                    'materials-level-2', 'materials-level-3',
                    'materials-level-4'], f'names={names}')
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
    by_name = {p['name']: p for p in SEED_MSCI_PAGE_DISPLAYS}
    wb = json.loads(by_name['formulation-search']['definition'])
    wb_inputs = wb['rows'][0]['items'][0]['componentProps']['inputs']
    check('workbench defaults to the seeded search definition',
          wb_inputs['defaultSearchRef']
          == SEED_FORMULATION_SEARCHES[0]['name'])
    def _default_ref(name):
        page = json.loads(by_name[name]['definition'])
        return (page['rows'][0]['items'][0]['componentProps']
                ['inputs']['defaultModelRef'])
    check('model pages default to the seeded proof models',
          _default_ref('fem-models') == 'wax-thermal-continuum'
          and _default_ref('dft-models') == 'paraffin-quantum-energy')
    from materialsScience.l2_l3_models_seed import (
        SEED_MD_MODELS, SEED_MESO_MODELS,
    )
    check('md/meso pages default to msci-26 seeded models '
          '(validation rung + the assumption-closing study)',
          _default_ref('md-models') == SEED_MD_MODELS[0]['name']
          and _default_ref('meso-models')
          == SEED_MESO_MODELS[0]['name'])
    from materialsScience.materials_basis import SCALE_LEVEL_DETAILS
    check('one level page per SCALE_LEVEL_DETAILS entry, level wired '
          'as the component input',
          all(json.loads(by_name[f'materials-level-{lvl}']['definition'])
              ['rows'][0]['items'][0]['componentProps']['inputs']
              ['level'] == lvl for lvl in SCALE_LEVEL_DETAILS))
    check('level-page descriptions carry the taxonomy (name + range), '
          'generated not hand-copied',
          all(SCALE_LEVEL_DETAILS[lvl]['name']
              in by_name[f'materials-level-{lvl}']['description']
              and SCALE_LEVEL_DETAILS[lvl]['lengthRange']
              in by_name[f'materials-level-{lvl}']['description']
              for lvl in SCALE_LEVEL_DETAILS))

    total, passed = len(_results), sum(_results)
    print(f'\n{passed}/{total} checks passed')
    raise SystemExit(0 if passed == total else 1)
