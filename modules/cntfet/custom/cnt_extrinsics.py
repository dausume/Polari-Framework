"""
@module cntfet.custom.cnt_extrinsics

[VS2] extrinsic elements, clean-room from the published Part II
paper (Lee/Pop/Franklin/Haensch/Wong, IEEE TED 62(9):3070 (2015),
DOI 10.1109/TED.2015.2457424, read via arXiv:1503.04398 — [VS2]):

  Rc(Lc, d)  transmission-line contact model, eqs (2)-(3):
             2Rc = RQ sqrt(1 + 4/(lam_c gc RQ)) coth(Lc/LT) - RQ
             LT = [gc RQ/lam_c + (gc RQ/2)^2]^(-1/2)
             gc = gco exp(-phi_b/E00);
             phi_b = Eg/2 + (phi_m - phi_s)  [n-type form]
             extracted constants: E00 = 32 meV, lam_c = 380 nm,
             gco = 0.49 uS/nm, phi_m(Pd) = 5.1 eV, phi_s = 4.7 eV.
             Paper-stated validation pin: d = 1.2 nm, Lc = 12.9 nm
             -> 2Rc ~ 70 kOhm.
  Rext       eq (5): Rext = Rext0 Lext/(d^2 nsd^2.1), Rext0=35 Ohm
             (Lext, d in nm; nsd in nm^-1).
  I_SDT      intra-band source-drain tunneling, eqs (6)-(8): WKB
             through OUR eq.(5) barrier (the Part I profile this
             module already carries — the paper's EXPS profile is
             the same two-exponential family), vF = 1e6 m/s as the
             paper states for eq.(7); Landauer integral evaluated
             NUMERICALLY (the paper itself does; the analytic
             Verilog-A recast lives in the NEEDS-blocked manual
             [31], so the OSDI twin stays thermionic-only —
             labeled, not hidden).
  I_BTBT     drain-junction band-to-band tunneling, eqs (12)-(14):
             Ec = u exp(-x/lam_BTBT), lam_BTBT(nm) =
             0.092 kspa + 2.13; closed-form tb =
             lam_BTBT pi (zeta - sqrt(zeta^2 - 1)),
             zeta = -2E/Eg - 1; I_BTBT = 0 for Vds < Eg — the
             mechanism VANISHES NATURALLY (D12's whole point; at
             the S1 device VDD 0.6 V < Eg 0.68 eV it is exactly 0).
  Lof(kspa)  eq (11): Lof = (0.0263 kspa + 0.056) t_ox — refines
             Part I's t_ox/3 when a spacer k is declared.

Mechanisms are ADDITIVE (D12): I_total = I_thermionic + I_SDT +
I_BTBT; profile VS_FULL evaluates them, VS_MINIMAL does not —
never a regime switch. Parasitic capacitance models ([VS2] cites
its ref [36], paywalled, unread) are NOT implemented — the cell
stand-in caps remain the labeled placeholder.

@consumers
  - cntfet.custom.cnt_derive ({action: iv, profile: VS_FULL} + the
    contact-model suggestion)
  - cntfet.cntfet_selftest
"""

import math

import numpy as np

from cntfet.custom.cnt_constants import H_JS, KB_J_PER_K, Q_C

# [VS2] Sec.II extracted constants (all cite-values, Pd contacts).
RQ_OHM = H_JS / (4.0 * Q_C * Q_C)          # h/4q^2 ~ 6.45 kOhm
E00_EV = 0.032
LAMBDA_C_NM = 380.0
GCO_S_PER_NM = 0.49e-6
PHI_M_PD_EV = 5.1
PHI_S_CNT_EV = 4.7
REXT0_OHM = 35.0
ALPHA_D = 2.0
ALPHA_N = 2.1
VF_WKB_M_PER_S = 1.0e6   # [VS2] eq.(7) states vF ~ 1e6 m/s

TWIN_NOTE = ('OSDI twin carries thermionic conduction only: the '
             'analytic Te recast of eqs (7)-(8) is in the NEEDS-'
             'blocked technical manual [31]; VS_FULL tunneling '
             'terms are Python-reference-side (numeric Landauer, '
             'as the paper itself evaluates them)')


