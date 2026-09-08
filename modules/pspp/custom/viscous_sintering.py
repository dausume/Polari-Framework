"""
@module pspp.custom.viscous_sintering

mtt-2 glass core, the VISCOUS-SINTERING variant of the Part B engine:
glass frit densifies by VISCOUS FLOW (surface tension against melt
viscosity), not solid-state diffusion — so the work integral swaps
exp(−Q/RT)/T for γ/(η(T)·r).

The same honest split as the Master Sintering Curve engine:

- REDUCED VISCOUS WORK  Λ(t,T) = ∫ γ/(η(T)·r) dt  (dimensionless) —
  pure math once γ (surface tension), r (particle radius) and the
  glass's viscosity curve are given. η(T) comes from the EXACT VFT
  fit through cited fixed points (pspp.custom.glass_refinement) — zero free
  parameters. Schedule temperatures above the fitted span REFUSE;
  below it the glass is rigid and contributes zero (stated).
- EARLY STAGE (Frenkel 1945): linear shrinkage y = (3/8)·Λ, so
  ρ = ρ_green/(1−y)³ under isotropic shrinkage — a CITED closed-form
  model, valid only to y ≈ 0.10. Past that the engine REFUSES and
  names the two ways forward (digitize a frit master curve ρ(log Λ),
  or measure a checkpoint and run the final stage).
- FINAL STAGE (Mackenzie & Shuttleworth 1949): from a MEASURED
  closed-pore checkpoint ρ₀ ≥ 0.9, 1−ρ = (1−ρ₀)·exp(−(3/2)·Λ_pore)
  with Λ_pore built on the measured pore radius. No measured
  checkpoint → refuses (the mid-stage gap between Frenkel validity
  and closed pores is a real model gap — Scherer's cylinder model or
  the master curve are the cited bridges, neither is invented here).
- MASTER CURVE  ρ(log10 Λ) as a DigitizedDataset (seeded provisional
  in glass_refinement, refusing until a real frit run is digitized) —
  when ready it covers all stages, exactly like ρ(log10 Θ) does for
  ceramics.

γ default: soda-lime melt surface tension ~0.30 N/m
(literature-approximate, Scholze 1991) — used only when the caller
passes none, and always named in the assumptions.

@consumers
  - pspp.pspp_api (POST /api/pspp/sinter/viscous)
  - pspp.viscous_sintering_selftest
"""

import math

from pspp.custom.glass_refinement import fit_vft
from pspp.custom.sintering_engine import (
    C_TO_K, _integrate_over_schedule, _validate_schedule,
)

#: Frenkel early-stage validity cap (linear shrinkage fraction).
FRENKEL_MAX_SHRINKAGE = 0.10
#: Mackenzie-Shuttleworth needs isolated (closed) pores.
MS_MIN_DENSITY = 0.9

#: Soda-lime melt surface tension — literature-approximate default,
#: only used when no γ is passed, always surfaced in assumptions.
DEFAULT_SURFACE_TENSION = {
    'value_n_per_m': 0.30,
    'status': 'literature-approximate',
    'source': 'Scholze, Glass — Nature, Structure and Properties '
              '(Springer 1991): soda-lime melt ~0.3 N/m, weakly '
              'temperature-dependent',
}

_RIGID_NOTE = ('schedule time below the viscosity fit\'s coldest '
               'point contributes ZERO viscous work (the glass is '
               'effectively rigid there) — conservative and stated, '
               'not hidden')


def _resolve_gamma(gamma_n_per_m):
    if gamma_n_per_m is None:
        d = DEFAULT_SURFACE_TENSION
        return d['value_n_per_m'], (
            f"γ defaulted to {d['value_n_per_m']} N/m "
            f"({d['status']}: {d['source']})")
    try:
        g = float(gamma_n_per_m)
    except (TypeError, ValueError):
        return None, f'surface tension {gamma_n_per_m!r} is not a number'
    if g <= 0:
        return None, f'surface tension {g} must be positive'
    return g, None


