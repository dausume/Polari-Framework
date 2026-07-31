"""
@cross-cutting
@module materialsScience.engines.fem_engine
@tags @xc:bindings

Continuum (scale level 1) FEM engine over scikit-fem — the general
FEM capability, using a pre-existing open-source OO library rather
than hand-rolled assembly (scikit-fem: BSD, pure Python, numpy/scipy
only, so it rides the existing image with no system packages).

First real solve: steady heat conduction through a unit-square slab
(-∇·(k∇T) = q, T=0 on the boundary) — the property it consumes
(thermal conductivity) is exactly what ConsistentFiniteElementMaterial
rows carry, so a level-1 MaterialScaleDefinition can point here and be
EXECUTED, not just stored.

capability() reports honestly; solve functions refuse with a
suggestion when scikit-fem is absent (knobs-and-suggestions).
"""


def capability():
    """{'available': bool, 'library': 'scikit-fem', 'version': str,
    'suggestion': {...}|None} — never raises."""
    try:
        import skfem
        return {'available': True, 'library': 'scikit-fem',
                'version': getattr(skfem, '__version__', 'unknown'),
                'suggestion': None}
    except Exception as e:
        return {
            'available': False, 'library': 'scikit-fem', 'version': '',
            'suggestion': {
                'evidence': f'import skfem failed: {e}',
                'knob': 'requirements.txt (scikit-fem) + image rebuild',
                'action': 'Rebuild the backend image — scikit-fem==10.0.2 '
                          'is already in requirements.txt.',
            },
        }


def effective_conductivity(matrix_k, inclusion_k, volume_fraction,
                           refine=5):
    """NUMERICAL homogenization of a 2-phase composite unit cell — the
    rigorous upgrade from the algebraic Voigt/Reuss bounds in
    formulation_math.

    Unit square of matrix material (matrix_k) with a centered circular
    inclusion (inclusion_k) at the given volume fraction. A unit
    temperature difference is imposed across x (insulated top/bottom);
    the effective conductivity is the resulting mean heat flux:
        k_eff = -∫ k ∂T/∂x dA   (unit cell, unit ΔT, unit length).

    Returns {'ok', 'effectiveK', 'voigtBound', 'reussBound',
    'withinBounds', 'actualVolumeFraction', 'elements'} — k_eff MUST sit
    inside [Reuss, Voigt]; the flag makes the check self-auditing.
    """
    cap = capability()
    if not cap['available']:
        return {'ok': False, 'error': 'FEM engine unavailable',
                'suggestion': cap['suggestion']}
    if matrix_k <= 0 or inclusion_k <= 0:
        return {'ok': False, 'error': 'conductivities must be > 0'}
    if not (0.0 < volume_fraction < 0.6):
        return {'ok': False,
                'error': f'volume_fraction must be in (0, 0.6) for a '
                         f'centered circular inclusion, got '
                         f'{volume_fraction}'}

    import numpy as np
    from skfem import (MeshTri, Basis, ElementTriP1, ElementTriP0, asm,
                       condense, solve, BilinearForm, Functional)
    from skfem.helpers import dot, grad

    mesh = MeshTri().refined(refine)
    basis = Basis(mesh, ElementTriP1())
    basis0 = basis.with_element(ElementTriP0())

    # Per-element conductivity: inclusion where the centroid falls
    # inside the circle of area = volume_fraction.
    radius = float(np.sqrt(volume_fraction / np.pi))
    centroids = mesh.p[:, mesh.t].mean(axis=1)
    inside = ((centroids[0] - 0.5) ** 2
              + (centroids[1] - 0.5) ** 2) <= radius ** 2
    kPerElement = np.where(inside, inclusion_k, matrix_k)
    actualFraction = float(
        np.sum(inside * _tri_areas(mesh)) / np.sum(_tri_areas(mesh)))

    @BilinearForm
    def conduction(u, v, w):
        return w['kk'] * dot(grad(u), grad(v))

    stiffness = asm(conduction, basis, kk=basis0.interpolate(kPerElement))

    # Dirichlet: T=1 at x=0, T=0 at x=1; top/bottom natural (insulated).
    left = basis.get_dofs(lambda x: x[0] == 0.0)
    right = basis.get_dofs(lambda x: x[0] == 1.0)
    temperature = basis.zeros()
    temperature[left] = 1.0
    temperature = solve(*condense(
        stiffness, basis.zeros(), x=temperature,
        D=np.concatenate([left, right])))

    @Functional
    def xFlux(w):
        return -w['kk'] * grad(w['temp'])[0]

    effectiveK = float(xFlux.assemble(
        basis, kk=basis0.interpolate(kPerElement),
        temp=basis.interpolate(temperature)))

    from materialsScience.formulation_math import mixture_bounds
    bounds = mixture_bounds(
        [matrix_k, inclusion_k],
        [1.0 - actualFraction, actualFraction], rule='hybrid')
    withinBounds = bool(
        bounds['reuss'] - 1e-9 <= effectiveK <= bounds['voigt'] + 1e-9)
    return {'ok': True, 'effectiveK': effectiveK,
            'voigtBound': bounds['voigt'], 'reussBound': bounds['reuss'],
            'withinBounds': withinBounds,
            'actualVolumeFraction': actualFraction,
            'elements': int(mesh.t.shape[1])}


