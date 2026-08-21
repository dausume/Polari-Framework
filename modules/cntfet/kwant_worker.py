"""
F3 NEGF worker — runs INSIDE the kwant virtualenv
(~/tools/kwant-venv, numpy<2), NEVER imported by the polari
process (plan D14: the heavy kernel is subprocess-isolated behind
a knob). Protocol: one JSON job on stdin, one JSON result on
stdout.

Physics: atomistic pz tight-binding of a zigzag (n,0) CNT with
EXPLICIT connectivity (4n atoms per 3*a_cc period — no
distance-tolerance guessing), hopping -Ep (the model family's
Ep = 3 eV, so the TB gap ~ 2*Ep*a_cc/d matches the compact
model's Eg by construction). The channel potential follows [VS1]
eq.(5): Ec(x) = a1 e^(-x/lam) + a2 e^(x/lam) + C with
C = vt0 - vg (the same barrier-vs-gate alignment the ToB mapping
uses) and boundary conditions Ec(-X) = -efsd,
Ec(+X) = -efsd - vd, X = Lg/2 + Lof; clamped to the lead values
outside. Transmission from kwant.smatrix; current
I = (2q/h) * 2_spin * Int T(E) [fS - fD] dE  (T counts the two
valleys as orbital modes).

HONEST LIMITS (the wrapper attaches them to every result):
coherent-only (no phonons), FIXED potential (no self-consistent
Poisson — that solver is ours to build, D13), pz zone-folding (no
curvature corrections). This is the tunneling-capable reference
F2 cannot be: thermionic AND S/D tunneling through the eq.(5)
barrier both emerge here.

Job JSON: {mode: 'iv'|'sanity', n, a_cc_nm, ep_ev, lg_nm, lof_nm,
           lambda_nm, efsd_ev, vt0_v, temperature_k,
           bias_points: [{vg_v, vd_v}], energy_points?}
"""

import json
import math
import sys

import numpy as np

Q_C = 1.602176634e-19
H_JS = 6.62607015e-34
KB_EV = 8.617333262e-5


def build_tube(n, a_cc, ep, n_cells, onsite_of_x):
    """Finite tube + two leads. Explicit zigzag (n,0)
    connectivity: per cell, rings A0/B1/A2/B3 at axial offsets
    0, a_cc, 1.5 a_cc, 2.5 a_cc; B1(i) bonds A2(i) and A2(i-1);
    B3(i) bonds next-cell A0(i) and A0(i+1)."""
    import kwant

    period = 3.0 * a_cc
    lat = kwant.lattice.general(
        [(period, 0.0)], [(0.0, 0.0)] * (4 * n), norbs=1)
    subs = lat.sublattices
    x_off = [0.0, a_cc, 1.5 * a_cc, 2.5 * a_cc]
    t = -ep

    def fill_sites(builder, j, onsite):
        for s_idx, sub in enumerate(subs):
            ring = s_idx // n
            builder[sub(j)] = onsite(j * period + x_off[ring])

    def fill_intra(builder, j):
        for i in range(n):
            builder[subs[i](j), subs[n + i](j)] = t
            builder[subs[n + i](j), subs[2 * n + i](j)] = t
            builder[subs[n + i](j),
                    subs[2 * n + ((i - 1) % n)](j)] = t
            builder[subs[2 * n + i](j), subs[3 * n + i](j)] = t

    def fill_inter(builder, j, j_next):
        for i in range(n):
            builder[subs[3 * n + i](j), subs[i](j_next)] = t
            builder[subs[3 * n + i](j),
                    subs[(i + 1) % n](j_next)] = t

    syst = kwant.Builder()
    # two passes: every site must exist before a hopping names it
    for j in range(n_cells):
        fill_sites(syst, j, onsite_of_x)
    for j in range(n_cells):
        fill_intra(syst, j)
        if j + 1 < n_cells:
            fill_inter(syst, j, j + 1)

    def make_lead(u_lead, direction):
        lead = kwant.Builder(kwant.TranslationalSymmetry(
            (direction * period, 0.0)))
        fill_sites(lead, 0, lambda x: u_lead)
        fill_intra(lead, 0)
        fill_inter(lead, 0, 1)
        return lead

    syst.attach_lead(make_lead(onsite_of_x(-1e9), -1))
    syst.attach_lead(make_lead(onsite_of_x(+1e9), +1))
    return syst.finalized()


