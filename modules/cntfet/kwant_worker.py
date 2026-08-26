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

D13 (built 2026-08-25): with scf.enabled the eq.(5) barrier
becomes the LAPLACE SEED of a self-consistent 1D cylindrical
Poisson solve.  The governing equation is the per-unit-length
Gauss law of a gate-all-around channel,

    lam^2 Ec''(x) - (Ec - C) = -q dn_l(x) / Cox     [eV],

whose zero-charge solution IS eq.(5) exactly — so the fixed
potential is the Delta_n = 0 limit of the SCF solver, and the
worker's 'poisson-pin' mode asserts that identity on the discrete
grid.  Charge dn_l comes from the NEGF scattering states
themselves (kwant.wave_function + kwant.operator-free |psi|^2
sums, flux-normalized: LDOS = sum |psi|^2 / 2pi — pinned against
kwant.ldos at run time), integrated over both leads' Fermi
functions; the neutrality reference is the source lead's own band
structure (kwant.physics.Bands) with an abrupt-junction donor
profile (donors = lead density for |x| > Lg/2, undoped channel
inside).  Damped fixed-point mixing mirrors cnt_tob (0.35
default), with recorded adaptive halving on oscillation and
continuation across bias points (the charge correction of point k
seeds point k+1, per the plan's F3-SCF budget note).

HONEST LIMITS (the wrapper attaches them to every result):
coherent-only (no phonons), pz zone-folding (no curvature
corrections); fixed mode: FIXED eq.(5) potential; scf mode:
electron-band charge in the transport window only (no
valence/hole charge — VDD < Eg regime), propagating-state charge
only (quasi-bound well states below both lead edges are not
counted — flagged per point as wellFormed), 1D cylindrical
Poisson through eq.(7) lambda + eq.(1) Cox (mode-space, not 3D).
This is the tunneling-capable reference F2 cannot be: thermionic
AND S/D tunneling through the barrier both emerge here.

Job JSON: {mode: 'iv'|'sanity'|'poisson-pin', n, a_cc_nm, ep_ev,
           lg_nm, lof_nm, lambda_nm, efsd_ev, vt0_v,
           temperature_k, bias_points: [{vg_v, vd_v}],
           energy_points?, cox_f_per_m?,
           scf?: {enabled, damping?, tol_ev?, max_iter?,
                  charge_energy_points?}}
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
    # subs rides along so charge accumulation can map a finalized
    # site's family back to its ring index (finalized site order
    # guarantees nothing about sublattice order).
    return syst.finalized(), subs


def fermi(e_ev, mu_ev, kt_ev):
    x = (e_ev - mu_ev) / kt_ev
    if x > 60.0:
        return 0.0
    if x < -60.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(x))


def node_grid(n_cells, a_cc, x0):
    """Centered axial positions of every ring (node), in builder
    order: cell j, rings at offsets 0, a_cc, 1.5a, 2.5a.  Control
    length is 0.75 a_cc for EVERY node (half-gap sums are uniform
    even though the gaps alternate a_cc / 0.5 a_cc)."""
    period = 3.0 * a_cc
    x_off = [0.0, a_cc, 1.5 * a_cc, 2.5 * a_cc]
    xs = np.array([x0 + j * period + off
                   for j in range(n_cells) for off in x_off])
    return xs, 0.75 * a_cc


def analytic_ec(xs, x_edge, lam, c_const, efsd, vd):
    """eq.(5) at the nodes, clamped to the lead values outside —
    the Laplace (zero-charge) profile."""
    # BCs: a1 e^{+X/lam} + a2 e^{-X/lam} = rhs1 (source),
    #      a1 e^{-X/lam} + a2 e^{+X/lam} = rhs2 (drain) —
    # Cramer on [[epl, emi], [emi, epl]].  (The pre-D13 worker had
    # a1/a2 swapped, mirroring the ramp; caught by this very pin.)
    epl = math.exp(x_edge / lam)
    emi = math.exp(-x_edge / lam)
    rhs1 = -efsd - c_const
    rhs2 = -efsd - vd - c_const
    det = epl * epl - emi * emi
    a1 = (rhs1 * epl - rhs2 * emi) / det
    a2 = (rhs2 * epl - rhs1 * emi) / det
    out = np.empty(len(xs))
    for i, x in enumerate(xs):
        if x <= -x_edge:
            out[i] = -efsd
        elif x >= x_edge:
            out[i] = -efsd - vd
        else:
            out[i] = (a1 * math.exp(-x / lam)
                      + a2 * math.exp(x / lam) + c_const)
    return out


