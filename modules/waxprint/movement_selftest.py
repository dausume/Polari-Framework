"""
Selftest for waxprint wp-3 — movement-pattern viability.

Run from polari-framework/:
    python3 -m waxprint.movement_selftest

Checks each pattern's criterion direction (a good bead passes; a bad bead
fails on the expected limiting factor), the overall worst-wins roll-up,
and the end-to-end run via a mock manager including at-height evaluation.
"""

from types import SimpleNamespace

from waxprint.custom import movement_patterns as mp
from waxprint.custom import movement_analysis
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


# A "good" bead: tight, fast-freezing, viscous. A "bad" bead: wide,
# slow-freezing, thin melt.
GOOD = {'voxel_xy_mm': 0.30, 'voxel_z_mm': 0.15, 'spread_mm': 0.03,
        't_solidify_s': 0.4, 'froze_in_window': True, 'warp_index': 0.0}
BAD = {'voxel_xy_mm': 1.10, 'voxel_z_mm': 0.30, 'spread_mm': 0.70,
       't_solidify_s': 6.0, 'froze_in_window': False, 'warp_index': 0.5}
COND = {'nozzle_d_mm': 0.4, 'print_speed_mm_s': 30.0, 'layer_height_mm': 0.2}
FEED_GOOD = {'exit_viscosity_pa_s': 1.0, 'density': 965.0}
FEED_THIN = {'exit_viscosity_pa_s': 0.05, 'density': 960.0}


if __name__ == '__main__':
    print('waxprint wp-3 — movement patterns')

    print('\nper-pattern criterion direction')
    check('perimeter: tight bead viable',
          mp.perimeter(GOOD, COND)['verdict'] == 'viable')
    check('perimeter: over-spread bead fails on spread',
          mp.perimeter(BAD, COND)['verdict'] == 'fail'
          and 'spread' in mp.perimeter(BAD, COND)['limiting_factor'])
    check('travel-retract: viscous wax viable',
          mp.travel_retract(GOOD, FEED_GOOD)['verdict'] == 'viable')
    check('travel-retract: thin wax strings (fail)',
          mp.travel_retract(BAD, FEED_THIN)['verdict'] == 'fail')
    check('sharp-corner: fast freeze viable',
          mp.sharp_corner(GOOD)['verdict'] == 'viable')
    check('sharp-corner: slow freeze blobs (fail)',
          mp.sharp_corner(BAD)['verdict'] == 'fail')
    check('bridge: fast+viscous bead viable',
          mp.bridge(GOOD, FEED_GOOD)['verdict'] == 'viable')
    check('bridge: slow+thin bead sags (fail/marginal)',
          mp.bridge(BAD, FEED_THIN)['verdict'] in ('fail', 'marginal'))
    check('small-circle reports a min radius = 1.5x voxel',
          abs(mp.small_circle(GOOD)['min_radius_mm']
              - 1.5 * GOOD['voxel_xy_mm']) < 1e-9)
    check('z-hop: fast freeze viable',
          mp.layer_z_hop(GOOD, COND)['verdict'] == 'viable')
    check('infill: unfrozen bead fails',
          mp.infill_raster(BAD, COND)['verdict'] == 'fail')

    print('\noverall roll-up (worst wins)')
    good_all = mp.evaluate_patterns(GOOD, COND, FEED_GOOD)
    bad_all = mp.evaluate_patterns(BAD, COND, FEED_THIN)
    check('good bead: overall viable, all patterns viable',
          good_all['overall'] == 'viable'
          and good_all['viable_count'] == good_all['total'],
          f"{good_all['viable_count']}/{good_all['total']}")
    check('bad bead: overall fail', bad_all['overall'] == 'fail')

    print('\nend-to-end via mock manager')
    mgr = _mgr()
    # fine-voxel recipe on the fine nozzle → should print well
    out = movement_analysis.run_movements(
        mgr, 'fine-nozzle-extruder', 'carnauba-rich', 'fine-voxel')
    check('run_movements ok', out['ok'])
    check('fine recipe: most patterns viable',
          out['movements']['viable_count'] >= 5,
          f"{out['movements']['viable_count']}/{out['movements']['total']}")

    # room-baseline on the demo (slow-freezing, wide) → weaker
    room = movement_analysis.run_movements(
        mgr, 'demo-auger-extruder', 'mvw-natural-blend', 'room-baseline')
    check('room baseline scores worse than the fine recipe',
          room['movements']['viable_count'] <= out['movements']['viable_count'],
          f"room {room['movements']['viable_count']} vs "
          f"fine {out['movements']['viable_count']}")

    # at-height: same condition high up should be no better than low
    low = movement_analysis.run_movements(
        mgr, 'fine-nozzle-extruder', 'carnauba-rich', 'fine-voxel',
        height_mm=0.2)
    high = movement_analysis.run_movements(
        mgr, 'fine-nozzle-extruder', 'carnauba-rich', 'fine-voxel',
        height_mm=30.0)
    check('voxel at height >= voxel low (resolution degrades up high)',
          high['voxel']['voxel_xy_mm'] >= low['voxel']['voxel_xy_mm'] - 1e-9,
          f"{low['voxel']['voxel_xy_mm']:.3f} -> "
          f"{high['voxel']['voxel_xy_mm']:.3f} mm")

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
