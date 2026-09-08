"""
@module pspp.custom.structure_sampling

gsp-2 (GEOPOLYMER_STRUCTURE_SAMPLING_PLAN): representative amorphous
clusters SAMPLED from a Q-species distribution — the honest analog of
a unit cell for a material that has none.

``build_geopolymer_sample`` draws one SiO4/AlO4 tetrahedra cluster
whose connectivity matches target Q0-Q4 fractions:

- DETERMINISTIC per seed (numpy default_rng) — same inputs, same
  cluster; "resample" is a new seed, never hidden randomness.
- Connectivity by stub pairing on the drawn Q degrees; when parity or
  clashes make the target unreachable at this N, the achieved
  fractions are REPORTED next to the targets (achievedQ vs targetQ)
  instead of pretending — small ensembles cannot hit fractions
  exactly, and saying so is the point.
- Optional Al substitution at ``si_al_ratio`` with Loewenstein
  (no Al-O-Al) repair passes; residual violations are counted, never
  hidden. Every AlO4- is charge-balanced by one alkali cation placed
  beside it.
- Geometry: spring relaxation of tetrahedron centers (bonded pairs
  to the literature T-T distance through a bridging O), bridging O at
  bond midpoints, terminal (non-bridging) O on repulsion-spread arms.
  Angstrom units, same convention as the crystal scenes.

@consumers
  - pspp.pspp_api (/api/pspp/structure/sample, /scene)
  - pspp.structure_sampling_selftest
"""

import numpy as np

from pspp.custom.structure_groups import MOTIFS

#: Literature geometry bands (Angstrom): Si-O ~1.62, Al-O ~1.75,
#: T-O-T bridge makes T..T ~3.0-3.2.
T_T_DISTANCE_A = 3.06
T_O_DISTANCE = {'Si': 1.62, 'Al': 1.75}
CATION_DISTANCE_A = 2.6
CATION_ELEMENT = {'Na': 'Na', 'K': 'K'}

MAX_TETRAHEDRA = 400


def _draw_q_counts(fractions, n, rng):
    """Largest-remainder apportionment of n tetrahedra over Q classes,
    with an even-stub parity repair (recorded by the caller)."""
    exact = {m: fractions.get(m, 0.0) * n for m in MOTIFS}
    counts = {m: int(exact[m]) for m in MOTIFS}
    remainder = n - sum(counts.values())
    by_frac = sorted(MOTIFS, key=lambda m: -(exact[m] - counts[m]))
    for m in by_frac[:remainder]:
        counts[m] += 1
    parity_adjusted = False
    total_stubs = sum(int(m[1]) * c for m, c in counts.items())
    if total_stubs % 2 == 1:
        # move one tetrahedron between adjacent Q classes to fix
        # parity, choosing the least-populated direction change
        candidates = [m for m in MOTIFS if counts[m] > 0 and m != 'Q0']
        move_from = rng.choice(candidates)
        lower = f'Q{int(move_from[1]) - 1}'
        counts[move_from] -= 1
        counts[lower] += 1
        parity_adjusted = True
    return counts, parity_adjusted


def _pair_stubs(degrees, rng, attempts=40):
    """Random simple-graph realization of a degree sequence: returns
    (edges, unpaired_stub_count). Self-loops/multi-edges rejected by
    retry; leftovers become terminal O, honestly counted."""
    best_edges, best_left = [], sum(degrees)
    for _ in range(attempts):
        stubs = [i for i, d in enumerate(degrees) for _ in range(d)]
        rng.shuffle(stubs)
        seen, edges, leftover = set(), [], []
        for k in range(0, len(stubs) - 1, 2):
            a, b = int(stubs[k]), int(stubs[k + 1])
            key = (min(a, b), max(a, b))
            if a == b or key in seen:
                leftover.extend((a, b))
                continue
            seen.add(key)
            edges.append(key)
        left = len(leftover) + (len(stubs) % 2)
        if left < best_left:
            best_edges, best_left = edges, left
        if best_left == 0:
            break
    return best_edges, best_left


