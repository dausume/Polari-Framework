"""
@module materialsScience.engines.meso_engine

Mesoscale structure and dynamics (scale level 2) — pure numpy. Two
surfaces, each chosen because it CLOSES an assumption a level-1 model
currently states:

  rod_percolation_threshold — Monte Carlo spanning of randomly placed/
      oriented spherocylinders (soft-core). DERIVES the percolation
      threshold vf_c that analytic.percolation-conductivity today
      takes as a literature assumption, and checks itself against the
      slender-rod excluded-volume limit vf_c ~= 0.7 d/L
      [prov: Balberg et al. 1984, excluded-volume invariant].

  dipolar_chaining — overdamped Brownian dynamics of field-aligned
      dipolar spheres (WCA core + point-dipole forces, LJ-style
      reduced units, kT = sigma = 1). Answers whether magnetic filler
      CHAINS in a melt at a given dipolar coupling lambda — the
      microstructure question behind tuned magnetic structures
      [prov: de Gennes & Pincus 1970, chaining onsets near lambda ~ 2].

Both are idealizations and say so: real CNTs are wavy and attract
(lowers vf_c); real ferrite particles are polydisperse with finite
anisotropy. Validity notes travel with every result.
"""


def _numpy():
    try:
        import numpy
        return numpy
    except ImportError:
        return None


def capability():
    np = _numpy()
    report = {
        'engine': 'polari-meso',
        'available': np is not None,
        'models': ['rod-percolation (MC spanning, spherocylinders)',
                   'dipolar-chaining (overdamped Brownian dynamics)'],
        'gaps': {'dpd': 'momentum-conserving DPD (hydrodynamics, '
                        'nanoparticle dispersion kinetics) is not '
                        'wired yet — these two models are structure/'
                        'Brownian only.'},
    }
    if np is None:
        report['error'] = 'numpy unavailable'
    return report


def _segment_min_dist2(np, p1, d1, p2, d2):
    """Squared min distance between segment sets (vectorized Ericson
    closest-point-of-segments with clamping). p*: (M,3) starts,
    d*: (M,3) full-length direction vectors, pairwise over M."""
    r = p1[:, None, :] - p2[None, :, :]
    a = (d1 ** 2).sum(-1)[:, None]
    e = (d2 ** 2).sum(-1)[None, :]
    b = (d1[:, None, :] * d2[None, :, :]).sum(-1)
    c = (d1[:, None, :] * r).sum(-1)
    f = (d2[None, :, :] * r).sum(-1)
    denom = a * e - b ** 2
    s = np.where(denom > 1e-12,
                 np.clip((b * f - c * e) / np.where(
                     denom > 1e-12, denom, 1.0), 0.0, 1.0), 0.0)
    t = np.clip((b * s + f) / e, 0.0, 1.0)
    s = np.clip((b * t - c) / a, 0.0, 1.0)
    closest = (r + s[:, :, None] * d1[:, None, :]
               - t[:, :, None] * d2[None, :, :])
    return (closest ** 2).sum(-1)


def _spanning(np, vf, aspect_ratio, n_rods, rng):
    """One MC configuration: does a connected rod cluster span the box
    in x? Soft-core spherocylinders, non-periodic box (finite-size —
    n_rods is the knob)."""
    length = aspect_ratio  # d = 1 sets the unit
    v_rod = np.pi / 4.0 * length + np.pi / 6.0
    box = (n_rods * v_rod / vf) ** (1.0 / 3.0)
    starts = rng.random((n_rods, 3)) * box
    theta = np.arccos(1.0 - 2.0 * rng.random(n_rods))
    phi = 2.0 * np.pi * rng.random(n_rods)
    dirs = np.stack([np.sin(theta) * np.cos(phi),
                     np.sin(theta) * np.sin(phi),
                     np.cos(theta)], axis=1) * length
    dist2 = _segment_min_dist2(np, starts, dirs, starts, dirs)
    adjacency = dist2 < 1.0  # contact when closer than one diameter
    parent = list(range(n_rods))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ii, jj = np.nonzero(np.triu(adjacency, 1))
    for i, j in zip(ii.tolist(), jj.tolist()):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    x_ends = np.stack([starts[:, 0], starts[:, 0] + dirs[:, 0]], axis=1)
    touches_low = x_ends.min(axis=1) < 0.5
    touches_high = x_ends.max(axis=1) > box - 0.5
    low_roots = {find(i) for i in np.nonzero(touches_low)[0].tolist()}
    high_roots = {find(i) for i in np.nonzero(touches_high)[0].tolist()}
    return bool(low_roots & high_roots)