def viscous_work(schedule, particle_radius_um, gamma_n_per_m=None,
                 vft=None, points=None, substeps=200):
    """Λ = ∫ γ/(η(T)·r) dt over the firing schedule (dimensionless).
    Pure math once γ, r and the viscosity fit are given. REFUSES on a
    bad schedule, a missing/nonphysical r, or schedule temperatures
    above the fitted viscosity span (no invented high-T viscosity)."""
    ok, refusal = _validate_schedule(schedule)
    if not ok:
        return refusal
    if particle_radius_um is None:
        return {'ok': False,
                'refusal': 'no particle radius — viscous work scales '
                           'as 1/r and cannot be computed without it',
                'suggestion': 'supply the frit/powder particle radius '
                              'in µm (sieve or micrograph)'}
    try:
        r_um = float(particle_radius_um)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': f'particle radius {particle_radius_um!r} '
                           'is not a number',
                'suggestion': 'radius in µm'}
    if r_um <= 0:
        return {'ok': False,
                'refusal': f'particle radius {r_um} must be positive',
                'suggestion': 'radius in µm'}
    gamma, gamma_note = _resolve_gamma(gamma_n_per_m)
    if gamma is None:
        return {'ok': False, 'refusal': gamma_note,
                'suggestion': 'γ in N/m (soda-lime melt ~0.3)'}
    fit = vft if vft is not None else fit_vft(points)
    if not fit.get('ok'):
        return fit
    lo_c, hi_c = fit['validTempRangeC']
    # No invented viscosity ABOVE the fitted span — refuse the run.
    peak = None
    for seg in schedule:
        for key in ('hold_c', 'ramp_from_c', 'ramp_to_c'):
            if key in seg:
                try:
                    val = float(seg[key])
                except (TypeError, ValueError):
                    continue
                peak = val if peak is None else max(peak, val)
    if peak is not None and peak > hi_c:
        return {'ok': False,
                'refusal': f'schedule reaches {peak}C, above the '
                           f'viscosity fit\'s span (max {hi_c}C) — '
                           'no invented high-temperature viscosity',
                'suggestion': 'cite viscosity points covering the '
                              'peak, or cap the schedule'}
    r_m = r_um * 1e-6
    lo_k = lo_c + C_TO_K
    a, b, t0 = fit['A'], fit['B_K'], fit['T0_C'] + C_TO_K

    def integrand(t_k):
        if t_k < lo_k:
            return 0.0
        eta = 10.0 ** (a + b / (t_k - t0))
        return gamma / (eta * r_m)

    lam = _integrate_over_schedule(schedule, integrand, substeps)
    assumptions = [
        'Λ = ∫ γ/(η·r) dt with η(T) from the exact VFT fit through '
        'cited fixed points — no fitted/invented parameters',
        _RIGID_NOTE,
        'monosized spheres of radius r — a size distribution smears '
        'Λ (finer fraction densifies first)',
    ]
    if gamma_note:
        assumptions.append(gamma_note)
    return {
        'ok': True,
        'lambda': lam,
        'log10Lambda': math.log10(lam) if lam > 0 else None,
        'particleRadiusUm': r_um,
        'gammaNPerM': gamma,
        'assumptions': assumptions,
    }


def frenkel_density(lambda_value, green_density):
    """Early-stage ρ from Λ via Frenkel neck growth: y = (3/8)·Λ,
    ρ = ρ_green/(1−y)³. REFUSES past y = 0.10 (the model's cited
    validity) — the refusal names the two honest ways onward."""
    if green_density is None:
        return {'ok': False,
                'refusal': 'no green density — Frenkel densification '
                           'needs the starting packing fraction',
                'suggestion': 'measure the green compact (mass/'
                              'geometry); random-packed monosized '
                              'spheres run ~0.60-0.64, but measure, '
                              'don\'t assume'}
    try:
        rho_g = float(green_density)
        lam = float(lambda_value)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'green density and Λ must be numbers',
                'suggestion': 'ρ_green fraction of theoretical, Λ '
                              'from viscous_work'}
    if not 0.0 < rho_g < 1.0:
        return {'ok': False,
                'refusal': f'green density {rho_g} out of (0, 1)',
                'suggestion': 'fraction of theoretical'}
    if lam < 0:
        return {'ok': False, 'refusal': f'Λ {lam} negative',
                'suggestion': 'Λ from viscous_work'}
    y = 0.375 * lam
    if y > FRENKEL_MAX_SHRINKAGE:
        return {
            'ok': False,
            'refusal': f'Frenkel shrinkage y = {y:.3f} exceeds the '
                       f'model\'s early-stage validity '
                       f'(y <= {FRENKEL_MAX_SHRINKAGE}) — the '
                       'closed form does not extend here',
            'linearShrinkage': y,
            'suggestion': 'either digitize the glass-frit-viscous-'
                          'sintering-master-curve dataset (ρ vs '
                          'log10 Λ covers every stage), or measure a '
                          'closed-pore checkpoint (ρ >= 0.9 + pore '
                          'radius) and run the Mackenzie-Shuttleworth '
                          'final stage — the mid-stage bridge is '
                          'Scherer\'s model, not invented here'}
    rho = rho_g / (1.0 - y) ** 3
    return {
        'ok': True,
        'relativeDensity': min(rho, 1.0),
        'linearShrinkage': y,
        'greenDensity': rho_g,
        'stage': 'frenkel-early',
        'assumptions': [
            'Frenkel 1945 neck growth: y = (3/8)Λ, isotropic '
            'shrinkage ρ = ρ_green/(1−y)³ — valid only to y ≈ 0.10',
        ],
    }


