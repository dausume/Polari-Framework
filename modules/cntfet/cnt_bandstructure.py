"""
@module cntfet.cnt_bandstructure

S1a: chirality -> band structure -> gate electrostatics -> SCE
parameters. Pure functions; every output carries {value, unit,
role, source, equation} so the derive act can stamp
CNTFETParameterRow rows without re-deriving provenance.

Equation sources (see cnt_constants for the citation ledger):
  d(n,m)      d = a sqrt(n^2 + n m + m^2)/pi, a = sqrt(3) a_cc
              (standard zone-folding geometry; [VS1] Sec.II context)
  Eg          Eg = 2 Ep a_cc / d                     [VS1] Sec.II
  vF          vF = 3 a_cc Ep q / (2 hbar)   (tight-binding cone
              slope; the [GUO04] hyperbolic E(k) parameterization)
  E(k)        E = sqrt((Eg/2)^2 + (hbar vF k)^2)     [GUO04]
  m*          m* = Eg / (2 vF^2)                     [GUO04]
  DOS         g(E) = (4/(pi hbar vF)) E/sqrt(E^2-(Eg/2)^2) per unit
              length (2 spin x 2 valley; asymptote matches [VS1]
              Cqinf = 8 q^2/(3 pi a_cc Ep))
  Cox (GAA)   Cox = 2 pi k_ox eps0 / ln((2 t_ox + d)/d)  [VS1] eq(1)
  Cqe         Cqe = 0.64 sqrt(Eg) + 0.1  fF/um       [VS1] Sec.II.A
  Cinv        Cinv = Cox Cqe/(Cox + Cqe)             [VS1] Sec.II.A
  lambda      [VS1] eq.(7) (GAA scale length, tox > d/2 branch)
  SCE         [VS1] eq.(8): n_ss, DIBL delta, Vt roll-off, with
              eta = (Lg + 2 Lof)/(2 lambda), Lof ~= tox/3

@consumers
  - cntfet.cnt_derive (stamps rows), cnt_tob, cnt_vs_model
  - cntfet.selftest_cntfet (hand-value pins)
"""

import math

from cntfet.cnt_constants import (
    EPS0_F_PER_M, HBAR_JS, LIT, Q_C, lit_value,
)

M0_KG = 9.1093837015e-31  # electron rest mass (CODATA)


def chirality_to_diameter_nm(n, m):
    """d = a sqrt(n^2 + nm + m^2)/pi with a = sqrt(3) a_cc."""
    a_nm = math.sqrt(3.0) * lit_value('a_cc_nm')
    return a_nm * math.sqrt(n * n + n * m + m * m) / math.pi


def is_semiconducting(n, m):
    """Zone-folding rule: metallic iff (n - m) mod 3 == 0."""
    return (n - m) % 3 != 0


def eg_ev(diameter_nm):
    """[VS1]: Eg = 2 Ep a_cc / d (~0.85 eV nm / d)."""
    return (2.0 * lit_value('Ep_eV') * lit_value('a_cc_nm')
            / diameter_nm)


def fermi_velocity_m_per_s():
    """vF = 3 a_cc Ep q/(2 hbar) — the tight-binding cone slope
    with the model-family Ep (= 3 eV -> vF ~ 9.7e5 m/s)."""
    a_cc_m = lit_value('a_cc_nm') * 1e-9
    ep_j = lit_value('Ep_eV') * Q_C
    return 3.0 * a_cc_m * ep_j / (2.0 * HBAR_JS)


def m_eff_over_m0(eg):
    """[GUO04]: m* = Eg/(2 vF^2)."""
    vf = fermi_velocity_m_per_s()
    return (eg * Q_C) / (2.0 * vf * vf) / M0_KG


def dos_per_j_per_m(e_j, eg):
    """1D CNT DOS per unit length, lowest sub-band, 2 spin x 2
    valley: g(E) = (4/(pi hbar vF)) E/sqrt(E^2 - Delta^2), E
    measured from midgap, E > Delta = Eg/2. Zero below the edge."""
    delta = eg * Q_C / 2.0
    if e_j <= delta:
        return 0.0
    vf = fermi_velocity_m_per_s()
    return (4.0 / (math.pi * HBAR_JS * vf)) * e_j / math.sqrt(
        e_j * e_j - delta * delta)


def cox_gaa_f_per_m(t_ox_nm, d_nm, k_ox):
    """[VS1] eq.(1): Cox = 2 pi k_ox eps0 / ln((2 t_ox + d)/d)."""
    return (2.0 * math.pi * k_ox * EPS0_F_PER_M
            / math.log((2.0 * t_ox_nm + d_nm) / d_nm))


def cqe_f_per_m(eg):
    """[VS1] Sec.II.A empirical effective quantum capacitance:
    Cqe = 0.64 sqrt(Eg[eV]) + 0.1 in fF/um (= 1e-9 F/m)."""
    return (lit_value('cqe_coeff') * math.sqrt(eg)
            + lit_value('cqe_offset')) * 1e-9


def cinv_f_per_m(cox, cqe):
    """[VS1] Sec.II.A: series combination."""
    return cox * cqe / (cox + cqe)


