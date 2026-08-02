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
    if kind == 'hollow_frustum':
        return _hollow_frustum_inside(params, center, axis, x, y, z)
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


def _hollow_frustum_inside(params, center, axis, x, y, z):
    """Inside-test for a render-only 'hollow_frustum' primitive (see
    hollow_frustum_shell_mesh): between the inner and outer tapered
    profile at this height, and outside every one of its `holes`
    (each a plain cylinder-primitive param dict — same test
    primitive_inside('cylinder', ...) already uses)."""
    along, perp = _decompose(x, y, z, center, axis)
    h = _num(params, 'height', 1.0)
    if abs(along) > h / 2.0 + 1e-12:
        return False
    t = (along + h / 2.0) / h if h > 0 else 0.0
    r0o = _num(params, 'base_outer_radius', 1.0)
    r1o = _num(params, 'top_outer_radius', 0.9)
    r0i = _num(params, 'base_inner_radius', 0.8)
    r1i = _num(params, 'top_inner_radius', 0.7)
    outer = r0o + (r1o - r0o) * t
    inner = r0i + (r1i - r0i) * t
    if not (inner - 1e-9 <= perp <= outer + 1e-9):
        return False
    for hole_params in (params.get('holes') or []):
        if primitive_inside('cylinder', hole_params, x, y, z):
            return False
    return True


def _hollow_frustum_properties(params, center, axis, ai):
    """Approximate {volume, area, bounds, centroid} for a render-only
    'hollow_frustum' — NOT the authoritative volume (that's the
    quadric+CSG chain pot_shape_from_definition builds alongside this
    shape; see potMaterialVolumeCm3). Closed-form: outer frustum minus
    inner frustum minus each hole's own cylinder volume — a reasonable
    approximation, cheap, and here mainly so shape_properties()/GET
    .../properties never crashes on this shape name."""
    h = _num(params, 'height', 1.0)
    outer_vol, outer_area, outer_bounds, _ = primitive_properties('frustum', {
        'base_radius': _num(params, 'base_outer_radius', 1.0),
        'top_radius': _num(params, 'top_outer_radius', 0.9),
        'height': h, 'axis': axis, 'center': center})
    inner_vol, inner_area, _, _ = primitive_properties('frustum', {
        'base_radius': _num(params, 'base_inner_radius', 0.8),
        'top_radius': _num(params, 'top_inner_radius', 0.7),
        'height': h, 'axis': axis, 'center': center})
    holes_vol = 0.0
    for hole_params in (params.get('holes') or []):
        hv, _, _, _ = primitive_properties('cylinder', hole_params)
        holes_vol += hv
    vol = max(0.0, outer_vol - inner_vol - holes_vol)
    area = outer_area + inner_area          # doesn't subtract hole openings
    return vol, area, outer_bounds, list(center)


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
    if kind == 'hollow_frustum':
        return _hollow_frustum_properties(params, center, axis, ai)
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


def cone_quadric_matrix(base_radius, top_radius, height, axis='z',
                        center=(0.0, 0.0, 0.0)):
    """4x4 matrix Q (pᵀQp form, `quadric_value`) for the INFINITE cone/
    cylinder whose lateral surface passes through `base_radius` at this
    shape's own z = center[axis] - height/2 and `top_radius` at
    z = center[axis] + height/2 (assumes the shape is coaxial with
    `axis` through its perp-plane center — true for every shape this
    module derives). Pair with a height-bounding box (CSG intersection)
    for the finite solid — the quadric itself is the SOURCE-OF-TRUTH
    equation (Dustin 2026-07-13: "leverage matrix equations ... to
    form volumetric shapes"); a frustum's lateral surface is exactly a
    bounded slice of this surface. Degenerates to a true cylinder
    quadric (x²+y² = r²) when base_radius == top_radius (slope = 0).

    Derivation: radius(z)² = (base_radius + slope·(z - z0))², z0 the
    local base z. Expanding x²+y² - radius(z)² = 0 into pᵀQp form:
        Q[ai][ai]  = -slope²
        Q[ai][3]   = Q[3][ai] = slope·m,  m = slope·z0 - base_radius
        Q[3][3]    = -m²
        Q[perp][perp] = 1  (both perpendicular axes)
    """
    ai = _axis_index(axis)
    perp = _perp_axes(axis)
    z0 = center[ai] - height / 2.0
    slope = (top_radius - base_radius) / height if height > 1e-9 else 0.0
    m = slope * z0 - base_radius
    Q = [[0.0] * 4 for _ in range(4)]
    Q[perp[0]][perp[0]] = 1.0
    Q[perp[1]][perp[1]] = 1.0
    Q[ai][ai] = -slope * slope
    Q[ai][3] = Q[3][ai] = slope * m
    Q[3][3] = -m * m
    return Q


