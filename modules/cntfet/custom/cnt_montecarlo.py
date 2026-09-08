"""
@module cntfet.custom.cnt_montecarlo

S3: the Monte Carlo engine — the device declares targets, the
bound process set (cnt_process_basis rows sharing the device's
process_set name) contributes distributions, and the population is
instantiated + evaluated with the SAME metric ruler as everything
else (cnt_metrics). Deterministic under a caller-supplied seed
(reproducible rows).

Per virtual device:
  purification  metallic tube with p = 1 - purity  -> DEAD
  placement     missing tube with missing_tube_prob -> DEAD
  purification  diameter ~ N(mu, sigma)  -> Eg/vxo/mu/Cq re-derived
  lithography   Lg ~ N(target, feature_sigma)
  alignment     Lg_eff = Lg / cos(theta), theta ~ N(0, angle_sigma)
  gate stack    t_ox ~ N(target, tox_sigma), k_ox ~ N(target,
                kox_sigma), Vt0 shift ~ N(0, vt_sigma)
  contacts      Rc ~ lognormal(median, sigma_ln), floored at the
                quantum half RQ/2 (physics, not clipping for
                comfort)

Yield criteria are explicit knobs (min on/off ratio, Ion window);
the DOMINANT LIMITATION is reported from the kill/violation
counts — the feedback-loop output D7 asks for.

Honesty: sampling REFUSES when the process set is missing rows,
is bound across regimes (D6), or carries confidence 'none'.
Low-confidence priors sample but the run row lists them — a
population built on priors says so.

@consumers
  - cntfet.cnt_api ({action: montecarlo})
  - cntfet.cntfet_selftest
"""

import json
import math
from datetime import datetime, timezone

import numpy as np

from cntfet.custom.cnt_bandstructure import (
    cinv_f_per_m, cox_gaa_f_per_m, cqe_f_per_m, eg_ev,
    sce_parameters,
)
from cntfet.custom.cnt_constants import lit_value, thermal_voltage_v
from cntfet.custom.cnt_derive import resolve_components
from cntfet.custom.cnt_metrics import extract_metrics
from cntfet.custom.cnt_vs_model import (
    mu_cm2_per_vs, vs_terminal_current, vxo_m_per_s,
)

PROCESS_CLASSES = (
    'CNTAlignmentProcess', 'CNTPlacementProcess',
    'CNTPurificationProcess', 'ContactFormationProcess',
    'LithographyProcess', 'GateStackProcess',
)

DEFAULT_CRITERIA = {
    'min_on_off_ratio': 1e4,
    'min_ion_a': 1e-6,
    'vdd_v': 0.6,
}


def gather_process_set(manager, process_set, regime):
    """The six process rows for a set, with D6 regime coherence
    enforced. Returns (rows_by_class, refusal_or_None,
    prior_flags)."""
    tables = getattr(manager, 'objectTables', None) or {}
    rows, priors = {}, []
    for cls in PROCESS_CLASSES:
        found = [r for r in (tables.get(cls) or {}).values()
                 if getattr(r, 'process_set', '') == process_set]
        if not found:
            return None, (f'process set "{process_set}" has no '
                          f'{cls} row — sampling refuses rather '
                          'than idealize'), []
        row = found[0]
        row_regime = getattr(row, 'manufacturing_regime', '')
        if row_regime and regime and row_regime != regime:
            return None, (f'{cls} "{row.name}" describes regime '
                          f'"{row_regime}" but the device is '
                          f'"{regime}" — a line cannot fabricate '
                          'outside its regime (D6)'), []
        conf = getattr(row, 'confidence', 'low')
        if conf == 'none':
            return None, (f'{cls} "{row.name}" has confidence '
                          '"none" — measure or set a prior first'), []
        if conf == 'low':
            priors.append(f'{cls}.{row.name}')
        rows[cls] = row
    return rows, None, priors