def solve_poisson(xs, x_edge, lam, c_const, efsd, vd, rhs_ev):
    """One linear solve of  lam^2 Ec'' - (Ec - C) = rhs  on the
    non-uniform node grid, Dirichlet-clamped to the lead values at
    |x| >= x_edge.  rhs_ev = -q dn_l / Cox in eV.  Thomas
    tridiagonal solve — the interior is ~10^2 nodes."""
    m = len(xs)
    interior = [i for i in range(m)
                if -x_edge < xs[i] < x_edge and 0 < i < m - 1]
    ec = np.where(xs >= x_edge, -efsd - vd, -efsd).astype(float)
    if not interior:
        return ec
    k = len(interior)
    sub = np.zeros(k)
    diag = np.zeros(k)
    sup = np.zeros(k)
    rhs = np.zeros(k)
    pos = {node: idx for idx, node in enumerate(interior)}
    for idx, i in enumerate(interior):
        # Edge-adjacent nodes couple to the TRUE boundary
        # coordinate +-x_edge (where the Dirichlet value holds),
        # not to the nearest exterior node — the slope at the
        # drain edge is ~0.5 eV/nm, so a node-offset clamp costs
        # ~10 meV the pin would (and did) flag.
        left_in = (i - 1) in pos
        right_in = (i + 1) in pos
        h_m = xs[i] - (xs[i - 1] if left_in else -x_edge)
        h_p = (xs[i + 1] if right_in else x_edge) - xs[i]
        w = 2.0 / (h_m + h_p)
        c_m = lam * lam * w / h_m
        c_p = lam * lam * w / h_p
        diag[idx] = -(c_m + c_p) - 1.0
        rhs[idx] = rhs_ev[i] - c_const
        if left_in:
            sub[idx] = c_m
        else:
            rhs[idx] -= c_m * (-efsd)
        if right_in:
            sup[idx] = c_p
        else:
            rhs[idx] -= c_p * (-efsd - vd)
    # Thomas sweep
    for idx in range(1, k):
        f = sub[idx] / diag[idx - 1]
        diag[idx] -= f * sup[idx - 1]
        rhs[idx] -= f * rhs[idx - 1]
    sol = np.zeros(k)
    sol[-1] = rhs[-1] / diag[-1]
    for idx in range(k - 2, -1, -1):
        sol[idx] = (rhs[idx] - sup[idx] * sol[idx + 1]) / diag[idx]
    for idx, i in enumerate(interior):
        ec[i] = sol[idx]
    return ec


def lead_neutral_density(flead, e_lo, e_hi, kt, mu_ev, period_nm):
    """Neutrality reference: electron line density [1/m] of the
    (translationally invariant) source lead at equilibrium,
    counted over the SAME energy window as the channel charge —
    consistent subtraction, no window mismatch."""
    import kwant

    bands = kwant.physics.Bands(flead)
    ks = np.linspace(-math.pi, math.pi, 301)
    per_cell = 0.0
    prev = None
    for k_val in ks:
        es = bands(k_val)
        occ = sum(fermi(float(e), mu_ev, kt) for e in es
                  if e_lo <= e <= e_hi)
        if prev is not None:
            per_cell += 0.5 * (occ + prev) * (ks[1] - ks[0])
        prev = occ
    per_cell *= 2.0 / (2.0 * math.pi)  # spin x2, dk/2pi measure
    return per_cell / (period_nm * 1e-9)


