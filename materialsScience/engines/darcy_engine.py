"""
@cross-cutting
@module materialsScience.engines.darcy_engine
@tags @xc:bindings

Scalar Darcy flow engine (aqp-3) — steady saturated groundwater flow
through a porous medium, ∇·(K∇h) = source, the SAME elliptic operator
as fem_engine.solve_steady_conduction with hydraulic conductivity K
(m/s) in place of thermal k and hydraulic HEAD h (m) in place of T.

Domain: a 2-D VERTICAL CROSS-SECTION of a self-watering pot's soil
column (width = inner diameter, height = soil column), meshed with
scikit-fem MeshTri/ElementTriP1. Holes in the pot wall become
Dirichlet patches on the side boundaries:

  input hole   h = water_level (hydrostatic connection to the supply)
  output hole  h = z_hole      (open to atmosphere: p = 0, so total
                                head equals the hole's elevation)

everything else is a no-flux natural boundary (waterproof wall).
Outflow is recovered from the discrete reaction flux at the output
Dirichlet nodes ((A·h)_i with zero interior load = the boundary flux
integral carried by node i) — flux per unit thickness in 2-D,
converted to a volumetric rate using the hole diameter as the
effective slot thickness (stated in the result; the 2-D
approximation IS the fidelity ceiling here, full 3-D/Navier–Stokes is
out of scope).

Resolution ladder (same as dft_engine.molecular_energy): local skfem
when importable, else the msci-engines worker via remote_post
('/darcy/...' — topology-routed, no env var needed), else an honest
refusal carrying the knob. The worker-side twin of _solve_local lives
in msci-engines/engines_service.py (DarcyHeadFieldResource) — keep
them in sync.

Units discipline: everything entering this module is SI (metres,
m/s); callers convert from mm geometry ONCE (aquaponics/hydraulics.py
does) and every result carries its units in the key names.
"""


def capability():
    """{'available': bool, 'library': 'scikit-fem', ...} — never raises."""
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
                'knob': 'MSCI_ENGINES_URL / topology engines provider',
                'action': 'The msci-engines worker carries scikit-fem; '
                          'keep it running in the topology (pol compose '
                          'engines up) and the ladder resolves it.',
            },
        }


def _validate_payload(payload):
    """Shared payload checks; returns an error string or ''."""
    geometry = payload.get('geometry') or {}
    if float(geometry.get('width_m', 0) or 0) <= 0 \
            or float(geometry.get('height_m', 0) or 0) <= 0:
        return 'geometry.width_m and geometry.height_m must be > 0'
    if float(payload.get('k_m_per_s', 0) or 0) <= 0:
        return 'k_m_per_s (hydraulic conductivity) must be > 0'
    holes = payload.get('holes') or []
    if not any(h.get('kind') == 'output' for h in holes):
        return 'at least one output hole is required'
    return ''