def _tri_areas(mesh):
    import numpy as np
    p, t = mesh.p, mesh.t
    x1, y1 = p[:, t[0]]
    x2, y2 = p[:, t[1]]
    x3, y3 = p[:, t[2]]
    return 0.5 * np.abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))


def solve_steady_conduction(thermal_conductivity, heat_source=1.0,
                            refine=4):
    """Steady conduction on the unit square, homogeneous Dirichlet.

    thermal_conductivity: k (W/m·K, > 0)
    heat_source: uniform volumetric source q
    refine: mesh refinement level (elements ~ 2·4^refine)

    Returns {'ok': True, 'maxTemperature', 'meanTemperature',
    'degreesOfFreedom', 'elements'} — or {'ok': False, 'suggestion'}
    when the library is missing. Analytic sanity: max T of -k∇²T = q on
    the unit square is (q/k)·0.0736… at the center, so callers can
    validate scaling (T ∝ q/k).
    """
    cap = capability()
    if not cap['available']:
        return {'ok': False, 'error': 'FEM engine unavailable',
                'suggestion': cap['suggestion']}
    if thermal_conductivity <= 0:
        return {'ok': False,
                'error': f'thermal_conductivity must be > 0, got '
                         f'{thermal_conductivity}'}

    import numpy as np
    from skfem import MeshTri, Basis, ElementTriP1, asm, condense, solve
    from skfem.helpers import dot, grad
    from skfem.models.poisson import unit_load
    from skfem import BilinearForm

    mesh = MeshTri().refined(refine)
    basis = Basis(mesh, ElementTriP1())

    @BilinearForm
    def conduction(u, v, _):
        return thermal_conductivity * dot(grad(u), grad(v))

    stiffness = asm(conduction, basis)
    load = heat_source * asm(unit_load, basis)
    temperature = solve(*condense(stiffness, load, D=basis.get_dofs()))

    return {
        'ok': True,
        'maxTemperature': float(np.max(temperature)),
        'meanTemperature': float(np.mean(temperature)),
        'degreesOfFreedom': int(temperature.shape[0]),
        'elements': int(mesh.t.shape[1]),
    }


# ------------------------------------------------------------------ #
# LINEAR ELASTICITY (mag-15) — real stress tensors, so a cast part can
# be asked whether it survives the loads the motor actually applies.
#
# Everything below is LINEAR ELASTIC and SMALL STRAIN. That is a real
# restriction, not a formality: it means no yielding, no cracking, no
# contact, no large rotation, no fatigue, and no residual stress from
# casting or curing. It answers "what stress does this load produce in
# an intact elastic body", which is the question a failure criterion
# needs — and nothing beyond it.
#
# Both PLANE STRESS and PLANE STRAIN are offered because they are not
# interchangeable: a thin flat plate free to contract through its
# thickness is plane stress (sigma_zz = 0); a long prismatic body
# restrained along its axis is plane strain (epsilon_zz = 0, and
# sigma_zz = nu*(sxx+syy) is NOT zero). Choosing wrongly changes the
# von Mises answer, so the assumption is a required knob and it is
# echoed on every payload.
# ------------------------------------------------------------------ #

#: Rectangle edges a caller may load or restrain.
ELASTIC_EDGES = ('left', 'right', 'bottom', 'top')
ELASTIC_ASSUMPTIONS = ('plane-stress', 'plane-strain')


def elastic_capability():
    """Elasticity-specific availability: scikit-fem AND its
    skfem.models.elasticity helpers. Same shape as capability()."""
    base = capability()
    if not base['available']:
        return base
    try:
        from skfem.models.elasticity import (  # noqa: F401
            lame_parameters, linear_elasticity, plane_stress,
        )
        return {'available': True, 'library': 'scikit-fem',
                'version': base['version'], 'physics': 'linear-elasticity',
                'suggestion': None}
    except Exception as e:
        return {
            'available': False, 'library': 'scikit-fem',
            'version': base['version'], 'physics': 'linear-elasticity',
            'suggestion': {
                'evidence': f'import skfem.models.elasticity failed: {e}',
                'knob': 'requirements.txt (scikit-fem) + image rebuild',
                'action': 'scikit-fem 10.x ships skfem.models.elasticity; '
                          'check the installed version.',
            },
        }


ELASTICITY_VALIDITY = (
    'LINEAR ELASTIC, SMALL STRAIN, 2D. Valid only for an intact body '
    'below yield: no plasticity, no crack growth, no contact, no large '
    'rotation, no fatigue, no thermal or cure-shrinkage residual '
    'stress. MESH-DEPENDENT at singularities — stress at a re-entrant '
    'corner or a point load does NOT converge, it grows without bound '
    'as the mesh refines, so a number reported there is a property of '
    'the mesh and not of the part. Around a smooth hole the stress DOES '
    'converge (P1 elements approach the true peak from BELOW, because '
    'element-constant stress averages the gradient). Always read '
    'elementCount and re-run at a finer refine to see which of the two '
    'you have.'
)


