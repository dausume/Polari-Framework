"""
@module materialsScience.engines.lattice_dynamics_engine

L3 lattice dynamics (ssp-4): phonon dispersion + cubic elastic
constants from classical PAIR potentials on a CrystalStructureDefinition
— pure numpy + ASE, always available in the base image (the same
tradition as md_engine's reduced-unit rungs).

Physics: analytic pair-potential force constants
    K_ab(d) = (phi'' - phi'/r) n_a n_b + (phi'/r) delta_ab
assembled into the dynamical matrix D(k) over the periodic neighbor
shells (ase.neighborlist crosses images); the acoustic sum rule holds
by construction and is STILL checked numerically at Gamma — that check
is the engine's built-in honesty invariant. High-symmetry k-paths come
from ASE's Bravais-lattice bandpath (no spglib).

HONESTY (carried on every result): classical pair potentials give
trends and teaching-grade spectra, NOT quantitative phonons for real
metals/covalent solids (no many-body terms, no charges); quantitative
phonons are the DFPT gap named in the capability report. Elastic
constants are CLAMPED-ION (atoms follow the strain affinely — C44 of
diamond-type lattices is overestimated without internal relaxation).
A structure that is not at the potential's own minimum yields residual
pressure and possibly imaginary modes — reported, never hidden.

@consumers
  - materialsScience.scale_execution (ENGINE_REGISTRY ssp.* keys)
  - materialsScience.crystal_structure_api (named-structure routes)
  - materialsScience.selftest_lattice_dynamics
"""

import numpy as np

#: sqrt(eV / (amu * Angstrom^2)) expressed in THz (ordinary
#: frequency): 1.602176634e-19 / 1.66053906660e-27 / 1e-20 -> s^-2,
#: sqrt, / 2pi / 1e12.
SQRT_EV_AMU_A2_IN_THZ = 15.6330214
#: eV / Angstrom^3 in GPa.
EV_A3_TO_GPA = 160.2176634

DEFAULT_CUTOFF_MULT = 2.5   # LJ range in units of sigma
DEFAULT_NPOINTS = 120
DEFAULT_DOS_GRID = 8
ACOUSTIC_TOL_THZ = 0.02     # |omega(Gamma)| below this counts as zero
STABLE_TOL_THZ = -0.05      # min frequency above this counts stable


def capability():
    return {
        'available': True,
        'evidence': 'pure numpy + ASE neighbor lists / band paths — '
                    'runs in the base image',
        'potentials': ['lennard-jones', 'spring'],
        'gaps': {
            'dftPhonons': {
                'available': False,
                'note': 'quantitative phonons need DFPT (Quantum '
                        'ESPRESSO worker rung, ssp-5 gap) — classical '
                        'pair potentials give trends only',
            },
            'internalRelaxation': {
                'available': False,
                'note': 'elastic constants are clamped-ion; C44 of '
                        'diamond-type lattices is overestimated',
            },
        },
    }


def _refuse(error, knob, action):
    return {'ok': False, 'error': error,
            'suggestion': {'knob': knob, 'action': action}}


# --- pair potentials -------------------------------------------------

def _lj_derivatives(r, epsilon, sigma):
    """phi'(r), phi''(r) of 4*eps*((s/r)^12 - (s/r)^6)."""
    sr6 = (sigma / r) ** 6
    sr12 = sr6 * sr6
    d1 = 4.0 * epsilon * (-12.0 * sr12 + 6.0 * sr6) / r
    d2 = 4.0 * epsilon * (156.0 * sr12 - 42.0 * sr6) / r ** 2
    return d1, d2


def _lj_energy(r, epsilon, sigma):
    sr6 = (sigma / r) ** 6
    return 4.0 * epsilon * (sr6 * sr6 - sr6)


