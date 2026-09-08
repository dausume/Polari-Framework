"""
@module sifet.custom.si_transport

fg-4 (FET_GENERIC_PAGES_PLAN): the SILICON scattering basis —
un-refuses GET /api/fet/device/{si}/transport (cnt_transport
dispatches Si rows here). Every number is DERIVED from the SAME
cited mobility chain the device's own VS parameters already use
(si_model.SI_LIT), or CITED beside it — nothing new is fitted.

Physics (each step cited):

  v_T = sqrt(2kT/(π m* m0))       non-degenerate unidirectional
                                  thermal velocity [LUN97]
                                  (degeneracy: a named gap)
  λ_i = μ_i · 2(kT/q)/v_T         the SAME [LUN97] relation
                                  cnt_transport uses, inverted
  Matthiessen decomposition of the cited mobility curve:
    μ_lattice  = ct_mu_max                     [CT67]/[SZE07]
    1/μ_imp    = 1/μ_CT(N) − 1/μ_lattice       [CT67] (the doping
                 term of the same fitted curve, N = the channel
                 doping ROW's concentration)
    1/μ_sr     = 1/μ_eff − 1/μ_bulk            [TAK94] surface
                 factor PRIOR (E_eff dependence a named gap)
  λ_eff by Matthiessen over the λ_i (algebraically = λ(μ_eff) —
  the selftest proves the identity), then
  T = λ_eff/(λ_eff + Lg), B = T/(2−T)          [LUN97]

Cross-checks REPORTED, never silently reconciled:
  - λ_eff beside SI_LIT lambda_mfp_si_nm ([LUN97] 10–20 nm near-
    source mfp) — different lengths (channel mfp vs kT-layer mfp),
    both stated;
  - the VS card's own ballisticity (si_model.ballisticity) beside
    Lundstrom B — two definitions, both stated (the CNT convention).

Honesty: the lattice term lumps acoustic + optical phonon branches
(that is what the [CT67] fit measures — stated, unlike the CNT
module where the optical branch is bias-gated); contact resistance
is ALREADY a series element of the VS card, so no contact
transmission factor is folded in (double counting — stated); there
are no Si aging priors, so no time series is invented.

@consumers
  - cntfet.cnt_transport_basis.transport_report (Si dispatch)
  - cnt_api GET /api/fet/device/{name}/transport (via the dispatch)
  - sifet.si_transport_selftest
"""

import math

from cntfet.cnt_transport_basis import (
    TRANSPORT_KNOBS, classify_regime, regime_defs, transmission,
)
from sifet.custom.si_device import get_row, resolve_components
from sifet.custom.si_model import (
    KB_J_PER_K, M0_KG, Q_C, effective_mobility, lit,
    mobility_caughey_thomas,
)

FIDELITY = ('F1 (VS_SI_MINIMAL + Lundstrom scattering theory): the '
            'mechanism mean free paths are DERIVED from the cited '
            'Caughey-Thomas/[TAK94] mobility chain via the [LUN97] '
            'relation — the same chain the derived device already '
            'uses; the surface term is a PRIOR')


def thermal_velocity_si_m_per_s(temperature_k, polarity):
    """v_T = sqrt(2kT/(π m*)) [LUN97], m* = the [SZE07] conductivity
    effective mass (non-degenerate — degeneracy is a named gap)."""
    m_star = lit('m_eff_n_over_m0' if polarity == 'n'
                 else 'm_eff_p_over_m0') * M0_KG
    return math.sqrt(2.0 * KB_J_PER_K * temperature_k
                     / (math.pi * m_star))


def lambda_from_mu_nm(mu_cm2_per_vs, temperature_k, polarity):
    """λ = μ · 2(kT/q)/v_T — the [LUN97] μ_app relation inverted;
    None for a non-positive μ (mechanism absent)."""
    if mu_cm2_per_vs is None or mu_cm2_per_vs <= 0.0:
        return None
    phit = KB_J_PER_K * temperature_k / Q_C
    v_t = thermal_velocity_si_m_per_s(temperature_k, polarity)
    return mu_cm2_per_vs * 1e-4 * 2.0 * phit / v_t * 1e9


