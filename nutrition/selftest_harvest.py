"""
Selftest — nut-2: plant harvest -> meal-nutrient yield.

Run from polari-framework/:
    python3 -m nutrition.selftest_harvest

Covers: harvest mass from the aqp-4 basil part at mature volume; mass
scales with a smaller REALIZED aqp-8 grow volume (volumeSource labeled);
nutrient yield scales with mass; basil reports its headline vitamin-k/
vitamin-a/calcium; missing content and missing edible parts refuse
honestly; the catalog ranks each food's top nutrients.
"""

from types import SimpleNamespace

from nutrition.food_seed import SEED_FOOD_ITEMS, SEED_NUTRIENT_CONTENTS
from nutrition.harvest_analysis import (
    food_catalog, harvest_mass_g, harvest_nutrients,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


# The aqp-4 basil leaf part (mature 120 cm3, density 0.25, dmf 0.11) —
# the SAME plant that grows in the self-watering pot.
BASIL_PARTS = [
    {'name': 'sweet-basil-leaf', 'plant_name': 'sweet-basil',
     'part': 'leaf', 'mature_volume_cm3': 120.0,
     'dry_density_g_cm3': 0.25, 'dry_matter_fraction': 0.11},
    # a minimal kale part so the catalog + kale mass work in-test
    {'name': 'kale-leaf', 'plant_name': 'kale', 'part': 'leaf',
     'mature_volume_cm3': 200.0, 'dry_density_g_cm3': 0.2,
     'dry_matter_fraction': 0.10},
]


def _mgr():
    return SimpleNamespace(objectTables={
        'FoodItem': _rows(SEED_FOOD_ITEMS),
        'NutrientContent': _rows(SEED_NUTRIENT_CONTENTS),
        'PlantPart': _rows(BASIL_PARTS),
    })


if __name__ == '__main__':
    manager = _mgr()

    print('harvest mass (mature volume)')
    mass = harvest_mass_g(manager, 'basil-leaf')
    # 120 * 0.25 = 30 g dry; /0.11 = 272.7 g fresh.
    check('basil mature harvest mass ~ 272.7 g fresh',
          mass['ok'] and abs(mass['freshMassG'] - 272.73) < 1.0,
          extra=str(mass['freshMassG']))
    check('volume source labeled mature',
          'mature' in mass['volumeSource'])

    print('harvest mass (realized aqp-8 grow)')
    grow_result = {'perPart': [
        {'part': 'sweet-basil-leaf', 'finalVolumeCm3': 60.0}]}
    realized = harvest_mass_g(manager, 'basil-leaf',
                              grow_result=grow_result)
    check('smaller realized volume -> smaller mass',
          realized['freshMassG'] < mass['freshMassG']
          and abs(realized['freshMassG'] - mass['freshMassG'] / 2)
          < 1.0)
    check('volume source labeled realized',
          'realized' in realized['volumeSource'])

    print('harvest nutrients')
    nut = harvest_nutrients(manager, 'basil-leaf')
    check('nutrient yield ok + carries priors',
          nut['ok'] and nut['flaggedPriors'])
    # vitamin-k 414.8 ug/100g × 272.73 g / 100 = 1131 ug
    check('vitamin-k yield scales with mass (~1131 ug)',
          abs(nut['nutrients']['vitamin-k']['amount'] - 1131.0) < 5.0,
          extra=str(nut['nutrients']['vitamin-k']['amount']))
    check('reports basil headline nutrients',
          {'vitamin-k', 'vitamin-a', 'calcium'}
          <= set(nut['nutrients']))
    half = harvest_nutrients(manager, 'basil-leaf',
                             grow_result=grow_result)
    check('half the mass -> half the nutrient yield',
          abs(half['nutrients']['vitamin-k']['amount']
              - nut['nutrients']['vitamin-k']['amount'] / 2) < 5.0)

    print('honest refusals')
    check('unknown food refuses',
          not harvest_nutrients(manager, 'nope').get('ok'))
    no_content = SimpleNamespace(objectTables={
        'FoodItem': _rows([{'name': 'mystery', 'plant_name': 'x',
                            'edible_parts_json': '["kale-leaf"]'}]),
        'NutrientContent': {}, 'PlantPart': _rows(BASIL_PARTS)})
    check('food without NutrientContent refuses with the knob',
          not harvest_nutrients(no_content, 'mystery').get('ok'))
    no_parts = SimpleNamespace(objectTables={
        'FoodItem': _rows([{'name': 'empty', 'plant_name': 'x',
                            'edible_parts_json': '[]'}]),
        'NutrientContent': {}, 'PlantPart': {}})
    check('food with no edible parts refuses',
          not harvest_mass_g(no_parts, 'empty').get('ok'))

    print('catalog')
    catalog = food_catalog(manager)
    check('catalog lists both foods with top nutrients',
          catalog['count'] == 2
          and all(f['topNutrients'] for f in catalog['foods']))
    basil_cat = next(f for f in catalog['foods']
                     if f['name'] == 'basil-leaf')
    check('top nutrient ranked by per-100g (vitamin-k highest)',
          basil_cat['topNutrients'][0]['nutrient'] == 'vitamin-k')

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