def _sample_device_params(rng, targets, procs, phit_v):
    """One virtual device's compact-model params, or a kill
    reason."""
    purification = procs['CNTPurificationProcess']
    if rng.random() > purification.semiconducting_purity:
        return None, 'metallic-tube'
    if rng.random() < procs['CNTPlacementProcess'].missing_tube_prob:
        return None, 'missing-tube'
    d_nm = rng.normal(purification.diameter_mu_nm,
                      purification.diameter_sigma_nm)
    if d_nm < 0.5:
        return None, 'unphysical-diameter'
    litho = procs['LithographyProcess']
    lg_nm = rng.normal(targets['lg_nm'], litho.feature_sigma_nm)
    if lg_nm < 2.0:
        return None, 'unphysical-lg'
    theta = math.radians(rng.normal(
        0.0, procs['CNTAlignmentProcess'].angle_sigma_deg))
    lg_eff_nm = lg_nm / max(0.2, math.cos(theta))
    gate = procs['GateStackProcess']
    t_ox_nm = max(0.3, rng.normal(targets['t_ox_nm'],
                                  gate.tox_sigma_nm))
    k_ox = max(2.0, rng.normal(targets['k_ox'], gate.kox_sigma))
    vt0_v = targets['vt0_v'] + rng.normal(0.0, gate.vt_sigma_v)
    contact = procs['ContactFormationProcess']
    rc_ohm = max(lit_value('rq_half_ohm'),
                 contact.rc_median_ohm
                 * math.exp(rng.normal(0.0, contact.rc_sigma_ln)))
    eg = eg_ev(d_nm)
    cox = cox_gaa_f_per_m(t_ox_nm, d_nm, k_ox)
    cinv = cinv_f_per_m(cox, cqe_f_per_m(eg))
    sce = sce_parameters(lg_eff_nm, t_ox_nm, d_nm, k_ox, eg,
                         targets['efsd_ev'])
    return ({
        'equation_revision': targets['equation_revision'],
        'lg_m': lg_eff_nm * 1e-9,
        'cinv_f_per_m': cinv,
        'vxo_m_per_s': vxo_m_per_s(lg_eff_nm, d_nm),
        'mu_m2_per_vs': mu_cm2_per_vs(lg_eff_nm, d_nm) * 1e-4,
        'vt0_v': vt0_v, 'dvt_v': sce['dvt_v'],
        'dibl_v_per_v': sce['dibl_v_per_v'], 'n_ss': sce['n_ss'],
        'alpha': lit_value('alpha_vs'), 'beta': lit_value('beta_vs'),
        'phit_v': phit_v, 'rs_ohm': rc_ohm, 'rd_ohm': rc_ohm,
        'temperature_k': targets['temperature_k'],
        '_sampled': {'d_nm': d_nm, 'lg_eff_nm': lg_eff_nm,
                     't_ox_nm': t_ox_nm, 'k_ox': k_ox,
                     'vt0_v': vt0_v, 'rc_ohm': rc_ohm}},
        None)


def _quantiles(values):
    if not values:
        return None
    arr = np.array(values, dtype=float)
    return {'p05': float(np.quantile(arr, 0.05)),
            'p50': float(np.quantile(arr, 0.50)),
            'p95': float(np.quantile(arr, 0.95)),
            'mean': float(arr.mean()),
            'sigma': float(arr.std())}


#: fi-3: the Vg grid the stochastic envelope is sampled on (matches
#: cnt_device_viz SWEEP_STEP/SWEEP_MAX so the band overlays the
#: nominal curve point-for-point).
ENVELOPE_VG = [round(i * 0.02, 4) for i in range(31)]