def _parse_potential(potential):
    """-> (kind, params, cutoff resolver) or refusal dict."""
    pot = dict(potential or {})
    kind = pot.get('kind', 'lennard-jones')
    if kind == 'lennard-jones':
        epsilon = float(pot.get('epsilonEv', 0.0) or 0.0)
        sigma = float(pot.get('sigmaA', 0.0) or 0.0)
        if epsilon <= 0 or sigma <= 0:
            return None, _refuse(
                'lennard-jones needs positive epsilonEv and sigmaA',
                "potential.epsilonEv / potential.sigmaA",
                'set the well depth (eV) and size parameter '
                '(Angstrom); fitSigmaToStructure=true derives sigmaA '
                'from the lattice instead')
        cutoff = float(pot.get('cutoffA', 0.0) or 0.0) \
            or DEFAULT_CUTOFF_MULT * sigma
        return {'kind': kind, 'epsilon': epsilon, 'sigma': sigma,
                'cutoff': cutoff}, None
    if kind == 'spring':
        stiffness = float(pot.get('stiffnessEvA2', 0.0) or 0.0)
        if stiffness <= 0:
            return None, _refuse(
                'spring needs positive stiffnessEvA2',
                'potential.stiffnessEvA2',
                'set the bond stiffness in eV/Angstrom^2')
        return {'kind': kind, 'stiffness': stiffness,
                'neighborCutoffScale': float(
                    pot.get('neighborCutoffScale', 1.2) or 1.2)}, None
    return None, _refuse(
        f"unknown potential kind '{kind}'", 'potential.kind',
        "use 'lennard-jones' (epsilonEv, sigmaA[, cutoffA]) or "
        "'spring' (stiffnessEvA2[, neighborCutoffScale])")


def _neighbor_shells(atoms, pot):
    """Ordered neighbor pairs (i, j, r, unit vectors, d vectors) under
    the potential's range. Spring bonds use covalent-radius cutoffs;
    LJ uses its radial cutoff."""
    from ase.neighborlist import neighbor_list
    if pot['kind'] == 'spring':
        from ase.data import covalent_radii
        cutoffs = covalent_radii[atoms.numbers] \
            * pot['neighborCutoffScale']
        i, j, r, d = neighbor_list('ijdD', atoms, cutoffs)
    else:
        i, j, r, d = neighbor_list('ijdD', atoms, pot['cutoff'])
    return i, j, r, d


def _pair_derivatives(pot, r, r0=None):
    """phi', phi'' arrays for all pair distances r. Springs are
    harmonic about the CURRENT structure (r0 = r -> phi' = 0): the
    lattice is taken as the equilibrium, which is exactly the honest
    'structure-as-given' contract."""
    if pot['kind'] == 'spring':
        d1 = np.zeros_like(r)
        d2 = np.full_like(r, pot['stiffness'])
        return d1, d2
    return _lj_derivatives(r, pot['epsilon'], pot['sigma'])


def _force_constant_blocks(r, d, d1, d2):
    """K_ab per pair: (phi'' - phi'/r) n_a n_b + (phi'/r) delta_ab."""
    n = d / r[:, None]
    radial = (d2 - d1 / r)
    blocks = radial[:, None, None] * n[:, :, None] * n[:, None, :]
    blocks += (d1 / r)[:, None, None] * np.eye(3)[None, :, :]
    return blocks


def _dynamical_matrices(atoms, pot, kpts_cart):
    """D(k) for every k (cartesian, includes 2pi) -> frequencies THz
    [nk, 3n] sorted ascending; negative = imaginary (unstable)."""
    i_list, j_list, r, d = _neighbor_shells(atoms, pot)
    if len(i_list) == 0:
        return None
    d1, d2 = _pair_derivatives(pot, r)
    blocks = _force_constant_blocks(r, d, d1, d2)
    masses = atoms.get_masses()
    n = len(atoms)
    freqs = np.empty((len(kpts_cart), 3 * n))
    inv_sqrt_m = 1.0 / np.sqrt(masses)
    for ik, k in enumerate(kpts_cart):
        D = np.zeros((3 * n, 3 * n), dtype=complex)
        phases = np.exp(1j * (d @ k))
        for pair in range(len(i_list)):
            i, j = int(i_list[pair]), int(j_list[pair])
            K = blocks[pair]
            D[3 * i:3 * i + 3, 3 * i:3 * i + 3] += K / masses[i]
            D[3 * i:3 * i + 3, 3 * j:3 * j + 3] -= (
                K * phases[pair] * inv_sqrt_m[i] * inv_sqrt_m[j])
        eigvals = np.linalg.eigvalsh(D)
        freqs[ik] = (np.sign(eigvals)
                     * np.sqrt(np.abs(eigvals))
                     * SQRT_EV_AMU_A2_IN_THZ)
    return freqs


