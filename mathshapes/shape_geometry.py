"""
@cross-cutting
@module mathshapes.shape_geometry
@tags @xc:render-3d

Pure geometry math for math-defined shapes — NO manager, NO I/O, stdlib
`math` only (so selftests + the analysis layer both import it freely).

Three responsibilities:
  - primitives: closed-form inside-test, volume, surface area, AABB, and
    a parametric surface mesh (points + triangles) for box/sphere/
    cylinder/cone/frustum/ellipsoid.
  - quadrics: evaluate the matrix form pᵀQp, and classify an axis-
    aligned Q into its standard surface type from the sign pattern (the
    general non-diagonal path lives in shape_analysis behind a numpy
    capability gate).
  - a small parametric ellipsoid/cylinder mesher reused by both.

All lengths are cm; volumes cm³, areas cm². Coordinates are a flat
[x, y, z]; a shape carries its own `center` and `axis`.

@consumers
  - mathshapes.shape_analysis (wraps these with manager lookups + CSG)
@see /MATH_SHAPES_PLAN.md
"""

import math

_AXIS = {'x': 0, 'y': 1, 'z': 2}


# --------------------------------------------------------------------------
# small vector helpers
# --------------------------------------------------------------------------
def _axis_index(axis):
    return _AXIS.get(axis, 2)


def _decompose(x, y, z, center, axis):
    """Split a point into (signed distance ALONG the axis from center,
    radial distance PERP to the axis)."""
    p = (x, y, z)
    ai = _axis_index(axis)
    along = p[ai] - center[ai]
    perp2 = sum((p[i] - center[i]) ** 2 for i in range(3) if i != ai)
    return along, math.sqrt(perp2)


def _perp_axes(axis):
    ai = _axis_index(axis)
    return [i for i in range(3) if i != ai]


# --------------------------------------------------------------------------
# primitive parameter access (tolerant defaults)
# --------------------------------------------------------------------------
def _center(params):
    c = params.get('center', [0.0, 0.0, 0.0])
    try:
        return [float(c[0]), float(c[1]), float(c[2])]
    except (TypeError, ValueError, IndexError):
        return [0.0, 0.0, 0.0]


def _num(params, key, default):
    try:
        v = params.get(key, default)
        return float(default if v is None else v)
    except (TypeError, ValueError):
        return float(default)


# --------------------------------------------------------------------------
# primitive inside-test
# --------------------------------------------------------------------------
def primitive_inside(kind, params, x, y, z):
    """True if (x,y,z) is inside/on the primitive."""
    center = _center(params)
    axis = params.get('axis', 'z')
    if kind == 'box':
        size = params.get('size', [1.0, 1.0, 1.0])
        try:
            sx, sy, sz = (float(size[0]), float(size[1]), float(size[2]))
        except (TypeError, ValueError, IndexError):
            sx = sy = sz = 1.0
        return (abs(x - center[0]) <= sx / 2.0 + 1e-12
                and abs(y - center[1]) <= sy / 2.0 + 1e-12
                and abs(z - center[2]) <= sz / 2.0 + 1e-12)
    if kind == 'sphere':
        r = _num(params, 'radius', 1.0)
        d2 = sum((p - c) ** 2 for p, c in zip((x, y, z), center))
        return d2 <= r * r + 1e-9
    if kind == 'ellipsoid':
        radii = params.get('radii', [1.0, 1.0, 1.0])
        try:
            a, b, c = (float(radii[0]), float(radii[1]), float(radii[2]))
        except (TypeError, ValueError, IndexError):
            a = b = c = 1.0
        if a <= 0 or b <= 0 or c <= 0:
            return False
        return (((x - center[0]) / a) ** 2 + ((y - center[1]) / b) ** 2
                + ((z - center[2]) / c) ** 2) <= 1.0 + 1e-9
    # axial primitives share the along/perp decomposition
    along, perp = _decompose(x, y, z, center, axis)
    h = _num(params, 'height', 1.0)
    if abs(along) > h / 2.0 + 1e-12:
        return False
    t = along + h / 2.0                       # 0 at base .. h at top
    if kind == 'cylinder':
        r = _num(params, 'radius', 1.0)
        return perp <= r + 1e-9
    if kind == 'cone':
        base_r = _num(params, 'base_radius', 1.0)
        local = base_r * (1.0 - t / h) if h > 0 else 0.0
        return perp <= local + 1e-9
    if kind == 'frustum':
        base_r = _num(params, 'base_radius', 1.0)
        top_r = _num(params, 'top_radius', 0.5)
        local = base_r + (top_r - base_r) * (t / h) if h > 0 else base_r
        return perp <= local + 1e-9
    return False