def _score_population(manager, device, nominal_p, samples, vdd):
    """fi-3: score every functional sample with the fi-2 terms;
    keep the best/worst-case devices (score max/min) WITH their
    sampled process values and a per-term attribution against the
    nominal device — 'which distribution moved it'. Pure over the
    sample list."""
    from cntfet.cnt_scoring_seed import (
        CONCEPT_NAME, score_frame, score_from_frame,
    )
    nominal_frame = score_frame(
        lambda vg, vd: vs_terminal_current(vg, vd, nominal_p)['id_a'],
        nominal_p, device.temperature_k, {'vdd_v': vdd})
    nominal = score_from_frame(nominal_frame, manager)
    scored = []
    for params, metrics in samples:
        frame = score_frame(None, params, device.temperature_k,
                            {'vdd_v': vdd}, metrics=metrics)
        res = score_from_frame(frame, manager)
        scored.append((res['score'], params['_sampled'], res))
    if not scored:
        return {'concept': CONCEPT_NAME, 'nominal': nominal['score'],
                'refusal': 'no functional sample to score'}
    scored.sort(key=lambda s: s[0])
    per_term = {}
    for _s, _p, res in scored:
        for t in res['terms']:
            if t.get('found'):
                per_term.setdefault(t['term'], []).append(
                    t['normalized'])
    nominal_norm = {t['term']: t['normalized']
                    for t in nominal['terms'] if t.get('found')}

    def _case(entry):
        score, sampled, res = entry
        attribution = sorted(
            ({'term': t['term'], 'label': t['label'],
              'normalized': t['normalized'],
              'deltaVsNominal': round(
                  t['normalized'] - nominal_norm.get(t['term'], 0.0),
                  6)}
             for t in res['terms'] if t.get('found')),
            key=lambda a: abs(a['deltaVsNominal']), reverse=True)
        return {'score': score, 'sampled': sampled,
                'terms': res['terms'], 'attribution': attribution,
                'movedMostBy': attribution[0]['term']
                if attribution else None}

    return {
        'concept': CONCEPT_NAME,
        'nominal': nominal['score'],
        'quantiles': _quantiles([s[0] for s in scored]),
        'termSpread': {k: _quantiles(v) for k, v in per_term.items()},
        'best': _case(scored[-1]),
        'worst': _case(scored[0]),
        'scoredSamples': len(scored),
        'note': 'best/worst = score max/min over the FUNCTIONAL '
                'samples (dead tubes and criterion failures are the '
                'yield report, not a score); attribution = per-term '
                'normalized delta vs the nominal device, largest '
                'first',
    }


def _envelope(samples, vdd):
    """fi-3: Id(Vg) at Vd = vdd across the functional samples —
    min/max and p05/p95 per grid point (µA), the band drawn over the
    nominal transfer curve."""
    if not samples:
        return None
    cols = []
    for params, _m in samples:
        cols.append([vs_terminal_current(vg, vdd, params)['id_a'] * 1e6
                     for vg in ENVELOPE_VG])
    arr = np.array(cols, dtype=float)
    return {'vd_v': vdd, 'vgs': ENVELOPE_VG,
            'min': arr.min(axis=0).tolist(),
            'p05': np.quantile(arr, 0.05, axis=0).tolist(),
            'p50': np.quantile(arr, 0.50, axis=0).tolist(),
            'p95': np.quantile(arr, 0.95, axis=0).tolist(),
            'max': arr.max(axis=0).tolist(),
            'unit': 'uA', 'samples': len(cols)}


