"""
@module cntfet.cnt_charge

S4b: the terminal charge model — [VS1] Sec.III eq.(11), the
published correction for the CNT quantum capacitance (Cgg rises to
a peak then DECREASES at high Vgs because the CNT DOS collapses
past the van Hove singularity — Fig.2a/Fig.9 behavior):

  Qch   = -Lg (Qxo - Qxob)
  Qxob  = (Cinv - Cinvb) n_ss phit ln(1 + exp((Vgs -
          [Vtb - alpha phit Ff(Vtb)]) / (n_ss phit)))
  Cinvb = Cox Cqinf/(Cox + Cqinf),
  Cqinf = 8 q^2/(3 a_cc pi Ep)      (the asymptotic CNT DOS)
  Vtb   = 0.7 Eg/q + 0.13           (empirical, [VS1] Sec.III)

CLEAN-ROOM BOUNDARY, stated plainly: [VS1] says Qs and Qd follow
from Qch by Ward-Dutton partitioning with a Vds-dependent
drift-diffusion/ballistic blend whose complete derivation lives in
the NEEDS-licensed technical manual [26] — which this project may
NOT read. S4b therefore uses an EXPLICIT 50/50 split
(Qs = Qd = Qch/2). That is an approximation, labeled everywhere it
travels: adequate for inverter/RO delay estimates, NOT for precise
Miller/partitioning effects. Upgrading it is future work from
OPEN sources only.

@consumers
  - cntfet.cnt_verilog_a (the r3 ddt contributions mirror these)
  - cntfet.cnt_ring_oscillator (delay context)
  - cntfet.selftest_cntfet (Cgg qualitative pins + AC cross-check)
"""

import math

from cntfet.cnt_constants import Q_C, lit_value
from cntfet.cnt_vs_model import _logistic, _softplus

PARTITION_NOTE = ('Qs = Qd = Qch/2 — explicit 50/50 approximation '
                  '(the Ward-Dutton blend derivation is in the '
                  'blocked NEEDS manual [26]); delay-grade only')


def cqinf_f_per_m():
    """[VS1] Sec.III: Cqinf = 8 q^2/(3 a_cc pi Ep) — the
    asymptotic quantum capacitance of the CNT DOS."""
    a_cc_m = lit_value('a_cc_nm') * 1e-9
    ep_j = lit_value('Ep_eV') * Q_C
    return 8.0 * Q_C * Q_C / (3.0 * a_cc_m * math.pi * ep_j)


def vtb_v(eg_ev_val):
    """[VS1] Sec.III empirical: Vtb = 0.7 Eg/q + 0.13."""
    return 0.7 * eg_ev_val + 0.13


def _qxo_like(vgsi_v, vt_v, cap_f_per_m, p):
    """The eq.(11)-family charge integral shape shared by Qxo and
    Qxob: cap * n_ss * phit * softplus((Vgs - [Vt - alpha phit
    Ff])/(n_ss phit)) with Ff evaluated against the SAME Vt."""
    phit = p['phit_v']
    ff = _logistic(-(vgsi_v - (vt_v - p['alpha'] * phit / 2.0))
                   / (p['alpha'] * phit))
    return cap_f_per_m * p['n_ss'] * phit * _softplus(
        (vgsi_v - (vt_v - p['alpha'] * phit * ff))
        / (p['n_ss'] * phit))


def channel_charge_c(vgsi_v, vdsi_v, p, charge_extras):
    """Qch [C] per eq.(11). charge_extras: {cinvb_f_per_m,
    vtb_v} precomputed from the device (cnt_derive stamps them
    into the params the twin shares). Vt for the Qxo term carries
    the same SCE shifts as the current."""
    vt = (p['vt0_v'] - p['dvt_v']
          - p['dibl_v_per_v'] * vdsi_v)
    qxo = _qxo_like(vgsi_v, vt, p['cinv_f_per_m'], p)
    qxob = _qxo_like(
        vgsi_v, charge_extras['vtb_v'],
        p['cinv_f_per_m'] - charge_extras['cinvb_f_per_m'], p)
    return -p['lg_m'] * (qxo - qxob)


def gate_charge_c(vgsi_v, vdsi_v, p, charge_extras):
    """Qg = -Qch (two-terminal channel bookkeeping at S4b: the
    gate images the channel charge; 50/50 of Qg rides each of
    gate-source / gate-drain in the twin)."""
    return -channel_charge_c(vgsi_v, vdsi_v, p, charge_extras)


def cgg_f(vgs_v, vds_v, p, charge_extras, dv=1e-3):
    """Numeric Cgg = dQg/dVgs [F] at fixed Vds (intrinsic, no
    Rc solve — the qualitative Fig.9 pin: rises, peaks,
    DECREASES)."""
    q_hi = gate_charge_c(vgs_v + dv, vds_v, p, charge_extras)
    q_lo = gate_charge_c(vgs_v - dv, vds_v, p, charge_extras)
    return (q_hi - q_lo) / (2.0 * dv)


def charge_extras_for(eg_ev_val, cox_f_per_m):
    """The two derived charge parameters the model card carries."""
    cqinf = cqinf_f_per_m()
    return {
        'cinvb_f_per_m': cox_f_per_m * cqinf
        / (cox_f_per_m + cqinf),
        'vtb_v': vtb_v(eg_ev_val),
    }
