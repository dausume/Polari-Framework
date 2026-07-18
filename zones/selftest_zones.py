"""Selftest for zones — capture rows, geometry (prism + hull +
calibration), and cube packing.

Run: python3 -m zones.selftest_zones
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

PASS = '\033[92m[PASS]\033[0m'
FAIL = '\033[91m[FAIL]\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'{PASS if cond else FAIL} {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr():
    return types.SimpleNamespace(objectTables={}, idList=[], db=None)


def _add_zone(m, name, mode='prism', scale=1.0, site='',
              role='selection', room=''):
    from zones.zone_basis import ZoneDefinition
    ZoneDefinition(name=name, capture_mode=mode,
                   scale_correction=scale, site_name=site,
                   room_label=name, zone_role=role,
                   room_zone_name=room, manager=m)


def _add_points(m, zone, triples, kind='ground', start=0):
    from zones.zone_basis import ZonePoint
    for i, (x, y, z) in enumerate(triples):
        ZonePoint(name=f'{zone}-{kind}-{start + i}', zone_name=zone,
                  index=start + i, kind=kind, x=x, y=y, z=z,
                  manager=m)


def phase_prism(m):
    from zones.zone_geometry import (estimate_prism, estimate_zone,
                                     point_distances)
    _add_zone(m, 'square')
    _add_points(m, 'square',
                [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)])
    r = estimate_prism(m, 'square')
    check('unit square area 1, footprint-only without height',
          r['ok'] and abs(r['groundAreaM2'] - 1.0) < 1e-9
          and r['model'] == 'footprint-only' and r['warnings'])
    r = estimate_prism(m, 'square', default_height_m=0.5)
    check('assumed-height volume flagged as assumption',
          r['ok'] and abs(r['volumeM3'] - 0.5) < 1e-9
          and 'ASSUMED' in r['heightSource'])
    _add_points(m, 'square', [(0.5, 2.0, 0.5)], kind='height',
                start=10)
    r = estimate_prism(m, 'square')
    check('height point gives prism volume 2.0',
          r['ok'] and r['model'] == 'prism'
          and abs(r['volumeM3'] - 2.0) < 1e-9)
    r = point_distances(m, 'square')
    check('perimeter legs 3 × 1 m (open walk)',
          r['ok'] and len(r['legs']) == 3
          and abs(r['perimeterM'] - 3.0) < 1e-9)

    _add_zone(m, 'triangle')
    _add_points(m, 'triangle', [(0, 0, 0), (1, 0, 0), (0, 0, 1)])
    r = estimate_prism(m, 'triangle', default_height_m=1.0)
    check('3 points = minimal volume capture (triangle 0.5 m²)',
          r['ok'] and abs(r['groundAreaM2'] - 0.5) < 1e-9)

    _add_zone(m, 'two-points')
    _add_points(m, 'two-points', [(0, 0, 0), (1, 0, 0)])
    r = estimate_prism(m, 'two-points')
    check('2 points refused with suggestion',
          not r['ok'] and 'at least 3' in r['error'])

    _add_zone(m, 'bowtie')
    _add_points(m, 'bowtie',
                [(0, 0, 0), (1, 0, 1), (1, 0, 0), (0, 0, 1)])
    r = estimate_prism(m, 'bowtie')
    check('self-intersecting walk refused, edges named',
          not r['ok'] and 'self-intersects' in r['error'])

    _add_zone(m, 'lshape')
    _add_points(m, 'lshape',
                [(0, 0, 0), (2, 0, 0), (2, 0, 1), (1, 0, 1),
                 (1, 0, 2), (0, 0, 2)])
    r = estimate_prism(m, 'lshape', default_height_m=1.0)
    check('L-shape area 3', r['ok']
          and abs(r['groundAreaM2'] - 3.0) < 1e-9)

    _add_zone(m, 'tilted')
    _add_points(m, 'tilted',
                [(0, 0, 0), (1, 1, 0), (1, 1, 1), (0, 0, 1)])
    r = estimate_prism(m, 'tilted')
    check('tilted plane fits with ~zero residual (sqrt2 area)',
          r['ok'] and r['planeResidualRmsM'] < 1e-9
          and abs(r['groundAreaM2'] - 2 ** 0.5) < 1e-9)

    r = estimate_zone(m, 'lshape', default_height_m=1.0)
    check('estimate_zone persists a ZoneEstimateRecord',
          r['ok'] and len(m.objectTables.get('ZoneEstimateRecord',
                                             {})) >= 1)


def phase_calibration(m):
    from zones.zone_geometry import calibrate_zone, estimate_prism
    _add_zone(m, 'cal')
    _add_points(m, 'cal', [(0, 0, 0), (2, 0, 0), (2, 0, 2),
                           (0, 0, 2)])
    _add_points(m, 'cal', [(0, 1, 0), (0.5, 1, 0)],
                kind='reference', start=20)
    r = calibrate_zone(m, 'cal', known_length_m=1.0)
    check('calibration: measured 0.5 m across a known 1 m → ×2',
          r['ok'] and abs(r['scaleCorrection'] - 2.0) < 1e-9)
    r = estimate_prism(m, 'cal', default_height_m=1.0)
    check('calibrated area scales ×s² (4 → 16)',
          r['ok'] and r['calibrated']
          and abs(r['groundAreaM2'] - 16.0) < 1e-9)
    _add_zone(m, 'cal-none')
    r = calibrate_zone(m, 'cal-none', 1.0)
    check('calibration without reference points refused',
          not r['ok'] and 'reference point' in r['error'])


def phase_hull(m):
    from zones.zone_geometry import estimate_hull
    _add_zone(m, 'air-tri', mode='hull')
    _add_points(m, 'air-tri', [(0, 1, 0), (1, 1, 0), (0, 2, 0)],
                kind='free')
    r = estimate_hull(m, 'air-tri')
    check('3 free points = planar triangle, volume 0 + suggestion',
          r['ok'] and r['model'] == 'planar-triangle'
          and r['volumeM3'] == 0.0 and r['warnings'])

    _add_zone(m, 'air-tetra', mode='hull')
    _add_points(m, 'air-tetra',
                [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)],
                kind='free')
    r = estimate_hull(m, 'air-tetra')
    check('4th point makes the volume (tetrahedron 1/6)',
          r['ok'] and r['model'] == 'hull'
          and abs(r['volumeM3'] - 1 / 6) < 1e-9)

    _add_zone(m, 'air-cube', mode='hull')
    _add_points(m, 'air-cube',
                [(x, y, z) for x in (0, 1) for y in (0, 1)
                 for z in (0, 1)], kind='free')
    r = estimate_hull(m, 'air-cube')
    check('8 corner points = 1 m³ hull',
          r['ok'] and abs(r['volumeM3'] - 1.0) < 1e-9)

    _add_zone(m, 'air-flat', mode='hull')
    _add_points(m, 'air-flat',
                [(0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1)],
                kind='free')
    r = estimate_hull(m, 'air-flat')
    check('coplanar 4 points refused honestly', not r['ok'])


def phase_planar(m):
    from zones.zone_geometry import estimate_planar
    from zones.zone_packing import pack_zone
    _add_zone(m, 'plane-sq', mode='planar')
    _add_points(m, 'plane-sq',
                [(0, 0.48, 0), (1, 0.52, 0), (1, 0.5, 1),
                 (0, 0.5, 1)])
    r = estimate_planar(m, 'plane-sq')
    check('imperfect dots average to a 0.5 m plane, 0.5 m³ volume',
          r['ok'] and r['model'] == 'planar-extrusion'
          and abs(r['planeHeightM'] - 0.5) < 1e-9
          and abs(r['volumeM3'] - 0.5) < 1e-9, str(r)[:160])
    check('flatness spread reported as evidence',
          r['planarSpreadRmsM'] > 0)
    r = pack_zone(m, 'plane-sq', cube_size_m=0.25)
    check('planar pack: 16/layer × 2 layers = 32 cubes',
          r['ok'] and r['cubesPerLayer'] == 16 and r['layers'] == 2
          and r['totalCubes'] == 32, str(r)[:160])
    check('planar lattice stacks along +y from the floor',
          r['lattice']['frame']['normal'] == [0.0, 1.0, 0.0])

    _add_zone(m, 'plane-low', mode='planar')
    _add_points(m, 'plane-low',
                [(0, 0.0, 0), (1, 0.0, 0), (1, 0.0, 1)])
    r = estimate_planar(m, 'plane-low')
    check('dots at floor level: area but zero volume + warning',
          r['ok'] and r['volumeM3'] == 0.0 and r['warnings'])

    _add_zone(m, 'plane-spread', mode='planar')
    _add_points(m, 'plane-spread',
                [(0, 0.1, 0), (1, 0.9, 0), (1, 0.5, 1), (0, 0.5, 1)])
    r = estimate_planar(m, 'plane-spread')
    check('wide height spread warned, plane still forced to average',
          r['ok'] and any('spread' in w for w in r['warnings'])
          and abs(r['planeHeightM'] - 0.5) < 1e-9)


def phase_packing(m):
    from zones.zone_basis import SiteDefinition
    from zones.zone_packing import pack_zone, site_summary
    _add_zone(m, 'pack-sq', site='test-site')
    _add_points(m, 'pack-sq',
                [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)])
    _add_points(m, 'pack-sq', [(0.5, 0.5, 0.5)], kind='height',
                start=10)
    r = pack_zone(m, 'pack-sq', cube_size_m=0.25)
    check('1 m² × 0.5 m: 16/layer × 2 layers = 32 cubes',
          r['ok'] and r['cubesPerLayer'] == 16 and r['layers'] == 2
          and r['totalCubes'] == 32, str(r)[:160])
    check('full utilization on an axis-aligned square',
          abs(r['footprintUtilization'] - 1.0) < 1e-9
          and r['lattice']['cellsListed']
          and len(r['lattice']['cells']) == 16)
    r = pack_zone(m, 'pack-sq', cube_size_m=0.3)
    check('0.3 m cubes undercount honestly (full-cell: 9/layer)',
          r['ok'] and r['cubesPerLayer'] == 9 and r['layers'] == 1)
    r = pack_zone(m, 'pack-sq', cube_size_m=0.3, fit_test='center')
    check('center fit-test counts more than full-cell',
          r['ok'] and r['cubesPerLayer'] >= 9)
    r = pack_zone(m, 'pack-sq', fit_test='bogus')
    check('bogus fit_test refused', not r['ok'])

    _add_zone(m, 'pack-air', mode='hull', site='test-site',
              room='pack-room')
    _add_points(m, 'pack-air',
                [(x, y, z) for x in (0, 1) for y in (0, 1)
                 for z in (0, 1)], kind='free')
    r = pack_zone(m, 'pack-air', cube_size_m=0.25)
    check('hull cube 1 m³ packs 4³ = 64 cubes',
          r['ok'] and r['totalCubes'] == 64, str(r)[:160])


def phase_summaries(m):
    from zones.zone_basis import SiteDefinition
    from zones.zone_packing import room_summary, site_summary
    SiteDefinition(name='sum-site', manager=m)
    # The room: 2×2×1 m prism (volume 4).
    _add_zone(m, 'sum-room', site='sum-site', role='room')
    _add_points(m, 'sum-room',
                [(0, 0, 0), (2, 0, 0), (2, 0, 2), (0, 0, 2)])
    _add_points(m, 'sum-room', [(1, 1.0, 1)], kind='height',
                start=10)
    # A planar selection inside it: 1×1 outline at 0.5 m (volume 0.5).
    _add_zone(m, 'sum-shelf', mode='planar', site='sum-site',
              role='selection', room='sum-room')
    _add_points(m, 'sum-shelf',
                [(0, 0.5, 0), (1, 0.5, 0), (1, 0.5, 1), (0, 0.5, 1)])
    # A free-standing hull selection (1 m³, 64 cubes).
    _add_zone(m, 'sum-free', mode='hull', site='sum-site',
              role='selection')
    _add_points(m, 'sum-free',
                [(x, y, z) for x in (0, 1) for y in (0, 1)
                 for z in (0, 1)], kind='free')

    r = room_summary(m, 'sum-room', cube_size_m=0.25)
    check('room summary shows BOTH volumes (room 4, selected 0.5)',
          r['ok'] and abs(r['roomVolumeM3'] - 4.0) < 1e-9
          and abs(r['selectedVolumeM3'] - 0.5) < 1e-9
          and r['selectedCubes'] == 32, str(r)[:220])

    r = site_summary(m, 'sum-site', cube_size_m=0.25)
    check('site summary: room volumes vs selected volumes split',
          r['ok'] and abs(r['totalRoomVolumeM3'] - 4.0) < 1e-9
          and abs(r['totalSelectedVolumeM3'] - 1.5) < 1e-9
          and r['totalSelectedCubes'] == 96, str(r)[:220])
    check('free-standing selection listed separately',
          len(r['freeSelections']) == 1
          and r['freeSelections'][0]['zone'] == 'sum-free')
    r = site_summary(m, 'no-such-site')
    check('unknown site refused with known list',
          not r['ok'] and 'knownSites' in r)


def phase_seeds(m):
    from zones.zone_basis import (SEED_SITES, SEED_ZONE_POINTS,
                                  SEED_ZONES, SiteDefinition,
                                  ZoneDefinition, ZonePoint)
    for seed in SEED_SITES:
        SiteDefinition(**seed, manager=m)
    for seed in SEED_ZONES:
        ZoneDefinition(**seed, manager=m)
    for seed in SEED_ZONE_POINTS:
        ZonePoint(**seed, manager=m)
    from zones.zone_packing import room_summary, site_summary
    r = room_summary(m, 'demo-room-zone', cube_size_m=0.25)
    sel = {s['zone']: s for s in r['selections']}
    check('demo room: room volume 1.5, selections shelf+air',
          r['ok'] and abs(r['roomVolumeM3'] - 1.5) < 1e-6
          and set(sel) == {'demo-shelf-selection', 'demo-air-shape'},
          str(r)[:220])
    check('demo shelf (planar, imperfect dots): 0.25 m³, 16 cubes '
          '(8/layer × 2)',
          sel['demo-shelf-selection']['totalCubes'] == 16
          and abs(sel['demo-shelf-selection']['volumeM3'] - 0.25)
          < 1e-6, str(sel['demo-shelf-selection']))
    check('demo air shape packs 64 cubes',
          sel['demo-air-shape']['totalCubes'] == 64)
    r = site_summary(m, 'demo-house', cube_size_m=0.25)
    check('demo house: room 1.5 m³ vs selected 1.25 m³ / 80 cubes',
          r['ok'] and abs(r['totalRoomVolumeM3'] - 1.5) < 1e-6
          and abs(r['totalSelectedVolumeM3'] - 1.25) < 1e-6
          and r['totalSelectedCubes'] == 80, str(r)[:260])


def phase_sim_bridge(m):
    from zones.zone_sim_bridge import (zone_constraints,
                                       zone_to_simulation)
    _add_zone(m, 'bridge-zone', mode='planar', site='bridge-site')
    _add_points(m, 'bridge-zone',
                [(0, 0.5, 0), (1, 0.5, 0), (1, 0.5, 1), (0, 0.5, 1)])
    r = zone_constraints(m, 'bridge-zone')
    check('constraints carry the reality numbers',
          r['ok']
          and abs(r['constraints']['zone_footprint_area_m2'] - 1.0)
          < 1e-9
          and abs(r['constraints']['zone_volume_m3'] - 0.5) < 1e-9
          and r['constraints']['zone_perimeter_m'] > 0, str(r)[:200])
    r = zone_constraints(m, 'no-such-zone')
    check('constraints for unknown zone refused', not r['ok'])
    r = zone_to_simulation(m, 'bridge-zone',
                           target_simulation_ref='demo-sim',
                           target_class_name='DemoSimState')
    check('swap-modes act creates sim space + IC interface',
          r['ok'] and r['simSpaceCreated'] and r['icInterfaceCreated']
          and r['simSpace'] == 'bridge-zone-space'
          and r['icInterface'] == 'zone-ic--bridge-zone',
          str(r)[:220])
    from scoring.worldview_elections import _by_name, _rows
    ic = _by_name(m, 'InitialConditionInterfaceDefinition')[
        'zone-ic--bridge-zone']
    import json as _json
    config = _json.loads(ic.config_json)
    check('IC choice applies constraints as setParams',
          config['choices'][0]['key'] == 'apply-real-constraints'
          and abs(config['choices'][0]['setParams']
                  ['zone_volume_m3'] - 0.5) < 1e-9
          and ic.target_simulation_ref == 'demo-sim')
    space = _by_name(m, 'SimSpaceDefinition')['bridge-zone-space']
    check('zone sim space is XR-ready with the board interface',
          space.xr_mode == 'both'
          and 'zones-board' in space.configured_interfaces_json)
    # Zones tie to a specific simulation; the bridge defaults the IC
    # target to that tie.
    from zones.zone_basis import ZoneDefinition, ZonePoint
    ZoneDefinition(name='tied-zone', capture_mode='planar',
                   zone_role='selection',
                   simulation_ref='zone-block-filling', manager=m)
    for i, (x, z) in enumerate([(0, 0), (1, 0), (1, 1)]):
        ZonePoint(name=f'tied-p{i}', zone_name='tied-zone', index=i,
                  kind='ground', x=x, y=0.5, z=z, manager=m)
    r = zone_to_simulation(m, 'tied-zone')
    ic2 = _by_name(m, 'InitialConditionInterfaceDefinition')[
        'zone-ic--tied-zone']
    check('bridge defaults IC target to the zone\'s tied simulation',
          r['ok'] and ic2.target_simulation_ref
          == 'zone-block-filling')
    from zones.zone_basis import SEED_SIMULATION_DEFINITIONS
    sample = [s for s in SEED_SIMULATION_DEFINITIONS
              if s.get('name') == 'zone-block-filling']
    check('sample AR-required simulation seeded once',
          len(sample) == 1
          and sample[0]['xr_requirement'] == 'ar-capture')
    r = zone_to_simulation(m, 'bridge-zone')
    check('bridge is idempotent (updates, no duplicates)',
          r['ok'] and not r['simSpaceCreated']
          and not r['icInterfaceCreated']
          and len([s for s in _rows(m, 'SimSpaceDefinition')
                   if getattr(s, 'name', '')
                   == 'bridge-zone-space']) == 1)


def main():
    m = _mgr()
    phase_prism(m)
    phase_calibration(m)
    phase_planar(m)
    phase_hull(m)
    phase_packing(m)
    phase_summaries(m)
    phase_sim_bridge(m)
    phase_seeds(_mgr())
    passed, total = sum(_results), len(_results)
    print(f'{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
