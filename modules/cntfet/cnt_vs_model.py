"""
@module cntfet.cnt_vs_model

S1c: the clean-room VS-CNFET-DERIVED compact model — Python
CANONICAL REFERENCE implementation (plan D3: Python owns parameter
derivation/provenance/validation; the Verilog-A twin in
cnt_verilog_a is the circuit-execution implementation; both carry
EQUATION_REVISION and must pass the numerical-equivalence
regression in cnt_osdi).

Labeling (D3, carried as data on CNTTransportModel rows):
  model_family = "VS-CNFET-derived"; implementation =
  "independent"; numerically_equivalent_to_stanford = False.
  Equations come from [VS1] (arXiv:1503.04397) and the original VS
  formulation [KHA09] AS PUBLISHED — the Stanford source was never
  read (NEEDS Modified CMC License; S0 gate).

Equation set (revision cntfet-vs-s1-r1):
  v_xo   = lambda_v/(lambda_v + 2 Lg) vB,  vB = vB0 sqrt(d/d0)
                                                    [VS1] eq.(9)
  mu     = mu0 Lg/(lambda_mu + Lg) d^c_mu           [VS1] eq.(4)
  SCE    n_ss, DIBL delta, Vt roll-off              [VS1] eq.(8)
  Vt     = Vt0 - dVt_rolloff - delta Vdsi
  Ff     = 1/(1 + exp((Vgsi - (Vt - alpha phit/2))/(alpha phit)))
                                                    [KHA09 via VS1]
  Qxo    = Cinv n_ss phit ln(1 + exp((Vgsi - (Vt - alpha phit Ff))
                                     /(n_ss phit)))     [C/m]
  Vdsat  = (v_xo Lg / mu)(1 - Ff) + phit Ff
  Fsat   = (Vdsi/Vdsat)/(1 + (Vdsi/Vdsat)^beta)^(1/beta)
  Id     = Qxo v_xo Fsat                            [A, per tube]
  Rc     first-class: Vgsi/Vdsi solved against per-terminal
         rs/rd (D9 — never folded into mu)

Mechanisms are ADDITIVE and none switch at regime boundaries
(D12). S1 profile VS_MINIMAL = channel + Rc + SCE; BTBT / S-D
tunneling terms are S2+ ([VS2]) and simply absent (refused by the
capability report, never faked).

@consumers
  - cntfet.cnt_derive (parameter stamping)
  - cntfet.cnt_osdi (equivalence regression reference leg)
  - cntfet.selftest_cntfet
"""

import math

from cntfet.cnt_bandstructure import (
    cinv_f_per_m, cox_gaa_f_per_m, cqe_f_per_m, sce_parameters,
)
from cntfet.cnt_constants import (
    EQUATION_REVISION, lit_value, thermal_voltage_v,
)


def vxo_m_per_s(lg_nm, d_nm):
    """[VS1] eq.(9) with l ~= Lg (paper simplification)."""
    lam_v = lit_value('lambda_v_nm')
    vb = lit_value('vB0_m_per_s') * math.sqrt(
        d_nm / lit_value('d0_nm'))  # vB0 = 4.1e7 cm/s = 4.1e5 m/s
    return lam_v / (lam_v + 2.0 * lg_nm) * vb


def mu_cm2_per_vs(lg_nm, d_nm):
    """[VS1] eq.(4) apparent mobility (d in nm)."""
    return (lit_value('mu0_cm2_per_vs')
            * lg_nm / (lit_value('lambda_mu_nm') + lg_nm)
            * d_nm ** lit_value('c_mu'))


def build_vs_params(material, geometry, gate, contact, transport,
                    temperature_k):
    """Assemble the compact-model parameter dict from the derived
    device rows (objects in, plain params out). Every entry the
    Verilog-A twin needs; same names as the .va parameters."""
    d_nm = material['diameter_nm']
    eg = material['eg_ev']
    lg_nm = geometry['lg_nm']
    cox = cox_gaa_f_per_m(gate['t_ox_nm'], d_nm, gate['k_ox'])
    cqe = cqe_f_per_m(eg)
    sce = sce_parameters(lg_nm, gate['t_ox_nm'], d_nm,
                         gate['k_ox'], eg, transport['efsd_ev'])
    return {
        'equation_revision': EQUATION_REVISION,
        'lg_m': lg_nm * 1e-9,
        'cinv_f_per_m': cinv_f_per_m(cox, cqe),
        'vxo_m_per_s': vxo_m_per_s(lg_nm, d_nm),
        'mu_m2_per_vs': mu_cm2_per_vs(lg_nm, d_nm) * 1e-4,
        'vt0_v': transport['vt0_v'],
        'dvt_v': sce['dvt_v'],
        'dibl_v_per_v': sce['dibl_v_per_v'],
        'n_ss': sce['n_ss'],
        'lambda_nm': sce['lambda_nm'],
        'alpha': lit_value('alpha_vs'),
        'beta': lit_value('beta_vs'),
        'phit_v': thermal_voltage_v(temperature_k),
        'rs_ohm': contact['rc_ohm'],
        'rd_ohm': contact['rc_ohm'],
        'temperature_k': temperature_k,
        # r2: 0 = n-type, 1 = p-type (mirrored equations — [VS1]
        # premise ii: symmetric conduction/valence bands).
        'ptype': 0,
    }


