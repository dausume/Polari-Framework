"""
Selftest for the L3 MD + L2 mesoscale engines (msci-25).

Run from polari-framework/:
  python3 -m materialsScience.selftest_md_meso_engines

Physics-INVARIANT validations (bands from the msci-25 smoke runs,
set generously): thermostat accuracy, NVE energy drift, dilute-gas
pressure vs ideal, dense-melt cohesion, Kremer-Grest bond length,
rod-percolation vs the Balberg slender-rod limit + aspect-ratio
monotonicity, dipolar chaining on/off across the coupling threshold,
and honest range-naming refusals. Small N / few steps: < ~2 min.
"""

import sys

from materialsScience.engines import md_engine, meso_engine

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def main():
    caps = md_engine.capability(), meso_engine.capability()
    check('capabilities honest: available flags + named gaps',
          all(c.get('available') for c in caps)
          and 'forceFieldMD' in str(caps[0])
          and ('dpd' in str(caps[1]).lower()
               or 'hydrodynam' in str(caps[1]).lower()), str(caps)[:200])

    # --- LJ melt: thermostat + cohesion -------------------------------
    melt = md_engine.lj_melt(density=0.8, temperature=1.0,
                             n_particles=125, steps=1500,
                             equilibration=600, seed=7)
    check('LJ melt: Langevin holds T* within 8% of target',
          melt['ok'] and abs(melt['measuredTemperature'] - 1.0) < 0.08,
          str(melt.get('measuredTemperature')))
    check('LJ melt: dense-liquid cohesion U*/N in (-7, -3)',
          -7.0 < melt['potentialPerParticle'] < -3.0,
          str(melt.get('potentialPerParticle')))

    # --- dilute gas: pressure ~ ideal ----------------------------------
    gas = md_engine.lj_melt(density=0.05, temperature=2.0,
                            n_particles=125, steps=1500,
                            equilibration=600, seed=7)
    check('LJ dilute gas: P within 12% of rho*T (small negative '
          'virial expected)',
          gas['ok'] and abs(gas['pressure'] - gas['idealGasPressure'])
          / gas['idealGasPressure'] < 0.12,
          f"{gas.get('pressure')} vs {gas.get('idealGasPressure')}")

    # --- NVE drift ------------------------------------------------------
    nve = md_engine.lj_melt(density=0.8, temperature=1.0,
                            n_particles=125, steps=500,
                            equilibration=100, thermostat='none',
                            seed=7)
    check('NVE: energy drift < 5e-3 per particle',
          nve['ok'] and abs(nve.get('nveDriftPerParticle', 1)) < 5e-3,
          str(nve.get('nveDriftPerParticle')))

    # --- bead-spring ------------------------------------------------------
    bs = md_engine.bead_spring_melt(chain_length=10, n_chains=15,
                                    steps=1500, equilibration=600,
                                    seed=7)
    check('bead-spring: KG bond length in [0.92, 1.02] '
          '(literature ~0.97 sigma)',
          bs['ok'] and 0.92 < bs['meanBondLength'] < 1.02,
          str(bs.get('meanBondLength')))
    check('bead-spring: chains intact + Rg physically sized',
          bs['ok'] and 1.0 < bs['radiusOfGyration'] < 3.5,
          str(bs.get('radiusOfGyration')))

    # --- rod percolation ---------------------------------------------------
    rp20 = meso_engine.rod_percolation_threshold(aspect_ratio=20,
                                                 n_rods=150, trials=6,
                                                 iterations=8, seed=7)
    check('rod percolation: vf_c within [0.8, 2.5]x the Balberg '
          'slender-rod limit at aspect 20',
          rp20['ok'] and 0.8 < rp20['ratioToLimit'] < 2.5,
          str(rp20.get('ratioToLimit')))
    rp10 = meso_engine.rod_percolation_threshold(aspect_ratio=10,
                                                 n_rods=150, trials=6,
                                                 iterations=8, seed=7)
    rp40 = meso_engine.rod_percolation_threshold(aspect_ratio=40,
                                                 n_rods=150, trials=6,
                                                 iterations=8, seed=7)
    check('rod percolation: vf_c falls as aspect rises (10 > 40)',
          rp10['ok'] and rp40['ok']
          and rp10['percolationThreshold']
          > rp40['percolationThreshold'],
          f"{rp10.get('percolationThreshold')} vs "
          f"{rp40.get('percolationThreshold')}")

    # --- dipolar chaining ---------------------------------------------------
    strong = meso_engine.dipolar_chaining(coupling_lambda=6.0,
                                          volume_fraction=0.12,
                                          n_particles=100,
                                          steps=6000, seed=7)
    check('dipolar: chains FORM at lambda=6, vf=0.12',
          strong['ok'] and strong['chainsFormed'],
          str({k: strong.get(k) for k in ('chainedFraction',
                                          'fieldAlignment')}))
    weak = meso_engine.dipolar_chaining(coupling_lambda=0.5,
                                        volume_fraction=0.12,
                                        n_particles=100,
                                        steps=3000, seed=7)
    check('dipolar: chains do NOT form at lambda=0.5',
          weak['ok'] and not weak['chainsFormed'],
          str(weak.get('chainedFraction')))

    # --- honest refusals name their ranges -------------------------------
    bad = [md_engine.lj_melt(density=5.0, temperature=1.0),
           md_engine.bead_spring_melt(chain_length=10, n_chains=20,
                                      density=0.1),
           meso_engine.rod_percolation_threshold(aspect_ratio=1000),
           meso_engine.dipolar_chaining(coupling_lambda=50,
                                        volume_fraction=0.1)]
    check('refusals: every out-of-range input refused with the range '
          'named',
          all(not b['ok'] and any(ch.isdigit()
                                  for ch in str(b.get('error', '')))
              for b in bad),
          str([b.get('error', '')[:40] for b in bad]))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
