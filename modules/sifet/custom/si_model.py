"""
@module sifet.custom.si_model

fp-2: silicon MOSFET physics -> the virtual-source parameter dict
`p` that cntfet.custom.cnt_vs_model.vs_terminal_current consumes. The VS
model IS a silicon MOSFET model ([KHA09] was written for silicon),
so the silicon device only needs the PARAMETER builder — every
downstream fv/fi surface (states, regimes, metrics, scoring,
validity, characteristics, compare) then works unchanged.

Equation set (revision sifet-vs-si-r1; VS core = cntfet revision):
  phi_F    = phit ln(N/ni)                               [SZE07] 1.4
  x_dmax   = sqrt(2 eps_si 2phi_F / (q N))               [SZE07] 6.2
  Vt (n)   = Vfb + 2phi_F + sqrt(2 q eps_si N 2phi_F)/Cox
  Vt (p)   = Vfb - 2phi_F - sqrt(2 q eps_si N 2phi_F)/Cox
                                                         [SZE07] eq.6.28
  Cox      = k eps0 / t_ox  (planar, per area); fin/GAA per
             effective width W_eff = n_fins (2 H_fin + W_fin)
  Cdep     = eps_si / x_d  (x_d capped at the half body for thin
             bodies -> fully depleted -> Cdep = 0)      [SZE07] 6.2
  n_ss     = (1 + Cdep/Cox) / (1 - e^-eta)   body factor [SZE07]
             eq.6.63 times the SAME SCE form as cnt_bandstructure.
             sce_parameters ([VS1] eq.(8))
  mu       = Caughey-Thomas  mu_min + (mu_max - mu_min)/
             (1 + (N/N_ref)^alpha)                       [CT67]/[SZE07]
             times a surface (inversion-layer) factor prior [TAK94]
  v_xo     = B v_T,  B = lambda/(lambda + l_kT),  l_kT = f Lg
                                                         [LUN97]/[KHA09]
  lambda   planar: sqrt(eps_si/eps_ox t_ox x_d)          [TN09] 3.2
           finfet (double-gate): Suzuki/Taur DG form     [SUZ93]
           gaa (cylinder): Auth-Plummer form             [AP98]
  SCE      eta = pi Lg/(2 lambda); DIBL = e^-eta [V/V];
           dVt roll-off = 2phi_F e^-eta.  Exponential form as in
           [VS1] eq.(8)/[TN09] 3.2.1 (stated: the pi/2 prefactor
           is the Taur-Ning definition of lambda; the CNT module's
           eta = Lg/(2 lambda) uses the [VS1] eq.(7) definition).
  Id       = cntfet.custom.cnt_vs_model.vs_terminal_current (REUSED)

Width normalisation (the 'per tube' -> 'per device' mapping):
  cnt: Cinv [F/m] along the TUBE length, Qxo [C/m], Id = Qxo v_xo.
  si : Cinv_area [F/m^2] x W [m] = Cinv [F/m] along the CHANNEL,
       Qxo [C/m], Id = Qxo v_xo  [A for the whole device width].
       A device row with w_nm = 1000 therefore reports A per um of
       width; rs/rd = rc_ohm_um / W_um (per-terminal).

Refusals (see si_device.capability): no gate-leakage/tunnelling
model (sol-gel leakage is a PRIOR carried on the dielectric row and
never enters Id), no GIDL, no interface-trap SS degradation beyond
the body factor, no quantum-confinement Vt shift, no strain.

@consumers
  - sifet.custom.si_device (derive + device_model adaptor)
  - sifet.sifet_selftest
"""

import math

from cntfet.custom.cnt_constants import (
    EPS0_F_PER_M, KB_J_PER_K, Q_C, thermal_voltage_v,
)
from cntfet.custom.cnt_vs_model import vs_terminal_current

SI_EQUATION_REVISION = 'sifet-vs-si-r1'

