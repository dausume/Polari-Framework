"""
@cross-cutting
@module casting.mesh_voxelize
@tags @xc:bindings

cast-2: the FreeCAD/STL bridge — an imported mesh becomes an
OccupancyGrid, so any part (math shape or CAD import) enters the
casting pipeline as the same structure. This closes the cast-1 trap
honestly: an imported mesh still has NO analytic field (mathshapes
refuses equations for it, correctly), but it now has a grid, which
is all the fill/demold/undercut machinery needs.

Method: column parity ray casting. For each (y,z) grid column, every
triangle crossed by the +x ray contributes one crossing-x (computed
barycentrically on the triangle's yz projection); a cell center is
inside iff an ODD number of crossings lie beyond it. Triangles
parallel to the ray project to ~zero yz area and are skipped —
exactly the faces that cannot cross the ray. Column points carry a
tiny deterministic jitter so cell centers cannot land exactly on
projected edges/vertices (the classic parity degeneracy) — named
here, not hidden.

Shrink allowance for meshes is vertex algebra: v → s·v about the
origin — the same uniform scale the quadric transform applies to
math shapes, exact for a mesh by construction.

Watertightness is CHECKED (gap geo-mesh-watertight closed): every
edge of a closed manifold is shared by exactly two triangles; a mesh
failing that REFUSES with the boundary-edge count — parity on a
holed mesh misclassifies every column beyond the hole, so proceeding
would be confident garbage. Self-intersection and units (cm ASSUMED
— STL carries none) remain named gaps.

@consumers casting.mold_geometry (imported-part derivation), cast-5+
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-2)
"""

import json
from bisect import bisect_right

from casting.voxel_grid import OccupancyGrid

#: Deterministic sub-cell jitter keeping column rays off projected
#: mesh edges/vertices (two different irrational-ish fractions so a
#: column never sits on an axis-aligned edge in BOTH y and z).
_JITTER_Y = 1.0e-7 * 1.618
_JITTER_Z = 1.0e-7 * 2.414
#: Degenerate-projection threshold: |2·area| of the yz-projected
#: triangle below this (relative to its bbox scale) = parallel to
#: the ray, skipped.
_DEGENERATE_EPS = 1.0e-12

UNITS_GAP = ('units ASSUMED cm — STL/STEP carry none; a ~10× bbox '
             'surprise means the source was modelled in mm '
             '(gap geo-import-units)')
SELF_INTERSECT_GAP = ('self-intersection unchecked — overlapping '
                      'shells double-count parity crossings '
                      '(gap geo-mesh-self-intersect)')


def manifold_check(triangles):
    """Closed-manifold edge test: every undirected edge shared by
    exactly 2 triangles. Uses INDEX topology when available; falls
    back to vertex-position keys for pre-flattened triangle lists."""
    edge_count = {}
    for tri in triangles:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]),
                     (tri[2], tri[0])):
            ka, kb = (tuple(a), tuple(b)) if not isinstance(a, int) \
                else (a, b)
            key = (ka, kb) if ka <= kb else (kb, ka)
            edge_count[key] = edge_count.get(key, 0) + 1
    bad = sum(1 for c in edge_count.values() if c != 2)
    return {'watertight': bad == 0, 'edges': len(edge_count),
            'boundaryOrOddEdges': bad}


def triangles_of(shape, scale=1.0):
    """World-space triangles from an imported-mesh shape row's cached
    parameters_json (meshPoints + triangles, the cad_import cache),
    with the exact vertex scale applied. Refuses when the cache is
    absent — absent data is absent."""
    try:
        cached = json.loads(getattr(shape, 'parameters_json', '{}')
                            or '{}')
    except (TypeError, ValueError):
        cached = {}
    points = cached.get('meshPoints') or []
    tris = cached.get('triangles') or []
    if not points or not tris:
        return {'ok': False,
                'error': f"'{getattr(shape, 'name', '')}' carries no "
                         f'cached mesh (meshPoints/triangles empty) — '
                         f're-import it via cad_import, or the '
                         f'original import predates the mesh cache'}
    s = float(scale)
    verts = [(float(p[0]) * s, float(p[1]) * s, float(p[2]) * s)
             for p in points]
    out = []
    for t in tris:
        try:
            out.append((verts[t[0]], verts[t[1]], verts[t[2]]))
        except (IndexError, TypeError):
            return {'ok': False,
                    'error': 'triangle index out of range — corrupt '
                             'mesh cache'}
    return {'ok': True, 'triangles': out, 'vertexCount': len(verts)}


