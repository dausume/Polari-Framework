"""
@module cntfet.custom.cnt_tob

S1b: the F2 quasi-ballistic reference — the top-of-the-barrier
(ToB) model of [RAH03] specialized to a single-sub-band CNT
([GUO04] hyperbolic bands, 2 spin x 2 valley), with the [LUN97]
transmission lift T = lambda/(lambda + Lg) as an explicit knob.

This is the plan's validation-triangle edge #1: an INDEPENDENT
physics path the VS compact model is compared against — same
device rows, different equations. It is NOT the circuit model
(F2 never enters ngspice; D12).

Equations ([RAH03] Sec.II, notation adapted):
  levels at the barrier top shift by U;
  U = -q(alpha_G Vg + alpha_D Vd) + q^2 dN / C_sigma   (self-consistent)
  alpha_G = C_G/C_sigma, alpha_D = C_D/C_sigma
  N = Lg (2/pi) Int_0^inf [f_S(E(k)+U) + f_D(E(k)+U)] dk
      (k-space integration — the 1/sqrt van Hove singularity never
      appears; E(k) = sqrt(Delta^2 + (hbar vF k)^2), Delta = Eg/2)
  I = (4q/h) T kT [ln(1+exp((mu_S - E_top)/kT))
                   - ln(1+exp((mu_D - E_top)/kT))]
      (constant-T Landauer, closed form == [VS1] eq.(10))

S1 honesty notes (named gaps, not silent):
  - T is energy-INdependent (acoustic mfp only); optical-phonon
    emission (lambda_op ~ 10-15 nm) is a named S2 gap — expect the
    high-field edge of the triangle to disagree there.
  - C_D/C_G is mapped from the derived DIBL (eq.(8) delta) for
    comparability with the VS path, not solved from 3D Poisson.
  - NO contact resistance: ToB is the INTRINSIC reference —
    compare trends/SS/barrier behavior against the VS path, not
    absolute Ion (the VS path carries Rc; this one cannot).

@consumers
  - cntfet.cnt_api ({action: iv, engine: tob})
  - cntfet.cntfet_selftest (physics pins + closed-form cross-check)
"""

import math

import numpy as np

from cntfet.custom.cnt_constants import (
    H_JS, HBAR_JS, KB_J_PER_K, Q_C, lit_value,
)


def _fermi(e_j, mu_j, kt_j):
    # exp-safe: clip the argument (numerical technique, not physics
    # switching — plan D12).
    x = np.clip((e_j - mu_j) / kt_j, -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(x))


def transmission(lg_nm, mode):
    """'ballistic' -> T = 1; 'acoustic-mfp' -> [LUN97]
    T = lambda_ap/(lambda_ap + Lg)."""
    if mode == 'ballistic':
        return 1.0
    if mode == 'acoustic-mfp':
        lam = lit_value('lambda_ap_nm')
        return lam / (lam + lg_nm)
    raise ValueError(f'unknown transmission mode "{mode}"')


def _linear_density_per_m(u_ev, vd_v, eg_ev, vf, eta0_ev, kt_j,
                          k_grid):
    """Carrier line density [1/m] at the barrier top with the
    levels shifted by U: (2/pi) Int [f_S + f_D] dk. Energies are
    referenced to the equilibrium source Fermi level (mu_S = 0);
    the equilibrium band edge sits at eta0_ev above it."""
    delta_j = eg_ev * Q_C / 2.0
    e_k = np.sqrt(delta_j ** 2 + (HBAR_JS * vf * k_grid) ** 2)
    # Absolute level energy: edge offset + dispersion above midgap.
    e_abs = (eta0_ev * Q_C) + (e_k - delta_j) + (u_ev * Q_C)
    f_s = _fermi(e_abs, 0.0, kt_j)
    f_d = _fermi(e_abs, -Q_C * vd_v, kt_j)
    return (2.0 / math.pi) * np.trapezoid(f_s + f_d, k_grid)