# ---- citations (cnt_citations TAG_CITATIONS style) ------------------
SI_CITATIONS = {
    '[SZE07]': {'citation': 'S. M. Sze, K. K. Ng, "Physics of '
                'Semiconductor Devices", 3rd ed., Wiley (2007) — '
                'Ch.1 (ni, Eg, mobility vs doping), Ch.6 (MOSFET: '
                'phi_F, depletion width, Vt eq.6.28, body factor)',
                'doi': '10.1002/0470068329'},
    '[KHA09]': {'citation': 'A. Khakifirooz, O. M. Nayfeh, D. A. '
                'Antoniadis, "A Simple Semiempirical Short-Channel '
                'MOSFET Current-Voltage Model Continuous Across All '
                'Regions of Operation and Employing Only Physical '
                'Parameters", IEEE TED 56(8):1674-1680 (2009)',
                'doi': '10.1109/TED.2009.2024022'},
    '[CT67]': {'citation': 'D. M. Caughey, R. E. Thomas, "Carrier '
               'mobilities in silicon empirically related to doping '
               'and field", Proc. IEEE 55(12):2192-2193 (1967)',
               'doi': '10.1109/PROC.1967.6123'},
    '[TN09]': {'citation': 'Y. Taur, T. H. Ning, "Fundamentals of '
               'Modern VLSI Devices", 2nd ed., Cambridge (2009) — '
               'Sec.3.2 short-channel effects / scale length, '
               'Sec.3.1 body-effect coefficient',
               'doi': '10.1017/CBO9781139195065'},
    '[LUN97]': {'citation': 'M. Lundstrom, "Elementary Scattering '
                'Theory of the Si MOSFET", IEEE EDL 18(7):361-363 '
                '(1997) — B = lambda/(lambda + l), l = kT-layer',
                'doi': '10.1109/55.596937'},
    '[TAK94]': {'citation': 'S. Takagi, A. Toriumi, M. Iwase, H. '
                'Tango, "On the universality of inversion layer '
                'mobility in Si MOSFETs: Part I", IEEE TED '
                '41(12):2357-2362 (1994)',
                'doi': '10.1109/16.337449'},
    '[SUZ93]': {'citation': 'K. Suzuki, T. Tanaka, Y. Tosaka, H. '
                'Horie, Y. Arimoto, "Scaling theory for double-gate '
                'SOI MOSFETs", IEEE TED 40(12):2326-2329 (1993)',
                'doi': '10.1109/16.249482'},
    '[AP98]': {'citation': 'C. P. Auth, J. D. Plummer, "Scaling '
               'theory for cylindrical, fully-depleted, '
               'surrounding-gate MOSFETs", IEEE EDL 18(2):74-76 '
               '(1997)', 'doi': '10.1109/55.553049'},
    '[BS90]': {'citation': 'C. J. Brinker, G. W. Scherer, "Sol-Gel '
               'Science: The Physics and Chemistry of Sol-Gel '
               'Processing", Academic Press (1990) — hydrolysis/'
               'condensation of alkoxides (TEOS), film densification '
               'on anneal', 'isbn': '978-0-12-134970-7'},
    '[SG-HFO2]': {'citation': 'Open-literature sol-gel HfO2 gate '
                  'dielectric for thin-film transistors (solution-'
                  'processed high-k, spin-coated Hf-alkoxide/'
                  'HfCl4 precursor, annealed 300-500 C): k ~ 12-20, '
                  'leakage 1e-7..1e-5 A/cm^2 at 1-2 MV/cm, '
                  'breakdown 2-5 MV/cm. E.g. J. Ko et al. / '
                  'Y.-H. Kim et al., solution-processed HfO2 '
                  'dielectrics for oxide TFTs',
                  'doi': 'citation to be verified',
                  'note': 'PRIOR bucket (plan §2 decision 4): '
                          'values are ranges from the open TFT '
                          'literature, replaced by a measured row '
                          'when one exists'},
    '[SG-SIO2]': {'citation': 'Open-literature sol-gel SiO2 (TEOS) '
                  'spin-on dielectric for TFTs: k ~ 3.5-4.2, '
                  'density 85-95% of thermal oxide after 400-600 C '
                  'anneal, leakage 1e-8..1e-6 A/cm^2 at 1 MV/cm',
                  'doi': 'citation to be verified',
                  'note': 'PRIOR bucket; [BS90] for the chemistry'},
}