def charge_profile(syst, n, fam_idx, n_nodes, energies, kt, vd,
                   ctrl_nm, check_ldos=False):
    """Non-equilibrium electron line density at every node [1/m]:
    n(site) = 2_spin Int dE/2pi  sum_leads f_lead(E)
              sum_modes |psi|^2, ring-summed and divided by the
    control length.  Returns (n_l, ldos_pin_rel)."""
    import kwant

    node_of_site = np.array(
        [site.tag[0] * 4 + fam_idx[site.family] // n
         for site in syst.sites])
    n_sites = len(node_of_site)
    dens_rows = np.zeros((len(energies), n_sites))
    ldos_pin = None
    for e_idx, e_val in enumerate(energies):
        try:
            wf = kwant.wave_function(syst, float(e_val))
        except Exception:
            continue
        unweighted = np.zeros(n_sites)
        row = np.zeros(n_sites)
        for lead, mu in ((0, 0.0), (1, -vd)):
            psis = wf(lead)
            if len(psis) == 0:
                continue
            dens = np.sum(np.abs(psis) ** 2, axis=0)
            unweighted += dens
            row += fermi(float(e_val), mu, kt) * dens
        dens_rows[e_idx] = row
        if check_ldos and ldos_pin is None and unweighted.max() > 0:
            ref = kwant.ldos(syst, float(e_val))
            ours = unweighted / (2.0 * math.pi)
            ldos_pin = float(np.max(np.abs(ours - ref))
                             / max(np.max(ref), 1e-30))
    n_site = 2.0 * np.trapz(dens_rows, energies, axis=0) \
        / (2.0 * math.pi)
    n_node = np.zeros(n_nodes)
    np.add.at(n_node, node_of_site, n_site)
    return n_node / (ctrl_nm * 1e-9), ldos_pin


