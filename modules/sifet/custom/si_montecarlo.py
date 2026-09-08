"""
@module sifet.custom.si_montecarlo

Silicon variability basis (2026-08-29): the stochastic surfaces
(envelope, score spread, best / worst case) for a SiliconMOSFET row,
in the SAME report shape as cntfet.custom.cnt_montecarlo so every fi-3
consumer (device_viz curves, /score?samples) works unchanged.

The distributions are ENGINEERING PRIORS as data (SI_VARIATION_KNOBS,
every payload flags them): random-dopant / work-function Vt shift,
gate-length (litho) and oxide-thickness (deposition) sigmas, and a
mobility spread. No process rows exist for silicon yet — when a
`SiliconProcess` basis lands these become rows like the CNT process
set; until then the report says PRIOR population, like S3 does.

@consumers cntfet.cnt_device_viz_seed._montecarlo (dispatch by class)
"""

import numpy as np

from cntfet.custom.cnt_metrics import extract_metrics
from cntfet.custom.cnt_montecarlo import _envelope, _quantiles, _score_population
from cntfet.custom.cnt_vs_model import vs_terminal_current

SI_VARIATION_KNOBS = {
    'vt_sigma_v': 0.030,          # RDF + WF: ~30 mV at 90 nm-class (prior)
    'lg_sigma_fraction': 0.05,    # litho: 5 % of Lg (prior)
    'tox_sigma_fraction': 0.03,   # oxide deposition: 3 % (prior)
    'mu_sigma_fraction': 0.05,    # mobility spread (prior)
    'min_on_off_ratio': 1e4,
    'min_ion_a': 1e-6,
}
PRIORS = ['SI_VARIATION_KNOBS.vt_sigma_v', 'SI_VARIATION_KNOBS.lg_sigma_fraction',
          'SI_VARIATION_KNOBS.tox_sigma_fraction',
          'SI_VARIATION_KNOBS.mu_sigma_fraction']


def _sample(rng, rows, device, k):
    """One virtual silicon device's VS params via the SAME builder the
    nominal device uses, on perturbed copies of its rows."""
    import types
    from sifet.custom.si_device import params_from_rows
    diel = rows['dielectric']
    t0 = float(getattr(diel, 'thickness_nm'))
    lg0 = float(getattr(device, 'lg_nm'))
    d2 = types.SimpleNamespace(**{a: getattr(diel, a) for a in dir(diel)
                                  if not a.startswith('_')
                                  and not callable(getattr(diel, a))})
    d2.thickness_nm = max(0.5, rng.normal(t0, k['tox_sigma_fraction'] * t0))
    r2 = dict(rows); r2['dielectric'] = d2
    lg = max(2.0, rng.normal(lg0, k['lg_sigma_fraction'] * lg0))
    p = params_from_rows(r2, device, lg_nm=lg)
    p = dict(p)
    p['vt0_v'] = p['vt0_v'] + rng.normal(0.0, k['vt_sigma_v'])
    p['mu_m2_per_vs'] = p['mu_m2_per_vs'] * max(
        0.2, rng.normal(1.0, k['mu_sigma_fraction']))
    p['ptype'] = 0
    p['_sampled'] = {'lg_eff_nm': lg, 't_ox_nm': d2.thickness_nm,
                     'vt0_v': p['vt0_v'],
                     'mu_cm2_per_vs': p['mu_m2_per_vs'] * 1e4}
    return p


def monte_carlo(manager, device, sample_count=100, seed=1, criteria=None,
                result_factory=None, score=True):
    from sifet.custom.si_device import params_from_rows, resolve_components
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False, 'error': f'missing component rows: {missing}'}
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    k = {**SI_VARIATION_KNOBS, **(criteria or {})}
    vdd = float(getattr(device, 'vdd_v', 1.0) or 1.0)
    nominal = dict(params_from_rows(rows, device)); nominal['ptype'] = 0
    rng = np.random.default_rng(seed)
    samples, pop = [], {'ion_a': [], 'ioff_a': [], 'on_off_ratio': [],
                        'ss_mv_per_dec': [], 'vt_cc_lin_v': [],
                        'gm_peak_s': []}
    violations = {'on-off-ratio': 0, 'ion-floor': 0}
    functional = 0
    for _ in range(sample_count):
        p = _sample(rng, rows, device, k)
        m = extract_metrics(lambda vg, vd, p=p:
                            vs_terminal_current(vg, vd, p)['id_a'],
                            {'vdd_v': vdd})
        ok = True
        if (m['on_off_ratio'] or 0.0) < k['min_on_off_ratio']:
            violations['on-off-ratio'] += 1; ok = False
        if m['ion_a'] < k['min_ion_a']:
            violations['ion-floor'] += 1; ok = False
        if ok:
            functional += 1
            samples.append((p, m))
        for key in pop:
            if m.get(key) is not None:
                pop[key].append(m[key])
    report = {
        'ok': True, 'device': device.name, 'processSet': 'si-priors',
        'sampleCount': sample_count, 'seed': seed, 'criteria': k,
        'yield': {'functional': functional,
                  'functionalFraction': functional / max(sample_count, 1),
                  'aliveButFailing': sample_count - functional,
                  'kills': {}, 'criterionViolations': violations},
        'population': {key: _quantiles(v) for key, v in pop.items()},
        'dominantLimitation': max(violations, key=violations.get)
        if any(violations.values()) else 'none',
        'priorFlagged': PRIORS,
        'honesty': 'silicon variability = ENGINEERING PRIORS '
                   '(SI_VARIATION_KNOBS), not process rows — a '
                   'SiliconProcess basis replaces them when it lands',
        'resultRow': 'unrecorded',
    }
    if score:
        report['score'] = _score_population(manager, device, nominal,
                                            samples, vdd)
        report['envelope'] = _envelope(samples, vdd)
        if report['score'].get('quantiles'):
            report['population']['score'] = report['score']['quantiles']
    return report