# ---- physical constants ------------------------------------------
M0_KG = 9.1093837015e-31


def _rec(value, unit, role, source, confidence, notes=''):
    return {'value': value, 'unit': unit, 'role': role,
            'source': source, 'confidence': confidence,
            'notes': notes}


SI_LIT = {
    'ni_300k_cm3': _rec(1.0e10, 'cm^-3', 'physical',
                        '[SZE07] Sec.1.4: ni(300 K) ~ 9.65e9 '
                        '(rounded 1e10 in Ch.6 examples)', 'high',
                        'T scaling ni(T) = ni0 (T/300)^1.5 '
                        'exp(-Eg/2k (1/T - 1/300)) applied in '
                        'intrinsic_density_cm3'),
    'eg_si_ev': _rec(1.12, 'eV', 'physical',
                     '[SZE07] Sec.1.4: Eg(300 K) = 1.12 eV', 'high'),
    'eps_si_rel': _rec(11.7, '1', 'physical',
                       '[SZE07] Appendix G: eps_Si = 11.7 (11.9 in '
                       'some tables)', 'high'),
    'eps_sio2_rel': _rec(3.9, '1', 'physical',
                         '[SZE07] Appendix G: thermal SiO2 k = 3.9',
                         'high'),
    'chi_si_ev': _rec(4.05, 'eV', 'physical',
                      '[SZE07] Sec.1.4: electron affinity 4.05 eV',
                      'high', 'used only to explain Vfb priors'),
    'm_eff_n_over_m0': _rec(0.26, 'm0', 'physical',
                            '[SZE07] Sec.1.5: conductivity effective '
                            'mass electrons 0.26 m0', 'high'),
    'm_eff_p_over_m0': _rec(0.39, 'm0', 'physical',
                            '[SZE07] Sec.1.5: conductivity effective '
                            'mass holes 0.39 m0', 'high'),
    'v_sat_m_per_s': _rec(1.0e5, 'm/s', 'physical',
                          '[SZE07] Sec.1.5.1: saturation velocity '
                          '~1e7 cm/s (electrons and holes, 300 K)',
                          'high'),
    'v_t_inj_m_per_s': _rec(1.2e5, 'm/s', 'compact-model',
                            '[LUN97]/[KHA09]: unidirectional thermal '
                            'injection velocity in the Si inversion '
                            'layer ~1.2e7 cm/s (degenerate 2DEG); '
                            '[KHA09] fits v_xo 1.0-1.4e7 cm/s at '
                            '32-45 nm nodes', 'medium'),
    'lambda_mfp_si_nm': _rec(15.0, 'nm', 'compact-model',
                             '[LUN97]: near-source backscattering '
                             'mean free path 10-20 nm in the Si '
                             'inversion layer at 300 K (midpoint)',
                             'low', 'the ballisticity B = '
                             'lambda/(lambda + l)'),
    'kt_layer_fraction': _rec(0.1, '1', 'compact-model',
                              '[LUN97]: the critical (kT) layer l is '
                              'the channel length over which the '
                              'potential drops kT/q near the '
                              'virtual source — a small fraction of '
                              'Lg; f = 0.1 chosen so v_xo(90 nm) ~ '
                              '0.75e7 cm/s, v_xo(35 nm) ~ 1.0e7 '
                              'cm/s, matching the [KHA09] extraction '
                              'trend', 'low',
                              'PRIOR: with l = Lg the VS Vdsat = '
                              'v_xo Lg/mu closes at ~20 mV for a '
                              '90 nm device — physically wrong; '
                              'the kT-layer form is the [LUN97] '
                              'statement'),
    # Caughey-Thomas parameter sets ([CT67] form; [SZE07] Sec.1.5
    # values for 300 K, Arora/Masetti-style fit quoted by Sze & Ng).
    'ct_n_mu_min': _rec(68.5, 'cm^2/(V s)', 'compact-model',
                        '[SZE07] Sec.1.5 / [CT67] electrons', 'medium'),
    'ct_n_mu_max': _rec(1414.0, 'cm^2/(V s)', 'compact-model',
                        '[SZE07] Sec.1.5 / [CT67] electrons', 'medium'),
    'ct_n_n_ref_cm3': _rec(9.2e16, 'cm^-3', 'compact-model',
                           '[SZE07] Sec.1.5 / [CT67] electrons',
                           'medium'),
    'ct_n_alpha': _rec(0.711, '1', 'compact-model',
                       '[SZE07] Sec.1.5 / [CT67] electrons', 'medium'),
    'ct_p_mu_min': _rec(44.9, 'cm^2/(V s)', 'compact-model',
                        '[SZE07] Sec.1.5 / [CT67] holes', 'medium'),
    'ct_p_mu_max': _rec(470.5, 'cm^2/(V s)', 'compact-model',
                        '[SZE07] Sec.1.5 / [CT67] holes', 'medium'),
    'ct_p_n_ref_cm3': _rec(2.23e17, 'cm^-3', 'compact-model',
                           '[SZE07] Sec.1.5 / [CT67] holes', 'medium'),
    'ct_p_alpha': _rec(0.719, '1', 'compact-model',
                       '[SZE07] Sec.1.5 / [CT67] holes', 'medium'),
    'surface_mu_factor_n': _rec(0.40, '1', 'compact-model',
                                '[TAK94]: universal inversion-layer '
                                'mobility ~300-400 cm^2/Vs at E_eff '
                                '~0.7 MV/cm vs ~800 bulk at 1e17 -> '
                                'ratio ~0.4', 'low',
                                'PRIOR — E_eff dependence not '
                                'modeled'),
    'surface_mu_factor_p': _rec(0.35, '1', 'compact-model',
                                '[TAK94] Part I holes: ~100-130 '
                                'cm^2/Vs at E_eff ~0.7 MV/cm', 'low',
                                'PRIOR'),
    'cinv_over_cox': _rec(0.90, '1', 'compact-model',
                          '[KHA09] Sec.II: Cinv is the effective '
                          'strong-inversion gate capacitance, a few '
                          'to ~10 % below Cox (inversion-layer '
                          'thickness / gate depletion)', 'low',
                          'PRIOR'),
    'alpha_vs': _rec(3.5, '1', 'compact-model',
                     '[KHA09] alpha = 3.5 (Ff transition width)',
                     'medium'),
    'beta_vs': _rec(1.8, '1', 'compact-model',
                    '[KHA09] beta = 1.8 (Fsat knee; 1.8 n / 1.6 p)',
                    'medium'),
    'kT_over_q_300k_v': _rec(KB_J_PER_K * 300.0 / Q_C, 'V', 'derived',
                             'kT/q at 300 K (exact constants)', 'high'),
}