def tob_operating_point(vg_v, vd_v, p):
    """Solve the ToB self-consistency for one bias point.

    p: {eg_ev, vf_m_per_s, lg_nm, cox_f_per_m, temperature_k,
        eta0_ev, cd_over_cg, transmission_mode}
    Returns {id_a, u_ev, n_per_m, converged, iterations,
             e_top_ev}."""
    kt_j = KB_J_PER_K * p['temperature_k']
    lg_m = p['lg_nm'] * 1e-9
    cg = p['cox_f_per_m'] * lg_m
    cd = p['cd_over_cg'] * cg
    c_sigma = cg + cd
    alpha_g = cg / c_sigma
    alpha_d = cd / c_sigma

    # k grid: dispersion up to ~1.5 eV above the band edge.
    delta_j = p['eg_ev'] * Q_C / 2.0
    e_max_j = delta_j + 1.5 * Q_C
    k_max = math.sqrt(e_max_j ** 2 - delta_j ** 2) / (HBAR_JS
                                                      * p['vf_m_per_s'])
    k_grid = np.linspace(0.0, k_max, 1200)

    def n_of_u(u_ev, vd):
        return _linear_density_per_m(
            u_ev, vd, p['eg_ev'], p['vf_m_per_s'], p['eta0_ev'],
            kt_j, k_grid) * lg_m

    n0 = n_of_u(0.0, 0.0)
    u_l = -(alpha_g * vg_v + alpha_d * vd_v)  # in eV (x q implicit)
    u = u_l
    converged = False
    iterations = 0
    for iterations in range(1, 401):
        n = n_of_u(u, vd_v)
        u_target = u_l + (Q_C * (n - n0) / c_sigma)
        du = u_target - u
        if abs(du) < 1e-7:
            converged = True
            break
        u += 0.35 * du  # damped fixed point (numerical, smooth)
    e_top_ev = p['eta0_ev'] + u
    t_bar = transmission(p['lg_nm'], p['transmission_mode'])
    kt_ev = kt_j / Q_C
    # Closed-form constant-T Landauer (== [VS1] eq.(10) shape).
    ln_s = math.log1p(math.exp(
        max(min(-e_top_ev / kt_ev, 60.0), -60.0)))
    ln_d = math.log1p(math.exp(
        max(min((-e_top_ev - vd_v) / kt_ev, 60.0), -60.0)))
    id_a = (4.0 * Q_C / H_JS) * t_bar * kt_j * (ln_s - ln_d)
    return {'id_a': id_a, 'u_ev': u, 'n_per_m': n_of_u(u, vd_v) / lg_m,
            'converged': converged, 'iterations': iterations,
            'e_top_ev': e_top_ev, 't_bar': t_bar}


def current_integral_check(e_top_ev, vd_v, temperature_k, t_bar):
    """The same current as an explicit energy integral
    (4q/h) T Int [f_S - f_D] dE — the selftest cross-checks this
    against the closed form."""
    kt_j = KB_J_PER_K * temperature_k
    e = np.linspace(e_top_ev, e_top_ev + 2.0, 4000) * Q_C
    f_s = _fermi(e, 0.0, kt_j)
    f_d = _fermi(e, -Q_C * vd_v, kt_j)
    return (4.0 * Q_C / H_JS) * t_bar * np.trapezoid(f_s - f_d, e)


def tob_iv(p, vg_list, vd_list):
    """Id over the bias grid. Returns points + convergence honesty
    (any non-converged point flags the run)."""
    points = []
    all_ok = True
    for vg in vg_list:
        for vd in vd_list:
            op = tob_operating_point(vg, vd, p)
            all_ok = all_ok and op['converged']
            points.append({'vg_v': vg, 'vd_v': vd,
                           'id_a': op['id_a'],
                           'u_ev': op['u_ev'],
                           'converged': op['converged']})
    return {'points': points, 'all_converged': all_ok,
            'transmission_mode': p['transmission_mode'],
            'engine': 'cntfet.tob-f2'}