# --------------------------------------------------------------------------
# primitive analytic properties
# --------------------------------------------------------------------------
def primitive_properties(kind, params):
    """Closed-form {volume, area, bounds, centroid} for a primitive."""
    center = _center(params)
    axis = params.get('axis', 'z')
    ai = _axis_index(axis)
    if kind == 'box':
        size = params.get('size', [1.0, 1.0, 1.0])
        sx, sy, sz = (float(size[0]), float(size[1]), float(size[2]))
        vol = sx * sy * sz
        area = 2.0 * (sx * sy + sy * sz + sx * sz)
        half = [sx / 2.0, sy / 2.0, sz / 2.0]
        bounds = [[center[i] - half[i], center[i] + half[i]]
                  for i in range(3)]
        return vol, area, bounds, list(center)
    if kind == 'sphere':
        r = _num(params, 'radius', 1.0)
        vol = (4.0 / 3.0) * math.pi * r ** 3
        area = 4.0 * math.pi * r * r
        bounds = [[center[i] - r, center[i] + r] for i in range(3)]
        return vol, area, bounds, list(center)
    if kind == 'ellipsoid':
        radii = params.get('radii', [1.0, 1.0, 1.0])
        a, b, c = (float(radii[0]), float(radii[1]), float(radii[2]))
        vol = (4.0 / 3.0) * math.pi * a * b * c
        # Thomsen approximation for a general ellipsoid surface (p=1.6075)
        p = 1.6075
        area = 4.0 * math.pi * (
            ((a * b) ** p + (a * c) ** p + (b * c) ** p) / 3.0) ** (1.0 / p)
        bounds = [[center[0] - a, center[0] + a],
                  [center[1] - b, center[1] + b],
                  [center[2] - c, center[2] + c]]
        return vol, area, bounds, list(center)
    # axial primitives
    h = _num(params, 'height', 1.0)
    perp = _perp_axes(axis)
    if kind == 'cylinder':
        r = _num(params, 'radius', 1.0)
        vol = math.pi * r * r * h
        area = 2.0 * math.pi * r * r + 2.0 * math.pi * r * h
        rad = r
        centroid = list(center)
    elif kind == 'cone':
        r = _num(params, 'base_radius', 1.0)
        vol = (1.0 / 3.0) * math.pi * r * r * h
        slant = math.sqrt(r * r + h * h)
        area = math.pi * r * r + math.pi * r * slant
        rad = r
        centroid = list(center)
        centroid[ai] = center[ai] - h / 4.0    # 1/4 up from the base
    elif kind == 'frustum':
        base_r = _num(params, 'base_radius', 1.0)
        top_r = _num(params, 'top_radius', 0.5)
        vol = math.pi * h / 3.0 * (base_r ** 2 + base_r * top_r + top_r ** 2)
        slant = math.sqrt((base_r - top_r) ** 2 + h * h)
        area = (math.pi * (base_r + top_r) * slant
                + math.pi * base_r ** 2 + math.pi * top_r ** 2)
        rad = max(base_r, top_r)
        # centroid drifts toward the wider end; small offset, keep centre
        centroid = list(center)
    else:
        return 0.0, 0.0, [[0, 0], [0, 0], [0, 0]], list(center)
    bounds = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
    bounds[ai] = [center[ai] - h / 2.0, center[ai] + h / 2.0]
    for i in perp:
        bounds[i] = [center[i] - rad, center[i] + rad]
    return vol, area, bounds, centroid


# --------------------------------------------------------------------------
# quadric matrix form
# --------------------------------------------------------------------------
def quadric_value(Q, x, y, z):
    """pᵀ Q p for p = [x, y, z, 1]; < 0 is interior, 0 the surface."""
    p = (x, y, z, 1.0)
    total = 0.0
    for i in range(4):
        row = Q[i]
        total += p[i] * (row[0] * p[0] + row[1] * p[1]
                         + row[2] * p[2] + row[3] * p[3])
    return total


def quadric_is_axis_aligned(Q, tol=1e-9):
    """True if the top-left 3x3 block is diagonal (no cross terms)."""
    return (abs(Q[0][1]) < tol and abs(Q[0][2]) < tol
            and abs(Q[1][2]) < tol)


def _sign(v, tol=1e-9):
    return 0 if abs(v) < tol else (1 if v > 0 else -1)