def lit(key):
    return SI_LIT[key]['value']


# ---- semiconductor basics -----------------------------------------
def intrinsic_density_cm3(temperature_k):
    """ni(T) = ni(300) (T/300)^1.5 exp(-(Eg/2k)(1/T - 1/300))
    [SZE07] Sec.1.4 (Eg held at its 300 K value — stated)."""
    eg_j = lit('eg_si_ev') * Q_C
    t0 = 300.0
    return (lit('ni_300k_cm3') * (temperature_k / t0) ** 1.5
            * math.exp(-(eg_j / (2.0 * KB_J_PER_K))
                       * (1.0 / temperature_k - 1.0 / t0)))


def fermi_potential(n_cm3, temperature_k):
    """phi_F = (kT/q) ln(N/ni)  [V], > 0 for either dopant type
    (the sign enters through the polarity in threshold_voltage)."""
    if n_cm3 <= 0.0:
        return 0.0
    return (thermal_voltage_v(temperature_k)
            * math.log(n_cm3 / intrinsic_density_cm3(temperature_k)))


def eps_si():
    return lit('eps_si_rel') * EPS0_F_PER_M


def depletion_width_max_m(n_cm3, temperature_k):
    """x_dmax = sqrt(2 eps_si (2 phi_F)/(q N))  [SZE07] eq.6.14."""
    n_m3 = n_cm3 * 1e6
    if n_m3 <= 0.0:
        return float('inf')
    return math.sqrt(2.0 * eps_si() * 2.0
                     * fermi_potential(n_cm3, temperature_k)
                     / (Q_C * n_m3))


