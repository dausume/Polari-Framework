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