def scf_point(job, n, a_cc, ep, eg, n_cells, x0, x_edge, lam,
              efsd, vt0, kt, vg, vd, carry_delta):
    """Self-consistent Poisson <-> NEGF-charge loop for one bias
    point.  Returns (ec_array, scf_report, carry_delta_out)."""
    import kwant

    scf = job.get('scf') or {}
    damping = float(scf.get('damping', 0.35))
    tol_ev = float(scf.get('tol_ev', 2e-3))
    max_iter = int(scf.get('max_iter', 30))
    cox = float(job['cox_f_per_m'])
    lg = float(job['lg_nm'])
    period = 3.0 * a_cc
    xs, ctrl_nm = node_grid(n_cells, a_cc, x0)
    c_const = vt0 - vg
    ec_l = analytic_ec(xs, x_edge, lam, c_const, efsd, vd)
    ec = ec_l.copy()
    if carry_delta is not None and len(carry_delta) == len(ec):
        ec = ec_l + carry_delta  # continuation seed
        ec[xs <= -x_edge] = -efsd
        ec[xs >= x_edge] = -efsd - vd
    n_charge = int(scf.get('charge_energy_points') or
                   max(int(job.get('energy_points', 60)), 80))
    interior = (xs > -x_edge) & (xs < x_edge)
    # Abrupt-junction donor profile: lead density outside the
    # gated Lg, undoped channel inside.
    donor_mask = np.abs(xs) > (lg / 2.0)

    converged = False
    residual = None
    ldos_pin = None
    src_ratio = None
    n0_l = None
    residual_hist = []
    iterations = 0
    for iterations in range(1, max_iter + 1):
        ec_interp = ec.copy()

        def onsite(x_builder):
            return float(np.interp(x_builder + x0, xs, ec_interp)
                         ) - eg / 2.0

        syst, subs = build_tube(n, a_cc, ep, n_cells, onsite)
        fam_idx = {fam: i for i, fam in enumerate(subs)}
        e_hi = float(max(ec.max(), -efsd) + 0.45)
        e_lo = float(-efsd - vd - 2.0 * kt)
        energies = np.linspace(e_lo, e_hi, n_charge)
        n_l, pin = charge_profile(
            syst, n, fam_idx, len(xs), energies, kt, vd, ctrl_nm,
            check_ldos=(iterations == 1))
        if pin is not None:
            ldos_pin = pin
        if n0_l is None:
            n0_l = lead_neutral_density(
                syst.leads[0], e_lo, e_hi, kt, 0.0, period)
            flat = (xs <= -x_edge)
            if flat.sum() >= 2 and n0_l > 0:
                src_ratio = float(np.mean(n_l[flat]) / n0_l)
        delta_n = n_l - np.where(donor_mask, n0_l, 0.0)
        rhs_ev = -(Q_C * delta_n / cox)
        ec_new = solve_poisson(xs, x_edge, lam, c_const, efsd, vd,
                               rhs_ev)
        residual = float(np.max(np.abs(ec_new[interior]
                                       - ec[interior])))
        residual_hist.append(residual)
        if residual < tol_ev:
            converged = True
            break
        if (len(residual_hist) >= 3
                and residual_hist[-1] > residual_hist[-2]
                and residual_hist[-2] > residual_hist[-3]
                and damping > 0.05):
            damping = max(0.05, damping * 0.5)  # recorded below
        ec = ec + damping * (ec_new - ec)
        ec[xs <= -x_edge] = -efsd
        ec[xs >= x_edge] = -efsd - vd
    well_formed = bool(np.min(ec[interior]) < (-efsd - vd - 1e-9)) \
        if interior.any() else False
    report = {
        'converged': converged,
        'iterations': iterations,
        'residual_ev': residual,
        'damping_final': damping,
        'ldos_pin_rel': ldos_pin,
        'source_density_ratio': src_ratio,
        'n0_per_m': n0_l,
        'ec_top_laplace_ev': float(ec_l[interior].max())
        if interior.any() else float(ec_l.max()),
        'wellFormed': well_formed,
    }
    step = max(1, len(xs) // 48)
    report['profile'] = {
        'x_nm': [round(float(v), 4) for v in xs[::step]],
        'ec_ev': [round(float(v), 6) for v in ec[::step]],
    }
    return ec, report, ec - ec_l


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
        syst, _subs = build_tube(n, a_cc, ep, 8, lambda x: 0.0)
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

    if job.get('mode') == 'poisson-pin':
        # The D13 identity pin, no NEGF involved: the discrete
        # Poisson solve with zero charge must reproduce the
        # analytic eq.(5) profile to discretization error.
        point = job['bias_points'][0]
        vg = float(point['vg_v'])
        vd = float(point['vd_v'])
        c_const = vt0 - vg
        xs, _ctrl = node_grid(n_cells, a_cc, x0)
        ec_l = analytic_ec(xs, x_edge, lam, c_const, efsd, vd)
        ec_d = solve_poisson(xs, x_edge, lam, c_const, efsd, vd,
                             np.zeros(len(xs)))
        json.dump({'ok': True, 'nodes': len(xs),
                   'max_dev_ev': float(np.max(np.abs(ec_d - ec_l))),
                   'vg_v': vg, 'vd_v': vd}, sys.stdout)
        return

    scf_enabled = bool((job.get('scf') or {}).get('enabled'))
    if scf_enabled and 'cox_f_per_m' not in job:
        json.dump({'ok': False,
                   'error': 'scf requested without cox_f_per_m — '
                            'the Poisson coupling needs the eq.(1) '
                            'gate capacitance'}, sys.stdout)
        return

    results = []
    carry_delta = None
    for point in job['bias_points']:
        vg = float(point['vg_v'])
        vd = float(point['vd_v'])
        c_const = vt0 - vg
        scf_report = None
        if scf_enabled:
            ec_arr, scf_report, carry_delta = scf_point(
                job, n, a_cc, ep, eg, n_cells, x0, x_edge, lam,
                efsd, vt0, kt, vg, vd, carry_delta)
            xs_nodes, _ctrl = node_grid(n_cells, a_cc, x0)

            def ec(x_centered):
                return float(np.interp(x_centered, xs_nodes,
                                       ec_arr))
        else:
            # Fixed-potential path rides the same (corrected)
            # analytic profile as the SCF seed — see analytic_ec's
            # note on the pre-D13 a1/a2 swap.
            xs_nodes, _ctrl = node_grid(n_cells, a_cc, x0)
            ec_arr = analytic_ec(xs_nodes, x_edge, lam, c_const,
                                 efsd, vd)

            def ec(x_centered):
                if x_centered <= -x_edge:
                    return -efsd
                if x_centered >= x_edge:
                    return -efsd - vd
                return float(np.interp(x_centered, xs_nodes,
                                       ec_arr))

        def onsite(x_builder):
            # builder x (cell coords) -> centered axial coord;
            # pristine conduction edge sits at +eg/2
            return ec(x_builder + x0) - eg / 2.0

        syst, _subs = build_tube(n, a_cc, ep, n_cells, onsite)
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
        entry = {'vg_v': vg, 'vd_v': vd,
                 'id_a': float(current),
                 'ec_top_ev': float(ec_top),
                 't_max': float(max(t_vals)),
                 'energyPoints': len(energies)}
        if scf_report is not None:
            entry['scf'] = scf_report
        results.append(entry)
    json.dump({'ok': True, 'd_nm': d_nm, 'eg_tb_ev': eg,
               'cells': n_cells, 'atoms': 4 * n * n_cells,
               'scf_enabled': scf_enabled,
               'points': results}, sys.stdout)


if __name__ == '__main__':
    main()