def cox_planar(t_ox_nm, k_rel):
    """Planar oxide capacitance per AREA [F/m^2] = k eps0/t_ox."""
    return k_rel * EPS0_F_PER_M / (t_ox_nm * 1e-9)


def cox_fin(t_ox_nm, k_rel, fin_height_nm, fin_width_nm, n_fins,
            gate_all_around=False):
    """Fin/GAA oxide capacitance: per-area Cox is the same
    parallel-plate value (t_ox << fin dims); what changes is the
    EFFECTIVE WIDTH the gate wraps: W_eff = n_fins (2 H + W) for a
    tri-gate fin, n_fins (2 H + 2 W) for a GAA nanosheet perimeter.
    Returns (cox_area_f_per_m2, w_eff_m)."""
    cox = cox_planar(t_ox_nm, k_rel)
    perim_nm = (2.0 * fin_height_nm + 2.0 * fin_width_nm
                if gate_all_around
                else 2.0 * fin_height_nm + fin_width_nm)
    return cox, n_fins * perim_nm * 1e-9


def cdep(n_cm3, temperature_k, body_half_width_nm=None):
    """Depletion capacitance per AREA [F/m^2] = eps_si/x_dmax
    ([SZE07] Sec.6.2). Thin bodies (fin/GAA) whose half-width is
    below x_dmax are FULLY DEPLETED: the depletion charge is fixed
    and no longer responds to the surface potential, so Cdep -> 0
    (stated approximation: no back-gate coupling term)."""
    xd = depletion_width_max_m(n_cm3, temperature_k)
    if body_half_width_nm is not None and xd > body_half_width_nm * 1e-9:
        return 0.0
    return eps_si() / xd if xd > 0 else 0.0


def body_factor_n_ss(cdep_f_per_m2, cox_f_per_m2):
    """n = 1 + Cdep/Cox  [SZE07] eq.6.63 (ideal interface)."""
    return 1.0 + cdep_f_per_m2 / cox_f_per_m2


def depletion_charge_per_area(n_cm3, temperature_k,
                              body_half_width_nm=None):
    """|Q_dep| = sqrt(2 q eps_si N 2phi_F) (bulk) or q N (W/2)
    when fully depleted."""
    n_m3 = n_cm3 * 1e6
    xd = depletion_width_max_m(n_cm3, temperature_k)
    if body_half_width_nm is not None and xd > body_half_width_nm * 1e-9:
        return Q_C * n_m3 * body_half_width_nm * 1e-9
    return math.sqrt(2.0 * Q_C * eps_si() * n_m3 * 2.0
                     * fermi_potential(n_cm3, temperature_k))


def threshold_voltage(vfb_v, phi_f_v, cox_f_per_m2, n_cm3,
                      temperature_k, polarity='n',
                      body_half_width_nm=None):
    """Bulk MOSFET threshold [SZE07] eq.6.28:
       n: Vt = Vfb + 2phi_F + sqrt(2 q eps_si N_A 2phi_F)/Cox
       p: Vt = Vfb - 2phi_F - sqrt(2 q eps_si N_D 2phi_F)/Cox
    phi_f_v is the (positive) Fermi potential of the CHANNEL
    doping; Vfb is a PRIOR on the device row."""
    qdep = depletion_charge_per_area(n_cm3, temperature_k,
                                     body_half_width_nm)
    if polarity == 'p':
        return vfb_v - 2.0 * phi_f_v - qdep / cox_f_per_m2
    return vfb_v + 2.0 * phi_f_v + qdep / cox_f_per_m2


