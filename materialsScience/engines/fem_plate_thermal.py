"""
@cross-cutting
@module materialsScience.engines.fem_plate_thermal

Steady heat spreading in a THIN PLATE that loses heat from both faces -
the standard finite-element formulation of a board (or any fin-like
sheet), solved with the same open-source library as fem_engine
(scikit-fem). Nothing here is a new model; it is the textbook one:

    -div( K grad(theta) ) + 2 h theta = q''          on the plate
     K grad(theta) . n = 0                           on the edges
    theta = T - T_ambient
    K   = sum_i k_i t_i  (W/K) - the plate's SHEET CONDUCTANCE: in-plane
          conduction through layers in parallel (each layer's
          conductivity x its thickness), per element, so copper pours
          raise it only where they are
    h   = convection coefficient of each face (W/m2K), both faces
    q'' = heat input per unit area (W/m2)

The plate is thin compared with its width, so temperature through the
thickness is taken as uniform (the fin approximation; Incropera &
DeWitt ch. 3.6). Edge loss is left out (the edge area is the thickness
times the perimeter - small for a board, and said).

Two checks are built into every solve, the way effective_conductivity
checks its bounds:
  - ENERGY BALANCE: in steady state everything put in leaves through
    the faces, so the integral of 2 h theta over the plate equals the sum
    of the sources. Reported as balanceError.
  - MEAN RISE: the same balance makes the area-mean rise exactly
    P / (h 2A) - the lumped first-order estimate - so the FEM agrees
    with that number on the mean and adds where the heat actually sits.

Units are SI throughout (metres, W, W/K); callers convert.
Geometry: rectangles {'x0','y0','x1','y1'} or polygons {'polygon':
[[x, y], ...]}. The mesh grid lines fall on every rectangle edge
(fem_engine._mesh_aligned_to_features), so a source or a rectangular
pour never straddles an element; a polygon is assigned by element
centroid, so its boundary is resolved only to the mesh spacing (said
on the payload, and plate_mesh_convergence measures it).
"""

from materialsScience.engines.fem_engine import capability, _mesh_aligned_to_features, _tri_areas


def _inside(centres, region):
    """Element centroids inside one region (rectangle, or polygon by the even-odd ray cast)."""
    import numpy as np
    x, y = centres
    if 'polygon' in region:
        pts = np.asarray(region['polygon'], dtype=float)
        inside = np.zeros(x.shape, dtype=bool)
        for (xa, ya), (xb, yb) in zip(pts, np.roll(pts, -1, axis=0)):
            crosses = (ya > y) != (yb > y)
            with np.errstate(divide='ignore', invalid='ignore'):
                xc = xa + (y - ya) * (xb - xa) / (yb - ya)
            inside ^= crosses & (x < xc)
        return inside
    return ((x >= region['x0']) & (x <= region['x1'])
            & (y >= region['y0']) & (y <= region['y1']))


def _bounds(region):
    if 'polygon' in region:
        xs = [p[0] for p in region['polygon']]
        ys = [p[1] for p in region['polygon']]
        return min(xs), min(ys), max(xs), max(ys)
    return region['x0'], region['y0'], region['x1'], region['y1']


def _sample(mesh, values, xs, ys):
    """The nodal field on a drawing grid. The mesh is a tensor grid, so its nodes ARE a grid: interpolate along it (bilinear between
    nodes - the map is for looking at; every reported number comes from the nodal solution itself)."""
    import numpy as np
    from scipy.interpolate import RegularGridInterpolator
    ux, uy = np.unique(mesh.p[0]), np.unique(mesh.p[1])
    grid = np.zeros((ux.size, uy.size))
    grid[np.searchsorted(ux, mesh.p[0]), np.searchsorted(uy, mesh.p[1])] = values
    gx, gy = np.meshgrid(xs, ys)
    return RegularGridInterpolator((ux, uy), grid)(np.column_stack([gx.ravel(), gy.ravel()])).reshape(len(ys), len(xs))