def ms_final_stage(schedule, measured_density, pore_radius_um,
                   gamma_n_per_m=None, vft=None, points=None,
                   substeps=200):
    """Final-stage densification from a MEASURED closed-pore
    checkpoint (Mackenzie & Shuttleworth 1949):
    1−ρ = (1−ρ₀)·exp(−(3/2)·Λ_pore), Λ_pore = ∫ γ/(η·a₀) dt on the
    measured pore radius a₀. REFUSES below ρ₀ = 0.9 (the model needs
    isolated pores) or without a measured pore radius."""
    if measured_density is None or pore_radius_um is None:
        return {'ok': False,
                'refusal': 'the final stage starts from a MEASURED '
                           'checkpoint — need both the measured '
                           'density and the measured pore radius',
                'suggestion': 'dilatometry/Archimedes for ρ, '
                              'micrograph for pore radius; nothing '
                              'is assumed here'}
    try:
        rho0 = float(measured_density)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': f'measured density {measured_density!r} '
                           'is not a number',
                'suggestion': 'fraction of theoretical'}
    if not MS_MIN_DENSITY <= rho0 < 1.0:
        return {'ok': False,
                'refusal': f'measured density {rho0} outside '
                           f'[{MS_MIN_DENSITY}, 1) — Mackenzie-'
                           'Shuttleworth assumes isolated (closed) '
                           'pores',
                'suggestion': 'below ~0.9 pores are still connected; '
                              'use the master curve or Frenkel range '
                              'instead'}
    work = viscous_work(schedule, pore_radius_um,
                        gamma_n_per_m=gamma_n_per_m, vft=vft,
                        points=points, substeps=substeps)
    if not work.get('ok'):
        return work
    porosity = (1.0 - rho0) * math.exp(-1.5 * work['lambda'])
    return {
        'ok': True,
        'relativeDensity': 1.0 - porosity,
        'startDensity': rho0,
        'poreLambda': work['lambda'],
        'stage': 'mackenzie-shuttleworth-final',
        'assumptions': work['assumptions'] + [
            'Mackenzie & Shuttleworth 1949 closed-pore law on the '
            'MEASURED pore radius — the checkpoint is data, the '
            'decay is the cited model',
        ],
    }