# ---- transport -----------------------------------------------------
def mobility_caughey_thomas(n_cm3, carrier_type):
    """Bulk low-field mobility vs total doping [CT67] form with the
    [SZE07] 300 K parameter set: mu = mu_min + (mu_max - mu_min)/
    (1 + (N/N_ref)^alpha)  [cm^2/(V s)]. carrier_type 'n' | 'p'."""
    c = 'n' if carrier_type == 'n' else 'p'
    mu_min, mu_max = lit(f'ct_{c}_mu_min'), lit(f'ct_{c}_mu_max')
    n_ref, alpha = lit(f'ct_{c}_n_ref_cm3'), lit(f'ct_{c}_alpha')
    return mu_min + (mu_max - mu_min) / (1.0 + (n_cm3 / n_ref) ** alpha)


def effective_mobility(n_cm3, carrier_type):
    """Inversion-layer effective mobility = Caughey-Thomas bulk value
    times the [TAK94] surface factor prior (E_eff dependence is a
    named gap). Returns (mu_bulk, mu_eff) in cm^2/(V s)."""
    mu_bulk = mobility_caughey_thomas(n_cm3, carrier_type)
    factor = lit('surface_mu_factor_n' if carrier_type == 'n'
                 else 'surface_mu_factor_p')
    return mu_bulk, mu_bulk * factor


def ballisticity(lg_nm, lambda_nm=None, kt_fraction=None):
    """B = lambda/(lambda + l_kT), l_kT = f Lg  [LUN97]."""
    lam = lit('lambda_mfp_si_nm') if lambda_nm is None else lambda_nm
    f = lit('kt_layer_fraction') if kt_fraction is None else kt_fraction
    return lam / (lam + f * lg_nm)


def vxo_si(lg_nm, ballisticity_value=None):
    """Virtual-source injection velocity v_xo = B v_T [m/s]
    ([LUN97] backscattering; [KHA09] uses v_xo as the fitted
    parameter — here it is DERIVED from the mean-free-path prior)."""
    b = ballisticity(lg_nm) if ballisticity_value is None \
        else ballisticity_value
    return b * lit('v_t_inj_m_per_s')


# ---- electrostatics: scale length per shape --------------------------
def scale_length(shape_kind, t_ox_nm, k_rel, x_dep_nm=None,
                 body_width_nm=None):
    """Electrostatic scale length lambda [nm] per shape:
       planar-bulk / soi : lambda = sqrt((eps_si/eps_ox) t_ox x_d)
                           ([TN09] Sec.3.2.1 leading term; soi uses
                           the body thickness as x_d)
       finfet (double-gate): lambda = sqrt((eps_si/(2 eps_ox)) t_si
                           t_ox (1 + eps_ox t_si/(4 eps_si t_ox)))
                           [SUZ93] eq.(10)
       gaa-nanosheet (cylinder, radius r = W/2):
                           lambda = sqrt((2 eps_si r^2 ln(1 + t_ox/r)
                           + eps_ox r^2)/(4 eps_ox))     [AP98] eq.(6)
    """
    e_si, e_ox = lit('eps_si_rel'), k_rel
    if shape_kind in ('planar-bulk', 'soi'):
        xd = x_dep_nm if shape_kind == 'planar-bulk' else body_width_nm
        return math.sqrt((e_si / e_ox) * t_ox_nm * xd)
    if shape_kind == 'finfet':
        t_si = body_width_nm
        return math.sqrt((e_si / (2.0 * e_ox)) * t_si * t_ox_nm
                         * (1.0 + e_ox * t_si / (4.0 * e_si * t_ox_nm)))
    if shape_kind == 'gaa-nanosheet':
        r = body_width_nm / 2.0
        return math.sqrt((2.0 * e_si * r * r * math.log(1.0 + t_ox_nm / r)
                          + e_ox * r * r) / (4.0 * e_ox))
    raise ValueError(f'unknown shape kind {shape_kind!r}')