def _elastic_lame(youngs_modulus, poisson_ratio, assumption):
    """(lambda, mu, sigma_zz_factor) for the chosen 2D assumption.

    plane strain uses the 3D Lame parameters directly and carries a
    real out-of-plane stress sigma_zz = nu*(sxx+syy); plane stress
    substitutes the reduced (E*, nu*) pair and has sigma_zz = 0."""
    from skfem.models.elasticity import lame_parameters, plane_stress
    if assumption == 'plane-strain':
        lam, mu = lame_parameters(youngs_modulus, poisson_ratio)
        return lam, mu, float(poisson_ratio)
    lam, mu = lame_parameters(*plane_stress(youngs_modulus, poisson_ratio))
    return lam, mu, 0.0


def _mesh_rectangle(width, height, refine):
    """Structured triangulation of [0,width] x [0,height]."""
    import numpy as np
    from skfem import MeshTri
    n = max(4, 4 * int(refine))
    aspect = max(width, height) / max(min(width, height), 1e-12)
    nx = n if width >= height else max(4, int(round(n / aspect)))
    ny = n if height > width else max(4, int(round(n / aspect)))
    return MeshTri.init_tensor(np.linspace(0.0, width, nx + 1),
                               np.linspace(0.0, height, ny + 1))


def _mesh_rectangle_with_hole(width, height, hole_radius, hole_center,
                              refine, bias=2.0):
    """O-grid between a circular hole and the rectangle boundary.

    Rays are cast from the hole centre to the rectangle edge, so the
    hole may sit OFF-CENTRE — which is what a real part looks like (the
    Lavet stator's bore is at one end, not the middle). `bias` > 1
    clusters layers toward the hole, where the gradient is."""
    import numpy as np
    from skfem import MeshTri
    cx, cy = hole_center
    n_theta = max(24, 24 * int(refine))
    n_r = max(8, 6 + 6 * int(refine))
    theta = 2.0 * np.pi * np.arange(n_theta) / n_theta
    dx, dy = np.cos(theta), np.sin(theta)
    big = np.inf
    with np.errstate(divide='ignore', invalid='ignore'):
        tx = np.where(dx > 1e-14, (width - cx) / dx,
                      np.where(dx < -1e-14, cx / (-dx), big))
        ty = np.where(dy > 1e-14, (height - cy) / dy,
                      np.where(dy < -1e-14, cy / (-dy), big))
    r_out = np.minimum(tx, ty)
    if not np.all(np.isfinite(r_out)) or np.any(r_out <= hole_radius):
        return None
    xi = (np.arange(n_r + 1) / n_r) ** bias
    radius = hole_radius + (r_out[None, :] - hole_radius) * xi[:, None]
    points = np.vstack([(cx + radius * dx[None, :]).ravel(),
                        (cy + radius * dy[None, :]).ravel()])
    tris = []
    for j in range(n_r):
        for i in range(n_theta):
            i2 = (i + 1) % n_theta
            a00, a10 = j * n_theta + i, j * n_theta + i2
            a01, a11 = (j + 1) * n_theta + i, (j + 1) * n_theta + i2
            tris.append([a00, a10, a11])
            tris.append([a00, a11, a01])
    return MeshTri(points, np.array(tris, dtype=np.int64).T)


def _edge_predicate(edge, width, height):
    import numpy as np
    if edge == 'left':
        return lambda x: np.isclose(x[0], 0.0)
    if edge == 'right':
        return lambda x: np.isclose(x[0], width)
    if edge == 'bottom':
        return lambda x: np.isclose(x[1], 0.0)
    return lambda x: np.isclose(x[1], height)