def radius_at_z(Q, axis, z):
    """Radius of a cone_quadric_matrix's lateral surface at a given z —
    the exact algebraic inverse of its construction (Q is normalized
    to 1 on both perpendicular-axis diagonal entries, so x²+y² at the
    surface is just -(Q[ai][ai]z² + 2·Q[ai][3]z + Q[3][3])). Used to
    DERIVE numeric mesh/render parameters FROM the quadric equation
    (rather than compute them independently) so the equation stays the
    single source of truth end to end."""
    ai = _axis_index(axis)
    val = -(Q[ai][ai] * z * z + 2.0 * Q[ai][3] * z + Q[3][3])
    return math.sqrt(max(0.0, val))


_AXIS_LATEX_SYMBOL = {'x': 'x', 'y': 'y', 'z': 'z'}


def cone_quadric_latex(base_radius, top_radius, height, z0, axis='z',
                       ndigits=4):
    """Human-readable LaTeX for the SAME surface cone_quadric_matrix
    encodes — a DERIVED display, not a second source of truth (the Q
    matrix is authoritative; this is read directly off the same
    base_radius/slope/z0/axis inputs, never re-derived from Q). Uses
    the two PERPENDICULAR axis symbols on the left (e.g. a hole bored
    along x reads `y^2 + z^2 = ...`, not a hardcoded x/y) — a straight
    cylinder (base_radius == top_radius) renders without the
    now-degenerate slope/z0 terms."""
    perp = _perp_axes(axis)
    p0 = _AXIS_LATEX_SYMBOL.get(('x', 'y', 'z')[perp[0]], 'x')
    p1 = _AXIS_LATEX_SYMBOL.get(('x', 'y', 'z')[perp[1]], 'y')
    av = _AXIS_LATEX_SYMBOL.get(axis, 'z')
    slope = (top_radius - base_radius) / height if height > 1e-9 else 0.0
    r0 = round(base_radius, ndigits)
    if abs(slope) < 1e-9:
        return f'{p0}^2 + {p1}^2 = {r0}^2'
    k = round(slope, ndigits)
    z0r = round(z0, ndigits)
    return f'{p0}^2 + {p1}^2 = ({r0} + {k}({av} - {z0r}))^2'


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
        # Complete the square (translate to the quadric's own vertex/
        # center) before reading the constant's sign — the sphere vs.
        # ellipsoid vs. point vs. empty AND cone vs. hyperboloid splits
        # are properties of the SURFACE, not of which frame its
        # equation happens to be written in. A cone whose apex isn't
        # at the origin (e.g. cone_quadric_matrix's pot-local frame,
        # z0 = the wall's own base, not the true apex) has a nonzero
        # RAW Q[3][3] despite genuinely being a cone — recentering
        # first (same algebra quadric_as_ellipsoid already uses) makes
        # this coordinate-invariant. No-op for already-centered
        # quadrics (Q[i][3]==0 → c_i==0 → recentered_const==Q[3][3]).
        c_i = [-Q[i][3] / quad[i] for i in range(3)]
        recentered_const = (
            Q[3][3] - sum(quad[i] * c_i[i] ** 2 for i in range(3)))
        cs = _sign(recentered_const)
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
    # complete the square: a(x - x0)^2 + ... = -const'  (all a,b,c>0).
    # a·x² + 2·Q[0][3]·x = a·(x - cx)² - a·cx² for cx = -Q[0][3]/a (and
    # likewise y, z) — so the recentered constant is Q[3][3] minus the
    # sum, with NO extra term (previously had a stray "+ 2·Σ Q[i][3]·c_i"
    # that only vanished for an already-centered quadric — i.e. every
    # quadric this function had ever actually been called with; a
    # hand-verified off-center sphere caught it — see
    # AQUAPONICS_POT_SHAPE_PLAN.md).
    cx, cy, cz = -Q[0][3] / a, -Q[1][3] / b, -Q[2][3] / c
    const = Q[3][3] - (a * cx * cx + b * cy * cy + c * cz * cz)
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