def si_mechanisms(n_cm3, temperature_k, polarity):
    """The three contributors as payload entries (the cnt_transport
    mechanism shape), each λ derived from its cited μ term."""
    c = 'n' if polarity == 'n' else 'p'
    mu_lattice = lit(f'ct_{c}_mu_max')
    mu_ct = mobility_caughey_thomas(n_cm3, c)
    mu_bulk, mu_eff = effective_mobility(n_cm3, c)
    inv_imp = max(1.0 / mu_ct - 1.0 / mu_lattice, 0.0)
    mu_imp = (1.0 / inv_imp) if inv_imp > 0 else None
    inv_sr = max(1.0 / mu_eff - 1.0 / mu_bulk, 0.0)
    mu_sr = (1.0 / inv_sr) if inv_sr > 0 else None

    def entry(name, display, mu, formula, description, enforced,
              is_prior, why_extra=''):
        lam = lambda_from_mu_nm(mu, temperature_k, polarity)
        why = (f'μ = {mu:.4g} cm²/Vs → λ = μ·2(kT/q)/v_T = '
               f'{lam:.4g} nm' if lam is not None
               else 'term absent at this doping (μ contribution ~ 0)')
        return {
            'name': name, 'display_name': display,
            'lambda_nm': lam, 'mu_cm2_per_vs': mu,
            'active': lam is not None,
            'why': why + (f'; {why_extra}' if why_extra else ''),
            'lambda_formula': formula,
            'enforced': enforced,
            'time_profile': {'kind': 'none',
                             'note': 'no Si aging priors — a '
                                     'measured series is future '
                                     'work, not invented'},
            'is_prior': is_prior, 'prior_used': is_prior,
            'transmission_factor': None,
        }

    return [
        entry('lattice-phonon', 'Lattice (phonon) scattering',
              mu_lattice,
              f'μ_lattice = ct_{c}_mu_max [CT67]/[SZE07]; λ = '
              'μ·2(kT/q)/v_T [LUN97]',
              'The undoped-limit mobility of the cited Caughey-'
              'Thomas fit — acoustic + optical phonon branches '
              'LUMPED, because that is what the fit measures '
              '(stated; the CNT module gates its optical branch '
              'separately).',
              {'mu_app': 'sets the clean-silicon mobility ceiling',
               'ion': 'Ion = Ion_ballistic · B [LUN97]',
               'ss': 'none (SS is electrostatic)'},
              False),
        entry('ionized-impurity', 'Ionized-impurity scattering',
              mu_imp,
              f'1/μ_imp = 1/μ_CT(N) − 1/μ_lattice, N = '
              f'{n_cm3:.3g} cm⁻³ (the channel doping ROW) [CT67]',
              'The doping-dependent term of the same cited curve, '
              'split out by Matthiessen — heavier channel doping '
              'shortens this mfp.',
              {'mu_app': 'degrades mobility with channel doping',
               'vt': 'none here (doping sets Vt electrostatically '
                     'in the derive chain)'},
              False),
        entry('surface-roughness', 'Surface roughness + confinement',
              mu_sr,
              '1/μ_sr = 1/μ_eff − 1/μ_bulk, μ_eff = f·μ_bulk, '
              f'f = {lit(f"surface_mu_factor_{c}"):g} [TAK94] PRIOR',
              'The inversion layer rides the Si/dielectric '
              'interface; the [TAK94] universal-curve factor is a '
              'PRIOR (E_eff dependence not modeled — named gap).',
              {'mu_app': 'the dominant inversion-layer penalty',
               'ss': 'none modeled (interface traps are a separate '
                     'named gap)'},
              True),
    ]