def sce(lg_nm, lambda_nm, phi_f_v):
    """Short-channel parameters in the SAME exponential form as
    cntfet.custom.cnt_bandstructure.sce_parameters ([VS1] eq.(8)):
       eta = pi Lg/(2 lambda)   ([TN09] lambda definition)
       DIBL = e^-eta  [V/V];  dVt roll-off = 2 phi_F e^-eta  [V];
       n_ss SCE factor = 1/(1 - e^-eta) (multiplies the body factor)."""
    eta = math.pi * lg_nm / (2.0 * lambda_nm)
    ex = math.exp(-eta)
    return {'eta': eta, 'dibl_v_per_v': ex,
            'dvt_v': 2.0 * phi_f_v * ex,
            'n_ss_sce_factor': 1.0 / (1.0 - ex),
            'lambda_nm': lambda_nm}


# ---- the VS parameter builder ------------------------------------
def _body_half_width(shape):
    if shape['kind'] in ('finfet', 'gaa-nanosheet'):
        return shape['fin_width_nm'] / 2.0
    if shape['kind'] == 'soi':
        return shape['channel_width_nm'] / 2.0
    return None


def build_si_vs_params(shape, channel_doping, sd_doping, dielectric,
                       device, temperature_k):
    """Assemble the VS `p` dict from plain dicts of the rows
    (objects in, plain params out — the cnt_vs_model.build_vs_params
    shape). Keys the VS core reads are IDENTICAL to the CNT case;
    extra 'si_*' keys carry the silicon derivation for stamping.

    shape:          kind, channel_width_nm, fin_height_nm,
                    fin_width_nm, n_fins, gate_all_around
    channel_doping: dopant_type, concentration_cm3, activation_fraction
    sd_doping:      concentration_cm3 (contact/S-D — Rc prior only)
    dielectric:     thickness_nm, k_rel
    device:         polarity, lg_nm, w_nm, vfb_v, rc_ohm_um
    """
    pol = device['polarity']
    carrier = 'n' if pol == 'n' else 'p'
    n_ch = (channel_doping['concentration_cm3']
            * channel_doping.get('activation_fraction', 1.0))
    lg_nm = device['lg_nm']
    t_ox, k = dielectric['thickness_nm'], dielectric['k_rel']
    kind = shape['kind']
    half_w = _body_half_width(shape)

    phi_f = fermi_potential(n_ch, temperature_k)
    xd_m = depletion_width_max_m(n_ch, temperature_k)
    if kind in ('finfet', 'gaa-nanosheet'):
        cox_area, w_eff_m = cox_fin(t_ox, k, shape['fin_height_nm'],
                                    shape['fin_width_nm'],
                                    shape.get('n_fins', 1),
                                    shape.get('gate_all_around', False))
    else:
        cox_area = cox_planar(t_ox, k)
        w_eff_m = device['w_nm'] * 1e-9
    c_dep = cdep(n_ch, temperature_k, half_w)
    n_body = body_factor_n_ss(c_dep, cox_area)
    vt0 = threshold_voltage(device['vfb_v'], phi_f, cox_area, n_ch,
                            temperature_k, pol, half_w)
    lam = scale_length(kind, t_ox, k, x_dep_nm=xd_m * 1e9,
                       body_width_nm=(shape.get('fin_width_nm')
                                      or shape.get('channel_width_nm')))
    s = sce(lg_nm, lam, phi_f)
    mu_bulk, mu_eff = effective_mobility(n_ch, carrier)
    b = ballisticity(lg_nm)
    vxo = vxo_si(lg_nm, b)
    cinv_area = cox_area * lit('cinv_over_cox')
    w_um = w_eff_m * 1e6
    rc = device['rc_ohm_um'] / w_um if w_um > 0 else 0.0
    return {
        'equation_revision': SI_EQUATION_REVISION,
        'lg_m': lg_nm * 1e-9,
        # per-DEVICE width normalisation (module docstring)
        'cinv_f_per_m': cinv_area * w_eff_m,
        'vxo_m_per_s': vxo,
        'mu_m2_per_vs': mu_eff * 1e-4,
        # the VS core expects the n-type (positive) threshold; the
        # p-device is the mirrored system (ptype = 1)
        'vt0_v': abs(vt0),
        'dvt_v': s['dvt_v'],
        'dibl_v_per_v': s['dibl_v_per_v'],
        'n_ss': n_body * s['n_ss_sce_factor'],
        'lambda_nm': lam,
        'alpha': lit('alpha_vs'),
        'beta': lit('beta_vs'),
        'phit_v': thermal_voltage_v(temperature_k),
        'rs_ohm': rc,
        'rd_ohm': rc,
        'temperature_k': temperature_k,
        'ptype': 1 if pol == 'p' else 0,
        # silicon derivation record (stamped onto the device row)
        'si_vt0_signed_v': vt0,
        'si_phi_f_v': phi_f,
        'si_x_dmax_nm': xd_m * 1e9,
        'si_cox_f_per_m2': cox_area,
        'si_cdep_f_per_m2': c_dep,
        'si_n_body': n_body,
        'si_w_eff_um': w_um,
        'si_mu_bulk_cm2_per_vs': mu_bulk,
        'si_mu_eff_cm2_per_vs': mu_eff,
        'si_ballisticity': b,
        'si_eta': s['eta'],
        'si_shape_kind': kind,
        'si_polarity': pol,
    }