def _lattice_energy(atoms, pot):
    """Total pair energy of the cell (eV) — ordered pairs / 2."""
    _, _, r, _ = _neighbor_shells(atoms, pot)
    if pot['kind'] == 'spring':
        return 0.0
    return float(_lj_energy(r, pot['epsilon'], pot['sigma']).sum()
                 / 2.0)


def _pressure_gpa(atoms, pot, delta=1e-3):
    """Residual pressure -dE/dV from symmetric volume differences."""
    energies = []
    for sign in (-1.0, 1.0):
        scaled = atoms.copy()
        factor = (1.0 + sign * delta) ** (1.0 / 3.0)
        scaled.set_cell(scaled.cell * factor, scale_atoms=True)
        energies.append(_lattice_energy(scaled, pot))
    volume = atoms.get_volume()
    dE_dV = (energies[1] - energies[0]) / (2.0 * delta * volume)
    return -dE_dV * EV_A3_TO_GPA


def fit_sigma_to_structure(atoms, epsilon, cutoff_mult=None):
    """The sigma making the structure the LJ energy minimum under
    uniform scaling (residual pressure = 0), by bisection. The fitted
    value is returned as EVIDENCE on the result — a suggestion, never
    silently substituted elsewhere."""
    from ase.neighborlist import neighbor_list
    nn = float(neighbor_list('d', atoms,
                             1.5 * float(np.max(atoms.cell.lengths()))
                             ).min())
    mult = cutoff_mult or DEFAULT_CUTOFF_MULT
    lo, hi = nn / 1.6, nn / 0.9

    def pressure(sigma):
        pot = {'kind': 'lennard-jones', 'epsilon': epsilon,
               'sigma': sigma, 'cutoff': mult * sigma}
        return _pressure_gpa(atoms, pot)

    p_lo, p_hi = pressure(lo), pressure(hi)
    if p_lo * p_hi > 0:
        return None
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        p_mid = pressure(mid)
        if p_lo * p_mid <= 0:
            hi, p_hi = mid, p_mid
        else:
            lo, p_lo = mid, p_mid
    return 0.5 * (lo + hi)


def _build_structure_atoms(structure, use_primitive):
    """Structure dict/row -> (atoms, refusal)."""
    from materialsScience import crystal_ops
    built = crystal_ops.build_atoms(structure)
    if not built['ok']:
        return None, built
    atoms = built['atoms']
    if use_primitive:
        struct = crystal_ops.structure_dict(structure)
        atoms = crystal_ops.primitive_atoms(atoms,
                                            struct['spaceGroup'])
    return atoms, None