def plan_viscous_structure(state_key, relative_density,
                           particle_radius_um=None,
                           theoretical_density_g_cm3=None):
    """The L2 structure rows a viscous-sintered (amorphous) body
    implies: an amorphous-matrix row + a pore-network row. No grain
    row — glass has no grains; that absence is the point. Nothing is
    persisted (plan-first, the gsp-4 seam applies them)."""
    if not state_key:
        return {'ok': False,
                'refusal': 'no state_key — a structure row must '
                           'attach to a MaterialState',
                'suggestion': "pass '<material>#<fire-checkpoint>'"}
    try:
        rho = float(relative_density)
    except (TypeError, ValueError):
        return {'ok': False,
                'refusal': 'relativeDensity must be a number',
                'suggestion': 'run the viscous engine first'}
    if not 0.0 < rho <= 1.0:
        return {'ok': False,
                'refusal': f'relativeDensity {rho} out of (0, 1]',
                'suggestion': 'fraction of theoretical'}
    porosity = 1.0 - rho
    core = {
        'totalPorosity': round(porosity, 6),
        'reactionExtent': 1.0,
        'moistureState': 'dry-fired',
        'phaseFractions': {'amorphous': 1.0},
    }
    # Bulk density only when the theoretical density is supplied — no
    # invented value (absence is honest; the descriptor is omitted).
    if theoretical_density_g_cm3 is not None:
        try:
            core['bulkDensity'] = round(
                float(theoretical_density_g_cm3) * rho, 6)
        except (TypeError, ValueError):
            pass
    lengths = {}
    if particle_radius_um:
        try:
            r_m = float(particle_radius_um) * 1e-6
            lengths = {'characteristic_length_min_m': round(r_m * 0.5,
                                                            12),
                       'characteristic_length_max_m': round(r_m * 2.0,
                                                            12)}
        except (TypeError, ValueError):
            lengths = {}
    matrix_row = {
        'name': f'{state_key}@L2-amorphous-matrix',
        'state_key': state_key,
        'scale_level': 2,
        'domain_type': 'amorphous-matrix',
        'representation_type': 'descriptor-summary',
        **lengths,
        'descriptors_json': {**core,
                             'relativeDensity': round(rho, 6)},
        'status': 'defined',
        'notes': 'viscous-flow densified glass matrix — amorphous by '
                 'construction (XRD sees a halo; devitrified fraction '
                 'would appear in phaseFractions)',
    }
    pore_row = {
        'name': f'{state_key}@L2-pore-network',
        'state_key': state_key,
        'scale_level': 2,
        'domain_type': 'capillary-pore',
        'representation_type': 'descriptor-summary',
        **({'characteristic_length_min_m':
                round(lengths['characteristic_length_min_m'] * 0.1,
                      12),
            'characteristic_length_max_m':
                lengths['characteristic_length_max_m']}
           if lengths else {}),
        'descriptors_json': dict(core),
        'status': 'defined',
        'notes': 'residual porosity from viscous sintering '
                 '(porosity = 1 − relative density; closed pores '
                 'near full density)',
    }
    return {
        'ok': True,
        'stateKey': state_key,
        'relativeDensity': round(rho, 6),
        'totalPorosity': round(porosity, 6),
        'proposedRows': [matrix_row, pore_row],
        'note': 'plan-first: rows are PROPOSED, the structure seam '
                'applies them — no grain-domain row because an '
                'amorphous body has no grains',
    }


def viscous_fire(schedule, particle_radius_um, gamma_n_per_m=None,
                 green_density=None, master_curve=None, measured=None,
                 vft=None, points=None, state_key=None, substeps=200):
    """One viscous firing, every piece honest in place:
    - Λ always (given γ, r, viscosity fit);
    - ρ via the master curve when one is ready, else Frenkel while
      valid, else the refusal that names the asks;
    - the Mackenzie-Shuttleworth final stage when a measured
      closed-pore checkpoint {density, poreRadiusUm} is given;
    - the amorphous L2 structure plan when a ρ exists + state_key."""
    out = {'ok': True}
    work = viscous_work(schedule, particle_radius_um,
                        gamma_n_per_m=gamma_n_per_m, vft=vft,
                        points=points, substeps=substeps)
    out['work'] = work
    if not work.get('ok'):
        out['ok'] = False
        return out
    if master_curve is not None:
        from pspp.custom.dataset_interpolation import read_dataset
        if work['log10Lambda'] is None:
            out['density'] = {
                'ok': False,
                'refusal': 'Λ is zero (no time above the rigid '
                           'floor) — nothing to read off the master '
                           'curve',
                'suggestion': 'the schedule never reaches viscous '
                              'temperatures'}
            return out
        verdict = read_dataset(
            master_curve, {'log10Lambda': work['log10Lambda']})
        if verdict.get('ok'):
            out['density'] = {
                'ok': True,
                'relativeDensity':
                    verdict['values'].get('relativeDensity'),
                'stage': 'master-curve',
                'band': verdict.get('band'),
                'evidence': verdict.get('evidence')}
        else:
            verdict['log10Lambda'] = work['log10Lambda']
            out['density'] = verdict
    else:
        out['density'] = frenkel_density(work['lambda'],
                                         green_density)
    if measured:
        out['finalStage'] = ms_final_stage(
            schedule, measured.get('density'),
            measured.get('poreRadiusUm'),
            gamma_n_per_m=gamma_n_per_m, vft=vft, points=points,
            substeps=substeps)
    rho_source = out.get('finalStage') \
        if out.get('finalStage', {}).get('ok') else out['density']
    if state_key and rho_source.get('ok'):
        out['structurePlan'] = plan_viscous_structure(
            state_key, rho_source['relativeDensity'],
            particle_radius_um=particle_radius_um)
    return out