def solve_plate_conduction_2d(width, height, base_k_sheet, h, sources=(), regions=(), refine=6, grid=(24, 0)):
    """Steady temperature rise of a thin rectangular plate [0,width] x [0,height] (m).

    base_k_sheet: sheet conductance everywhere (W/K, > 0)
    h: convection coefficient of EACH face (W/m2K, > 0)
    sources: [{'name', 'power_w', + a rectangle}] - spread uniformly over it
    regions: [{'name', 'add_k_sheet', + a rectangle or polygon}] - ADDED to
        the sheet conductance where they lie (copper in parallel)
    grid: (columns, rows) of the sampled map for drawing; rows 0 = keep
        the plate's aspect

    Returns {'ok', 'maxRise', 'meanRise', 'minRise', 'lumpedMeanRise',
    'inputW', 'lostW', 'balanceError', 'spreadingLength', 'sources':
    [{name, power_w, peakRise, meanRise}], 'map': {xs, ys, rise}, 'dofs',
    'elements', 'notes'} or {'ok': False, 'error', 'suggestion'?}.
    """
    cap = capability()
    if not cap['available']:
        return {'ok': False, 'error': 'FEM engine unavailable', 'suggestion': cap['suggestion']}
    if width <= 0 or height <= 0:
        return {'ok': False, 'error': 'the plate needs a width and a height > 0, got %r x %r' % (width, height)}
    if base_k_sheet <= 0 or h <= 0:
        return {'ok': False, 'error': 'sheet conductance and h must be > 0, got K = %r W/K, h = %r W/m2K' % (base_k_sheet, h)}
    for s in sources:
        x0, y0, x1, y1 = _bounds(s)
        if not (x1 > x0 and y1 > y0) or s['power_w'] < 0:
            return {'ok': False, 'error': 'source %r needs an area and power >= 0' % s.get('name')}

    import numpy as np
    from skfem import Basis, ElementTriP1, ElementTriP0, BilinearForm, LinearForm, Functional, asm, solve
    from skfem.helpers import dot, grad

    rects = [dict(zip(('x0', 'y0', 'x1', 'y1'), _bounds(r))) for r in list(sources) + [r for r in regions if 'polygon' not in r]]
    mesh = _mesh_aligned_to_features(width, height, rects, refine)
    basis = Basis(mesh, ElementTriP1())
    basis0 = basis.with_element(ElementTriP0())
    centres = mesh.p[:, mesh.t].mean(axis=1)
    areas = _tri_areas(mesh)

    k_sheet = np.full(mesh.t.shape[1], float(base_k_sheet))
    for r in regions:
        k_sheet[_inside(centres, r)] += float(r['add_k_sheet'])
    q = np.zeros(mesh.t.shape[1])
    covered = []
    for s in sources:
        inside = _inside(centres, s)
        area = float(np.sum(areas[inside]))
        if area <= 0:
            return {'ok': False, 'error': 'source %r falls off the plate' % s.get('name')}
        q[inside] += float(s['power_w']) / area  # normalised on the meshed area, so it puts in exactly power_w
        covered.append(inside)

    @BilinearForm
    def plate(u, v, w):
        return w['kk'] * dot(grad(u), grad(v)) + 2.0 * h * u * v

    @LinearForm
    def heat(v, w):
        return w['qq'] * v

    kk, qq = basis0.interpolate(k_sheet), basis0.interpolate(q)
    rise = solve(asm(plate, basis, kk=kk), asm(heat, basis, qq=qq))

    @Functional
    def lost(w):
        return 2.0 * h * w['t']

    lost_w = float(lost.assemble(basis, t=basis.interpolate(rise)))
    input_w = float(sum(s['power_w'] for s in sources))
    elem_rise = rise[mesh.t].mean(axis=0)
    total_area = float(np.sum(areas))

    per_source = []
    for s, inside in zip(sources, covered):
        nodes = np.unique(mesh.t[:, inside])
        per_source.append({'name': s.get('name', ''), 'power_w': float(s['power_w']), 'peakRise': float(np.max(rise[nodes])),
                           'meanRise': float(np.sum(elem_rise[inside] * areas[inside]) / np.sum(areas[inside]))})

    cols = max(2, int(grid[0]))
    rows = int(grid[1]) or max(2, int(round(cols * height / width)))
    xs = np.linspace(0.0, width, cols)
    ys = np.linspace(0.0, height, rows)
    rise_map = _sample(mesh, rise, xs, ys)

    return {
        'ok': True,
        'maxRise': float(np.max(rise)), 'meanRise': float(np.sum(elem_rise * areas) / total_area), 'minRise': float(np.min(rise)),
        'lumpedMeanRise': input_w / (h * 2.0 * total_area),
        'inputW': input_w, 'lostW': lost_w, 'balanceError': abs(lost_w - input_w) / input_w if input_w > 0 else 0.0,
        'spreadingLength': float(np.sqrt(base_k_sheet / (2.0 * h))),
        'sources': per_source,
        'map': {'xs': xs.tolist(), 'ys': ys.tolist(), 'rise': rise_map.tolist()},
        'dofs': int(rise.shape[0]), 'elements': int(mesh.t.shape[1]),
        'notes': ('thin-plate fin equation, both faces at h = %g W/m2K, edges insulated; a polygon region is assigned by element centroid '
                  '(resolved to the mesh spacing)' % h),
    }


def plate_mesh_convergence(refines=(4, 6, 8), **kwargs):
    """Peak rise against mesh refinement - a peak that moves with the mesh is a mesh artefact."""
    runs = []
    for r in refines:
        out = solve_plate_conduction_2d(refine=r, **kwargs)
        if not out.get('ok'):
            return out
        runs.append({'refine': r, 'dofs': out['dofs'], 'maxRise': out['maxRise']})
    values = [r['maxRise'] for r in runs]
    drift = abs(values[-1] - values[-2]) / abs(values[-1]) if len(values) > 1 and values[-1] else None
    return {'ok': True, 'runs': runs, 'finestMaxRise': values[-1], 'relativeChangeLastStep': drift,
            'converged': bool(drift is not None and drift < 0.05),
            'note': 'convergence here means the DISCRETISATION has settled; it says nothing about whether h, the stackup or the powers are right.'}