def monte_carlo(manager, device, sample_count=200, seed=1,
                criteria=None, result_factory=None, score=True):
    """The S3 act. Deterministic under `seed`; every kill and
    criterion violation counted; dominant limitation named.
    fi-3: `score=True` adds the per-sample fi-2 scores (best/worst
    case + attribution) and the Id(Vg) envelope."""
    if not getattr(device, 'derived_at', ''):
        return {'ok': False, 'error': 'device never derived — POST '
                                      '{"action": "derive"} first'}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    process_set = getattr(device, 'process_set', '')
    if not process_set:
        return {'ok': False,
                'refusal': 'device declares no process_set — bind '
                           'one (its distributions are the whole '
                           'point of S3)'}
    procs, refusal, priors = gather_process_set(
        manager, process_set,
        getattr(device, 'manufacturing_regime', ''))
    if refusal:
        return {'ok': False, 'refusal': refusal}
    criteria = {**DEFAULT_CRITERIA, **(criteria or {})}
    geo, gate = rows['geometry'], rows['gate_stack']
    transport = rows['transport']
    targets = {
        'lg_nm': geo.lg_nm, 't_ox_nm': gate.t_ox_nm,
        'k_ox': gate.k_ox, 'vt0_v': transport.vt0_v,
        'efsd_ev': transport.efsd_ev,
        'temperature_k': device.temperature_k,
        'equation_revision': transport.equation_revision,
    }
    phit = thermal_voltage_v(device.temperature_k)
    rng = np.random.default_rng(seed)
    kills = {}
    violations = {'on-off-ratio': 0, 'ion-floor': 0}
    metrics_pop = {'ion_a': [], 'ioff_a': [], 'on_off_ratio': [],
                   'ss_mv_per_dec': [], 'vt_cc_lin_v': [],
                   'gm_peak_s': [], 'rc_ohm': [], 'd_nm': []}
    functional = 0
    samples = []   # fi-3: (params, metrics) of every functional device
    vdd = criteria['vdd_v']
    for _ in range(sample_count):
        params, kill = _sample_device_params(rng, targets, procs,
                                             phit)
        if kill:
            kills[kill] = kills.get(kill, 0) + 1
            continue
        metric_spec = {'vdd_v': vdd}
        metrics = extract_metrics(
            lambda vg, vd, p=params:
                vs_terminal_current(vg, vd, p)['id_a'],
            metric_spec)
        ok = True
        if (metrics['on_off_ratio'] or 0.0) \
                < criteria['min_on_off_ratio']:
            violations['on-off-ratio'] += 1
            ok = False
        if metrics['ion_a'] < criteria['min_ion_a']:
            violations['ion-floor'] += 1
            ok = False
        if ok:
            functional += 1
            samples.append((params, metrics))
        for key in ('ion_a', 'ioff_a', 'on_off_ratio',
                    'ss_mv_per_dec', 'vt_cc_lin_v', 'gm_peak_s'):
            value = metrics.get(key)
            if value is not None:
                metrics_pop[key].append(value)
        metrics_pop['rc_ohm'].append(params['_sampled']['rc_ohm'])
        metrics_pop['d_nm'].append(params['_sampled']['d_nm'])
    dead = sum(kills.values())
    alive = sample_count - dead
    limitation_counts = {**kills, **{f'criterion:{k}': v
                                     for k, v in violations.items()
                                     if v}}
    dominant = (max(limitation_counts, key=limitation_counts.get)
                if limitation_counts else 'none')
    stamp = datetime.now(timezone.utc).isoformat()
    report = {
        'ok': True, 'device': device.name,
        'processSet': process_set, 'sampleCount': sample_count,
        'seed': seed, 'criteria': criteria,
        'yield': {
            'functional': functional,
            'functionalFraction': functional / sample_count,
            'aliveButFailing': alive - functional,
            'kills': kills, 'criterionViolations': violations},
        'population': {key: _quantiles(vals)
                       for key, vals in metrics_pop.items()},
        'dominantLimitation': dominant,
        'priorFlagged': priors,
        'honesty': 'distributions marked low-confidence are '
                   'engineering priors — this population is a '
                   'PRIOR population until line data replaces '
                   f'them ({len(priors)} flagged rows)',
    }
    if score:
        # fi-3: best/worst case BY SCORE from the stochastic
        # definitions + the Id(Vg) envelope; the nominal params come
        # from the same builder the device's curves use.
        from cntfet.custom.cnt_vs_model import build_vs_params
        nominal_p = build_vs_params(
            {'diameter_nm': rows['material'].diameter_nm,
             'eg_ev': rows['material'].eg_ev},
            {'lg_nm': geo.lg_nm},
            {'t_ox_nm': gate.t_ox_nm, 'k_ox': gate.k_ox},
            {'rc_ohm': rows['contact'].rc_ohm},
            {'vt0_v': transport.vt0_v, 'efsd_ev': transport.efsd_ev},
            device.temperature_k)
        report['score'] = _score_population(manager, device, nominal_p,
                                            samples, vdd)
        report['envelope'] = _envelope(samples, vdd)
        if report['score'].get('quantiles'):
            report['population']['score'] = report['score']['quantiles']
    if result_factory is None:
        from cntfet.cnt_process_basis import CNTFETMonteCarloRun
        result_factory = CNTFETMonteCarloRun
    row = result_factory(
        name=f'{device.name}-mc-{stamp[11:19].replace(":", "")}',
        device=device.name, process_set=process_set,
        sample_count=sample_count, seed=seed,
        inputs_json=json.dumps({'criteria': criteria,
                                'targets': targets,
                                'priorFlagged': priors}),
        yield_json=json.dumps(report['yield']),
        population_json=json.dumps(report['population']),
        dominant_limitation=dominant,
        verdict='population-recorded', ran_at=stamp,
        notes=report['honesty'], manager=manager)
    try:
        db = getattr(manager, 'db', None)
        if db is not None:
            db.saveInstanceInDB(row)
    except Exception:
        pass
    report['resultRow'] = row.name
    return report
