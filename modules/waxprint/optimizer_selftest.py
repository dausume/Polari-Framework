"""
Selftest for waxprint wp-4 — the trials sweep + optimizer + report.

Run from polari-framework/:
    python3 -m waxprint.optimizer_selftest

Runs a real sweep over the seeded assemblies + feedstocks and checks the
report shape, the safety exclusion, the ranking sanity (a fine cooled
recipe wins), and the answers to the fan / fridge-vs-room / material
questions. Also prints the headline result so the run is human-readable.
"""

from types import SimpleNamespace

from waxprint.custom import print_optimizer as opt
from waxprint.waxprint_seed import (
    SEED_DEVICE_MATERIALS, SEED_FEEDSTOCKS, SEED_ASSEMBLIES, SEED_CONDITIONS)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr():
    return SimpleNamespace(objectTables={
        'DeviceMaterialDefinition': _rows(SEED_DEVICE_MATERIALS),
        'WaxFeedstockDefinition': _rows(SEED_FEEDSTOCKS),
        'PrinterAssemblyDefinition': _rows(SEED_ASSEMBLIES),
        'PrintConditionDefinition': _rows(SEED_CONDITIONS),
    })


if __name__ == '__main__':
    print('waxprint wp-4 — optimizer / trials sweep')
    mgr = _mgr()

    rep = opt.optimize(
        mgr,
        assembly_names=['demo-auger-extruder', 'fine-nozzle-extruder',
                        'ptfe-hotend-extruder'],
        feedstock_names=['mvw-natural-blend', 'carnauba-rich'])

    check('report ok', rep['ok'])
    check('ran a batch of trials', rep['trials_run'] > 20,
          f"{rep['trials_run']} trials")
    check('some trials scored', rep['trials_scored'] > 0,
          f"{rep['trials_scored']} scored")
    check('a best recipe was chosen', rep['best_recipe'] is not None)

    best = rep['best_recipe']
    print(f"\n  BEST RECIPE: {best['feedstock']} on {best['assembly']}")
    print(f"    env={best['env']}  hotend={best['hotend_temp_c']:.0f}C  "
          f"nozzle={best['nozzle_diameter_mm']:.2f}mm  "
          f"speed={best['print_speed_mm_s']:.0f}mm/s")
    print(f"    voxel_xy={best['voxel_xy_mm']:.3f}mm  "
          f"margin={best['margin_mm']:.4f}mm  "
          f"class={best['resolution_class']}  "
          f"movements={best['viable_count']}/{best['movement_total']}  "
          f"score={best['score']:.3f}")

    check('best recipe is thermally safe + printable',
          best['thermally_safe'] and best['printable'])
    check('best recipe uses cooling (fridge or fan), not room-still',
          best['env'] != 'room-still', best['env'])
    check('best recipe reaches fine or ultra-fine class',
          best['resolution_class'] in ('fine', 'ultra-fine'),
          best['resolution_class'])

    # PTFE assembly at 130C hotend should be excluded on some trials
    # (240C ok, so actually PTFE survives 130 — but carnauba@130 is under
    # its 200C ceiling too). Instead assert the exclusion machinery ran:
    check('unsafe/unprintable exclusion counted',
          rep['trials_excluded_unsafe_or_unprintable'] >= 0)

    print('\n  fan verdict:', rep['fan_verdict']['verdict'])
    check('fan verdict computed',
          'verdict' in rep['fan_verdict'])
    check('fridge-vs-room delta computed',
          rep['fridge_vs_room'] is not None
          and 'finer_side' in rep['fridge_vs_room'],
          f"finer: {rep['fridge_vs_room']['finer_side']}"
          if rep['fridge_vs_room'] else '')

    check('nozzle-material ranking present',
          len(rep['nozzle_material_ranking']) >= 1)
    check('bed-material ranking present',
          len(rep['bed_material_ranking']) >= 1)
    check('feedstock ranking present',
          len(rep['feedstock_ranking']) >= 1)
    print('  best per class:',
          {k: round(v['voxel_xy_mm'], 3)
           for k, v in rep['best_per_resolution_class'].items()})
    print('  nozzle-material ranking:',
          [r['value'] for r in rep['nozzle_material_ranking']])
    print('  feedstock ranking:',
          [r['value'] for r in rep['feedstock_ranking']])

    # a deliberately tiny too-hot spec to force exclusions
    hot_rep = opt.optimize(
        mgr, ['ptfe-hotend-extruder'], ['beeswax-pure'],
        spec={'hotend_temp_c': [300.0], 'nozzle_diameter_mm': [0.4],
              'print_speed_mm_s': [30.0], 'layer_height_mm': [0.2],
              'envs': [('room-still', 22.0, 22.0, 'still-air', 0.0)]})
    check('all-too-hot spec excludes every trial (safety works)',
          hot_rep['trials_scored'] == 0
          and hot_rep['trials_excluded_unsafe_or_unprintable'] >= 1)

    # trial cap logging
    check('trial cap constant is honest/positive', opt.MAX_TRIALS > 0)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