def solve_elasticity_2d(width, height, youngs_modulus, poisson_ratio,
                        tractions=(), fixed_edges=(),
                        assumption='plane-stress', hole_radius=None,
                        hole_center=None, refine=3,
                        pin_rigid_body=False, include_field=False):
    """Plane linear elasticity on a rectangle, optionally with a hole.

    width, height        rectangle [0,width] x [0,height] (metres)
    youngs_modulus       E (Pa, > 0)
    poisson_ratio        nu, physically -1 < nu < 0.5
    tractions            ({'edge','tx','ty'}, ...) surface traction in Pa
    fixed_edges          ({'edge','dof': 'x'|'y'|'xy'}, ...)
    assumption           'plane-stress' | 'plane-strain'
    hole_radius/center   optional circular hole (centre defaults to the
                         rectangle centroid)
    refine               mesh knob; elementCount is reported
    pin_rigid_body       pin one node's y-DOF on the first fixed edge —
                         for a body restrained in x only, which is
                         otherwise free to translate/rotate

    Returns the STRESS TENSOR (sxx, syy, sxy, and szz, which is only
    zero in plane stress), VON MISES, and the PRINCIPAL stresses with
    their locations. Von Mises and max-principal are both returned
    deliberately: von Mises predicts yielding in DUCTILE metals, while
    a brittle cast ceramic or geopolymer fails on MAXIMUM PRINCIPAL
    TENSILE stress, and using the wrong one understates the risk.
    Choosing between them is the caller's job; this returns both.
    """
    cap = elastic_capability()
    if not cap['available']:
        return {'ok': False, 'error': 'FEM elasticity unavailable',
                'suggestion': cap['suggestion']}
    if assumption not in ELASTIC_ASSUMPTIONS:
        return {'ok': False,
                'error': f'assumption must be one of '
                         f'{ELASTIC_ASSUMPTIONS}, got "{assumption}"'}
    if youngs_modulus <= 0:
        return {'ok': False,
                'error': f'youngs_modulus must be > 0, got '
                         f'{youngs_modulus}'}
    if not (-1.0 < poisson_ratio < 0.5):
        return {'ok': False,
                'error': f'poisson_ratio must satisfy -1 < nu < 0.5 '
                         f'(0.5 is incompressible and singular here), '
                         f'got {poisson_ratio}'}
    if width <= 0 or height <= 0:
        return {'ok': False, 'error': 'width and height must be > 0'}
    if not tractions:
        return {'ok': False,
                'error': 'no tractions given — an unloaded body has '
                         'zero stress and nothing to report',
                'suggestion': {
                    'evidence': 'tractions=()',
                    'knob': 'tractions',
                    'action': "pass e.g. [{'edge': 'right', 'tx': 1e6}]"}}
    if not fixed_edges:
        return {'ok': False,
                'error': 'no fixed edges — the body is unrestrained and '
                         'the stiffness matrix is singular',
                'suggestion': {
                    'evidence': 'fixed_edges=()',
                    'knob': 'fixed_edges',
                    'action': "restrain at least one edge, e.g. "
                              "[{'edge': 'left', 'dof': 'x'}]"}}

    import numpy as np
    from skfem import (Basis, ElementTriP1, ElementVector, FacetBasis,
                       LinearForm, asm, condense, solve)
    from skfem.models.elasticity import linear_elasticity

    if hole_radius:
        centre = hole_center or (width / 2.0, height / 2.0)
        mesh = _mesh_rectangle_with_hole(width, height, hole_radius,
                                         centre, refine)
        if mesh is None:
            return {'ok': False,
                    'error': f'hole radius {hole_radius} does not fit '
                             f'inside the rectangle at centre {centre} '
                             f'— it reaches or crosses an edge'}
    else:
        centre = None
        mesh = _mesh_rectangle(width, height, refine)

    basis = Basis(mesh, ElementVector(ElementTriP1()))
    lam, mu, szz_factor = _elastic_lame(youngs_modulus, poisson_ratio,
                                        assumption)
    stiffness = asm(linear_elasticity(lam, mu), basis)

    load = basis.zeros()
    for spec in tractions:
        edge = spec.get('edge')
        if edge not in ELASTIC_EDGES:
            return {'ok': False,
                    'error': f'traction edge must be one of '
                             f'{ELASTIC_EDGES}, got "{edge}"'}
        tx_val = float(spec.get('tx', 0.0))
        ty_val = float(spec.get('ty', 0.0))
        facets = mesh.facets_satisfying(
            _edge_predicate(edge, width, height))
        if facets.size == 0:
            return {'ok': False,
                    'error': f'no facets found on edge "{edge}" — the '
                             f'mesh does not reach it'}
        fbasis = FacetBasis(mesh, basis.elem, facets=facets)

        @LinearForm
        def traction(v, w, _tx=tx_val, _ty=ty_val):
            return _tx * v[0] + _ty * v[1]

        load = load + asm(traction, fbasis)

    dirichlet = []
    for spec in fixed_edges:
        edge = spec.get('edge')
        if edge not in ELASTIC_EDGES:
            return {'ok': False,
                    'error': f'fixed edge must be one of '
                             f'{ELASTIC_EDGES}, got "{edge}"'}
        dof = spec.get('dof', 'xy')
        nodal = basis.get_dofs(_edge_predicate(edge, width, height)).nodal
        if dof in ('x', 'xy'):
            dirichlet.append(nodal['u^1'])
        if dof in ('y', 'xy'):
            dirichlet.append(nodal['u^2'])
    if pin_rigid_body:
        first = fixed_edges[0].get('edge')
        pred = _edge_predicate(first, width, height)
        on_edge = np.where(pred(mesh.p))[0]
        if on_edge.size:
            mid = height / 2.0 if first in ('left', 'right') else width / 2.0
            axis = 1 if first in ('left', 'right') else 0
            node = on_edge[np.argmin(np.abs(mesh.p[axis][on_edge] - mid))]
            dirichlet.append(np.array([2 * node + 1 if axis == 1
                                       else 2 * node]))
    dirichlet = np.unique(np.concatenate(dirichlet))

    displacement = solve(*condense(stiffness, load, D=dirichlet))

    # --- stress recovery (P1 => element-constant strain) -----------
    grad = np.array(basis.interpolate(displacement).grad)
    strain = 0.5 * (grad + grad.transpose(1, 0, 2, 3))
    trace = strain[0, 0] + strain[1, 1]
    sxx = (2.0 * mu * strain[0, 0] + lam * trace).mean(axis=1)
    syy = (2.0 * mu * strain[1, 1] + lam * trace).mean(axis=1)
    sxy = (2.0 * mu * strain[0, 1]).mean(axis=1)
    szz = szz_factor * (sxx + syy)

    von_mises = np.sqrt(
        0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
        + 3.0 * sxy ** 2)
    centre_s = 0.5 * (sxx + syy)
    radius_s = np.sqrt((0.5 * (sxx - syy)) ** 2 + sxy ** 2)
    s1_in_plane = centre_s + radius_s
    s2_in_plane = centre_s - radius_s
    # szz is itself a principal stress (no out-of-plane shear here), so
    # the true 3D extremes include it.
    max_principal = np.maximum(s1_in_plane, szz)
    min_principal = np.minimum(s2_in_plane, szz)

    centroids = mesh.p[:, mesh.t].mean(axis=1)

    def _at(values, use_max=True):
        idx = int(np.argmax(values) if use_max else np.argmin(values))
        return {'value': float(values[idx]),
                'atXY': [float(centroids[0][idx]),
                         float(centroids[1][idx])]}

    result = {
        'ok': True,
        'assumption': assumption,
        'assumptionNote': (
            'plane strain: epsilon_zz = 0, so sigma_zz = nu*(sxx+syy) '
            'is NOT zero and it enters von Mises'
            if assumption == 'plane-strain' else
            'plane stress: sigma_zz = 0 (a thin plate free to contract '
            'through its thickness)'),
        'youngsModulus': float(youngs_modulus),
        'poissonRatio': float(poisson_ratio),
        'geometry': {'width': float(width), 'height': float(height),
                     'holeRadius': (float(hole_radius) if hole_radius
                                    else None),
                     'holeCenter': ([float(centre[0]), float(centre[1])]
                                    if centre else None)},
        'elementCount': int(mesh.t.shape[1]),
        'degreesOfFreedom': int(displacement.shape[0]),
        'refine': int(refine),
        'maxVonMises': _at(von_mises),
        'maxPrincipal': _at(max_principal),
        'minPrincipal': _at(min_principal, use_max=False),
        'maxShear': _at(radius_s),
        'stressRange': {
            'sxx': [float(sxx.min()), float(sxx.max())],
            'syy': [float(syy.min()), float(syy.max())],
            'sxy': [float(sxy.min()), float(sxy.max())],
            'szz': [float(szz.min()), float(szz.max())],
        },
        'meanStress': {'sxx': float(sxx.mean()), 'syy': float(syy.mean()),
                       'sxy': float(sxy.mean()), 'szz': float(szz.mean())},
        'criterionNote': (
            'von Mises predicts YIELDING in ductile metals (copper, '
            'steel). A brittle cast ceramic or geopolymer instead fails '
            'on MAXIMUM PRINCIPAL TENSILE stress, at a tensile strength '
            'far below its compressive one — judging such a part by von '
            'Mises understates the risk. Both are returned; pick by '
            'material, and say which you picked.'),
        'validity': ELASTICITY_VALIDITY,
    }
    if include_field:
        result['field'] = {
            'centroidX': [float(v) for v in centroids[0]],
            'centroidY': [float(v) for v in centroids[1]],
            'sxx': [float(v) for v in sxx],
            'syy': [float(v) for v in syy],
            'sxy': [float(v) for v in sxy],
            'szz': [float(v) for v in szz],
            'vonMises': [float(v) for v in von_mises],
            'maxPrincipal': [float(v) for v in max_principal],
        }
        result['fieldNote'] = ('per-ELEMENT values (P1 => constant '
                               'strain per element), ordered as mesh.t')
    return result