def axial_mesh(kind, params, n_lon=24, n_stack=1,
               cap_base=False, cap_top=False, inward=False):
    """Lateral (+ optional end-cap) mesh for cylinder/cone/frustum along
    its axis. `cap_base`/`cap_top` triangulate a flat disc at that end
    (a fan from the ring to its center) — OFF by default so a shape
    meant to be seen through (a bore hole, a hollow wall's own lateral
    surface) stays open; turn them on for a primitive meant to read as
    a SOLID (e.g. a pot's base slab).

    `inward=True` reverses every triangle's winding (and therefore its
    outward-pointing normal) — for a surface meant to be viewed from
    the axis side rather than from outside (e.g. the INNER surface of
    a hollow shell, where the visible face looks back toward the
    center). Without this, an inner-wall mesh built the same way as an
    outer-wall mesh would have its front face pointing INTO the solid
    material — invisible from inside the vessel with a single-sided
    material (this was the aquaponics-pot-shape phase-1 bug: a solid
    frustum with no caps read as an open, one-sided sheet)."""
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

    if cap_base and r0 > 1e-9:
        c0 = len(pts)
        base_center = list(center)
        base_center[ai] = center[ai] - h / 2.0
        pts.append(base_center)
        for j in range(n_lon):
            jn = (j + 1) % n_lon
            # Base cap faces DOWN/OUT (away from the solid) — opposite
            # winding sense from the lateral surface's base ring.
            tris.append([c0, b0 + jn, b0 + j])
    if cap_top and r1 > 1e-9:
        c1 = len(pts)
        top_center = list(center)
        top_center[ai] = center[ai] + h / 2.0
        pts.append(top_center)
        for j in range(n_lon):
            jn = (j + 1) % n_lon
            tris.append([c1, t0 + j, t0 + jn])

    if inward:
        tris = [[t[0], t[2], t[1]] for t in tris]
    return pts, tris


def tube_mesh(center, axis, r_outer, r_inner, height, n_lon=32):
    """Closed annular tube (a cylinder with a coaxial bore): outer
    lateral surface + inner lateral surface (inward-wound, same fix as
    axial_mesh's `inward` note) + an annulus rim at BOTH ends, stitched
    from one vertex set so it reads as one solid ring — the exact
    parametric mesh for a CSG difference of two coaxial cylinders
    (mag-7: the motor coil winding body). Analogous special-casing
    precedent: quadric_as_ellipsoid lets an axis-aligned quadric skip
    the marching fallback."""
    ai = _axis_index(axis)
    perp = _perp_axes(axis)

    def ring(t, radius):
        out = []
        for j in range(n_lon):
            phi = 2.0 * math.pi * j / n_lon
            p = [0.0, 0.0, 0.0]
            p[ai] = center[ai] - height / 2.0 + t * height
            p[perp[0]] = center[perp[0]] + radius * math.cos(phi)
            p[perp[1]] = center[perp[1]] + radius * math.sin(phi)
            out.append(p)
        return out

    pts = []
    ob = len(pts); pts.extend(ring(0.0, r_outer))   # outer base
    ot = len(pts); pts.extend(ring(1.0, r_outer))   # outer top
    ib = len(pts); pts.extend(ring(0.0, r_inner))   # inner base
    it = len(pts); pts.extend(ring(1.0, r_inner))   # inner top
    tris = []
    for j in range(n_lon):
        jn = (j + 1) % n_lon
        # outer lateral, outward winding (same sense as axial_mesh)
        tris.append([ob + j, ob + jn, ot + j])
        tris.append([ob + jn, ot + jn, ot + j])
        # inner lateral, reversed — visible from inside the bore
        tris.append([ib + j, it + j, ib + jn])
        tris.append([ib + jn, it + j, it + jn])
        # base rim annulus (faces down/out) + top rim annulus (up/out)
        tris.append([ob + j, ib + j, ob + jn])
        tris.append([ob + jn, ib + j, ib + jn])
        tris.append([ot + j, ot + jn, it + j])
        tris.append([ot + jn, it + jn, it + j])
    return pts, tris


