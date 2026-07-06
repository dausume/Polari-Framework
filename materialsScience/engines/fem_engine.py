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