def _assign_aluminum(n, edges, si_al_ratio, rng, repair_passes=30):
    """Al site selection at ~1/(1+ratio) of tetrahedra with
    Loewenstein (no Al-O-Al edge) swap repairs; returns (elements,
    violations)."""
    if not si_al_ratio or si_al_ratio <= 0:
        return ['Si'] * n, 0
    n_al = int(round(n / (1.0 + si_al_ratio)))
    elements = np.array(['Si'] * n, dtype=object)
    if n_al == 0:
        return list(elements), 0
    elements[rng.choice(n, size=min(n_al, n), replace=False)] = 'Al'
    neighbors = [[] for _ in range(n)]
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)

    def violations():
        return [(a, b) for a, b in edges
                if elements[a] == 'Al' and elements[b] == 'Al']

    for _ in range(repair_passes):
        bad = violations()
        if not bad:
            break
        a, b = bad[int(rng.integers(len(bad)))]
        moving = a if rng.random() < 0.5 else b
        safe_si = [i for i in range(n) if elements[i] == 'Si'
                   and not any(elements[j] == 'Al'
                               for j in neighbors[i])
                   and i not in neighbors[moving]]
        if not safe_si:
            break
        elements[moving] = 'Si'
        elements[int(rng.choice(safe_si))] = 'Al'
    return list(elements), len(violations())


#: gel densification (gsp-2b): mean mass per tetrahedral unit for the
#: container-radius estimate — between SiO2 (60) and NaAlO2 (82),
#: recorded as an assumption on every densified sample.
MEAN_UNIT_MASS_G_MOL = 66.0
AVOGADRO = 6.02214076e23


def container_radius_a(n, density_g_cm3):
    """Sphere radius (Angstrom) holding n tetrahedral units at the
    target density."""
    volume_cm3 = n * MEAN_UNIT_MASS_G_MOL / (AVOGADRO * density_g_cm3)
    return (3.0 * volume_cm3 / (4.0 * np.pi)) ** (1.0 / 3.0) * 1e8


def _relax_centers(n, edges, rng, iterations=400, container=None):
    """Spring relaxation: bonded pairs to T_T_DISTANCE_A, everything
    else pushed apart below a soft floor; with a container radius, a
    weak inward restraint packs the cluster to gel density.
    Deterministic via rng."""
    radius = container or 2.4 * max(n, 2) ** (1.0 / 3.0)
    pos = rng.uniform(-radius, radius, size=(n, 3))
    floor = 0.95 * T_T_DISTANCE_A
    for iteration in range(iterations):
        force = np.zeros_like(pos)
        for a, b in edges:
            d = pos[b] - pos[a]
            length = float(np.linalg.norm(d)) or 1e-9
            pull = 0.5 * (length - T_T_DISTANCE_A) * d / length
            force[a] += pull
            force[b] -= pull
        # pairwise soft repulsion (O(n^2) fine at N<=400)
        delta = pos[None, :, :] - pos[:, None, :]
        dist = np.linalg.norm(delta, axis=-1)
        # diagonal pinned AT the floor: zero shortfall, zero push,
        # and no inf/NaN ever enters the arithmetic below
        np.fill_diagonal(dist, floor)
        shortfall = np.minimum(dist - floor, 0.0)
        if shortfall.any():
            # delta[i, j] = pos[j] - pos[i]; shortfall <= 0, so the
            # +0.25 sign sends i AWAY from too-close j (repulsion —
            # the earlier minus sign silently ATTRACTED and collapsed
            # the cluster; caught by the gsp-5 halo validation)
            # repulsion must out-muscle the container pull + bond
            # springs or packed clusters jam below the floor
            # (parameter sweep 2026-07-26: 0.75 holds min T-T > 2.2
            # at gel density; 0.25 let pairs jam to 1.6)
            force += (0.75 * shortfall[..., None]
                      * delta / dist[..., None]).sum(axis=1)
        if container:
            # weak surface-tension proxy: centers outside the
            # container sphere are pulled back toward it
            radial = np.linalg.norm(pos, axis=1)
            outside = radial > container
            if outside.any():
                pull = -0.3 * (radial[outside] - container)
                force[outside] += (pull[:, None]
                                   * pos[outside]
                                   / radial[outside, None])
        # annealed step cap: big moves early, settling at the end
        step = 0.8 if iteration < iterations * 0.7 else 0.3
        pos += np.clip(force, -step, step)
    return pos - pos.mean(axis=0)