def hollow_frustum_shell_mesh(params, n_lon=32, n_stack=16,
                              hole_local_samples=14, hole_margin_factor=2.5):
    """ONE integrated, closed mesh for a hollow tapered shell (a pot's
    side wall): outer lateral surface + inner lateral surface (inward-
    wound) + a top rim annulus AND a bottom rim annulus (Dustin
    2026-07-13 round 3: "the top of the bottom shape should be flush
    with the bottom of the siding shape" — the bottom rim closes what
    was an open ring, sitting exactly on the bottom-slab's top face)
    — stitched from a SINGLE vertex grid so it reads as one solid
    object, not floating surfaces.

    Each hole in `params['holes']` (plain cylinder-primitive param
    dicts) is CUT OUT: a grid quad with a corner inside that hole's
    cylinder (primitive_inside('cylinder', ...) — the SAME solid
    volume the hole's own standalone primitive is, no separate
    "hollow" concept) is dropped. The angular/height grid is NOT
    uniform — round 2 used a flat n_lon×n_stack grid, and a hole
    (~1cm) is a couple of PERCENT of the wall's circumference/height,
    so at n_lon~32 a hole spanned under 2 grid columns: the resulting
    cut was a single ragged wedge, not a hole (Dustin: "you subtracted
    a random section of the siding"). Fixed by inserting
    `hole_local_samples` extra angular AND height samples densely
    clustered around EACH hole's own (azimuth, elevation) — resolving
    each hole's actual round footprint — while leaving the rest of the
    wall at the coarse base resolution (bounded total triangle count).
    Still a blocky (not analytically exact) boolean cut — this module
    has no general mesh-boolean/marching-cubes engine — but now
    resolved at hole scale, not wall scale.
    """
    # `2*k/(hole_local_samples-1)` below divides by zero at 1 and is
    # meaningless at 0 (no local refinement at all) — every current
    # caller passes the default (14), but this keyword is a real,
    # externally-settable parameter, not just an internal constant.
    hole_local_samples = max(2, int(hole_local_samples))
    center = _center(params)
    axis = params.get('axis', 'z')
    ai = _axis_index(axis)
    perp = _perp_axes(axis)
    h = _num(params, 'height', 1.0)
    r0o = _num(params, 'base_outer_radius', 1.0)
    r1o = _num(params, 'top_outer_radius', 0.9)
    r0i = _num(params, 'base_inner_radius', 0.8)
    r1i = _num(params, 'top_inner_radius', 0.7)
    holes = params.get('holes') or []

    def outer_r(t):
        return r0o + (r1o - r0o) * t

    def inner_r(t):
        return r0i + (r1i - r0i) * t

    two_pi = 2.0 * math.pi
    phis = [two_pi * j / n_lon for j in range(n_lon)]
    ts = [i / n_stack for i in range(n_stack + 1)]
    for hp in holes:
        hc = hp.get('center') or [0.0, 0.0, 0.0]
        r_hole = max(1e-6, _num(hp, 'radius', 0.1))
        px, py = hc[perp[0]], hc[perp[1]]
        mid_r = max(1e-3, math.hypot(px, py))
        phi_c = math.atan2(py, px) % two_pi
        half_phi = min(math.pi * 0.4, hole_margin_factor * r_hole / mid_r)
        phis.extend(
            (phi_c + half_phi * (2.0 * k / (hole_local_samples - 1) - 1.0))
            % two_pi for k in range(hole_local_samples))
        z_c = hc[ai]
        half_z = hole_margin_factor * r_hole
        t_c = (z_c - (center[ai] - h / 2.0)) / h if h > 1e-9 else 0.5
        half_t = half_z / h if h > 1e-9 else 0.1
        ts.extend(
            min(1.0, max(0.0, t_c + half_t * (2.0 * k / (hole_local_samples - 1) - 1.0)))
            for k in range(hole_local_samples))

    phis = sorted(set(round(p, 9) for p in phis))
    ts = sorted(set(round(t, 9) for t in ts))
    n_j, n_i = len(phis), len(ts)

    def grid_point(t, radius, phi):
        p = [0.0, 0.0, 0.0]
        p[ai] = center[ai] - h / 2.0 + t * h
        p[perp[0]] = center[perp[0]] + radius * math.cos(phi)
        p[perp[1]] = center[perp[1]] + radius * math.sin(phi)
        return p

    def cut(p):
        return any(primitive_inside('cylinder', hp, p[0], p[1], p[2])
                  for hp in holes)

    pts = []
    outer_idx, inner_idx = {}, {}
    for i, t in enumerate(ts):
        for j, phi in enumerate(phis):
            outer_idx[(i, j)] = len(pts)
            pts.append(grid_point(t, outer_r(t), phi))
    for i, t in enumerate(ts):
        for j, phi in enumerate(phis):
            inner_idx[(i, j)] = len(pts)
            pts.append(grid_point(t, inner_r(t), phi))

    cut_outer = {k: cut(pts[v]) for k, v in outer_idx.items()}
    cut_inner = {k: cut(pts[v]) for k, v in inner_idx.items()}

    tris = []
    for i in range(n_i - 1):
        for j in range(n_j):
            jn = (j + 1) % n_j
            corners = ((i, j), (i, jn), (i + 1, j), (i + 1, jn))
            if not any(cut_outer[c] for c in corners):
                a, b, c, d = (outer_idx[(i, j)], outer_idx[(i, jn)],
                             outer_idx[(i + 1, j)], outer_idx[(i + 1, jn)])
                tris.append([a, b, c])
                tris.append([b, d, c])
            if not any(cut_inner[c] for c in corners):
                a, b, c, d = (inner_idx[(i, j)], inner_idx[(i, jn)],
                             inner_idx[(i + 1, j)], inner_idx[(i + 1, jn)])
                # inward winding — see axial_mesh's `inward` docstring.
                tris.append([a, c, b])
                tris.append([b, c, d])

    # Top rim annulus (i = n_i-1) — closes the open mouth so the wall
    # reads as having real thickness at the rim, not a knife edge.
    i = n_i - 1
    for j in range(n_j):
        jn = (j + 1) % n_j
        if (cut_outer[(i, j)] or cut_outer[(i, jn)]
                or cut_inner[(i, j)] or cut_inner[(i, jn)]):
            continue
        oa, ob = outer_idx[(i, j)], outer_idx[(i, jn)]
        ia, ib = inner_idx[(i, j)], inner_idx[(i, jn)]
        tris.append([oa, ob, ia])
        tris.append([ob, ib, ia])

    # Bottom rim annulus (i = 0) — closes the wall's own bottom edge so
    # it sits flush against the bottom-slab's top face instead of
    # leaving an open ring where the two independently-built meshes
    # meet (round 3 feedback).
    i = 0
    for j in range(n_j):
        jn = (j + 1) % n_j
        if (cut_outer[(i, j)] or cut_outer[(i, jn)]
                or cut_inner[(i, j)] or cut_inner[(i, jn)]):
            continue
        oa, ob = outer_idx[(i, j)], outer_idx[(i, jn)]
        ia, ib = inner_idx[(i, j)], inner_idx[(i, jn)]
        # Reversed winding vs. the top rim — outward normal points
        # DOWN here, not up (hand-verified via cross product).
        tris.append([oa, ia, ob])
        tris.append([ob, ia, ib])

    return pts, tris


