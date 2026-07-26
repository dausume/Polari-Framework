"""
@module pspp.sintering_engine

mtt-2 Part B (MTT2_SOLGEL_SINTERING_PLAN) — the CERAMIC SINTERING
engine, the genuinely-new one: MICROSTRUCTURE evolution (densification
+ grain growth), NOT molecular graph rewriting. Starts from the
analytic Master Sintering Curve (Su & Johnson 1996) — the cheapest,
data-calibratable, honest model — per the plan.

Two axes, both integrals of an Arrhenius rate over a firing schedule:

- WORK OF SINTERING  Θ(t,T) = ∫ (1/T) exp(−Q/RT) dt  — pure math from
  the schedule + one apparent activation energy Q. Always computable
  once Q is given; the isothermal hold has a closed form used as the
  engine's self-check.
- RELATIVE DENSITY  ρ = f(Θ) via the MASTER CURVE — this mapping is
  DATA (a DigitizedDataset ρ vs log10 Θ collapsed from real
  densification runs). Without a calibrated curve the engine returns Θ
  but REFUSES ρ. That split is the honesty: the integral is physics,
  the curve is measurement.
- GRAIN GROWTH  d^n − d0^n = ∫ K dt,  K = k0 exp(−Qg/RT)  (mean-field,
  Arrhenius K) — refuses without a cited (n, k0, Qg).

Invariant (pspp house rule, the I5 analog): no invented activation
energy, no invented master curve. Q / k0 / n / the ρ(Θ) curve all
arrive as CITED data; absent, the engine refuses and names the ask.

@consumers
  - pspp.sintering_structure (L2 descriptor plan)
  - pspp.pspp_api (/api/pspp/sinter/*)
  - pspp.selftest_sintering_engine
"""

import math

#: Gas constant (J/mol/K).
R_GAS = 8.314462618
#: Celsius -> Kelvin.
C_TO_K = 273.15

_ISOTHERMAL_NOTE = (
    'isothermal holds integrate in closed form; ramps by fine '
    'substeps (Simpson) — Θ carries no invented physics beyond the '
    'single apparent activation energy Q (Su & Johnson 1996)')


def _seg_duration_s(segment):
    minutes = segment.get('minutes')
    if minutes is None:
        return None
    try:
        return float(minutes) * 60.0
    except (TypeError, ValueError):
        return None


def _temps_k(segment):
    """(T0_K, T1_K) for a segment — hold is flat, ramp is linear.
    Returns (None, None) on a malformed segment."""
    if 'hold_c' in segment:
        try:
            t = float(segment['hold_c']) + C_TO_K
        except (TypeError, ValueError):
            return None, None
        return t, t
    if 'ramp_from_c' in segment and 'ramp_to_c' in segment:
        try:
            return (float(segment['ramp_from_c']) + C_TO_K,
                    float(segment['ramp_to_c']) + C_TO_K)
        except (TypeError, ValueError):
            return None, None
    return None, None


def _validate_schedule(schedule):
    """Every segment must be a hold or a ramp with a positive duration
    and above absolute zero. Returns (ok, refusal|None)."""
    if not schedule:
        return False, {
            'ok': False, 'refusal': 'empty firing schedule',
            'suggestion': 'pass segments like [{"hold_c": 1200, '
                          '"minutes": 120}] or {"ramp_from_c": 25, '
                          '"ramp_to_c": 1200, "minutes": 200}'}
    for i, seg in enumerate(schedule):
        t0, t1 = _temps_k(seg)
        dur = _seg_duration_s(seg)
        if t0 is None:
            return False, {
                'ok': False,
                'refusal': f'segment {i} is neither a hold (hold_c) '
                           'nor a ramp (ramp_from_c + ramp_to_c)',
                'suggestion': 'fix the segment shape'}
        if min(t0, t1) <= 0:
            return False, {
                'ok': False,
                'refusal': f'segment {i} temperature is at/below '
                           'absolute zero',
                'suggestion': 'temperatures are Celsius; check the row'}
        if dur is None or dur <= 0:
            return False, {
                'ok': False,
                'refusal': f'segment {i} has no positive duration '
                           '(minutes)',
                'suggestion': 'every segment needs minutes > 0'}
    return True, None


def _integrate_over_schedule(schedule, integrand, substeps=200):
    """∫ integrand(T_K) dt over the whole schedule, seconds. Holds are
    exact (constant integrand); ramps use composite Simpson over a
    linear T(t). integrand: (T_K)->float."""
    total = 0.0
    for seg in schedule:
        t0, t1 = _temps_k(seg)
        dur = _seg_duration_s(seg)
        if t0 == t1:
            total += integrand(t0) * dur
            continue
        n = substeps if substeps % 2 == 0 else substeps + 1
        h = dur / n
        acc = integrand(t0) + integrand(t1)
        for k in range(1, n):
            temp = t0 + (t1 - t0) * (k / n)
            acc += (4 if k % 2 else 2) * integrand(temp)
        total += acc * h / 3.0
    return total


