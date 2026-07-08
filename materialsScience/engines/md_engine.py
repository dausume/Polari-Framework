"""
@module materialsScience.engines.md_engine

Atomistic / bead-level molecular dynamics (scale level 3) — pure numpy,
Lennard-Jones REDUCED UNITS (epsilon = sigma = m = kB = 1), so results
are dimensionless and map to a real material by choosing epsilon/sigma.

Two surfaces:

  lj_melt          — monatomic LJ fluid: velocity-Verlet + Langevin
                     thermostat (or NVE), shifted-potential cutoff,
                     virial pressure. The validation workhorse: energy
                     conservation, equipartition, and the ideal-gas
                     limit are CHECKABLE physics, not quoted numbers.
  bead_spring_melt — Kremer-Grest-style polymer melt: FENE bonds
                     (k=30, R0=1.5) + WCA between all beads. The
                     coarse-grained chain model wax/polymer L2-L3 work
                     builds on.

HONEST GAP: full force-field MD (TraPPE/GAFF alkanes with real
torsions and electrostatics) needs OpenMM or LAMMPS — planned as a
WITH_MD build of the msci-engines worker, same ladder as WITH_QE.
capability() names it.

O(N^2) numpy pair math — right for N <= ~500, steps <= ~5000; the
inputs are knobs and the cost scales as N^2 * steps.
"""

_LJ_CUTOFF = 2.5
_WCA_CUTOFF = 2.0 ** (1.0 / 6.0)
_FENE_K = 30.0      # Kremer-Grest 1990 standard bead-spring constants
_FENE_R0 = 1.5


def _numpy():
    try:
        import numpy
        return numpy
    except ImportError:
        return None


def capability():
    np = _numpy()
    report = {
        'engine': 'polari-md',
        'available': np is not None,
        'units': 'LJ reduced (epsilon=sigma=m=kB=1)',
        'integrators': ['velocity-verlet (NVE)',
                        'velocity-verlet + Langevin (NVT)'],
        'potentials': ['lennard-jones (shifted, rc=2.5)',
                       'FENE + WCA bead-spring chains'],
        'forceFieldMD': {
            'available': False,
            'note': 'TraPPE/GAFF alkane MD (real torsions + '
                    'electrostatics) needs OpenMM or LAMMPS — planned '
                    'as a WITH_MD msci-engines worker build, same '
                    'ladder as WITH_QE.'},
    }
    if np is None:
        report['error'] = 'numpy unavailable'
    return report


def _lj_forces(np, positions, box, cutoff):
    """Shifted-potential LJ forces. Returns (forces, potential, virial).
    Minimum-image periodic; O(N^2)."""
    delta = positions[:, None, :] - positions[None, :, :]
    delta -= box * np.round(delta / box)
    r2 = (delta ** 2).sum(axis=-1)
    n = len(positions)
    r2[np.arange(n), np.arange(n)] = np.inf
    mask = r2 < cutoff ** 2
    inv_r2 = np.where(mask, 1.0 / r2, 0.0)
    inv_r6 = inv_r2 ** 3
    # u(r) = 4(r^-12 - r^-6), shifted to 0 at the cutoff.
    shift = 4.0 * (cutoff ** -12 - cutoff ** -6)
    pair_u = np.where(mask, 4.0 * inv_r6 * (inv_r6 - 1.0) - shift, 0.0)
    # w = r du/dr = -(48 r^-12 - 24 r^-6); force = w * dr / r^2 ... sign
    # convention below gives repulsion at short range.
    pair_w = 24.0 * inv_r6 * (2.0 * inv_r6 - 1.0)
    forces = (pair_w * inv_r2)[:, :, None] * delta
    return (forces.sum(axis=1), 0.5 * pair_u.sum(),
            0.5 * pair_w.sum())


def _langevin_o_step(np, velocities, gamma, temperature, dt, rng):
    c1 = float(np.exp(-gamma * dt))
    c2 = float(np.sqrt(max(0.0, (1.0 - c1 ** 2) * temperature)))
    return c1 * velocities + c2 * rng.standard_normal(velocities.shape)


def _lattice_positions(np, n_particles, box):
    per_side = int(np.ceil(n_particles ** (1.0 / 3.0)))
    spacing = box / per_side
    grid = np.arange(per_side) * spacing
    pts = np.array(np.meshgrid(grid, grid, grid)).reshape(3, -1).T
    return pts[:n_particles] + spacing / 2.0