def phonon_dispersion(structure, potential=None, npoints=None,
                      use_primitive=True, dos_grid=None,
                      fit_sigma=False):
    """Phonon band structure along the lattice's standard
    high-symmetry path + DOS on a uniform k-grid.

    structure: a CrystalStructureDefinition row or seed-style dict.
    potential: {'kind': 'lennard-jones', 'epsilonEv', 'sigmaA'
                [, 'cutoffA']}  or {'kind': 'spring',
                'stiffnessEvA2'[, 'neighborCutoffScale']}.
    fit_sigma: derive sigmaA from the lattice (P=0) — the fitted value
    is reported as evidence.
    """
    atoms, refusal = _build_structure_atoms(structure, use_primitive)
    if refusal is not None:
        return refusal
    pot_input = dict(potential or {})
    if fit_sigma and pot_input.get('kind', 'lennard-jones') \
            == 'lennard-jones':
        epsilon = float(pot_input.get('epsilonEv', 0.0) or 0.0)
        if epsilon <= 0:
            return _refuse('fitSigmaToStructure still needs epsilonEv',
                           'potential.epsilonEv',
                           'set the well depth in eV — only sigmaA is '
                           'fitted')
        fitted = fit_sigma_to_structure(atoms, epsilon)
        if fitted is None:
            return _refuse('sigma fit found no zero-pressure point '
                           'for this lattice', 'potential.sigmaA',
                           'set sigmaA explicitly')
        pot_input['sigmaA'] = fitted
    pot, refusal = _parse_potential(pot_input)
    if refusal is not None:
        return refusal

    npoints = int(npoints or DEFAULT_NPOINTS)
    if not 10 <= npoints <= 600:
        return _refuse(f'npoints {npoints} outside [10, 600]',
                       'npoints', 'choose a path sampling in range')
    try:
        bandpath = atoms.cell.bandpath(npoints=npoints)
    except Exception as e:
        return _refuse(f'ASE found no standard path for this cell: '
                       f'{e}', 'use_primitive',
                       'try use_primitive=false, or supply a P1 cell')
    recip = 2.0 * np.pi * atoms.cell.reciprocal()
    kpts_cart = bandpath.kpts @ recip
    freqs = _dynamical_matrices(atoms, pot, kpts_cart)
    if freqs is None:
        return _refuse('the potential range reaches no neighbors',
                       'potential.cutoffA / neighborCutoffScale',
                       'widen the range past the nearest-neighbor '
                       'distance')

    # DOS on a uniform grid.
    grid_n = int(dos_grid or DEFAULT_DOS_GRID)
    grid = np.stack(np.meshgrid(*[
        (np.arange(grid_n) + 0.5) / grid_n] * 3,
        indexing='ij'), axis=-1).reshape(-1, 3)
    dos_freqs = _dynamical_matrices(atoms, pot, grid @ recip).ravel()
    hist, edges = np.histogram(dos_freqs, bins=60)

    gamma_index = int(np.argmin(np.linalg.norm(bandpath.kpts,
                                               axis=1)))
    gamma_acoustic = float(np.sort(np.abs(freqs[gamma_index]))[:3]
                           .max())
    min_freq = float(freqs.min())
    labels, label_positions = [], []
    for label, kpt in bandpath.special_points.items():
        matches = np.where(
            np.linalg.norm(bandpath.kpts - kpt, axis=1) < 1e-9)[0]
        for m in matches:
            labels.append(label)
            label_positions.append(int(m))
    order = np.argsort(label_positions)
    result = {
        'ok': True,
        'nAtoms': len(atoms),
        'branches': int(freqs.shape[1]),
        'path': bandpath.path,
        'pathLabels': [labels[i] for i in order],
        'pathLabelIndices': [label_positions[i] for i in order],
        'kDistances': _cumulative_k_distance(kpts_cart),
        'frequenciesThz': np.round(freqs, 4).tolist(),
        'dos': {'binsThz': np.round(edges, 4).tolist(),
                'counts': hist.tolist()},
        'gammaAcousticMaxThz': round(gamma_acoustic, 4),
        'acousticSumHolds': gamma_acoustic < ACOUSTIC_TOL_THZ,
        'stable': min_freq > STABLE_TOL_THZ,
        'minFrequencyThz': round(min_freq, 4),
        'residualPressureGpa': round(_pressure_gpa(atoms, pot), 3)
        if pot['kind'] == 'lennard-jones' else 0.0,
        'potential': {k: round(v, 5) if isinstance(v, float) else v
                      for k, v in pot.items()},
        'usePrimitive': bool(use_primitive),
        'validity': 'classical pair potential — trends/teaching '
                    'grade, not quantitative phonons (DFPT is the '
                    'named gap); negative frequencies mark imaginary '
                    '(unstable) modes',
    }
    if fit_sigma:
        result['fittedSigmaA'] = round(pot['sigma'], 5)
        result['fittedSigmaNote'] = (
            'sigmaA derived from the lattice (zero residual '
            'pressure) — evidence, adopt it explicitly if wanted')
    return result


def _cumulative_k_distance(kpts_cart):
    steps = np.linalg.norm(np.diff(kpts_cart, axis=0), axis=1)
    return np.round(np.concatenate([[0.0], np.cumsum(steps)]),
                    5).tolist()


def _strained_energy(atoms, pot, strain):
    strained = atoms.copy()
    cell = np.array(strained.cell)
    strained.set_cell(cell @ (np.eye(3) + strain), scale_atoms=True)
    return _lattice_energy(strained, pot)


def _second_derivative(atoms, pot, pattern, delta):
    """d^2 E / d e^2 for cell strain e*pattern (5-point stencil)."""
    energies = [_strained_energy(atoms, pot, e * pattern)
                for e in (-2 * delta, -delta, 0.0, delta, 2 * delta)]
    return ((-energies[0] + 16 * energies[1] - 30 * energies[2]
             + 16 * energies[3] - energies[4]) / (12 * delta ** 2))