def si_transport_report(manager, device, p, vgs=None, vds=None,
                        t_hours=0.0, horizon_hours=0, knobs=None):
    """The /transport payload for a SiliconMOSFET row — the same
    key shape cnt_transport serves, silicon-derived."""
    k = {**TRANSPORT_KNOBS, **(knobs or {})}
    if not getattr(device, 'derived_at', ''):
        return {'ok': False,
                'error': f'device "{device.name}" never derived — '
                         'POST {"action": "derive"} first'}
    rows, missing = resolve_components(manager, device)
    if missing:
        return {'ok': False,
                'error': f'missing component rows: {missing}'}
    ch = rows['channel_doping']
    n_cm3 = float(getattr(ch, 'concentration_cm3', 0.0) or 0.0)
    temperature_k = float(getattr(device, 'temperature_k', 300.0))
    polarity = getattr(device, 'polarity', 'n') or 'n'
    lg_nm = float(device.lg_nm)
    vdd = float(getattr(device, 'vdd_v', 1.0) or 1.0)
    vgs = vdd if vgs is None else vgs
    vds = vdd if vds is None else vds

    mechs = si_mechanisms(n_cm3, temperature_k, polarity)
    inv_sum = sum(1.0 / m['lambda_nm'] for m in mechs
                  if m['lambda_nm'])
    lambda_eff = (1.0 / inv_sum) if inv_sum > 0 else float('inf')
    for m in mechs:
        m['contribution'] = ((1.0 / m['lambda_nm']) / inv_sum
                             if m['lambda_nm'] and inv_sum > 0
                             else 0.0)
    t_ch = transmission(lambda_eff, lg_nm)
    b = t_ch / (2.0 - t_ch) if t_ch < 2.0 else 1.0
    _, mu_eff = effective_mobility(n_cm3,
                                   'n' if polarity == 'n' else 'p')
    defs = regime_defs(manager)
    frame = {'t_regime': t_ch, 'transmission': t_ch,
             'lambda_eff_nm': lambda_eff, 'lg_nm': lg_nm,
             't_ballistic': k['t_ballistic'], 't_quasi': k['t_quasi'],
             't_semi': k['t_semi']}
    regime, evaluations = classify_regime(frame, defs=defs)
    from sifet.custom.si_model import ballisticity
    active = [m for m in mechs if m['lambda_nm']]
    top = (max(active, key=lambda m: m['contribution'])['name']
           if active else None)
    lun_lo, lun_hi = 10.0, 20.0
    priors = sorted(m['name'] for m in mechs if m['prior_used'])
    return {
        'ok': True, 'device': device.name, 'fidelity': FIDELITY,
        'technology': 'silicon',
        'temperature_k': temperature_k,
        'knobs': {kk: k[kk] for kk in
                  ('t_ballistic', 't_quasi', 't_semi', 'regime_on')},
        'bias': {'vgs': vgs, 'vds': vds, 't_hours': t_hours,
                 'note': 'the mfp decomposition is bias-independent '
                         'at this fidelity (low-field mobilities; '
                         'E_eff and velocity saturation are named '
                         'gaps)'},
        'context': {'lg_nm': lg_nm, 'w_nm': float(device.w_nm),
                    'n_channel_cm3': n_cm3,
                    'channel_doping_row': getattr(ch, 'name', ''),
                    'dielectric_row': getattr(rows['dielectric'],
                                              'name', ''),
                    'polarity': polarity,
                    'temperature_k': temperature_k},
        'mechanisms': mechs,
        'topContributor': top,
        'lambda_eff_nm': lambda_eff,
        'lg_eff_nm': lg_nm,
        'transmission': t_ch,
        'contact_transmission': 1.0,
        'contact_note': ('Rc is ALREADY a series element of the VS '
                         'card (rc_ohm_um) — folding a contact '
                         'transmission in would double count; '
                         'stated, unlike the CNT RQ/2 factor'),
        'transmission_total': t_ch,
        'ballistic_efficiency': b,
        'vs_model_ballisticity': ballisticity(lg_nm),
        'ballisticity_note': (
            'two definitions, both stated: Lundstrom T = '
            'λ_eff/(λ_eff+Lg) with B = T/(2−T) over the FULL '
            'channel (ours, from the mobility decomposition) vs '
            'the VS card\'s own B = λ/(λ + f·Lg) over the kT '
            'LAYER (si_model.ballisticity, λ = lambda_mfp_si_nm) '
            '— different lengths, they need not agree'),
        'crossCheck': {
            'lambda_eff_nm': lambda_eff,
            'lun97_near_source_mfp_nm': [lun_lo, lun_hi],
            'lit_row': 'SI_LIT.lambda_mfp_si_nm',
            'consistent_scale': lun_lo / 3 <= lambda_eff
                                <= lun_hi * 3,
            'note': ('the [LUN97] 10–20 nm anchor is the NEAR-'
                     'SOURCE mfp; ours is the channel-average from '
                     'the mobility chain — same order expected, '
                     'not equality'),
        },
        'regime': {'name': regime, 'classified_on': k['regime_on'],
                   't_regime': t_ch, 'evaluations': evaluations},
        'regimes': defs,
        'enforced': {
            'ion_factor': b,
            'ion_formula': 'Ion = Ion_ballistic · B, B = T/(2−T) '
                           '[LUN97]',
            'mu_app_cm2_per_vs': mu_eff,
            'mu_formula': 'μ_eff = f_surface · μ_CT(N) '
                          '[CT67]/[TAK94] — λ_eff maps back to '
                          'exactly this μ via the [LUN97] relation '
                          '(identity, selftest-proven)',
            'ss_effect': 'none (SS is electrostatic)',
        },
        'timeSeries': [],
        'timeSeriesNote': ('no Si aging priors exist — an aging '
                           'series would be invented, so none is '
                           'served'),
        'priors_used': priors,
    }