def lj_melt(density, temperature, n_particles=256, steps=3000,
            equilibration=1000, dt=0.005, thermostat='langevin',
            seed=1234):
    """Equilibrium LJ fluid at (density*, T*). thermostat='none' runs
    NVE after a thermostatted equilibration and reports the total-
    energy drift — the integrator's own honesty check."""
    np = _numpy()
    if np is None:
        return {'ok': False, 'error': 'numpy unavailable',
                'suggestion': {'knob': 'backend image',
                               'action': 'numpy ships in the staging '
                                         'image; this refusal means a '
                                         'bare environment'}}
    if not (0 < density < 1.2):
        return {'ok': False,
                'error': f'density* must be in (0, 1.2), got {density} '
                         '(reduced units; ~0.05 gas, ~0.8 liquid)'}
    if temperature <= 0:
        return {'ok': False, 'error': 'temperature* must be > 0'}
    if thermostat not in ('langevin', 'none'):
        return {'ok': False,
                'error': f"thermostat must be 'langevin' or 'none', "
                         f"got '{thermostat}'"}
    n_particles = int(n_particles)
    if not (8 <= n_particles <= 1000):
        return {'ok': False,
                'error': 'nParticles must be in [8, 1000] (O(N^2) '
                         'engine — the knob is the cost)'}
    box = (n_particles / density) ** (1.0 / 3.0)
    cutoff = min(_LJ_CUTOFF, box / 2.0)
    rng = np.random.default_rng(int(seed))
    positions = _lattice_positions(np, n_particles, box)
    velocities = rng.standard_normal((n_particles, 3)) \
        * np.sqrt(temperature)
    velocities -= velocities.mean(axis=0)
    forces, potential, virial = _lj_forces(np, positions, box, cutoff)
    gamma = 1.0

    kinetic_samples, virial_samples, potential_samples = [], [], []
    drift_reference = None
    steps = int(steps)
    equilibration = int(min(equilibration, steps))
    for step in range(steps):
        nve = thermostat == 'none' and step >= equilibration
        velocities += 0.5 * dt * forces
        positions = (positions + dt * velocities) % box
        forces, potential, virial = _lj_forces(
            np, positions, box, cutoff)
        velocities += 0.5 * dt * forces
        if not nve:
            velocities = _langevin_o_step(
                np, velocities, gamma, temperature, dt, rng)
        kinetic = 0.5 * float((velocities ** 2).sum())
        if nve and drift_reference is None:
            drift_reference = kinetic + potential
        if step >= equilibration:
            kinetic_samples.append(kinetic)
            potential_samples.append(float(potential))
            virial_samples.append(float(virial))

    mean_kinetic = float(np.mean(kinetic_samples))
    measured_t = 2.0 * mean_kinetic / (3.0 * n_particles)
    volume = box ** 3
    pressure = (n_particles * measured_t
                + float(np.mean(virial_samples)) / 3.0) / volume
    result = {
        'ok': True, 'engine': 'polari-md', 'model': 'lj-melt',
        'nParticles': n_particles, 'box': box, 'cutoff': cutoff,
        'stepsSampled': len(kinetic_samples),
        'measuredTemperature': measured_t,
        'potentialPerParticle':
            float(np.mean(potential_samples)) / n_particles,
        'pressure': pressure,
        'idealGasPressure': density * measured_t,
        'validity': 'LJ reduced units; shifted-potential cutoff '
                    f'{cutoff:.2f} (no tail correction) — map to a '
                    'real material by choosing epsilon/sigma with '
                    'provenance.',
    }
    if thermostat == 'none' and drift_reference is not None:
        final_total = kinetic_samples[-1] + potential_samples[-1]
        result['nveDriftPerParticle'] = float(
            abs(final_total - drift_reference)) / n_particles
    return result


def _snake_chain_positions(np, n_beads, box):
    """Beads on a cubic lattice traversed as a boustrophedon snake, so
    every consecutive pair sits one lattice spacing apart — overlap-free
    chain initialization at melt density."""
    per_side = int(np.ceil(n_beads ** (1.0 / 3.0)))
    spacing = box / per_side
    pts = []
    for k in range(per_side):
        for j in range(per_side):
            row = range(per_side) if (j + k * per_side) % 2 == 0 \
                else range(per_side - 1, -1, -1)
            jj = j if k % 2 == 0 else per_side - 1 - j
            for i in row:
                pts.append((i, jj, k))
                if len(pts) == n_beads:
                    return np.array(pts, dtype=float) * spacing \
                        + spacing / 2.0
    return np.array(pts, dtype=float) * spacing + spacing / 2.0


def _fene_forces(np, positions, bonds, box):
    """FENE bond forces (k=30, R0=1.5). Returns (forces, potential);
    refuses (raises ValueError) if a bond exceeds R0 — a broken chain
    is an integration failure, never data."""
    i, j = bonds[:, 0], bonds[:, 1]
    delta = positions[i] - positions[j]
    delta -= box * np.round(delta / box)
    r2 = (delta ** 2).sum(axis=-1)
    if bool((r2 >= _FENE_R0 ** 2).any()):
        raise ValueError('FENE bond exceeded R0 (chain broke) — '
                         'reduce dt or steps')
    ratio = r2 / _FENE_R0 ** 2
    potential = float(
        (-0.5 * _FENE_K * _FENE_R0 ** 2 * np.log(1.0 - ratio)).sum())
    scale = -_FENE_K / (1.0 - ratio)
    pair_force = scale[:, None] * delta
    forces = np.zeros_like(positions)
    np.add.at(forces, i, pair_force)
    np.add.at(forces, j, -pair_force)
    return forces, potential