def work_of_sintering(schedule, activation_energy_j_per_mol,
                      substeps=200):
    """Θ = ∫ (1/T) exp(−Q/RT) dt over the firing schedule (SI: seconds,
    Kelvin). Pure math once Q is given — REFUSES only on a bad schedule
    or a missing/nonphysical Q (no invented activation energy)."""
    ok, refusal = _validate_schedule(schedule)
    if not ok:
        return refusal
    q = activation_energy_j_per_mol
    if q is None:
        return {
            'ok': False,
            'refusal': 'no activation energy Q — Θ cannot be computed',
            'suggestion': 'supply a CITED apparent activation energy '
                          '(J/mol) fitted from densification runs at '
                          '>=2 heating rates; none is invented here'}
    try:
        q = float(q)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': f'activation energy {q!r} is not a number',
                'suggestion': 'Q in J/mol'}
    if q <= 0:
        return {'ok': False,
                'refusal': f'activation energy {q} must be positive',
                'suggestion': 'Q in J/mol, typically 1e5–1e6'}

    def integrand(t_k):
        return (1.0 / t_k) * math.exp(-q / (R_GAS * t_k))

    theta = _integrate_over_schedule(schedule, integrand, substeps)
    return {
        'ok': True,
        'theta': theta,
        'logTheta': math.log10(theta) if theta > 0 else None,
        'activationEnergyJPerMol': q,
        'assumptions': [
            _ISOTHERMAL_NOTE,
            'Θ units are s·K^-1 (seconds, Kelvin) — compare only to a '
            'master curve fitted in the same units',
        ],
    }


def relative_density(schedule, activation_energy_j_per_mol,
                     master_curve=None, substeps=200):
    """ρ from the firing schedule via the MASTER CURVE ρ(log10 Θ).
    Θ is computed here; the ρ(Θ) mapping is DATA — without a ready
    master-curve dataset this returns Θ but REFUSES ρ (the honest
    split). master_curve: a dataset dict (digitized_datasets.
    dataset_dict shape) with independent 'log10Theta', dependent
    'relativeDensity'."""
    work = work_of_sintering(schedule, activation_energy_j_per_mol,
                             substeps)
    if not work.get('ok'):
        return work
    if master_curve is None:
        return {
            'ok': False,
            'refusal': 'Θ computed, but ρ needs the calibrated master '
                       'curve ρ(log10 Θ) — none provided',
            'theta': work['theta'], 'logTheta': work['logTheta'],
            'suggestion': 'digitize a densification master curve '
                          '(relative density vs log10 Θ, collapsed '
                          'from >=2 heating-rate runs) as a '
                          'DigitizedDataset and pass it in'}
    from pspp.dataset_interpolation import read_dataset
    verdict = read_dataset(master_curve, {'log10Theta': work['logTheta']})
    if not verdict.get('ok'):
        verdict['theta'] = work['theta']
        verdict['logTheta'] = work['logTheta']
        return verdict
    rho = verdict['values'].get('relativeDensity')
    return {
        'ok': True,
        'relativeDensity': rho,
        'theta': work['theta'], 'logTheta': work['logTheta'],
        'band': verdict.get('band'),
        'evidence': verdict.get('evidence'),
        'assumptions': work['assumptions'] + list(
            verdict.get('assumptions') or []) + [
            'ρ read off the master curve at this Θ — the curve is the '
            'calibration; extrapolation past its range refuses'],
    }


def grain_size(schedule, d0_um, growth_exponent_n,
               k0_um_n_per_s, grain_activation_energy_j_per_mol,
               substeps=200):
    """Mean-field grain growth: d^n − d0^n = ∫ k0 exp(−Qg/RT) dt.
    Returns final grain size (µm). REFUSES without a cited (n, k0, Qg)
    — no invented kinetics. Isothermal hold has the closed form
    d^n = d0^n + k0 exp(−Qg/RT)·t used by the self-check."""
    ok, refusal = _validate_schedule(schedule)
    if not ok:
        return refusal
    for label, val in (('growth exponent n', growth_exponent_n),
                       ('rate prefactor k0', k0_um_n_per_s),
                       ('grain activation energy Qg',
                        grain_activation_energy_j_per_mol),
                       ('initial grain size d0', d0_um)):
        if val is None:
            return {
                'ok': False,
                'refusal': f'no {label} — grain growth cannot be '
                           'computed',
                'suggestion': 'supply CITED grain-growth kinetics '
                              '(n, k0, Qg) + an initial grain size; '
                              'none is invented here'}
    try:
        n = float(growth_exponent_n)
        k0 = float(k0_um_n_per_s)
        qg = float(grain_activation_energy_j_per_mol)
        d0 = float(d0_um)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'grain-growth parameters must be numbers',
                'suggestion': 'n, k0, Qg, d0 numeric'}
    if n <= 0 or k0 <= 0 or qg <= 0 or d0 < 0:
        return {'ok': False,
                'refusal': 'grain-growth parameters must be positive '
                           '(d0 >= 0)',
                'suggestion': 'check the cited values'}

    def integrand(t_k):
        return k0 * math.exp(-qg / (R_GAS * t_k))

    grown = _integrate_over_schedule(schedule, integrand, substeps)
    d_final = (d0 ** n + grown) ** (1.0 / n)
    return {
        'ok': True,
        'grainSizeUm': d_final,
        'initialGrainSizeUm': d0,
        'growthExponent': n,
        'assumptions': [
            _ISOTHERMAL_NOTE,
            'mean-field law d^n − d0^n = ∫K dt — no spatial grain '
            'distribution (phase-field/kMC is the deferred sinter-5)',
        ],
    }
