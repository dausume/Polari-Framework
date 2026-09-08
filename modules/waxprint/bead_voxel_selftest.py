"""
Selftest for waxprint wp-2 — bead cooling, fan wind vector, print voxels.

Run from polari-framework/:
    python3 -m waxprint.bead_voxel_selftest

Validates the air/forced-convection helpers, an ANALYTIC no-latent
Newtonian-cooling closed form for the bead integrator, the fan-vector
effects (faster freeze + less spread + a warp asymmetry), the voxel
model, and the resolution-at-height profile on the seeded rows.
"""

import math
from types import SimpleNamespace

from waxprint.custom import bead_cooling as bc
from waxprint.custom import voxel_resolution as vox
from waxprint.custom import bead_analysis
from waxprint.custom.auger_melt import c_to_k
from waxprint.waxprint_seed import (
    SEED_DEVICE_MATERIALS, SEED_FEEDSTOCKS, SEED_ASSEMBLIES, SEED_CONDITIONS)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}{("  " + extra) if extra else ""}')


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


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
    print('waxprint wp-2 — bead cooling, fan vector, voxels')

    print('\nair + forced convection (the fan as a wind vector)')
    check('colder air is denser', bc.air_density(4.0) > bc.air_density(22.0),
          f'{bc.air_density(4.0):.3f} > {bc.air_density(22.0):.3f}')
    check('no wind -> no forced convection',
          bc.forced_h(0.0, 4e-4, 22.0) == 0.0)
    h_slow = bc.forced_h(0.5, 4e-4, 22.0)
    h_fast = bc.forced_h(3.0, 4e-4, 22.0)
    check('forced h rises with wind speed', h_fast > h_slow > 0,
          f'{h_slow:.1f} -> {h_fast:.1f} W/m2K')
    check('Nusselt monotonic in Re',
          bc.hilpert_nusselt(1000) > bc.hilpert_nusselt(100) >
          bc.hilpert_nusselt(10))
    check('aluminum bed conducts more than glass',
          bc.bed_conductance_h(167.0) > bc.bed_conductance_h(1.1))

    print('\nanalytic no-latent Newtonian cooling (closed form)')
    # latent=0, substrate at ambient, no wind -> pure exponential decay
    # with tau = m*cp / (h_air*P_air + h_bed*bed_w); solidify when the
    # bead crosses melt_point.
    w0, lh = 4e-4, 2e-4
    dens, cp = 950.0, 2100.0
    tamb, tmelt, texit = 22.0, 80.0, 120.0
    area, air_perim, bed_w = bc.bead_cross_section(w0, lh)
    mass = dens * area
    still_h = 8.0
    h_bed = bc.bed_conductance_h(0.25)   # substrate_is_bed=False path
    coeff = still_h * air_perim + h_bed * bed_w
    tau_c = mass * cp / coeff
    t_expected = tau_c * math.log((texit - tamb) / (tmelt - tamb))
    r = bc.cool_bead(texit, w0, lh, dens, cp, 0.0, tmelt,
                     0.6, 100.0, 6500.0, tamb, tamb, still_h, 0.0, 0.25,
                     substrate_is_bed=False, substrate_temp_c=tamb,
                     max_time_s=30.0, steps=6000, k_spread=0.0)
    check('t_solidify matches analytic exponential (latent=0)',
          close(r['t_solidify_s'], t_expected, tol=0.02),
          f"{r['t_solidify_s']:.3f} vs {t_expected:.3f} s")

    print('\nfan effects: faster freeze, less spread, warp asymmetry')
    feed = {'density': 965.0, 'cp': 2100.0, 'latent': 180000.0,
            'melt_point_c': 90.0, 'eta_ref': 0.6, 'eta_ref_temp': 100.0,
            'eta_act': 6500.0}
    base_env = {'ambient_c': 22.0, 'bed_temp_c': 22.0, 'still_air_h': 8.0,
                'wind_speed': 0.0, 'k_bed': 1.1, 'substrate_is_bed': True}
    no_fan = vox.achievable_voxel(114.0, 0.4, 0.2, feed, base_env)
    fan_env = dict(base_env, wind_speed=0.8)
    with_fan = vox.achievable_voxel(114.0, 0.4, 0.2, feed, fan_env)
    check('fan freezes the bead sooner',
          with_fan['t_solidify_s'] < no_fan['t_solidify_s'],
          f"{with_fan['t_solidify_s']:.3f} < {no_fan['t_solidify_s']:.3f} s")
    check('fan reduces spread (finer voxel)',
          with_fan['voxel_xy_mm'] <= no_fan['voxel_xy_mm'],
          f"{with_fan['voxel_xy_mm']:.3f} <= {no_fan['voxel_xy_mm']:.3f} mm")
    check('no fan -> zero warp asymmetry', close(no_fan['warp_index'], 0.0))
    check('fan -> positive warp asymmetry (the instability cost)',
          with_fan['warp_index'] > 0.0, f"{with_fan['warp_index']:.3f}")

    print('\nfridge vs room, and the voxel itself')
    room = vox.achievable_voxel(114.0, 0.4, 0.2, feed, base_env)
    fridge_env = dict(base_env, ambient_c=4.0, bed_temp_c=4.0, still_air_h=12.0)
    fridge = vox.achievable_voxel(114.0, 0.4, 0.2, feed, fridge_env)
    check('fridge gives a finer voxel than room',
          fridge['voxel_xy_mm'] <= room['voxel_xy_mm'],
          f"{fridge['voxel_xy_mm']:.3f} <= {room['voxel_xy_mm']:.3f} mm")
    check('voxel_xy is at least the nozzle bore',
          room['voxel_xy_mm'] >= 0.4 - 1e-9, f"{room['voxel_xy_mm']:.3f} mm")
    check('voxel volume = xy*xy*z',
          close(room['voxel_volume_mm3'],
                room['voxel_xy_mm'] ** 2 * room['voxel_z_mm']))
    check('margin is reported and non-negative', room['margin_mm'] >= 0.0,
          f"{room['margin_mm']:.4f} mm")
    check('resolution class assigned', room['resolution_class'] in
          ('ultra-fine', 'fine', 'standard', 'coarse'),
          room['resolution_class'])

    print('\nresolution degrades with build height')
    prof = vox.resolution_profile(114.0, 0.4, 0.2, feed, base_env)
    xys = [r['voxel_xy_mm'] for r in prof['rows']]
    check('profile has a row per height',
          len(prof['rows']) == len(vox.DEFAULT_PROFILE_HEIGHTS_MM))
    check('substrate warms with height',
          prof['rows'][-1]['substrate_temp_c'] >
          prof['rows'][0]['substrate_temp_c'],
          f"{prof['rows'][0]['substrate_temp_c']:.1f} -> "
          f"{prof['rows'][-1]['substrate_temp_c']:.1f} C")
    check('voxel is coarsest at the top (worst resolution high up)',
          xys[-1] >= xys[0] - 1e-9 and prof['degradation_mm'] >= 0.0,
          f"deg {prof['degradation_mm']:.3f} mm")

    print('\nend-to-end via mock manager (rows -> melt -> voxel)')
    mgr = _mgr()
    out = bead_analysis.run_voxel(mgr, 'demo-auger-extruder',
                                  'mvw-natural-blend', 'room-baseline')
    check('run_voxel ok + printable', out['ok'] and out['printable'],
          f"voxel_xy {out['voxel']['voxel_xy_mm']:.3f} mm")
    fine = bead_analysis.run_voxel(mgr, 'fine-nozzle-extruder',
                                   'mvw-natural-blend', 'fine-voxel')
    check('fine-nozzle recipe yields a finer voxel than the demo baseline',
          fine['voxel']['voxel_xy_mm'] < out['voxel']['voxel_xy_mm'],
          f"{fine['voxel']['voxel_xy_mm']:.3f} < "
          f"{out['voxel']['voxel_xy_mm']:.3f} mm")

    prof_out = bead_analysis.run_resolution_profile(
        mgr, 'demo-auger-extruder', 'mvw-natural-blend', 'room-baseline')
    check('resolution-profile endpoint returns a table',
          prof_out['ok'] and len(prof_out['profile']['rows']) > 0)

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