def _softplus(x):
    # ln(1+exp(x)), exp-safe (smooth everywhere — D12 numerics).
    if x > 40.0:
        return x
    if x < -40.0:
        return math.exp(x)
    return math.log1p(math.exp(x))


def _logistic(x):
    if x > 40.0:
        return 1.0
    if x < -40.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def vs_channel_current(vgsi_v, vdsi_v, p):
    """The intrinsic VS channel current (internal-node biases).
    This function IS the equation revision — the Verilog-A twin
    mirrors it line for line."""
    phit = p['phit_v']
    vt = (p['vt0_v'] - p['dvt_v']
          - p['dibl_v_per_v'] * vdsi_v)
    ff = _logistic(-(vgsi_v - (vt - p['alpha'] * phit / 2.0))
                   / (p['alpha'] * phit))
    qxo = (p['cinv_f_per_m'] * p['n_ss'] * phit
           * _softplus((vgsi_v - (vt - p['alpha'] * phit * ff))
                       / (p['n_ss'] * phit)))
    vdsat_strong = (p['vxo_m_per_s'] * p['lg_m']
                    / p['mu_m2_per_vs'])
    vdsat = vdsat_strong * (1.0 - ff) + phit * ff
    x = vdsi_v / vdsat
    fsat = x / (1.0 + abs(x) ** p['beta']) ** (1.0 / p['beta'])
    return qxo * p['vxo_m_per_s'] * fsat


def vs_terminal_current(vg_v, vd_v, p):
    """Terminal-bias current with the per-terminal contact
    resistances solved self-consistently. BISECTION on the monotone
    residual f(Id) = channel(Vg - Id Rs, Vd - Id (Rs+Rd)) - Id —
    bulletproof where a damped fixed point oscillates at high Rc
    (seen live at Rc = 20 kOhm). The twin lets the SPICE solver
    solve the same unique system through internal nodes; the
    solution is solver-independent.

    Polarity (r2): p-type is the MIRRORED n-type system — solve
    the n-type equations at (-Vg, -Vd) and negate the current
    ([VS1] premise ii). n-type expects vd >= 0; p-type vd <= 0."""
    if p.get('ptype'):
        mirrored = vs_terminal_current(-vg_v, -vd_v,
                                       {**p, 'ptype': 0})
        return {'id_a': -mirrored['id_a'],
                'converged': mirrored['converged'],
                'vgsi_v': -mirrored['vgsi_v'],
                'vdsi_v': -mirrored['vdsi_v']}
    rs, rd = p['rs_ohm'], p['rd_ohm']
    rtot = rs + rd

    def channel(id_a):
        return vs_channel_current(vg_v - id_a * rs,
                                  vd_v - id_a * rtot, p)
    if rtot <= 0.0 or vd_v <= 0.0:
        id_a = channel(0.0) if rtot <= 0.0 else 0.0
        return {'id_a': id_a, 'converged': True,
                'vgsi_v': vg_v, 'vdsi_v': vd_v}
    lo, f_lo = 0.0, channel(0.0)
    hi = vd_v / rtot  # internal Vds hits 0 here -> f(hi) < 0
    if f_lo <= 0.0:
        return {'id_a': 0.0, 'converged': True, 'vgsi_v': vg_v,
                'vdsi_v': vd_v}
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        f_mid = channel(mid) - mid
        if f_mid > 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < max(1e-20, 1e-14 * hi):
            break
    id_a = 0.5 * (lo + hi)
    return {'id_a': id_a, 'converged': True,
            'vgsi_v': vg_v - id_a * rs,
            'vdsi_v': vd_v - id_a * rtot}


def iv_family(p, vg_list, vd_list):
    """DC Id over the grid — the S1 deliverable curves."""
    points = []
    all_ok = True
    for vg in vg_list:
        for vd in vd_list:
            op = vs_terminal_current(vg, vd, p)
            all_ok = all_ok and op['converged']
            points.append({'vg_v': vg, 'vd_v': vd,
                           'id_a': op['id_a'],
                           'converged': op['converged']})
    return {'points': points, 'all_converged': all_ok,
            'engine': 'cntfet.vs-python-reference',
            'equation_revision': p['equation_revision']}


def subthreshold_slope_mv_per_dec(p, vd_v=0.05, vg_lo=0.0,
                                  vg_hi=0.15):
    """Numeric SS from two subthreshold points (diagnostic)."""
    i1 = vs_terminal_current(vg_lo, vd_v, p)['id_a']
    i2 = vs_terminal_current(vg_hi, vd_v, p)['id_a']
    if i1 <= 0.0 or i2 <= 0.0 or i2 == i1:
        return 0.0
    return (vg_hi - vg_lo) * 1000.0 / math.log10(i2 / i1)