def _column_crossings(triangles, cy, cz):
    """Sorted x-coordinates where the +x ray through (cy, cz) crosses
    the mesh. Barycentric on the yz projection."""
    xs = []
    for (v0, v1, v2) in triangles:
        # yz-projected edge vectors
        d1y, d1z = v1[1] - v0[1], v1[2] - v0[2]
        d2y, d2z = v2[1] - v0[1], v2[2] - v0[2]
        det = d1y * d2z - d1z * d2y
        scale = (abs(d1y) + abs(d1z) + abs(d2y) + abs(d2z)) or 1.0
        if abs(det) <= _DEGENERATE_EPS * scale * scale:
            continue                    # parallel to the ray
        py, pz = cy - v0[1], cz - v0[2]
        u = (py * d2z - pz * d2y) / det
        v = (d1y * pz - d1z * py) / det
        if u < 0.0 or v < 0.0 or (u + v) > 1.0:
            continue
        xs.append(v0[0] + u * (v1[0] - v0[0]) + v * (v2[0] - v0[0]))
    xs.sort()
    return xs


def mesh_grid(shape, resolution=32, scale=1.0, bounds=None):
    """OccupancyGrid of an imported-mesh shape row. Bounds default to
    the shape's stored AABB (scaled); pass explicit bounds to land on
    a shared lattice (e.g. the mold stock) for grid set-algebra.
    Non-watertight meshes REFUSE — parity would be confident
    garbage."""
    tri_res = triangles_of(shape, scale=scale)
    if not tri_res.get('ok'):
        return tri_res
    triangles = tri_res['triangles']
    manifold = manifold_check(triangles)
    if not manifold['watertight']:
        return {'ok': False, 'manifold': manifold,
                'error': f"mesh '{getattr(shape, 'name', '')}' is "
                         f'not watertight: '
                         f"{manifold['boundaryOrOddEdges']} of "
                         f"{manifold['edges']} edges are boundary/"
                         f'odd-shared — ray parity misclassifies '
                         f'every column beyond a hole. Repair the '
                         f'mesh (or re-export as a solid) and '
                         f're-import.'}
    if bounds is None:
        try:
            b = json.loads(getattr(shape, 'bounds_json', '') or 'null')
        except (TypeError, ValueError):
            b = None
        if not b:
            return {'ok': False,
                    'error': f"'{getattr(shape, 'name', '')}' has no "
                             f'bounds_json and no bounds were given'}
        s = float(scale)
        bounds = [[float(lo) * s, float(hi) * s] for lo, hi in b]

    grid = OccupancyGrid(bounds, resolution)
    for j in range(grid.n):
        cy = grid.bounds[1][0] + (j + 0.5) * grid.dy + _JITTER_Y
        for k in range(grid.n):
            cz = grid.bounds[2][0] + (k + 0.5) * grid.dz + _JITTER_Z
            xs = _column_crossings(triangles, cy, cz)
            if not xs:
                continue
            for i in range(grid.n):
                cx = grid.bounds[0][0] + (i + 0.5) * grid.dx
                # inside iff an odd number of crossings lie beyond cx
                if (len(xs) - bisect_right(xs, cx)) % 2 == 1:
                    grid.inside.add((i, j, k))
    return {'ok': True, 'grid': grid,
            'triangleCount': len(triangles),
            'vertexCount': tri_res['vertexCount'],
            'scale': float(scale), 'manifold': manifold,
            'gaps': [UNITS_GAP, SELF_INTERSECT_GAP],
            'summary': grid.summary()}