def scale_length_nm(d_nm, t_ox_nm, k_ox):
    """[VS1] eq.(7) (valid branch t_ox > d/2):
    lambda = (d + 2 t_ox)/(2 z0) [1 + b (gamma - 1)],
    b = 0.41 (z_0/2 - z_0^3/16)(pi z_0/2), z_0 = z0 d/(d + 2 t_ox),
    gamma = k_cnt/k_ox."""
    z0 = lit_value('z0_bessel')
    gamma = lit_value('k_cnt') / k_ox
    zeta0 = z0 * d_nm / (d_nm + 2.0 * t_ox_nm)
    b = (0.41 * (zeta0 / 2.0 - zeta0 ** 3 / 16.0)
         * (math.pi * zeta0 / 2.0))
    return ((d_nm + 2.0 * t_ox_nm) / (2.0 * z0)
            * (1.0 + b * (gamma - 1.0)))


def sce_parameters(lg_nm, t_ox_nm, d_nm, k_ox, eg, efsd_ev):
    """[VS1] eq.(8) with eta = (Lg + 2 Lof)/(2 lambda), Lof =
    t_ox/3: n_ss = (1 - e^-eta)^-1; DIBL delta = e^-eta; Vt
    roll-off = (2 E_fsd + Eg) e^-eta [V]. SS ~ 60 n_ss mV/dec at
    300 K — oxide-CNT interface non-idealities NOT included
    (the paper says so; experimental SS mismatch is expected and
    stays calibration-visible)."""
    lam = scale_length_nm(d_nm, t_ox_nm, k_ox)
    lof = lit_value('lof_over_tox') * t_ox_nm
    eta = (lg_nm + 2.0 * lof) / (2.0 * lam)
    exp_neg = math.exp(-eta)
    return {
        'lambda_nm': lam,
        'eta': eta,
        'n_ss': 1.0 / (1.0 - exp_neg),
        'dibl_v_per_v': exp_neg,
        'dvt_v': (2.0 * efsd_ev + eg) * exp_neg,
    }


def derive_material_values(n, m):
    """S1a material block: everything from chirality. Returns
    {parameter: {value, unit, role, source, equation,
    derived_from}}."""
    d = chirality_to_diameter_nm(n, m)
    semi = is_semiconducting(n, m)
    eg = eg_ev(d) if semi else 0.0
    vf = fermi_velocity_m_per_s()
    out = {
        'diameter_nm': {
            'value': d, 'unit': 'nm', 'role': 'derived',
            'source': 'zone-folding geometry',
            'equation': 'd = sqrt(3) a_cc sqrt(n^2+nm+m^2)/pi',
            'derived_from': f'chirality ({n},{m}) + a_cc'},
        'semiconducting': {
            'value': 1.0 if semi else 0.0, 'unit': 'bool',
            'role': 'derived',
            'source': 'zone-folding rule (Hamada/Saito 1992)',
            'equation': '(n - m) mod 3 != 0',
            'derived_from': f'chirality ({n},{m})'},
        'eg_ev': {
            'value': eg, 'unit': 'eV', 'role': 'derived',
            'source': LIT['Ep_eV']['source'],
            'equation': 'Eg = 2 Ep a_cc / d',
            'derived_from': 'diameter_nm + Ep'},
        'vf_m_per_s': {
            'value': vf, 'unit': 'm/s', 'role': 'derived',
            'source': '[GUO04] cone-slope parameterization',
            'equation': 'vF = 3 a_cc Ep q/(2 hbar)',
            'derived_from': 'a_cc + Ep'},
        'm_eff_over_m0': {
            'value': m_eff_over_m0(eg) if semi else 0.0,
            'unit': 'm0', 'role': 'derived',
            'source': '[GUO04]', 'equation': 'm* = Eg/(2 vF^2)',
            'derived_from': 'eg_ev + vf_m_per_s'},
    }
    return out


def derive_gate_values(t_ox_nm, d_nm, k_ox, eg):
    """S1a gate-stack block: Cox (GAA), Cqe, Cinv."""
    cox = cox_gaa_f_per_m(t_ox_nm, d_nm, k_ox)
    cqe = cqe_f_per_m(eg)
    cinv = cinv_f_per_m(cox, cqe)
    return {
        'cox_f_per_m': {
            'value': cox, 'unit': 'F/m', 'role': 'derived',
            'source': '[VS1] eq.(1) (GAA cylinder)',
            'equation': 'Cox = 2 pi k_ox eps0/ln((2 t_ox + d)/d)',
            'derived_from': 't_ox + d + k_ox'},
        'cqe_f_per_m': {
            'value': cqe, 'unit': 'F/m', 'role': 'compact-model',
            'source': LIT['cqe_coeff']['source'],
            'equation': 'Cqe = (0.64 sqrt(Eg) + 0.1) fF/um',
            'derived_from': 'eg_ev'},
        'cinv_f_per_m': {
            'value': cinv, 'unit': 'F/m', 'role': 'derived',
            'source': '[VS1] Sec.II.A',
            'equation': 'Cinv = Cox Cqe/(Cox + Cqe)',
            'derived_from': 'cox_f_per_m + cqe_f_per_m'},
    }
