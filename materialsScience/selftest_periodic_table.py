"""
Selftest: the periodic-table dataset + selection-space seeds. No server.

Run from polari-framework/:
    python3 -m materialsScience.selftest_periodic_table
"""

import json

from materialsScience.periodic_table_data import (
    CATEGORY_BY_CODE, ELEMENTS, common_ions_for,
)
from materialsScience.periodic_table_seed import (
    PERIODIC_SCENE,
    PERIODIC_SELECTOR_ITEMS,
    SEED_CHEMICAL_ELEMENTS,
    SEED_ELEMENT_CATEGORY_MATERIALS,
    SEED_PERIODIC_DISPLAYS,
    SEED_PERIODIC_SIMSPACES,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
results = []


def check(label, cond, extra=''):
    results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def main():
    print('Periodic table — dataset\n')
    check('118 elements, atomic numbers 1..118 exactly once',
          sorted(e[0] for e in ELEMENTS) == list(range(1, 119)))
    symbols = [e[1] for e in ELEMENTS]
    check('symbols unique', len(set(symbols)) == 118)
    check('groups within 1-18 and periods within 1-7',
          all(1 <= e[3] <= 18 and 1 <= e[4] <= 7 for e in ELEMENTS))
    check('every category code resolves',
          all(e[5] in CATEGORY_BY_CODE for e in ELEMENTS))
    check('spot checks: Fe ions, Na ion, Nd lanthanide default, He none',
          common_ions_for('Fe', 'tm') == ['Fe2+', 'Fe3+']
          and common_ions_for('Na', 'ak') == ['Na+']
          and common_ions_for('Nd', 'la') == ['Nd3+']
          and common_ions_for('He', 'ng') == [])

    print('\nPeriodic table — seeds\n')
    check('one ChemicalElementDefinition row per element (symbol-named)',
          len(SEED_CHEMICAL_ELEMENTS) == 118
          and {r['name'] for r in SEED_CHEMICAL_ELEMENTS} == set(symbols))
    positions = {(r['display_row'], r['display_col'])
                 for r in SEED_CHEMICAL_ELEMENTS}
    check('display positions are unique (no overlapping tiles)',
          len(positions) == 118)
    check('ions JSON parses on every row',
          all(isinstance(json.loads(r['common_ions_json']), list)
              for r in SEED_CHEMICAL_ELEMENTS))
    check('a category material exists per category',
          {m['name'] for m in SEED_ELEMENT_CATEGORY_MATERIALS}
          == {f'element-{c}' for c in CATEGORY_BY_CODE.values()})

    scene = SEED_PERIODIC_SIMSPACES[0]
    blob = json.loads(scene['definition'])
    camera = json.loads(scene['camera_json'])
    tiles = {e['id'] for e in blob['freestanding']}
    check('scene: 118 tiles, freestandingOnly, fixed auto-fit camera',
          scene['name'] == PERIODIC_SCENE and len(tiles) == 118
          and blob['freestandingOnly'] and camera['mode'] == 'fixed'
          and camera.get('fit') != 'off')
    check('scene has a phone screen profile',
          any(p.get('maxWidth') for p in blob.get('screenProfiles', [])))
    check('tile styles are category materials',
          {e['styleRef'] for e in blob['freestanding']}
          <= {m['name'] for m in SEED_ELEMENT_CATEGORY_MATERIALS})

    check('selector items map 1:1 onto scene tiles',
          {i['objectId'] for i in PERIODIC_SELECTOR_ITEMS} == tiles)
    fe_item = next(i for i in PERIODIC_SELECTOR_ITEMS if i['key'] == 'Fe')
    check('items carry ion variants + element overlay inputs',
          fe_item['variants'] == ['Fe2+', 'Fe3+']
          and fe_item['overlayInputs']['atomicNumber'] == 26
          and fe_item['overlayRef'] == 'element-choice')

    page = SEED_PERIODIC_DISPLAYS[0]
    page_def = json.loads(page['definition'])
    item = page_def['rows'][0]['items'][0]
    check('demo Display page hosts the selector as pure config',
          page['isPage'] and page['pageRoute'] == 'periodic-table'
          and item['componentProps']['componentName'] == 'sim-space-selector'
          and len(item['componentProps']['inputs']['items']) == 118)
    check('demo page declares its supported-screen disclaimer knob',
          item['componentProps']['inputs']['supportedScreen']['minWidth'] > 0)

    total, passed = len(results), sum(results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    raise SystemExit(main())