def si_terminal_current(vg_v, vd_v, p):
    """THE reuse point: the silicon device is evaluated by the very
    same VS core the CNT device uses. Returns cnt_vs_model's op dict
    ({id_a, converged, vgsi_v, vdsi_v})."""
    return vs_terminal_current(vg_v, vd_v, p)


def polarity_aware_id_fn(p, polarity):
    """id_fn(vg, vd) -> Id [A]. For polarity 'p' the mirror transform
    of cnt_inverter's p twin applies: Id_p(vg, vd) = -Id_n(-vg, -vd)
    with p built from the p-type parameters (|Vt|, hole mobility,
    n-well doping) — the VS core does this through ptype = 1."""
    pp = {**p, 'ptype': 1 if polarity == 'p' else 0}
    return lambda vg, vd: vs_terminal_current(vg, vd, pp)['id_a']


def provenance_for(p):
    """The stamped provenance block (no values — the row holds them)."""
    return {
        'equation_revision': SI_EQUATION_REVISION,
        'vs_core': 'cntfet.custom.cnt_vs_model.vs_terminal_current (reused)',
        'vt0': '[SZE07] eq.6.28 bulk Vt from Vfb prior + 2phi_F + '
               'Qdep/Cox (fully-depleted cap for thin bodies)',
        'n_ss': '[SZE07] eq.6.63 body factor x [VS1]-form SCE factor',
        'dibl_dvt': f'e^-eta, eta = pi Lg/(2 lambda), lambda per '
                    f"shape {p['si_shape_kind']} ([TN09]/[SUZ93]/[AP98])",
        'mu': '[CT67]/[SZE07] Caughey-Thomas x [TAK94] surface factor '
              'PRIOR',
        'vxo': '[LUN97] B = lambda/(lambda + f Lg) x v_T ([KHA09])',
        'cinv': 'Cox x cinv_over_cox PRIOR x W_eff (per-device width '
                'normalisation)',
        'rc': 'rc_ohm_um / W_um per terminal (prior on the device row)',
        'refusals': ['no gate-leakage / tunnelling model (sol-gel '
                     'leakage is a PRIOR on the dielectric row)',
                     'no GIDL', 'no interface-trap SS degradation',
                     'no quantum-confinement Vt shift', 'no strain'],
    }