def rod_percolation_threshold(aspect_ratio, n_rods=300, trials=8,
                              iterations=9, seed=1234):
    """Bisect the volume fraction where half the MC configurations
    span. Returns vfC with the trial spread and the slender-rod
    excluded-volume limit for comparison."""
    np = _numpy()
    if np is None:
        return {'ok': False, 'error': 'numpy unavailable'}
    if not (2 <= aspect_ratio <= 200):
        return {'ok': False,
                'error': f'aspectRatio must be in [2, 200], got '
                         f'{aspect_ratio} — below 2 rods are grains '
                         '(different physics); above 200 the '
                         'finite-size error at this n_rods swamps '
                         'the estimate'}
    n_rods, trials = int(n_rods), int(trials)
    if not (50 <= n_rods <= 2000):
        return {'ok': False, 'error': 'nRods must be in [50, 2000]'}
    if not (2 <= trials <= 32):
        return {'ok': False, 'error': 'trials must be in [2, 32]'}
    rng = np.random.default_rng(int(seed))
    slender_limit = 0.7 / aspect_ratio
    lo, hi = slender_limit / 10.0, min(0.9, slender_limit * 10.0)
    for _ in range(int(iterations)):
        mid = (lo + hi) / 2.0
        spans = sum(_spanning(np, mid, aspect_ratio, n_rods, rng)
                    for _ in range(trials))
        if spans / trials >= 0.5:
            hi = mid
        else:
            lo = mid
    vf_c = (lo + hi) / 2.0
    return {
        'ok': True, 'engine': 'polari-meso', 'model': 'rod-percolation',
        'aspectRatio': float(aspect_ratio), 'nRods': n_rods,
        'trials': trials,
        'percolationThreshold': vf_c,
        'searchWindow': [lo, hi],
        'slenderRodLimit': slender_limit,
        'ratioToLimit': vf_c / slender_limit,
        'validity': 'ideal straight soft-core rods in a non-periodic '
                    'box (finite-size: nRods is the knob) [prov: '
                    'excluded-volume invariant, Balberg et al. 1984 '
                    '-> vf_c ~= 0.7 d/L for slender rods]. Real CNTs '
                    'are wavy and van-der-Waals attractive — both '
                    'LOWER vf_c; treat this as an upper-bound '
                    'estimate. The derived value is meant to feed '
                    "analytic.percolation-conductivity's "
                    'percolationThreshold knob.',
    }


def _dipole_forces(np, positions, box, coupling, cutoff, cap=500.0):
    """WCA core + field-aligned point-dipole forces, minimum-image.
    U_dip = coupling * (r^2 - 3 z^2) / r^5 (moments pinned along z)."""
    delta = positions[:, None, :] - positions[None, :, :]
    delta -= box * np.round(delta / box)
    r2 = (delta ** 2).sum(-1)
    n = len(positions)
    r2[np.arange(n), np.arange(n)] = np.inf
    # WCA core
    wca_mask = r2 < 2.0 ** (1.0 / 3.0)
    inv_r2 = np.where(wca_mask, 1.0 / r2, 0.0)
    inv_r6 = inv_r2 ** 3
    wca_w = 24.0 * inv_r6 * (2.0 * inv_r6 - 1.0)
    forces = (wca_w * inv_r2)[:, :, None] * delta
    # Dipole-dipole (aligned with z): F = -grad U, U = c (r^2-3z^2)/r^5
    dip_mask = r2 < cutoff ** 2
    r2_safe = np.where(dip_mask, r2, 1.0)  # keep inf/large out of the math
    inv_r = np.where(dip_mask, 1.0 / np.sqrt(r2_safe), 0.0)
    inv_r5 = inv_r ** 5
    inv_r7 = inv_r ** 7
    z = delta[:, :, 2]
    common = 2.0 * inv_r5 - 5.0 * (r2_safe - 3.0 * z ** 2) * inv_r7
    fx = -coupling * delta[:, :, 0] * common
    fy = -coupling * delta[:, :, 1] * common
    fz = -coupling * (z * common - 6.0 * z * inv_r5)
    forces += np.stack([fx, fy, fz], axis=-1)
    norm = np.sqrt((forces ** 2).sum(-1, keepdims=True))
    forces = forces * np.where(norm > cap,
                               cap / np.maximum(norm, 1e-12), 1.0)
    return forces.sum(axis=1)