def contact_gc_s_per_nm(eg_ev, phi_m_ev=PHI_M_PD_EV,
                        phi_s_ev=PHI_S_CNT_EV, polarity='p'):
    """[VS2] eq.(3): phi_b = Eg/2 - (phi_m - phi_s) for p-type
    contacts (3b), Eg/2 + (phi_m - phi_s) for n-type. The
    CALIBRATED case is Pd on p-type ([FC10] devices): phi_b =
    0.355 - 0.4 = -0.045 eV — barrier-FREE, which is exactly why
    Pd is the p-CNFET contact metal. An n-type device needs a
    low-work-function metal; using these Pd constants for an
    n-device without flipping the metal is a modeling ERROR (made
    and caught live 2026-08-21 — Rc came out 10^9 kOhm)."""
    delta = phi_m_ev - phi_s_ev
    phi_b = (eg_ev / 2.0 - delta if polarity == 'p'
             else eg_ev / 2.0 + delta)
    return GCO_S_PER_NM * math.exp(-phi_b / E00_EV), phi_b


def contact_rc_ohm(lc_nm, eg_ev, phi_m_ev=PHI_M_PD_EV,
                   phi_s_ev=PHI_S_CNT_EV, polarity='p'):
    """[VS2] eq.(2): PER-TERMINAL Rc (the paper's 2Rc covers both
    contacts). Paper pin: d = 1.2 nm (Eg 0.71 eV), Lc = 12.9 nm,
    Pd/p -> 2Rc ~ 70 kOhm. For OUR n-type S1 device the honest
    usage is the MIRROR assumption: an ideal n-metal with
    phi_s - phi_m = 0.4 eV gives the same barrier — pass
    polarity='n' with phi_m = phi_s - 0.4 (flagged assumption,
    not a measured metal)."""
    gc, phi_b = contact_gc_s_per_nm(eg_ev, phi_m_ev, phi_s_ev,
                                    polarity)
    lt_nm = (gc * RQ_OHM / LAMBDA_C_NM
             + (gc * RQ_OHM / 2.0) ** 2) ** -0.5
    two_rc = (RQ_OHM
              * math.sqrt(1.0 + 4.0 / (LAMBDA_C_NM * gc * RQ_OHM))
              / math.tanh(lc_nm / lt_nm) - RQ_OHM)
    return two_rc / 2.0, {
        'phi_b_ev': phi_b, 'gc_s_per_nm': gc, 'lt_nm': lt_nm,
        'two_rc_ohm': two_rc,
        'source': '[VS2] eqs (2)-(3); E00 32 meV, lam_c 380 nm, '
                  'gco 0.49 uS/nm (Pd extraction)'}


def rext_ohm(lext_nm, d_nm, nsd_per_nm):
    """[VS2] eq.(5). Zero-length extensions cost nothing."""
    if lext_nm <= 0.0:
        return 0.0
    return (REXT0_OHM * lext_nm
            / (d_nm ** ALPHA_D * nsd_per_nm ** ALPHA_N))


def lof_nm_from_spacer(kspa, t_ox_nm):
    """[VS2] eq.(11)."""
    return (0.0263 * kspa + 0.056) * t_ox_nm


def _barrier_coeffs(vg_v, vd_v, vt0_v, efsd_ev, lam_nm, x_edge_nm):
    """The eq.(5) two-exponential barrier this module already uses
    everywhere (Part I profile; C = vt0 - vg alignment)."""
    c_const = vt0_v - vg_v
    epl = math.exp(x_edge_nm / lam_nm)
    emi = math.exp(-x_edge_nm / lam_nm)
    rhs1 = -efsd_ev - c_const
    rhs2 = -efsd_ev - vd_v - c_const
    det = emi * emi - epl * epl
    a1 = (rhs1 * emi - rhs2 * epl) / det
    a2 = (rhs2 * emi - rhs1 * epl) / det
    return a1, a2, c_const


