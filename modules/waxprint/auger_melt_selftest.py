"""
Selftest for waxprint wp-1 — two-zone auger melt physics + safety gate.

Run from polari-framework/:
    python3 -m waxprint.auger_melt_selftest

Stdlib only (the physics is pure `math`); the manager is a mock
SimpleNamespace built from the seed lists (aquaponics selftest idiom).
Validates the closed-form building blocks against hand-computed numbers,
the enthalpy-plateau state map, the integrator, and end-to-end melt +
safety verdicts on the seeded rows.
"""

import math
from types import SimpleNamespace

from waxprint.custom import auger_melt as am
from waxprint.custom import melt_analysis
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


def _find_result(mgr, assembly, feedstock, condition):
    out = melt_analysis.run_melt(mgr, assembly, feedstock, condition)
    assert out['ok'], out
    return out['result']


if __name__ == '__main__':
    print('waxprint wp-1 — auger two-zone melt')

    print('\nconveying geometry (hand-computed)')
    area = am.channel_area_m2(0.012, 0.006)
    check('channel area = pi/4(D^2-d^2)',
          close(area, math.pi / 4.0 * (0.012 ** 2 - 0.006 ** 2)),
          f'{area:.3e} m^2')
    v = am.axial_velocity_m_s(0.008, 25.0, 0.6)
    check('axial velocity = pitch*N*eff', close(v, 0.008 * (25.0 / 60.0) * 0.6),
          f'{v:.5f} m/s')
    q = am.volumetric_flow_m3_s(0.008, 25.0, 0.012, 0.006, 0.6)
    check('flow Q = v*A', close(q, v * area), f'{q:.3e} m^3/s')

    print('\nlumped thermal closed forms')
    tau = am.time_constant_s(1.0, 2000.0, 250.0, 0.01)
    check('tau = m*cp/(h*A)', close(tau, 1.0 * 2000.0 / (250.0 * 0.01)),
          f'{tau:.3f} s')
    # after exactly one tau, T = Tw + (T0-Tw)/e
    t1 = am.exponential_approach(300.0, 400.0, tau, tau)
    check('exp approach at t=tau hits Tw+(T0-Tw)/e',
          close(t1, 400.0 + (300.0 - 400.0) * math.exp(-1.0)), f'{t1:.3f} K')
    # energy-conservation identity: delivered == m*cp*(T(t)-T0)
    e = am.delivered_energy_j(300.0, 400.0, tau, tau, 1.0, 2000.0)
    check('delivered energy == m*cp*(T(t)-T0) (no phase change)',
          close(e, 1.0 * 2000.0 * (t1 - 300.0)), f'{e:.1f} J')
    check('Biot number = h*(r/3)/k',
          close(am.biot_number(250.0, 0.0015, 0.27),
                250.0 * (0.0015 / 3.0) / 0.27))

    print('\nviscosity + nozzle pressure')
    eta_ref = am.viscosity_pa_s(100.0, 0.6, 100.0, 6500.0)
    check('eta(T_ref) == eta_ref', close(eta_ref, 0.6), f'{eta_ref:.4f} Pa.s')
    eta_hot = am.viscosity_pa_s(120.0, 0.6, 100.0, 6500.0)
    check('eta falls as T rises', eta_hot < eta_ref,
          f'{eta_hot:.4f} < {eta_ref:.4f}')
    dp1 = am.hagen_poiseuille_dp_pa(1.0, 0.001, 1e-7, 0.0002)
    dp2 = am.hagen_poiseuille_dp_pa(1.0, 0.001, 1e-7, 0.0004)
    check('dP scales as 1/r^4 (halve r -> 16x)', close(dp1 / dp2, 16.0),
          f'ratio {dp1 / dp2:.2f}')

    print('\nenthalpy plateau state map')
    m, cp, L = 1e-5, 2100.0, 180000.0
    t0k, tmk = am.c_to_k(22.0), am.c_to_k(90.0)
    h_to_melt = m * cp * (tmk - t0k)
    h_latent = m * L
    _, mf0 = am.enthalpy_to_state(h_to_melt * 0.5, m, cp, L, t0k, tmk)
    check('below melt point -> solid (mf=0)', mf0 == 0.0)
    tmid, mfmid = am.enthalpy_to_state(h_to_melt + h_latent * 0.5, m, cp, L,
                                       t0k, tmk)
    check('mid-plateau -> T=Tmelt, mf=0.5',
          close(tmid, tmk) and close(mfmid, 0.5), f'mf={mfmid:.3f}')
    tliq, mfliq = am.enthalpy_to_state(h_to_melt + h_latent + m * cp * 10.0,
                                       m, cp, L, t0k, tmk)
    check('above plateau -> liquid (mf=1), T>Tmelt',
          mfliq == 1.0 and tliq > tmk, f'T={am.k_to_c(tliq):.1f}C')

    print('\nintegrator sanity')
    h_end = am.integrate_zone(0.0, am.c_to_k(115.0), 60.0, 0.7, m, cp, L,
                              t0k, tmk)
    ceiling = m * cp * (am.c_to_k(115.0) - t0k) + m * L
    check('long residence approaches the wall-temp enthalpy ceiling',
          h_end <= ceiling + 1e-9 and h_end > 0.9 * ceiling,
          f'H={h_end:.3f}/{ceiling:.3f} J')

    print('\nend-to-end melt + safety on seeded rows')
    mgr = _mgr()

    r = _find_result(mgr, 'demo-auger-extruder', 'mvw-natural-blend',
                     'room-baseline')
    check('room baseline is thermally safe', r['thermally_safe'] is True)
    check('room baseline fully molten', r['fully_molten'] is True,
          f"mf={r['melt_fraction']:.3f}")
    check('room baseline printable', r['printable'] is True,
          f"exit {r['exit_temp_c']:.1f}C, dP {r['nozzle_pressure_pa']:.0f} Pa")

    r = _find_result(mgr, 'demo-auger-extruder', 'mvw-natural-blend',
                     'hot-unsafe')
    check('over-ceiling condition is NOT thermally safe',
          r['thermally_safe'] is False)
    check('over-ceiling emits over-safe-ceiling finding',
          any(f['code'] == 'over-safe-ceiling' for f in r['findings']))
    check('over-ceiling not printable', r['printable'] is False)

    r = _find_result(mgr, 'demo-auger-extruder', 'mvw-natural-blend',
                     'cold-undermelt')
    check('cold/fast condition under-melts',
          r['fully_molten'] is False,
          f"mf={r['melt_fraction']:.3f}")
    check('under-melt emits a finding',
          any(f['code'] in ('under-melted', 'below-melt-margin')
              for f in r['findings']))

    # PTFE-lined hotend above its 240C service ceiling -> material block.
    ptfe_cond = SimpleNamespace(
        name='ptfe-overtemp', auger_temp_c=120.0, hotend_temp_c=260.0,
        rpm=25.0, nozzle_diameter_mm=0.0, ambient_temp_c=22.0, bed_temp_c=22.0)
    mgr2 = _mgr()
    mgr2.objectTables['PrintConditionDefinition'][99] = ptfe_cond
    r = _find_result(mgr2, 'ptfe-hotend-extruder', 'carnauba-rich',
                     'ptfe-overtemp')
    check('PTFE hotend over service temp -> material block',
          any(f['code'] == 'material-over-service-temp' for f in r['findings'])
          and r['printable'] is False)

    r = _find_result(mgr, 'demo-auger-extruder', 'mvw-natural-blend',
                     'fridge-print')
    check('fridge print still melts (chamber unaffected by ambient)',
          r['fully_molten'] is True, f"mf={r['melt_fraction']:.3f}")

    missing = melt_analysis.run_melt(mgr, 'nope', 'mvw-natural-blend',
                                     'room-baseline')
    check('missing assembly reported by name',
          missing['ok'] is False
          and any('nope' in m for m in missing.get('missing', [])))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)