def classify_axis_aligned(Q):
    """Classify a diagonal (axis-aligned) quadric from its sign pattern.

    Reads the quadratic diagonal (a,b,c), the linear terms (2·Q[i,3]),
    and the constant Q[3,3]. Returns a shape-type string. Assumes
    quadric_is_axis_aligned(Q) is True."""
    a, b, c = Q[0][0], Q[1][1], Q[2][2]
    lin = [2.0 * Q[0][3], 2.0 * Q[1][3], 2.0 * Q[2][3]]
    const = Q[3][3]
    quad = [a, b, c]
    signs = [_sign(v) for v in quad]
    nz = [i for i in range(3) if signs[i] != 0]
    zeros = [i for i in range(3) if signs[i] == 0]
    npos = sum(1 for i in nz if signs[i] > 0)
    nneg = sum(1 for i in nz if signs[i] < 0)
    cs = _sign(const)

    def _equal_mag(idxs):
        vals = [abs(quad[i]) for i in idxs]
        return max(vals) - min(vals) < 1e-9 * (max(vals) or 1.0)

    if len(nz) == 3:
        if npos == 3 or nneg == 3:            # all same sign
            if cs == 0:
                return 'point'
            if _sign(quad[0]) == cs:
                return 'empty'                # no real solution
            return 'sphere' if _equal_mag([0, 1, 2]) else 'ellipsoid'
        # mixed signs among all three nonzero
        if cs == 0:
            return 'cone'
        return 'hyperboloid'
    if len(nz) == 2:
        zi = zeros[0]
        if _sign(lin[zi]) != 0:               # a linear term on the flat axis
            return ('elliptic-paraboloid'
                    if signs[nz[0]] == signs[nz[1]]
                    else 'hyperbolic-paraboloid')
        # no linear term -> a cylinder along the zero axis
        if signs[nz[0]] == signs[nz[1]]:
            return 'cylinder' if _equal_mag(nz) else 'elliptic-cylinder'
        return 'hyperbolic-cylinder'
    if len(nz) == 1:
        if any(_sign(lin[i]) != 0 for i in zeros):
            return 'parabolic-cylinder'
        return 'planes'
    return 'degenerate'


# --------------------------------------------------------------------------
# quadric -> primitive extraction (for a clean parametric mesh)
# --------------------------------------------------------------------------
def quadric_as_ellipsoid(Q):
    """If Q is a diagonal ellipsoid/sphere, return {center, radii}, else
    None. Lets sample_surface emit an exact parametric mesh instead of a
    grid march for the common case."""
    if not quadric_is_axis_aligned(Q):
        return None
    a, b, c = Q[0][0], Q[1][1], Q[2][2]
    if _sign(a) <= 0 or _sign(b) <= 0 or _sign(c) <= 0:
        return None
    # complete the square: a(x - x0)^2 + ... = -const'  (all a,b,c>0)
    cx, cy, cz = -Q[0][3] / a, -Q[1][3] / b, -Q[2][3] / c
    const = Q[3][3] - (a * cx * cx + b * cy * cy + c * cz * cz) \
        + 2 * (Q[0][3] * cx + Q[1][3] * cy + Q[2][3] * cz)
    # surface a·X^2 + b·Y^2 + c·Z^2 + const = 0  -> need const < 0
    k = -const
    if k <= 0:
        return None
    return {'center': [cx, cy, cz],
            'radii': [math.sqrt(k / a), math.sqrt(k / b), math.sqrt(k / c)]}


# --------------------------------------------------------------------------
# parametric surface meshes (points + triangles) for rendering
# --------------------------------------------------------------------------
def ellipsoid_mesh(center, radii, n_lat=16, n_lon=24):
    """Lat/long triangulated ellipsoid surface."""
    a, b, c = radii
    pts, tris = [], []
    for i in range(n_lat + 1):
        theta = math.pi * i / n_lat          # 0..pi
        for j in range(n_lon):
            phi = 2.0 * math.pi * j / n_lon
            pts.append([
                center[0] + a * math.sin(theta) * math.cos(phi),
                center[1] + b * math.sin(theta) * math.sin(phi),
                center[2] + c * math.cos(theta)])
    for i in range(n_lat):
        for j in range(n_lon):
            p0 = i * n_lon + j
            p1 = i * n_lon + (j + 1) % n_lon
            p2 = (i + 1) * n_lon + j
            p3 = (i + 1) * n_lon + (j + 1) % n_lon
            tris.append([p0, p2, p1])
            tris.append([p1, p2, p3])
    return pts, tris


def axial_mesh(kind, params, n_lon=24, n_stack=1):
    """Lateral + cap mesh for cylinder/cone/frustum along its axis."""
    center = _center(params)
    axis = params.get('axis', 'z')
    ai = _axis_index(axis)
    perp = _perp_axes(axis)
    h = _num(params, 'height', 1.0)
    if kind == 'cylinder':
        r0 = r1 = _num(params, 'radius', 1.0)
    elif kind == 'cone':
        r0, r1 = _num(params, 'base_radius', 1.0), 0.0
    else:                                     # frustum
        r0 = _num(params, 'base_radius', 1.0)
        r1 = _num(params, 'top_radius', 0.5)

    def ring(t, radius):
        out = []
        for j in range(n_lon):
            phi = 2.0 * math.pi * j / n_lon
            p = [0.0, 0.0, 0.0]
            p[ai] = center[ai] - h / 2.0 + t * h
            p[perp[0]] = center[perp[0]] + radius * math.cos(phi)
            p[perp[1]] = center[perp[1]] + radius * math.sin(phi)
            out.append(p)
        return out

    pts, tris = [], []
    base_ring = ring(0.0, r0)
    top_ring = ring(1.0, r1)
    b0 = len(pts)
    pts.extend(base_ring)
    t0 = len(pts)
    pts.extend(top_ring)
    for j in range(n_lon):
        jn = (j + 1) % n_lon
        tris.append([b0 + j, b0 + jn, t0 + j])
        tris.append([b0 + jn, t0 + jn, t0 + j])
    return pts, tris