def sdt_current_a(vg_v, vd_v, dev):
    """Intra-band S/D tunneling, [VS2] eqs (6)-(8) over the eq.(5)
    barrier: Te(E) = exp[-2piEg/(h vF) tb(E)],
    tb = Int sqrt(1 - (1 - 2[Ec(x)-E]/Eg)^2) dx between turning
    points; I = (4q/h) Int Te [fS - fD] dE BELOW the barrier top
    (above it transport is the thermionic channel already counted
    — no double counting).

    dev: {eg_ev, lg_nm, lof_nm, lambda_nm, efsd_ev, vt0_v,
          temperature_k}."""
    eg = dev['eg_ev']
    lam = dev['lambda_nm']
    x_edge = dev['lg_nm'] / 2.0 + dev['lof_nm']
    a1, a2, c_const = _barrier_coeffs(
        vg_v, vd_v, dev['vt0_v'], dev['efsd_ev'], lam, x_edge)

    def ec(x_nm):
        return (a1 * math.exp(-x_nm / lam)
                + a2 * math.exp(x_nm / lam) + c_const)

    xs = np.linspace(-x_edge, x_edge, 401)
    ec_x = np.array([ec(float(x)) for x in xs])
    ec_top = float(ec_x.max())
    e_source_edge = -dev['efsd_ev']
    if ec_top <= e_source_edge:
        return 0.0  # no barrier above the source edge -> no SDT
    kt_ev = KB_J_PER_K * dev['temperature_k'] / Q_C
    # energy window: from the higher lead edge up to the barrier
    # top (tunneling); Te is WKB through the classically forbidden
    # stretch where Ec(x) > E.
    e_lo = e_source_edge
    e_hi = ec_top
    energies = np.linspace(e_lo, e_hi, 80, endpoint=False)
    prefactor_per_nm = (2.0 * math.pi * eg * Q_C
                        / (H_JS * VF_WKB_M_PER_S)) * 1e-9
    total = 0.0
    de = (e_hi - e_lo) / len(energies)
    for e in energies:
        above = ec_x - e
        inside = above > 0.0
        if not inside.any():
            continue
        frac = 1.0 - (1.0 - 2.0 * above[inside] / eg) ** 2
        frac = np.clip(frac, 0.0, None)
        tb_nm = np.trapz(np.sqrt(frac),
                         xs[inside])
        te = math.exp(-prefactor_per_nm * tb_nm)
        f_s = 1.0 / (1.0 + math.exp(
            min(max(e / kt_ev, -60.0), 60.0)))
        f_d = 1.0 / (1.0 + math.exp(
            min(max((e + vd_v) / kt_ev, -60.0), 60.0)))
        total += te * (f_s - f_d) * de
    return (4.0 * Q_C / H_JS) * total * Q_C


def btbt_current_a(vg_v, vd_v, dev, kspa=4.0):
    """Drain-junction BTBT, [VS2] eqs (12)-(14): zero when
    Vds < Eg (band windows never overlap — the mechanism vanishes
    naturally, no switch). Closed-form tb with
    zeta = -2E/Eg - 1 over the overlap window."""
    eg = dev['eg_ev']
    if vd_v <= eg:
        return 0.0
    lam_btbt_nm = 0.092 * kspa + 2.13
    kt_ev = KB_J_PER_K * dev['temperature_k'] / Q_C
    # overlap window (energies referenced to the source Fermi
    # level, drain CB edge at -efsd - vd, source VB top at
    # -efsd - Eg):
    e_hi = -dev['efsd_ev'] - eg          # source valence-band top
    e_lo = -dev['efsd_ev'] - vd_v        # drain conduction edge
    if e_lo >= e_hi:
        return 0.0
    prefactor_per_nm = (2.0 * math.pi * eg * Q_C
                        / (H_JS * VF_WKB_M_PER_S)) * 1e-9
    energies = np.linspace(e_lo, e_hi, 60)
    total = 0.0
    de = (e_hi - e_lo) / len(energies)
    for e in energies:
        # zeta measured from the local band frame (eq.(14) with
        # E relative to the junction edge)
        e_rel = (e - e_lo) / max(e_hi - e_lo, 1e-12)
        zeta = -2.0 * (-e_rel) - 1.0 + 2.0  # -> [1, ...) window
        zeta = max(zeta, 1.0 + 1e-9)
        tb_nm = lam_btbt_nm * math.pi * (
            zeta - math.sqrt(zeta * zeta - 1.0))
        te = math.exp(-prefactor_per_nm * tb_nm)
        f_s = 1.0 / (1.0 + math.exp(
            min(max(e / kt_ev, -60.0), 60.0)))
        f_d = 1.0 / (1.0 + math.exp(
            min(max((e + vd_v) / kt_ev, -60.0), 60.0)))
        total += te * (f_s - f_d) * de
    return (4.0 * Q_C / H_JS) * total * Q_C


def vs_full_current(vg_v, vd_v, p, dev, kspa=4.0):
    """The VS_FULL profile (D12 additive): thermionic (the
    existing terminal solve, Rc included) + I_SDT + I_BTBT.
    Returns the decomposition, never just a total."""
    from cntfet.custom.cnt_vs_model import vs_terminal_current
    i_th = vs_terminal_current(vg_v, vd_v, p)['id_a']
    i_sdt = sdt_current_a(vg_v, vd_v, dev)
    i_btbt = btbt_current_a(vg_v, vd_v, dev, kspa)
    return {'id_a': i_th + i_sdt + i_btbt,
            'thermionic_a': i_th, 'sdt_a': i_sdt,
            'btbt_a': i_btbt,
            'sdt_fraction': (i_sdt / (i_th + i_sdt + i_btbt))
            if (i_th + i_sdt + i_btbt) > 0 else 0.0,
            'twin_note': TWIN_NOTE}