def elastic_constants(structure, potential=None, delta=0.005,
                      fit_sigma=False):
    """Clamped-ion cubic elastic constants C11/C12/C44 + bulk modulus
    (two independent routes as a consistency check). Refuses honestly
    for non-cubic conventional cells and for spring potentials (no
    volumetric response without a radial term)."""
    from materialsScience import crystal_ops
    struct = crystal_ops.structure_dict(structure)
    a, b, c, alpha, beta, gamma = struct['cellpar']
    if not (abs(a - b) < 1e-6 and abs(b - c) < 1e-6
            and all(abs(x - 90.0) < 1e-6
                    for x in (alpha, beta, gamma))):
        return _refuse(
            'elastic_constants covers CUBIC conventional cells only '
            f'(got cellpar {struct["cellpar"]})',
            'structure',
            'use a cubic structure; general-symmetry elasticity is a '
            'named gap')
    atoms, refusal = _build_structure_atoms(structure,
                                            use_primitive=False)
    if refusal is not None:
        return refusal
    pot_input = dict(potential or {})
    if pot_input.get('kind', 'lennard-jones') != 'lennard-jones':
        return _refuse(
            'elastic_constants needs the lennard-jones potential '
            '(springs about the current structure carry no radial '
            'preload — every elastic response degenerates)',
            'potential.kind', "use 'lennard-jones'")
    if fit_sigma:
        epsilon = float(pot_input.get('epsilonEv', 0.0) or 0.0)
        if epsilon <= 0:
            return _refuse('fitSigmaToStructure still needs epsilonEv',
                           'potential.epsilonEv',
                           'set the well depth in eV')
        fitted = fit_sigma_to_structure(atoms, epsilon)
        if fitted is None:
            return _refuse('sigma fit found no zero-pressure point',
                           'potential.sigmaA', 'set sigmaA explicitly')
        pot_input['sigmaA'] = fitted
    pot, refusal = _parse_potential(pot_input)
    if refusal is not None:
        return refusal

    volume = atoms.get_volume()
    uniaxial = np.zeros((3, 3))
    uniaxial[0, 0] = 1.0
    ortho = np.diag([1.0, -1.0, 0.0])
    shear = np.zeros((3, 3))
    shear[1, 2] = shear[2, 1] = 0.5

    c11 = _second_derivative(atoms, pot, uniaxial, delta) / volume \
        * EV_A3_TO_GPA
    c11_minus_c12 = _second_derivative(atoms, pot, ortho, delta) \
        / (2.0 * volume) * EV_A3_TO_GPA
    c12 = c11 - c11_minus_c12
    c44 = _second_derivative(atoms, pot, shear, delta) / volume \
        * EV_A3_TO_GPA

    iso = np.eye(3)
    d2E_iso = _second_derivative(atoms, pot, iso, delta)
    bulk_eos = d2E_iso / (9.0 * volume) * EV_A3_TO_GPA
    bulk_elastic = (c11 + 2.0 * c12) / 3.0
    residual = _pressure_gpa(atoms, pot)
    consistent = (abs(bulk_eos - bulk_elastic)
                  <= 0.05 * max(abs(bulk_elastic), 1e-9))
    result = {
        'ok': True,
        'c11Gpa': round(float(c11), 3),
        'c12Gpa': round(float(c12), 3),
        'c44Gpa': round(float(c44), 3),
        'bulkModulusGpa': round(float(bulk_elastic), 3),
        'bulkModulusEosGpa': round(float(bulk_eos), 3),
        'bulkRoutesAgree': bool(consistent),
        'residualPressureGpa': round(float(residual), 3),
        'volumeA3': round(float(volume), 3),
        'potential': {k: round(v, 5) if isinstance(v, float) else v
                      for k, v in pot.items()},
        'validity': 'clamped-ion, classical pair potential: trends '
                    'only. Cauchy relation C12 = C44 (+pressure '
                    'terms) is INTRINSIC to pair potentials — real '
                    'metals violate it; large residual pressure means '
                    'the lattice is not this potential\'s minimum',
    }
    if fit_sigma:
        result['fittedSigmaA'] = round(pot['sigma'], 5)
    return result