def _cluster_stats(np, positions, box, bond_cut=1.3):
    """Connected clusters by center distance; returns (mean cluster
    size, fraction of particles in clusters >= 3, mean |cos| of
    cluster principal axes with the field axis z)."""
    delta = positions[:, None, :] - positions[None, :, :]
    delta -= box * np.round(delta / box)
    r2 = (delta ** 2).sum(-1)
    n = len(positions)
    r2[np.arange(n), np.arange(n)] = np.inf
    adjacency = r2 < bond_cut ** 2
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    ii, jj = np.nonzero(np.triu(adjacency, 1))
    for i, j in zip(ii.tolist(), jj.tolist()):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    clusters = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    sizes = [len(m) for m in clusters.values()]
    chained = sum(s for s in sizes if s >= 3)
    alignments = []
    for members in clusters.values():
        if len(members) < 3:
            continue
        # Unwrap the cluster around its first member before the
        # gyration tensor (periodic images would fake isotropy).
        ref = positions[members[0]]
        rel = positions[members] - ref
        rel -= box * np.round(rel / box)
        rel -= rel.mean(axis=0)
        gyration = rel.T @ rel
        eigvals, eigvecs = np.linalg.eigh(gyration)
        alignments.append(abs(float(eigvecs[2, -1])))
    return (float(np.mean(sizes)), chained / n,
            float(np.mean(alignments)) if alignments else 0.0)


def dipolar_chaining(coupling_lambda, volume_fraction, n_particles=150,
                     steps=2500, dt=0.002, seed=1234):
    """Do field-aligned dipolar spheres chain at this coupling and
    loading? Overdamped Brownian dynamics (kT = gamma = sigma = 1),
    lambda = dipole contact energy / kT."""
    np = _numpy()
    if np is None:
        return {'ok': False, 'error': 'numpy unavailable'}
    if not (0 <= coupling_lambda <= 20):
        return {'ok': False,
                'error': f'couplingLambda must be in [0, 20], got '
                         f'{coupling_lambda}'}
    if not (0.005 <= volume_fraction <= 0.3):
        return {'ok': False,
                'error': 'volumeFraction must be in [0.005, 0.3] — '
                         'above 0.3 this dilute-suspension model is '
                         'the wrong tool'}
    n_particles = int(n_particles)
    if not (20 <= n_particles <= 600):
        return {'ok': False, 'error': 'nParticles must be in [20, 600]'}
    box = (n_particles * np.pi / 6.0 / volume_fraction) ** (1.0 / 3.0)
    cutoff = min(4.0, box / 2.0)
    rng = np.random.default_rng(int(seed))
    per_side = int(np.ceil(n_particles ** (1.0 / 3.0)))
    spacing = box / per_side
    grid = np.arange(per_side) * spacing
    positions = np.array(
        np.meshgrid(grid, grid, grid)).reshape(3, -1).T[:n_particles]
    positions = positions + spacing / 2.0

    noise_scale = float(np.sqrt(2.0 * dt))
    for _ in range(int(steps)):
        forces = _dipole_forces(np, positions, box,
                                float(coupling_lambda), cutoff)
        positions = (positions + dt * forces + noise_scale
                     * rng.standard_normal(positions.shape)) % box

    mean_size, chained_fraction, field_alignment = _cluster_stats(
        np, positions, box)
    chains_formed = chained_fraction > 0.5 and field_alignment > 0.6
    return {
        'ok': True, 'engine': 'polari-meso', 'model': 'dipolar-chaining',
        'couplingLambda': float(coupling_lambda),
        'volumeFraction': float(volume_fraction),
        'nParticles': n_particles, 'box': float(box),
        'meanClusterSize': mean_size,
        'chainedFraction': chained_fraction,
        'fieldAlignment': field_alignment,
        'chainsFormed': chains_formed,
        'validity': 'monodisperse field-PINNED point dipoles, '
                    'overdamped, no hydrodynamics [prov: de Gennes & '
                    'Pincus 1970 — chaining onsets near lambda ~ 2]. '
                    'Real ferrite is polydisperse with finite '
                    'anisotropy; treat the lambda threshold as '
                    'indicative. chainsFormed = chainedFraction > 0.5 '
                    'AND fieldAlignment > 0.6 — both knobs visible in '
                    'the result.',
    }