def elasticity_mesh_convergence(refines=(1, 2, 3), **kwargs):
    """Run the same problem at several refine levels so the caller can
    SEE whether a reported peak is converging or just tracking the mesh.

    Returns {'ok', 'levels': [{refine, elementCount, maxVonMises,
    maxPrincipal}], 'converging', 'note'}. `converging` is True when the
    last relative change is under 2% — a smooth feature. A singularity
    keeps climbing and this stays False, which is the answer, not a
    failure."""
    kwargs.pop('refine', None)
    kwargs.pop('include_field', None)
    levels = []
    for level in refines:
        out = solve_elasticity_2d(refine=level, **kwargs)
        if not out.get('ok'):
            return out
        levels.append({
            'refine': int(level),
            'elementCount': out['elementCount'],
            'maxVonMises': out['maxVonMises']['value'],
            'maxPrincipal': out['maxPrincipal']['value'],
        })
    converging = None
    if len(levels) >= 2:
        last, prev = levels[-1]['maxPrincipal'], levels[-2]['maxPrincipal']
        if abs(last) > 0:
            converging = bool(abs(last - prev) / abs(last) < 0.02)
    return {
        'ok': True, 'levels': levels, 'converging': converging,
        'note': ('peak max-principal changed by under 2% on the last '
                 'refinement — treat it as a converged, real number'
                 if converging else
                 'peak max-principal is STILL MOVING with the mesh — '
                 'either refine further, or recognise it as a '
                 'singularity (sharp corner / point load) where no '
                 'converged value exists'),
        'validity': ELASTICITY_VALIDITY,
    }


