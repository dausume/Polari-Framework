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
    K   = the plate's SHEET CONDUCTANCE (W/K), a 2x2 tensor per element:
          - layers in parallel, sum k_i t_i, isotropic (the base, plus
            regions such as copper pours where they lie)
          - LINES (tracks): an embedded 1-D conductor of k A (W m/K) along
            its own direction d. Its weak form is the line integral
            k A (d . grad u)(d . grad v) ds; with linear elements grad u is
            constant on an element, so that integral is EXACTLY the element
            tensor (k A L_e / A_e) d d^T - the line's length L_e inside the
            element, smeared over the element's area A_e. A track conducts
            along itself only, never across.
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
pour never straddles an element; a polygon (a pour, the outline, a hole)
is assigned by element centroid, so its boundary is resolved only to the
mesh spacing (said on the payload; plate_mesh_convergence measures it).
A line is split into pieces no longer than a quarter of the typical mesh
spacing, each assigned to the element holding its midpoint.
"""

from materialsScience.engines.fem_engine import capability, _mesh_aligned_to_features, _tri_areas

SNAP_M = 1e-6


def _inside(centres, region):
    """Points inside one region (rectangle, or polygon by the even-odd ray cast)."""
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


class _Locator:
    """Which triangle of a TENSOR mesh holds a point, and its barycentric weights - the grid cell by bisection, then the cell's two triangles.
    (skfem's general element finder tests every point against every element, which does not fit in memory for a drawing grid.)"""

    def __init__(self, mesh):
        import numpy as np
        self.mesh = mesh
        self.ux, self.uy = np.unique(mesh.p[0]), np.unique(mesh.p[1])
        c = mesh.p[:, mesh.t].mean(axis=1)
        ci = np.clip(np.searchsorted(self.ux, c[0]) - 1, 0, self.ux.size - 2)
        cj = np.clip(np.searchsorted(self.uy, c[1]) - 1, 0, self.uy.size - 2)
        self.cell = -np.ones((self.ux.size - 1, self.uy.size - 1, 2), dtype=int)
        for e, (i, j) in enumerate(zip(ci, cj)):
            self.cell[i, j, 0 if self.cell[i, j, 0] < 0 else 1] = e

    def find(self, x, y):
        """(element index or -1, weights (3, n)) for points x, y."""
        import numpy as np
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        i = np.clip(np.searchsorted(self.ux, x, side='right') - 1, 0, self.ux.size - 2)
        j = np.clip(np.searchsorted(self.uy, y, side='right') - 1, 0, self.uy.size - 2)
        out, weights = -np.ones(x.shape, dtype=int), np.zeros((3,) + x.shape)
        off = (x < self.ux[0] - 1e-15) | (x > self.ux[-1] + 1e-15) | (y < self.uy[0] - 1e-15) | (y > self.uy[-1] + 1e-15)
        for k in (0, 1):
            e = self.cell[i, j, k]
            p = self.mesh.p[:, self.mesh.t[:, e]]  # (2, 3, n)
            det = (p[0, 1] - p[0, 0]) * (p[1, 2] - p[1, 0]) - (p[0, 2] - p[0, 0]) * (p[1, 1] - p[1, 0])
            l1 = ((x - p[0, 0]) * (p[1, 2] - p[1, 0]) - (p[0, 2] - p[0, 0]) * (y - p[1, 0])) / det
            l2 = ((p[0, 1] - p[0, 0]) * (y - p[1, 0]) - (x - p[0, 0]) * (p[1, 1] - p[1, 0])) / det
            hit = (out < 0) & ~off & (l1 >= -1e-9) & (l2 >= -1e-9) & (l1 + l2 <= 1 + 1e-9)
            out[hit] = e[hit]
            weights[:, hit] = np.vstack([1 - l1 - l2, l1, l2])[:, hit]
        return out, weights


def _line_tensor(loc, lines, n_elem, areas):
    """Per-element (kxx, kxy, kyy) of the embedded lines: sum k A L_e d d^T / A_e (see the module docstring), and their heat capacity c_line L_e / A_e
    (J/m2K; c_line = rho c A, J/(m K) - optional, 0 when a line does not carry it)."""
    import numpy as np
    kxx, kxy, kyy, cap = np.zeros(n_elem), np.zeros(n_elem), np.zeros(n_elem), np.zeros(n_elem)
    spacing = float(np.median(np.concatenate([np.diff(loc.ux), np.diff(loc.uy)])))  # the typical cell, not a feature-hugging sliver
    length_on_plate = 0.0
    for ln in lines:
        x0, y0, x1, y1, ka = ln['x0'], ln['y0'], ln['x1'], ln['y1'], float(ln['k_line'])
        L = float(np.hypot(x1 - x0, y1 - y0))
        if L <= 0 or ka <= 0:
            continue
        n = max(1, int(np.ceil(L / (spacing / 4))))
        s = (np.arange(n) + 0.5) / n
        e, _ = loc.find(x0 + s * (x1 - x0), y0 + s * (y1 - y0))
        dx, dy = (x1 - x0) / L, (y1 - y0) / L
        on = e >= 0
        piece = (L / n) / areas[e[on]]
        np.add.at(kxx, e[on], ka * piece * dx * dx)
        np.add.at(kxy, e[on], ka * piece * dx * dy)
        np.add.at(kyy, e[on], ka * piece * dy * dy)
        np.add.at(cap, e[on], float(ln.get('c_line', 0.0)) * piece)
        length_on_plate += L * on.sum() / n
    return kxx, kxy, kyy, cap, length_on_plate


def _build(width, height, base_k_sheet, h, sources=(), regions=(), lines=(), outline=None, holes=(), refine=6, base_c_sheet=0.0):
    """The discrete plate, shared by the steady solve and the transient one (fem_plate_transient): the mesh (outline and holes cut out), the stiffness
    + face-loss matrix A, one load vector per source for 1 W (so any power - or power over time - is a weighted sum), and, when base_c_sheet > 0, the
    heat-capacity (mass) matrix M of rho c t per unit area (regions add 'add_c_sheet', lines 'c_line'). -> dict, or {'ok': False, 'error'}."""
    cap = capability()
    if not cap['available']:
        return {'ok': False, 'error': 'FEM engine unavailable', 'suggestion': cap['suggestion']}
    if width <= 0 or height <= 0:
        return {'ok': False, 'error': 'the plate needs a width and a height > 0, got %r x %r' % (width, height)}
    if base_k_sheet <= 0 or h <= 0:
        return {'ok': False, 'error': 'sheet conductance and h must be > 0, got K = %r W/K, h = %r W/m2K' % (base_k_sheet, h)}
    for s in sources:
        x0, y0, x1, y1 = _bounds(s)
        if not (x1 > x0 and y1 > y0) or s.get('power_w', 0) < 0:
            return {'ok': False, 'error': 'source %r needs an area and power >= 0' % s.get('name')}

    import numpy as np
    from skfem import MeshTri, Basis, ElementTriP1, ElementTriP0, BilinearForm, LinearForm, asm
    from skfem.helpers import grad

    rects = [dict(zip(('x0', 'y0', 'x1', 'y1'), _bounds(r))) for r in list(sources) + [r for r in regions if 'polygon' not in r]]
    # the outline's and holes' vertices become grid lines too, so a rectilinear outline / cut-out is meshed exactly
    rects += [{'x0': x, 'x1': x, 'y0': y, 'y1': y} for loop in ([outline] if outline else []) + list(holes or ()) for x, y in loop]
    # cut lines closer than SNAP_M would make sliver elements: snap every cut to that grid (1 um - far below any board feature)
    rects = [{k: round(v / SNAP_M) * SNAP_M for k, v in r.items()} for r in rects]
    full = _mesh_aligned_to_features(width, height, rects, refine)
    loc = _Locator(full)
    centres = full.p[:, full.t].mean(axis=1)
    keep = np.ones(full.t.shape[1], dtype=bool)
    if outline:
        keep &= _inside(centres, {'polygon': outline})
    for hole in holes or ():
        keep &= ~_inside(centres, {'polygon': hole})
    if not keep.any():
        return {'ok': False, 'error': 'no part of the mesh lies inside the outline'}
    used = np.unique(full.t[:, keep])
    node_new = -np.ones(full.p.shape[1], dtype=int)
    node_new[used] = np.arange(used.size)
    mesh = MeshTri(np.ascontiguousarray(full.p[:, used]), np.ascontiguousarray(node_new[full.t[:, keep]]))
    elem_new = -np.ones(full.t.shape[1], dtype=int)
    elem_new[keep] = np.arange(keep.sum())

    basis = Basis(mesh, ElementTriP1())
    basis0 = basis.with_element(ElementTriP0())
    centres = centres[:, keep]
    areas = _tri_areas(mesh)

    k_iso = np.full(mesh.t.shape[1], float(base_k_sheet))
    c_iso = np.full(mesh.t.shape[1], float(base_c_sheet))
    for r in regions:
        inside = _inside(centres, r)
        k_iso[inside] += float(r['add_k_sheet'])
        c_iso[inside] += float(r.get('add_c_sheet', 0.0))
    lxx, lxy, lyy, lcap, line_len = _line_tensor(loc, lines, full.t.shape[1], _tri_areas(full))
    kxx, kxy, kyy = k_iso + lxx[keep], lxy[keep], k_iso + lyy[keep]  # a line in a removed element is off the board: dropped
    c_elem = c_iso + lcap[keep]
    covered, loads = [], []
    i0 = basis0.interpolate

    @LinearForm
    def heat(v, w):
        return w['qq'] * v

    for s in sources:
        inside = _inside(centres, s)
        area = float(np.sum(areas[inside]))
        if area <= 0:
            return {'ok': False, 'error': 'source %r falls off the plate' % s.get('name')}
        covered.append(inside)
        loads.append(asm(heat, basis, qq=i0(inside / area)))  # 1 W over the meshed area of the source, exactly

    @BilinearForm
    def plate(u, v, w):
        gu, gv = grad(u), grad(v)
        return (w['kxx'] * gu[0] * gv[0] + w['kxy'] * (gu[0] * gv[1] + gu[1] * gv[0]) + w['kyy'] * gu[1] * gv[1]
                + 2.0 * h * u * v)

    @BilinearForm
    def mass(u, v, w):
        return w['cc'] * u * v

    A = asm(plate, basis, kxx=i0(kxx), kxy=i0(kxy), kyy=i0(kyy))
    M = asm(mass, basis, cc=i0(c_elem)) if base_c_sheet > 0 else None
    return {'ok': True, 'mesh': mesh, 'basis': basis, 'loc': loc, 'elem_new': elem_new, 'areas': areas, 'covered': covered, 'loads': loads,
            'A': A, 'M': M, 'c_elem': c_elem, 'line_len': line_len, 'h': h, 'width': width, 'height': height, 'base_k_sheet': base_k_sheet}


def _lost_w(b, theta):
    """The heat leaving both faces, the integral of 2 h theta (W)."""
    from skfem import Functional
    h = b['h']

    @Functional
    def lost(w):
        return 2.0 * h * w['t']

    return float(lost.assemble(b['basis'], t=b['basis'].interpolate(theta)))


def _per_source(b, theta, powers, names):
    import numpy as np
    mesh, areas = b['mesh'], b['areas']
    elem = theta[mesh.t].mean(axis=0)
    out = []
    for name, p, inside in zip(names, powers, b['covered']):
        nodes = np.unique(mesh.t[:, inside])
        out.append({'name': name, 'power_w': float(p), 'peakRise': float(np.max(theta[nodes])),
                    'meanRise': float(np.sum(elem[inside] * areas[inside]) / np.sum(areas[inside]))})
    return out


def _map(b, theta, grid):
    """The field sampled on a regular grid for drawing; a point off the plate is None."""
    import numpy as np
    width, height, mesh = b['width'], b['height'], b['mesh']
    cols = max(2, int(grid[0]))
    rows = int(grid[1]) or max(2, int(round(cols * height / width)))
    xs, ys = np.linspace(0.0, width, cols), np.linspace(0.0, height, rows)
    gx, gy = np.meshgrid(xs, ys)
    e_full, wts = b['loc'].find(gx.ravel(), gy.ravel())
    e = np.where(e_full >= 0, b['elem_new'][np.maximum(e_full, 0)], -1)
    vals = np.einsum('kn,kn->n', wts, theta[mesh.t[:, np.maximum(e, 0)]])
    return {'xs': xs.tolist(), 'ys': ys.tolist(),
            'rise': [[None if e[r * cols + c] < 0 else float(vals[r * cols + c]) for c in range(cols)] for r in range(rows)]}


def solve_plate_conduction_2d(width, height, base_k_sheet, h, sources=(), regions=(), lines=(), outline=None, holes=(), refine=6, grid=(24, 0)):
    """Steady temperature rise of a thin plate inside [0,width] x [0,height] (m).

    base_k_sheet: sheet conductance everywhere (W/K, > 0)
    h: convection coefficient of EACH face (W/m2K, > 0)
    sources: [{'name', 'power_w', + a rectangle}] - spread uniformly over it
    regions: [{'name', 'add_k_sheet', + a rectangle or polygon}] - ADDED to
        the sheet conductance where they lie (copper in parallel)
    lines: [{'name', 'x0', 'y0', 'x1', 'y1', 'k_line'}] - embedded conductors,
        k_line = k x cross-section (W m/K), along their own direction only
    outline: [[x, y], ...] - the plate's own shape (None = the whole box);
        holes: [[[x, y], ...], ...] - cut-outs. Elements outside are removed.
    grid: (columns, rows) of the sampled map for drawing; rows 0 = keep
        the plate's aspect. A map point off the plate is None.

    Returns {'ok', 'maxRise', 'meanRise', 'minRise', 'lumpedMeanRise',
    'inputW', 'lostW', 'balanceError', 'spreadingLength', 'plateArea',
    'lineLengthOnPlate', 'sources': [{name, power_w, peakRise, meanRise}],
    'map': {xs, ys, rise}, 'dofs', 'elements', 'notes'} or {'ok': False,
    'error', 'suggestion'?}.
    """
    b = _build(width, height, base_k_sheet, h, sources, regions, lines, outline, holes, refine)
    if not b.get('ok'):
        return b
    import numpy as np
    from skfem import solve
    powers = [float(s['power_w']) for s in sources]
    rhs = sum((p * ld for p, ld in zip(powers, b['loads'])), np.zeros(b['A'].shape[0]))
    rise = solve(b['A'], rhs)
    lost_w, input_w = _lost_w(b, rise), float(sum(powers))
    areas = b['areas']
    elem_rise = rise[b['mesh'].t].mean(axis=0)
    plate_area = float(np.sum(areas))
    return {
        'ok': True,
        'maxRise': float(np.max(rise)), 'meanRise': float(np.sum(elem_rise * areas) / plate_area), 'minRise': float(np.min(rise)),
        'lumpedMeanRise': input_w / (h * 2.0 * plate_area),
        'inputW': input_w, 'lostW': lost_w, 'balanceError': abs(lost_w - input_w) / input_w if input_w > 0 else 0.0,
        'spreadingLength': float(np.sqrt(base_k_sheet / (2.0 * h))), 'plateArea': plate_area, 'lineLengthOnPlate': b['line_len'],
        'sources': _per_source(b, rise, powers, [s.get('name', '') for s in sources]),
        'map': _map(b, rise, grid),
        'dofs': int(rise.shape[0]), 'elements': int(b['mesh'].t.shape[1]),
        'notes': ('thin-plate fin equation, both faces at h = %g W/m2K, edges insulated; polygons (pours, outline, holes) assigned by element '
                  'centroid (resolved to the mesh spacing); lines are embedded 1-D conductors along their own direction' % h),
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