def _terminal_directions(count, bonded_dirs, rng, iterations=60):
    """`count` unit vectors spread away from bonded directions and
    each other (repulsion on the unit sphere)."""
    if count <= 0:
        return []
    dirs = rng.normal(size=(count, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    anchors = (np.asarray(bonded_dirs, float)
               if len(bonded_dirs) else np.zeros((0, 3)))
    for _ in range(iterations):
        force = np.zeros_like(dirs)
        others = np.vstack([dirs, anchors])
        for i in range(count):
            d = dirs[i] - others
            norms = np.linalg.norm(d, axis=1)
            mask = norms > 1e-9
            force[i] += (d[mask] / norms[mask, None] ** 3).sum(axis=0)
        dirs += 0.1 * force
        dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    return [v for v in dirs]


def build_geopolymer_sample(q_fractions, n_tetrahedra=60, seed=1,
                            cation='Na', si_al_ratio=None,
                            target_density_g_cm3=2.0):
    """One representative cluster drawn from a Q-distribution.
    Returns {ok, atoms, bonds, targetQ, achievedQ, honesty, counts,
    seed} | refusal. atoms: [{element, position, role, tet}];
    bonds: [[i, j], ...] into atoms.

    target_density_g_cm3 (gsp-2b knob): pack the cluster into a
    sphere at this gel density (literature cured-gel range ~1.5-2.6);
    0/None relaxes unconstrained (the sparse open network)."""
    if cation not in CATION_ELEMENT:
        return {'ok': False,
                'refusal': f'unsupported cation {cation!r}',
                'suggestion': f'available: {sorted(CATION_ELEMENT)}'}
    n = int(n_tetrahedra)
    if not 2 <= n <= MAX_TETRAHEDRA:
        return {'ok': False,
                'refusal': f'nTetrahedra {n} outside [2, '
                           f'{MAX_TETRAHEDRA}]',
                'suggestion': 'small enough to relax interactively; '
                              'raise MAX_TETRAHEDRA deliberately if '
                              'a bigger ensemble is really needed'}
    fractions = {m: float(q_fractions.get(m, 0.0)) for m in MOTIFS}
    total = sum(fractions.values())
    if total <= 0:
        return {'ok': False,
                'refusal': 'empty Q distribution',
                'suggestion': 'pass {Q0..Q4} fractions (see '
                              '/api/pspp/structure/groups)'}
    fractions = {m: v / total for m, v in fractions.items()}
    rng = np.random.default_rng(int(seed))

    counts, parity_adjusted = _draw_q_counts(fractions, n, rng)
    degrees = [int(m[1]) for m in MOTIFS for _ in range(counts[m])]
    rng.shuffle(degrees)
    edges, unpaired = _pair_stubs(degrees, rng)

    achieved_degrees = [0] * n
    for a, b in edges:
        achieved_degrees[a] += 1
        achieved_degrees[b] += 1
    achieved = {m: 0 for m in MOTIFS}
    for d in achieved_degrees:
        achieved[f'Q{min(d, 4)}'] += 1
    achieved_q = {m: round(c / n, 4) for m, c in achieved.items()}

    elements, loewenstein_violations = _assign_aluminum(
        n, edges, si_al_ratio, rng)
    container = None
    if target_density_g_cm3:
        density = float(target_density_g_cm3)
        if not 0.5 <= density <= 4.0:
            return {'ok': False,
                    'refusal': f'targetDensity {density} g/cm3 '
                               'outside [0.5, 4.0]',
                    'suggestion': 'cured geopolymer gels run '
                                  '~1.5-2.6 g/cm3; 0 disables '
                                  'densification'}
        container = container_radius_a(n, density)
    centers = _relax_centers(n, edges, rng, container=container)

    atoms, bonds = [], []
    for i in range(n):
        atoms.append({'element': elements[i],
                      'position': [round(float(v), 4)
                                   for v in centers[i]],
                      'role': 'tetrahedral-center', 'tet': i})
    # bridging O at bond midpoints
    for a, b in edges:
        mid = (centers[a] + centers[b]) / 2.0
        o_index = len(atoms)
        atoms.append({'element': 'O',
                      'position': [round(float(v), 4) for v in mid],
                      'role': 'bridging-oxygen', 'tet': -1})
        bonds.extend([[a, o_index], [b, o_index]])
    # terminal O on spread arms; cations beside Al centers
    cation_symbol = CATION_ELEMENT[cation]
    for i in range(n):
        bonded_dirs = []
        for a, b in edges:
            if i in (a, b):
                other = centers[b if a == i else a] - centers[i]
                norm = float(np.linalg.norm(other)) or 1e-9
                bonded_dirs.append(other / norm)
        terminal_count = 4 - achieved_degrees[i]
        arm_length = T_O_DISTANCE[elements[i]]
        arms = _terminal_directions(terminal_count, bonded_dirs, rng)
        for v in arms:
            o_index = len(atoms)
            atoms.append({'element': 'O',
                          'position': [round(float(x), 4) for x in
                                       centers[i] + arm_length * v],
                          'role': 'terminal-oxygen', 'tet': i})
            bonds.append([i, o_index])
        if elements[i] == 'Al':
            direction = (arms[0] if arms
                         else -np.mean(bonded_dirs, axis=0)
                         if bonded_dirs else np.array([0.0, 1.0, 0.0]))
            direction = np.asarray(direction, float)
            direction /= float(np.linalg.norm(direction)) or 1e-9
            atoms.append({'element': cation_symbol,
                          'position': [round(float(x), 4) for x in
                                       centers[i]
                                       + CATION_DISTANCE_A * direction],
                          'role': 'charge-balancing-cation', 'tet': i})

    density_block = None
    if container:
        radial = np.linalg.norm(centers, axis=1)
        effective_radius = float(radial.max()) + T_O_DISTANCE['Si']
        volume_cm3 = (4.0 / 3.0) * np.pi \
            * (effective_radius * 1e-8) ** 3
        achieved = n * MEAN_UNIT_MASS_G_MOL / (AVOGADRO * volume_cm3)
        density_block = {
            'targetGCm3': round(float(target_density_g_cm3), 3),
            'achievedGCm3': round(float(achieved), 3),
            'containerRadiusA': round(float(container), 2),
            'assumption': f'mean unit mass {MEAN_UNIT_MASS_G_MOL} '
                          'g/mol; achieved value is a bounding-'
                          'sphere estimate',
        }
    return {
        'ok': True, 'seed': int(seed), 'cation': cation,
        'density': density_block,
        'atoms': atoms, 'bonds': bonds,
        'targetQ': {m: round(fractions[m], 4) for m in MOTIFS},
        'achievedQ': achieved_q,
        'honesty': {
            'sampleNotStructure': True,
            'parityAdjusted': parity_adjusted,
            'unpairedStubs': unpaired,
            'loewensteinViolations': loewenstein_violations,
        },
        'counts': {
            'tetrahedra': n, 'bridgingO': len(edges),
            'terminalO': sum(4 - d for d in achieved_degrees),
            'cations': sum(1 for e in elements if e == 'Al'),
            'atoms': len(atoms), 'bonds': len(bonds),
        },
    }