def _solve_local(payload):
    """The actual skfem solve. payload (all SI):
      {'geometry': {'width_m', 'height_m'},
       'k_m_per_s': K,
       'water_level_m': L,           # head at the input / supply
       'holes': [{'kind': 'input'|'output', 'z_m': elevation of the
                  hole CENTER, 'radius_m': bore radius,
                  'side': 'left'|'right'}, ...],
       'refine': mesh refinement (default 6),
       'source': volumetric source (default 0.0)}

    Returns {'ok': True, 'headField': [[x_m, z_m, h_m], ...],
             'outflowRateM3s', 'outflowRateMlS', 'inflowRateM3s',
             'fluxStats': {...}, 'meshMeta': {...}, 'note'} or
            {'ok': False, 'error'}.

    WORKER TWIN: msci-engines/engines_service.py duplicates this body
    (the worker has no framework import path) — port changes there.
    """
    error = _validate_payload(payload)
    if error:
        return {'ok': False, 'error': error}

    import numpy as np
    from skfem import (MeshTri, Basis, ElementTriP1, asm, condense,
                       solve, BilinearForm)
    from skfem.helpers import dot, grad

    geometry = payload['geometry']
    width = float(geometry['width_m'])
    height = float(geometry['height_m'])
    conductivity = float(payload['k_m_per_s'])
    water_level = float(payload.get('water_level_m', height) or height)
    refine = int(payload.get('refine', 6) or 6)

    mesh = MeshTri().refined(refine).scaled([width, height])
    basis = Basis(mesh, ElementTriP1())
    spacing = max(width, height) / (2 ** refine)

    @BilinearForm
    def darcy(u, v, _):
        return conductivity * dot(grad(u), grad(v))

    stiffness = asm(darcy, basis)

    def _patch_dofs(hole):
        """Boundary nodes on the hole's side wall within the bore."""
        x_wall = 0.0 if hole.get('side', 'left') == 'left' else width
        z_center = float(hole['z_m'])
        halfspan = max(float(hole.get('radius_m', 0.005) or 0.005),
                       0.75 * spacing)   # guarantee >= 1 node
        return basis.get_dofs(
            lambda x: (np.abs(x[0] - x_wall) < 1e-9)
                      & (np.abs(x[1] - z_center) <= halfspan))

    head = basis.zeros()
    input_dofs, output_dofs = [], []
    for hole in payload.get('holes', []):
        dofs = _patch_dofs(hole)
        flat = np.array(dofs.flatten(), dtype=int)
        if flat.size == 0:
            return {'ok': False,
                    'error': f"hole at z={hole.get('z_m')} m matched no "
                             f'mesh nodes (mesh spacing {spacing:.4g} m) '
                             f'— raise refine'}
        if hole.get('kind') == 'input':
            head[flat] = water_level
            input_dofs.append(flat)
        else:
            head[flat] = float(hole['z_m'])
            output_dofs.append(flat)
    dirichlet = np.unique(np.concatenate(input_dofs + output_dofs))

    load = basis.zeros()
    source = float(payload.get('source', 0.0) or 0.0)
    if source:
        from skfem.models.poisson import unit_load
        load = source * asm(unit_load, basis)

    head = solve(*condense(stiffness, load, x=head, D=dirichlet))

    # Discrete reaction flux at Dirichlet nodes: with zero interior
    # residual, (A·h - f)_i = ∫ K∇h·n φ_i dΓ (outward normal, per unit
    # thickness). Darcy flux is q = -K∇h, so water LEAVING through a
    # patch is the NEGATED reaction sum there (and water entering at
    # the input is the positive reaction sum).
    reaction = stiffness @ head - load
    outflow_per_thickness = float(-sum(
        reaction[flat].sum() for flat in output_dofs))
    inflow_per_thickness = float(sum(
        reaction[flat].sum() for flat in input_dofs))

    # Effective slot thickness: the bore diameter of the (largest)
    # output hole — the stated 2-D -> volumetric approximation.
    out_holes = [h for h in payload.get('holes', [])
                 if h.get('kind') == 'output']
    thickness = max(2.0 * float(h.get('radius_m', 0.005) or 0.005)
                    for h in out_holes)
    outflow_m3s = outflow_per_thickness * thickness
    inflow_m3s = inflow_per_thickness * thickness

    # Per-element Darcy speed |−K∇h| (P1 -> constant gradient/element).
    p, t = mesh.p, mesh.t
    x1, y1 = p[:, t[0]]
    x2, y2 = p[:, t[1]]
    x3, y3 = p[:, t[2]]
    det = (x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)
    h1, h2, h3 = head[t[0]], head[t[1]], head[t[2]]
    grad_x = ((h2 - h1) * (y3 - y1) - (h3 - h1) * (y2 - y1)) / det
    grad_z = ((h3 - h1) * (x2 - x1) - (h2 - h1) * (x3 - x1)) / det
    speed = conductivity * np.sqrt(grad_x ** 2 + grad_z ** 2)

    head_field = [[round(float(x), 5), round(float(z), 5),
                   round(float(v), 6)]
                  for x, z, v in zip(mesh.p[0], mesh.p[1], head)]
    # Triangle connectivity (node indices into headField, one triple per
    # element) — 2026-07-15, aquaponics-pot-shape phase 3: without this
    # a caller only has a scattered point cloud, not a real surface to
    # triangulate for the water-flow visualization. mesh.t is (3, n).
    triangles = [[int(a), int(b), int(c)]
                for a, b, c in zip(mesh.t[0], mesh.t[1], mesh.t[2])]
    return {
        'ok': True, 'engine': 'scikit-fem', 'fidelity': 'fem',
        'headField': head_field,
        'headFieldColumns': ['x_m', 'z_m', 'head_m'],
        'headFieldTriangles': triangles,
        'outflowRateM3s': outflow_m3s,
        'outflowRateMlS': outflow_m3s * 1e6,
        'inflowRateM3s': inflow_m3s,
        'fluxStats': {'maxDarcySpeedMs': float(np.max(speed)),
                      'meanDarcySpeedMs': float(np.mean(speed))},
        'meshMeta': {'elements': int(mesh.t.shape[1]),
                     'nodes': int(mesh.p.shape[1]),
                     'refine': refine, 'spacingM': spacing,
                     'widthM': width, 'heightM': height},
        'note': '2-D vertical cross-section; volumetric rates use the '
                'output bore diameter as effective slot thickness — an '
                'approximation, stated here. Full 3-D / Navier-Stokes '
                'is out of scope (fidelity ceiling).',
    }


def solve_head_field(payload):
    """The ladder: local skfem -> msci-engines worker -> refusal."""
    if capability()['available']:
        return _solve_local(payload)
    from materialsScience.engines.remote import remote_post
    return remote_post('/darcy/head-field', payload)


def drains_by_gravity(payload):
    """The headline answer: does this pot drain by gravity?

    Same payload as solve_head_field. Returns {'ok', 'drains': bool,
    'outflowRateMlS', 'evidence', 'limitingFactor', 'fidelity'} —
    a refusal (with suggestion) when no solver is reachable.
    """
    error = _validate_payload(payload)
    if error:
        return {'ok': False, 'error': error}
    water_level = float(payload.get('water_level_m', 0) or 0)
    lowest_output = min(float(h['z_m']) for h in payload['holes']
                        if h.get('kind') == 'output')
    if water_level <= lowest_output:
        return {'ok': True, 'drains': False, 'fidelity': 'geometric',
                'outflowRateMlS': 0.0,
                'limitingFactor': 'water table at/below the lowest '
                                  'output hole',
                'evidence': f'water level {water_level:.4g} m <= lowest '
                            f'output lip {lowest_output:.4g} m — no head '
                            f'difference drives flow',
                }
    result = solve_head_field(payload)
    if not result.get('ok'):
        return result
    outflow_mls = float(result.get('outflowRateMlS', 0.0))
    drains = outflow_mls > 1e-9
    return {
        'ok': True, 'drains': drains,
        'outflowRateMlS': outflow_mls,
        'fidelity': result.get('fidelity', 'fem'),
        'limitingFactor': None if drains else
            'computed outflow ~ 0 despite positive head — check K and '
            'hole placement',
        'evidence': f'steady Darcy solve: water level '
                    f'{water_level:.4g} m vs lowest output '
                    f'{lowest_output:.4g} m; outflow '
                    f'{outflow_mls:.4g} mL/s '
                    f"({result.get('meshMeta', {}).get('elements', '?')} "
                    f'elements)',
        'meshMeta': result.get('meshMeta'),
    }
