"""
Selftest — tank-1: tank ecosystem nutrient balance, harvest yield, and
regulation suggestions (freshwater + saltwater).

Run from polari-framework/:
    python3 -m tanks.tank_selftest

Covers: the balanced saltwater food forest self-regulates (net N/P in
band, all required roles present); the fish-heavy system does NOT
(nitrogen accumulates, nutrient-regulator role missing) and its
suggestions name macroalgae to add; harvest yield supplies the
iodine/sodium/chloride the hydroponic garden can't (gap closed) + scales
with days; the freshwater system balances via duckweed vs tilapia;
honest refusals.
"""

from types import SimpleNamespace

from tanks.custom.tank_analysis import (
    harvest_yield, nutrient_balance, regulate_suggestions,
)
from tanks.tank_seed import (
    SEED_AQUACULTURE_SPECIES, SEED_TANK_SUBSTRATES, SEED_TANK_SYSTEMS,
    SEED_TANKS,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'AquacultureSpecies': _rows(SEED_AQUACULTURE_SPECIES),
        'TankDefinition': _rows(SEED_TANKS),
        'TankSubstrateDefinition': _rows(SEED_TANK_SUBSTRATES),
        'TankSystemDefinition': _rows(SEED_TANK_SYSTEMS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('balanced saltwater food forest')
    bal = nutrient_balance(manager, 'saltwater-food-forest')
    check('balance ok', bal['ok'])
    check('net nitrogen within the balance band',
          bal['nitrogenBalanced'],
          extra=f"net N {bal['netNitrogenMgPerDay']} band "
                f"{bal['balanceBandMg']}")
    check('all required roles present',
          not bal['missingRoles'],
          extra=str(bal['rolesPresent']))
    check('system reports self-regulating', bal['selfRegulating'])
    check('detritus removal positive (self-cleaning crew)',
          bal['detritusRemovedMgPerDay'] > 0)

    print('shrimp for cleaning + extra macroalgae included')
    species_names = {s['name'] for s in SEED_AQUACULTURE_SPECIES}
    check('cleaner shrimp present (salt + fresh)',
          {'skunk-cleaner-shrimp', 'pacific-white-shrimp',
           'amano-shrimp', 'cherry-shrimp'} <= species_names)
    check('extra macroalgae present (chaetomorpha + hornwort)',
          {'chaetomorpha', 'hornwort'} <= species_names)
    check('cleaner role stocked in the balanced system',
          'cleaner' in bal['rolesPresent'])

    print('NEW substrate ("soil") category')
    check('substrate contributes anaerobic denitrification',
          bal['substrateDenitrificationMgNPerDay'] > 0)
    check('substrate buffering reported (aragonite/live rock)',
          bal['substrateBuffering'] is True)
    check('per-bed substrate breakdown present',
          len(bal['substrateBeds']) == 2
          and all(b['denitrificationMgNPerDay'] > 0
                  for b in bal['substrateBeds']))
    salt_subs = [s for s in SEED_TANK_SUBSTRATES
                 if s['water_type'] == 'salt']
    fresh_subs = [s for s in SEED_TANK_SUBSTRATES
                  if s['water_type'] == 'fresh']
    check('substrate category has both salt + fresh soils',
          len(salt_subs) >= 2 and len(fresh_subs) >= 2)
    # Denitrification should push net N more negative than species alone.
    bare = SimpleNamespace(objectTables={
        'AquacultureSpecies': _rows(SEED_AQUACULTURE_SPECIES),
        'TankDefinition': _rows([
            dict(t, substrate_name='', substrate_volume_l=0.0)
            for t in SEED_TANKS]),
        'TankSubstrateDefinition': _rows(SEED_TANK_SUBSTRATES),
        'TankSystemDefinition': _rows(SEED_TANK_SYSTEMS)})
    bare_bal = nutrient_balance(bare, 'saltwater-food-forest')
    check('removing the substrate raises net nitrogen (denitrification '
          'was helping)',
          bare_bal['netNitrogenMgPerDay']
          > bal['netNitrogenMgPerDay']
          and bare_bal['substrateDenitrificationMgNPerDay'] == 0)

    print('fish-heavy imbalanced system')
    fh = nutrient_balance(manager, 'saltwater-fish-heavy')
    check('nitrogen accumulates (not balanced)',
          not fh['nitrogenBalanced']
          and fh['netNitrogenMgPerDay'] > 0)
    check('nutrient-regulator role missing',
          'nutrient-regulator' in fh['missingRoles'])
    check('not self-regulating + limiting factor named',
          not fh['selfRegulating'] and fh['limitingFactor'])
    sug = regulate_suggestions(manager, 'saltwater-fish-heavy')
    check('suggestions name macroalgae to add',
          any('sea-lettuce' in s.get('addOneOf', [])
              for s in sug['suggestions']))

    print('harvest yield — the alternate nutrient source')
    y = harvest_yield(manager, 'saltwater-food-forest', days=30.0)
    check('yield ok + biomass positive',
          y['ok'] and y['totalEdibleBiomassG'] > 0)
    check('supplies iodine + sodium + chloride (the hydroponic gap)',
          {'iodine', 'sodium', 'chloride'}
          <= set(y['nutrientsSupplied']))
    check('gapNutrientsCovered lists the three',
          set(y['gapNutrientsCovered'])
          == {'iodine', 'sodium', 'chloride'})
    check('supplies protein from fish + shellfish',
          y['nutrientsSupplied'].get('protein', 0) > 0)
    y90 = harvest_yield(manager, 'saltwater-food-forest', days=90.0)
    check('3× the days -> ~3× the iodine yield',
          abs(y90['nutrientsSupplied']['iodine']
              / y['nutrientsSupplied']['iodine'] - 3.0) < 0.01)

    print('freshwater system')
    fw = nutrient_balance(manager, 'freshwater-basic')
    check('freshwater balance computed (duckweed vs tilapia)',
          fw['ok'] and 'nutrient-regulator' in fw['rolesPresent'])
    fwy = harvest_yield(manager, 'freshwater-basic', days=30.0)
    check('freshwater yields protein (tilapia/duckweed)',
          fwy['nutrientsSupplied'].get('protein', 0) > 0)

    print('honest refusals')
    check('unknown system refuses',
          not nutrient_balance(manager, 'nope').get('ok'))
    empty = SimpleNamespace(objectTables={
        'AquacultureSpecies': _rows(SEED_AQUACULTURE_SPECIES),
        'TankSystemDefinition': _rows([{
            'name': 'empty', 'species_stock_json': '{}'}])})
    check('system with no stock refuses',
          not nutrient_balance(empty, 'empty').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