# --------------------------------------------------------------------------
# mq-1: quadric matrices for EVERY bounding surface — planes are
# degenerate quadrics, so a box is six 4x4 matrices and a capped
# cylinder is three. Sign convention throughout: pᵀQp < 0 inside
# (outward normals), so intersection composes as max().
# --------------------------------------------------------------------------
def plane_quadric_matrix(normal, point):
    """Degenerate 4x4 Q for the half-space n·(p - point) <= 0 with
    OUTWARD normal n: pᵀQp = n·p - n·point (linear terms only)."""
    n = list(normal)
    d = sum(n[i] * point[i] for i in range(3))
    Q = [[0.0] * 4 for _ in range(4)]
    for i in range(3):
        Q[i][3] = Q[3][i] = n[i] / 2.0
    Q[3][3] = -d
    return Q


def sphere_quadric_matrix(center, radius):
    """(p-c)·(p-c) - r² as pᵀQp."""
    c = list(center)
    Q = [[0.0] * 4 for _ in range(4)]
    for i in range(3):
        Q[i][i] = 1.0
        Q[i][3] = Q[3][i] = -c[i]
    Q[3][3] = sum(x * x for x in c) - radius * radius
    return Q


def ellipsoid_quadric_matrix(center, radii):
    """Σ (p_i - c_i)²/s_i² - 1 as pᵀQp."""
    c = list(center)
    s = list(radii)
    Q = [[0.0] * 4 for _ in range(4)]
    for i in range(3):
        k = 1.0 / (s[i] * s[i])
        Q[i][i] = k
        Q[i][3] = Q[3][i] = -c[i] * k
    Q[3][3] = sum((c[i] * c[i]) / (s[i] * s[i])
                  for i in range(3)) - 1.0
    return Q


def box_plane_quadrics(center, size):
    """Six outward plane quadrics (labels ±x/±y/±z) whose max() is
    the box's implicit field."""
    out = []
    axes = ('x', 'y', 'z')
    for i in range(3):
        h = size[i] / 2.0
        for sign, tag in ((1.0, '+'), (-1.0, '-')):
            n = [0.0, 0.0, 0.0]
            n[i] = sign
            pt = list(center)
            pt[i] += sign * h
            out.append((f'face-{tag}{axes[i]}',
                        plane_quadric_matrix(n, pt)))
    return out
