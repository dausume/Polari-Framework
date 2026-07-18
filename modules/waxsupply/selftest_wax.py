"""
Selftest — wax-1: bio wax source catalog, hydroponic filter, use ranking,
yield.

Run from polari-framework/:
    python3 -m waxsupply.selftest_wax

Covers: catalog resolves material links; the hydroponic filter drops the
not-easily-grown palm (carnauba is 'hard') and keeps shrub/byproduct
sources; mold/mask ranking puts a hard high-melt wax (carnauba/candelilla/
rice-bran) on top and a soft low-melt one (soy/bayberry) below; yield
scales with units + years; honest refusals.
"""

from types import SimpleNamespace

from waxsupply.wax_analysis import (
    hydroponic_wax_sources, wax_catalog, wax_for_use, wax_yield,
)
from waxsupply.wax_seed import SEED_WAX_SOURCES

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


WAX_MATERIALS = [{'name': n} for n in
                 ('carnauba-wax', 'candelilla-wax', 'beeswax',
                  'coconut-wax', 'soy-wax')]


def _mgr():
    return SimpleNamespace(objectTables={
        'WaxSourceDefinition': _rows(SEED_WAX_SOURCES),
        'MaterialsScienceMaterial': _rows(WAX_MATERIALS)})


if __name__ == '__main__':
    manager = _mgr()

    print('catalog + material links')
    cat = wax_catalog(manager)
    check('catalog lists all sources', cat['count'] == len(SEED_WAX_SOURCES))
    check('every source resolves its wax material',
          all(c['materialResolved'] for c in cat['sources']))
    check('spans plants, byproducts, insect, macroalgae',
          {c['sourceType'] for c in cat['sources']}
          >= {'plant-leaf', 'crop-byproduct', 'insect', 'macroalgae'})

    print('hydroponic filter')
    hydro = hydroponic_wax_sources(manager)
    hydro_names = {c['name'] for c in hydro['hydroponicSources']}
    check('drops carnauba (palm = hard to grow hydroponically)',
          'carnauba' not in hydro_names)
    check('keeps candelilla shrub + rice-bran byproduct',
          {'candelilla', 'rice-bran-wax'} <= hydro_names)

    print('mold / electronic-mask ranking (hard + high-melt first)')
    molds = wax_for_use(manager, 'mold')
    top = molds['ranked'][0]
    check('a hard high-melt wax tops the mold ranking',
          top['name'] in ('carnauba', 'candelilla', 'rice-bran-wax')
          and top['suitability'] > 0.8)
    check('soy/bayberry (soft) rank below the hard waxes',
          all(molds['ranked'][0]['suitability']
              > c['suitability'] for c in molds['ranked']
              if c['name'] in ('soy-wax', 'bayberry')))
    masks = wax_for_use(manager, 'electronic-mask')
    check('electronic-mask use has ranked sources + a recommendation',
          masks['ok'] and masks['recommended']
          and masks['ranked'][0]['suitability'] > 0.7)

    print('yield')
    y = wax_yield(manager, 'candelilla', units=10.0, years=3.0)
    # 30 g/plant/yr × 10 plants × 3 yr = 900 g
    check('yield scales with units + years',
          abs(y['totalWaxGrams'] - 900.0) < 0.1)
    check('per-year subtotal reported',
          abs(y['waxGramsPerYear'] - 300.0) < 0.1)

    print('honest refusals')
    check('unknown source refuses',
          not wax_yield(manager, 'nope').get('ok'))
    check('unserved use refuses',
          not wax_for_use(manager, 'not-a-use').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