def fermi(e_ev, mu_ev, kt_ev):
    x = (e_ev - mu_ev) / kt_ev
    if x > 60.0:
        return 0.0
    if x < -60.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(x))


def main():
    import kwant

    job = json.load(sys.stdin)
    n = int(job['n'])
    a_cc = float(job['a_cc_nm'])
    ep = float(job['ep_ev'])
    period = 3.0 * a_cc
    d_nm = math.sqrt(3.0) * a_cc * n / math.pi
    eg = 2.0 * ep * a_cc / d_nm

    if job.get('mode') == 'sanity':
        syst = build_tube(n, a_cc, ep, 8, lambda x: 0.0)
        t_mid = kwant.smatrix(syst, 0.0).transmission(1, 0)
        t_above = kwant.smatrix(
            syst, eg / 2.0 + 0.05).transmission(1, 0)
        t_below = kwant.smatrix(
            syst, eg / 2.0 - 0.05).transmission(1, 0)
        json.dump({'ok': True, 'd_nm': d_nm, 'eg_tb_ev': eg,
                   't_midgap': float(t_mid),
                   't_above_edge': float(t_above),
                   't_below_edge': float(t_below)}, sys.stdout)
        return

    lg = float(job['lg_nm'])
    lof = float(job['lof_nm'])
    lam = float(job['lambda_nm'])
    efsd = float(job['efsd_ev'])
    vt0 = float(job['vt0_v'])
    kt = KB_EV * float(job['temperature_k'])
    x_edge = lg / 2.0 + lof
    half_len = x_edge + 2.0 * period
    n_cells = max(6, int(math.ceil(2.0 * half_len / period)))
    x0 = -0.5 * n_cells * period  # absolute x of cell 0's origin

    results = []
    for point in job['bias_points']:
        vg = float(point['vg_v'])
        vd = float(point['vd_v'])
        c_const = vt0 - vg
        epl = math.exp(x_edge / lam)
        emi = math.exp(-x_edge / lam)
        rhs1 = -efsd - c_const
        rhs2 = -efsd - vd - c_const
        det = emi * emi - epl * epl
        a1 = (rhs1 * emi - rhs2 * epl) / det
        a2 = (rhs2 * emi - rhs1 * epl) / det

        def ec(x_centered):
            if x_centered <= -x_edge:
                return -efsd
            if x_centered >= x_edge:
                return -efsd - vd
            return (a1 * math.exp(-x_centered / lam)
                    + a2 * math.exp(x_centered / lam) + c_const)

        def onsite(x_builder):
            # builder x (cell coords) -> centered axial coord;
            # pristine conduction edge sits at +eg/2
            return ec(x_builder + x0) - eg / 2.0

        syst = build_tube(n, a_cc, ep, n_cells, onsite)
        ec_top = max(ec(x) for x in
                     np.linspace(-x_edge, x_edge, 201))
        e_lo = -efsd - 2.0 * kt
        e_hi = max(ec_top, -efsd) + 0.45
        energies = np.linspace(
            e_lo, e_hi, int(job.get('energy_points', 60)))
        t_vals = [kwant.smatrix(syst, float(e)).transmission(1, 0)
                  for e in energies]
        integrand = [t * (fermi(e, 0.0, kt) - fermi(e, -vd, kt))
                     for e, t in zip(energies, t_vals)]
        current = (2.0 * Q_C / H_JS) * 2.0 * np.trapz(
            integrand, energies) * Q_C
        results.append({'vg_v': vg, 'vd_v': vd,
                        'id_a': float(current),
                        'ec_top_ev': float(ec_top),
                        't_max': float(max(t_vals)),
                        'energyPoints': len(energies)})
    json.dump({'ok': True, 'd_nm': d_nm, 'eg_tb_ev': eg,
               'cells': n_cells, 'atoms': 4 * n * n_cells,
               'points': results}, sys.stdout)


if __name__ == '__main__':
    main()