# ---------------------------------------------------------------- #
# MAGNETOSTATICS — 2D vector-potential solve, for INDUCTANCE
#
# mag-23. The mag-22 power claim rested on a coil reaching its final
# current inside a 30 ms pulse, and named INDUCTANCE as the largest
# unmodelled risk to it. Naming a risk is not modelling it, so this
# solves the field.
#
# Formulation: in 2D the vector potential has one component, A_z, and
# curl-curl collapses to a variable-coefficient Poisson problem
#     -div( nu grad A_z ) = J_z ,   nu = 1/mu
# with B = curl A = (dA/dy, -dA/dx), so |B| = |grad A_z|. Stored
# energy is W = 1/2 * integral( nu |grad A_z|^2 ), and the inductance
# follows from W = 1/2 L i^2.
#
# Regions carry their own mu_r as DATA — a list of rectangles, not a
# hard-coded geometry — so the same solver serves any planar magnetic
# circuit the catalogue can describe.
# ---------------------------------------------------------------- #

MU0 = 4.0e-7 * 3.141592653589793


def magnetostatic_capability():
    """What this solver does and, more usefully, what it does not."""
    try:
        import skfem                                    # noqa: F401
        available = True
        why = ''
    except ImportError as exc:                          # pragma: no cover
        available, why = False, str(exc)
    return {
        'ok': True, 'available': available, 'why': why,
        'formulation': '2D magnetostatic vector potential A_z, '
                       'variable-coefficient Poisson, linear',
        'solves': ['flux density field B = |grad A_z|',
                   'stored magnetic energy W',
                   'inductance L = 2W / i^2',
                   'flux linkage lambda = N * Phi'],
        'doesNot': [
            'SATURATION — mu is constant per region, so a core driven '
            'past its knee is modelled as if it were not. For a clock '
            'coil at milliamps this is comfortable; for a motor at '
            'rated torque it is not.',
            'EDDY CURRENTS and any frequency dependence — this is '
            'magnetoSTATIC. Inductance from it is the low-frequency '
            'value.',
            'HYSTERESIS, and therefore core loss.',
            '3D leakage. A planar slice through a device whose flux '
            'leaves the plane will UNDERSTATE reluctance and so '
            'OVERSTATE inductance.',
        ],
    }


def _mesh_aligned_to_features(width, height, rects, refine):
    """Tensor mesh whose grid LINES fall on every region boundary.

    This is the structural fix to the gap-shorting failure. A uniform
    mesh assigns each element the permeability at its centroid, so an
    element straddling a 0.8 mm gap can take the CORE value and short
    the gap out — the solve then returns a confident number that was
    wrong by two orders in testing. Detecting that afterwards is
    second best; making it impossible is better.

    Every region edge becomes a grid line, so no element spans two
    materials no matter how coarse the mesh. Refinement then controls
    ACCURACY only, not correctness, and small features stay cheap
    because only the interval containing them is subdivided finely.
    """
    import numpy as np
    from skfem import MeshTri

    def axis(lo, hi, cuts):
        pts = sorted({round(float(c), 12) for c in cuts
                      if lo - 1e-15 <= c <= hi + 1e-15}
                     | {float(lo), float(hi)})
        target = (hi - lo) / max(4, 4 * int(refine))
        out = []
        for a, b in zip(pts[:-1], pts[1:]):
            span = b - a
            if span <= 0:
                continue
            k = max(1, int(np.ceil(span / target)))
            out.extend(np.linspace(a, b, k + 1)[:-1])
        out.append(pts[-1])
        return np.array(out)

    xs = axis(0.0, float(width),
              [c for r in rects for c in (r['x0'], r['x1'])])
    ys = axis(0.0, float(height),
              [c for r in rects for c in (r['y0'], r['y1'])])
    return MeshTri.init_tensor(xs, ys)


def _region_nu(mesh, regions, background_mu_r):
    """Per-element reluctivity from a list of rectangular regions.

    Regions are tested in order and the LAST match wins, so a caller
    may lay a gap over a core the way one draws it."""
    import numpy as np
    centres = mesh.p[:, mesh.t].mean(axis=1)
    mu_r = np.full(mesh.t.shape[1], float(background_mu_r))
    for reg in regions:
        x0, y0, x1, y1 = (float(reg['x0']), float(reg['y0']),
                          float(reg['x1']), float(reg['y1']))
        inside = ((centres[0] >= x0) & (centres[0] <= x1)
                  & (centres[1] >= y0) & (centres[1] <= y1))
        mu_r[inside] = float(reg['mu_r'])
    return 1.0 / (MU0 * mu_r), mu_r