def bead_spring_melt(chain_length=10, n_chains=20, density=0.85,
                     temperature=1.0, steps=3000, equilibration=1000,
                     dt=0.004, seed=1234):
    """Kremer-Grest bead-spring polymer melt: FENE + WCA, Langevin at
    T*. Outputs chain statistics (bond length, Rg, end-to-end) — the
    coarse-grained melt structure level-2/3 wax work builds on."""
    np = _numpy()
    if np is None:
        return {'ok': False, 'error': 'numpy unavailable'}
    chain_length, n_chains = int(chain_length), int(n_chains)
    if chain_length < 2:
        return {'ok': False, 'error': 'chainLength must be >= 2'}
    n_beads = chain_length * n_chains
    if not (8 <= n_beads <= 1000):
        return {'ok': False,
                'error': f'chainLength*nChains must be in [8, 1000], '
                         f'got {n_beads} (O(N^2) engine)'}
    if not (0.4 <= density < 1.1):
        return {'ok': False,
                'error': f'density* must be in [0.4, 1.1) for the '
                         f'chain model, got {density} — below 0.4 the '
                         f'lattice initialization spacing '
                         f'(~density^-1/3) approaches the FENE '
                         f'breaking length R0=1.5'}
    box = (n_beads / density) ** (1.0 / 3.0)
    rng = np.random.default_rng(int(seed))
    positions = _snake_chain_positions(np, n_beads, box)
    bonds = np.array([(c * chain_length + b, c * chain_length + b + 1)
                      for c in range(n_chains)
                      for b in range(chain_length - 1)])
    velocities = rng.standard_normal((n_beads, 3)) * np.sqrt(temperature)
    velocities -= velocities.mean(axis=0)

    def total_forces(pos):
        wca_f, wca_u, _ = _lj_forces(np, pos, box, _WCA_CUTOFF)
        fene_f, fene_u = _fene_forces(np, pos, bonds, box)
        return wca_f + fene_f, wca_u + fene_u

    try:
        forces, potential = total_forces(positions)
        bond_samples, rg_samples, ee_samples, kin_samples = [], [], [], []
        steps = int(steps)
        equilibration = int(min(equilibration, steps))
        for step in range(steps):
            velocities += 0.5 * dt * forces
            positions = (positions + dt * velocities) % box
            forces, potential = total_forces(positions)
            velocities += 0.5 * dt * forces
            velocities = _langevin_o_step(
                np, velocities, 1.0, temperature, dt, rng)
            if step >= equilibration and step % 10 == 0:
                delta = positions[bonds[:, 0]] - positions[bonds[:, 1]]
                delta -= box * np.round(delta / box)
                bond_samples.append(
                    float(np.sqrt((delta ** 2).sum(axis=-1)).mean()))
                chains = positions.reshape(n_chains, chain_length, 3)
                # Unwrap each chain through periodic images bond by
                # bond so Rg/end-to-end measure the real conformation.
                steps_ = np.diff(chains, axis=1)
                steps_ -= box * np.round(steps_ / box)
                unwrapped = np.concatenate(
                    [chains[:, :1, :],
                     chains[:, :1, :] + np.cumsum(steps_, axis=1)],
                    axis=1)
                com = unwrapped.mean(axis=1, keepdims=True)
                rg_samples.append(float(np.sqrt(
                    ((unwrapped - com) ** 2).sum(axis=-1)
                    .mean(axis=-1)).mean()))
                ee = unwrapped[:, -1, :] - unwrapped[:, 0, :]
                ee_samples.append(
                    float(np.sqrt((ee ** 2).sum(axis=-1)).mean()))
                kin_samples.append(0.5 * float((velocities ** 2).sum()))
    except ValueError as e:
        return {'ok': False, 'error': str(e),
                'suggestion': {'knob': 'dt / steps',
                               'action': 'reduce dt (0.004 is the '
                                         'tested default) or steps'}}

    measured_t = 2.0 * float(np.mean(kin_samples)) / (3.0 * n_beads)
    return {
        'ok': True, 'engine': 'polari-md', 'model': 'bead-spring-melt',
        'chainLength': chain_length, 'nChains': n_chains,
        'nBeads': n_beads, 'box': box,
        'measuredTemperature': measured_t,
        'meanBondLength': float(np.mean(bond_samples)),
        'radiusOfGyration': float(np.mean(rg_samples)),
        'endToEndDistance': float(np.mean(ee_samples)),
        'validity': 'Kremer-Grest FENE(k=30, R0=1.5)+WCA melt in LJ '
                    'reduced units [prov: Kremer & Grest 1990, '
                    'equilibrium bond length ~0.97 sigma] — a '
                    'coarse-grained CHAIN model, not a chemical '
                    'force field; map beads to monomers with '
                    'provenance.',
    }