def solve_magnetostatic_2d(width, height, regions=(), coils=(),
                           turns=1.0, current=1.0, depth=None,
                           background_mu_r=1.0, refine=3,
                           include_field=False, flux_cut=None):
    """Solve -div(nu grad A_z) = J_z and report the INDUCTANCE.

    `regions`  : rectangles {x0,y0,x1,y1,mu_r} — the magnetic circuit.
    `coils`    : rectangles {x0,y0,x1,y1,sign} — conductor windows. A
                 planar slice cuts a coil TWICE, so the go and return
                 sides carry opposite sign; a caller giving only one
                 side gets a warning rather than a silently wrong L.
    `turns`    : N. Current density is N*i/area, so L comes out with
                 its N^2 already in it.
    `flux_cut` : ((x0,y0),(x1,y1)) spanning the flux path, for the
                 independent cross-check. Strongly recommended.
    `depth`    : out-of-plane length (m). Defaults to width, and the
                 payload says so, because L scales linearly with it.

    Outer boundary is A_z = 0: flux is confined to the domain. That is
    a MODELLING CHOICE — too tight a box squeezes the return path and
    overstates reluctance. Grow the domain and watch L settle.
    """
    try:
        import numpy as np
        from skfem import (Basis, BilinearForm, ElementTriP0,
                           ElementTriP1, LinearForm, asm, condense,
                           solve)
        from skfem.helpers import dot, grad
    except ImportError as exc:
        return {'ok': False,
                'refusal': f'scikit-fem is not available ({exc}) — '
                           f'this returns NO inductance rather than a '
                           f'closed-form guess dressed as a solve'}
    if current == 0:
        return {'ok': False,
                'refusal': 'inductance is defined from energy at a '
                           'stated current; zero current gives 0/0'}
    depth = float(depth if depth else width)

    # RESOLUTION GUARD. This is not a nicety: a mesh too coarse for
    # the smallest feature does not degrade gracefully. Elements
    # straddling a gap take the core's mu_r from their centroid and
    # SHORT THE GAP OUT, and the solver returns a confident number
    # that was wrong by 150x in testing — larger domain, same refine,
    # inductance up two orders. Nothing in the solution looks amiss.
    # So the smallest feature must be measured against the element
    # size and the solve REFUSED when it cannot be resolved.
    features = []
    for reg in list(regions) + list(coils):
        w_r = abs(float(reg['x1']) - float(reg['x0']))
        h_r = abs(float(reg['y1']) - float(reg['y0']))
        features.extend([w_r, h_r])
    features = [f for f in features if f > 0]
    if features:
        smallest = min(features)
        n_cells = max(4, 4 * int(refine))
        h_elem = max(float(width), float(height)) / n_cells
        spans = smallest / h_elem
        # With a feature-aligned mesh no element straddles a material
        # boundary, so a coarse mesh costs ACCURACY rather than
        # correctness. The refusal is kept only for the degenerate
        # case where a feature gets no interior resolution at all.
        if spans < 0.5:
            needed = int(-(-(3.0 * max(float(width), float(height))
                             / smallest) // 4))
            return {
                'ok': False, 'kind': 'under-resolved',
                'refusal': (
                    f'the mesh cannot resolve this geometry: the '
                    f'smallest feature is {smallest * 1e3:.3g} mm and '
                    f'an element is {h_elem * 1e3:.3g} mm, so only '
                    f'{spans:.1f} elements span it (3 is the '
                    f'minimum). Elements straddling a gap take the '
                    f'CORE permeability from their centroid and short '
                    f'the gap out — the solve would return a '
                    f'confidently wrong inductance, not a noisy one.'),
                'smallestFeatureM': smallest,
                'elementSizeM': h_elem,
                'suggestion': {
                    'knob': 'refine',
                    'action': f'raise refine to at least {needed}, or '
                              f'shrink the domain — cost grows as '
                              f'refine^2'},
            }
    mesh = _mesh_aligned_to_features(
        float(width), float(height),
        list(regions) + list(coils), refine)
    basis = Basis(mesh, ElementTriP1())
    p0 = Basis(mesh, ElementTriP0())
    nu_vec, mu_r_vec = _region_nu(mesh, regions, background_mu_r)

    centres = mesh.p[:, mesh.t].mean(axis=1)
    j_vec = np.zeros(mesh.t.shape[1])
    signs = set()
    total_coil_area = 0.0
    for coil in coils:
        x0, y0, x1, y1 = (float(coil['x0']), float(coil['y0']),
                          float(coil['x1']), float(coil['y1']))
        sign = float(coil.get('sign', 1.0))
        signs.add(1 if sign > 0 else -1)
        inside = ((centres[0] >= x0) & (centres[0] <= x1)
                  & (centres[1] >= y0) & (centres[1] <= y1))
        area = float((x1 - x0) * (y1 - y0))
        if area <= 0 or not inside.any():
            continue
        total_coil_area += area
        j_vec[inside] = sign * float(turns) * float(current) / area

    if not coils or not np.any(j_vec):
        return {'ok': False,
                'refusal': 'no coil region carries current — there is '
                           'no source, so A_z is identically zero and '
                           'any inductance reported would be an '
                           'artefact of the mesh'}

    @BilinearForm
    def stiffness(u, v, w):
        return w['nu'] * dot(grad(u), grad(v))

    @LinearForm
    def source(v, w):
        return w['j'] * v

    nu_f = p0.interpolate(nu_vec)
    j_f = p0.interpolate(j_vec)
    K = asm(stiffness, basis, nu=nu_f)
    f = asm(source, basis, j=j_f)
    boundary = basis.get_dofs()
    a_z = solve(*condense(K, f, D=boundary))

    # W = 1/2 integral(nu |grad A|^2) per unit depth. The stiffness
    # form IS that integral, so the quadratic form gives it exactly
    # and consistently with the discretisation that produced A.
    energy_per_m = 0.5 * float(a_z @ (K @ a_z))
    energy = energy_per_m * depth
    inductance = 2.0 * energy / (float(current) ** 2)

    # GENUINELY INDEPENDENT CROSS-CHECK, and it has to be earned: an
    # earlier pass computed a_z @ f and called it flux linkage, but
    # for a linear system a.K.a == a.f, so that number IS 2W and
    # re-derives the energy route rather than testing it.
    #
    # The real identity: in 2D, the flux crossing any surface
    # spanning two points equals A_z(P1) - A_z(P2) per unit depth.
    # So a cut placed across the flux path gives Phi directly, and
    # L = N*Phi/i is computed from the FIELD, not from the energy.
    linkage = None
    l_from_linkage = None
    if flux_cut:
        (px0, py0), (px1, py1) = flux_cut
        probe = np.array([[float(px0), float(px1)],
                          [float(py0), float(py1)]])
        try:
            vals = basis.probes(probe) @ a_z
            phi = float(vals[0] - vals[1]) * depth
            linkage = float(turns) * phi
            l_from_linkage = linkage / float(current)
        except Exception:                               # noqa: BLE001
            linkage = l_from_linkage = None

    grad_a = basis.interpolate(a_z).grad
    b_mag = np.sqrt(grad_a[0] ** 2 + grad_a[1] ** 2)
    b_peak = float(np.max(b_mag))

    warnings = []
    if features and smallest / (max(float(width), float(height))
                                / max(4, 4 * int(refine))) < 3.0:
        warnings.append(
            f'the smallest feature ({smallest * 1e3:.2g} mm) gets few '
            f'elements across it. The mesh is ALIGNED to region '
            f'boundaries so no element straddles two materials — the '
            f'result is not corrupted — but the gradient inside that '
            f'feature is coarsely resolved. Raise refine and confirm '
            f'L settles.')
    if len(signs) < 2:
        warnings.append(
            'only ONE coil sign was given. A planar slice cuts a real '
            'coil twice, and a single-sided source drives flux out of '
            'the domain instead of around a circuit — L from this is '
            'not the device inductance.')
    if b_peak > 1.2:
        warnings.append(
            f'peak |B| is {b_peak:.2f} T, which is at or past the knee '
            f'of most soft magnetic materials. This solver is LINEAR, '
            f'so it does not saturate and therefore OVERSTATES both '
            f'flux and inductance here.')

    out = {
        'ok': True,
        'inductanceH': inductance,
        'inductanceFromLinkageH': l_from_linkage,
        'crossCheckRatio': (l_from_linkage / inductance
                            if (inductance and l_from_linkage)
                            else None),
        'crossCheckNote': (
            'L from a flux CUT (A_z difference across the path) '
            'against L from stored ENERGY — two different routes '
            'through the same solution. Agreement near 1.0 means the '
            'field is self-consistent; it does NOT mean the geometry '
            'or the permeabilities are right.'
            if l_from_linkage else
            'no flux_cut given, so the energy route stands '
            'UNCHECKED — pass two points spanning the flux path'),
        'energyJ': energy, 'peakBT': b_peak,
        'fluxLinkageWb': linkage,
        'turns': float(turns), 'currentA': float(current),
        'depthM': depth, 'depthWasDefaulted': not bool(depth),
        'coilAreaM2': total_coil_area,
        'muRRange': [float(mu_r_vec.min()), float(mu_r_vec.max())],
        'dofs': int(basis.N), 'elements': int(mesh.t.shape[1]),
        'refine': refine,
        'meshAlignedToFeatures': True,
        'warnings': warnings,
        'method': 'scikit-fem P1 vector potential, variable-nu '
                  'Poisson; L from stored energy, cross-checked '
                  'against flux linkage',
        'validity': 'LINEAR magnetostatics: no saturation, no eddy '
                    'currents, no hysteresis, and a Dirichlet box '
                    'that confines flux. L is the low-frequency '
                    'value.',
    }
    if include_field:
        out['field'] = {
            'aZ': a_z.tolist(),
            'points': mesh.p.T.tolist(),
            'triangles': mesh.t.T.tolist(),
        }
    return out


def inductance_mesh_convergence(refines=(2, 3, 4), **kwargs):
    """L against mesh refinement. A number that moves with the mesh
    is a mesh artefact, and this is how you tell."""
    runs = []
    for r in refines:
        out = solve_magnetostatic_2d(refine=r, **kwargs)
        if not out.get('ok'):
            return out
        runs.append({'refine': r, 'dofs': out['dofs'],
                     'inductanceH': out['inductanceH'],
                     'peakBT': out['peakBT']})
    values = [r['inductanceH'] for r in runs]
    drift = (abs(values[-1] - values[-2]) / abs(values[-1])
             if len(values) > 1 and values[-1] else None)
    return {
        'ok': True, 'runs': runs,
        'finestH': values[-1],
        'relativeChangeLastStep': drift,
        'converged': bool(drift is not None and drift < 0.05),
        'note': 'convergence here means the DISCRETISATION has '
                'settled. It says nothing about whether the geometry, '
                'the permeabilities or the boundary box are right.',
    }
