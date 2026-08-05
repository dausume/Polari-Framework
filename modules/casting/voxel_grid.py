"""
@cross-cutting
@module casting.voxel_grid
@tags @xc:bindings

cast-2: the framework's first REUSABLE occupancy grid. The voxelizer
has existed since shape-1 — buried inside
mathshapes.shape_analysis._grid_properties, which builds an interior
cell dict, reads a volume off it, and throws it away. This module
lifts that loop into a structure the casting pipeline (and later the
fill/demold sims) can keep and traverse, and adds what the framework
has never had anywhere: flood-fill and connected components.

The voxel side answers the questions the analytic field cannot
without root-finding — connectivity, trapped regions, reachability.
The analytic side (mathshapes equations) stays the authority on what
the geometry IS; where both can answer (volume), they cross-check.

Pure stdlib; cells are (i,j,k) tuples in a dict-backed set, matching
the existing _grid_properties idiom (no numpy dependency).

@consumers
  - casting.mold_geometry (grid derivation for imported meshes),
    casting.mesh_voxelize, cast-5 fill sim, cast-7 demold sweep
@see /WAX_MOLD_NESTING_PLAN.md (PHASE cast-2)
"""

from collections import deque

#: Same clamp as shape_analysis._grid_properties — the two
#: instruments stay comparable.
MAX_RESOLUTION = 80
#: 6-connectivity — fluid/air moves through faces, not corners.
NEIGHBOURS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
              (0, -1, 0), (0, 0, 1), (0, 0, -1))


class OccupancyGrid:
    """An axis-aligned grid over `bounds` with n cells per axis and a
    set of occupied (inside) cells. Cells are rectangular — the cell
    aspect follows the bounds, exactly like _grid_properties."""

    def __init__(self, bounds, n, inside=None):
        n = max(4, min(int(n), MAX_RESOLUTION))
        (x0, x1), (y0, y1), (z0, z1) = bounds
        self.bounds = [[float(x0), float(x1)], [float(y0), float(y1)],
                       [float(z0), float(z1)]]
        self.n = n
        self.dx = (x1 - x0) / n
        self.dy = (y1 - y0) / n
        self.dz = (z1 - z0) / n
        self.cell_volume = self.dx * self.dy * self.dz
        self.inside = set(inside or ())

    # -- construction ---------------------------------------------------
    @classmethod
    def from_predicate(cls, bounds, n, fn):
        """Occupy every cell whose CENTER satisfies fn(x, y, z)."""
        grid = cls(bounds, n)
        for i in range(grid.n):
            cx = grid.bounds[0][0] + (i + 0.5) * grid.dx
            for j in range(grid.n):
                cy = grid.bounds[1][0] + (j + 0.5) * grid.dy
                for k in range(grid.n):
                    cz = grid.bounds[2][0] + (k + 0.5) * grid.dz
                    if fn(cx, cy, cz):
                        grid.inside.add((i, j, k))
        return grid

    @classmethod
    def from_shape(cls, manager, shape_name, resolution=32,
                   bounds=None):
        """Voxelize a math shape through the SAME membership test
        _grid_properties uses. Imported meshes refuse here — their
        field silently evaluates outside-everywhere (the cast-1 trap);
        casting.mesh_voxelize.mesh_grid is their honest path."""
        from mathshapes.shape_analysis import (
            _evaluate_shape, _named, _shape_bounds,
        )
        shape = _named(manager, shape_name)
        if shape is None:
            return {'ok': False,
                    'error': f"no MathShapeDefinition named "
                             f"'{shape_name}'"}
        family = getattr(shape, 'family', 'primitive')
        if family == 'imported-mesh':
            return {'ok': False,
                    'error': f"'{shape_name}' is an imported mesh — "
                             f'its field silently reads outside-'
                             f'everywhere; voxelize it via '
                             f'casting.mesh_voxelize.mesh_grid '
                             f'instead'}
        b = bounds or _shape_bounds(manager, shape)
        if b is None:
            return {'ok': False,
                    'error': f"'{shape_name}' has no derivable bounds"}
        return cls.from_predicate(
            b, resolution,
            lambda x, y, z: _evaluate_shape(manager, shape, x, y, z)[0])

    # -- geometry -------------------------------------------------------
    def cell_center(self, cell):
        i, j, k = cell
        return (self.bounds[0][0] + (i + 0.5) * self.dx,
                self.bounds[1][0] + (j + 0.5) * self.dy,
                self.bounds[2][0] + (k + 0.5) * self.dz)

    def point_cell(self, x, y, z):
        i = int((x - self.bounds[0][0]) / self.dx)
        j = int((y - self.bounds[1][0]) / self.dy)
        k = int((z - self.bounds[2][0]) / self.dz)
        if 0 <= i < self.n and 0 <= j < self.n and 0 <= k < self.n:
            return (i, j, k)
        return None

    def volume_cm3(self):
        return len(self.inside) * self.cell_volume

    def surface_area_cm2(self):
        """Boundary faces exposed to a non-inside neighbour — the
        _grid_properties estimator, verbatim semantics."""
        fx, fy, fz = (self.dy * self.dz, self.dx * self.dz,
                      self.dx * self.dy)
        area = 0.0
        for (i, j, k) in self.inside:
            for (di, dj, dk), fa in zip(NEIGHBOURS,
                                        (fx, fx, fy, fy, fz, fz)):
                if (i + di, j + dj, k + dk) not in self.inside:
                    area += fa
        return area

    # -- set algebra (bounds/resolution must match — refuse, not guess) -
    def _compatible(self, other):
        return (self.n == other.n and self.bounds == other.bounds)

    def difference(self, other):
        if not self._compatible(other):
            return {'ok': False, 'error': 'grid bounds/resolution '
                    'differ — resample onto one lattice first'}
        return OccupancyGrid(self.bounds, self.n,
                             self.inside - other.inside)

    def union(self, other):
        if not self._compatible(other):
            return {'ok': False, 'error': 'grid bounds/resolution '
                    'differ — resample onto one lattice first'}
        return OccupancyGrid(self.bounds, self.n,
                             self.inside | other.inside)

    def intersection(self, other):
        if not self._compatible(other):
            return {'ok': False, 'error': 'grid bounds/resolution '
                    'differ — resample onto one lattice first'}
        return OccupancyGrid(self.bounds, self.n,
                             self.inside & other.inside)

    def complement(self):
        """Every in-bounds cell NOT occupied — for a mold body this is
        the cavity (plus nothing else when bounds == the stock)."""
        all_cells = {(i, j, k) for i in range(self.n)
                     for j in range(self.n) for k in range(self.n)}
        return OccupancyGrid(self.bounds, self.n,
                             all_cells - self.inside)

    # -- connectivity (new to the framework) ----------------------------
    def flood_fill(self, seeds, cells=None):
        """BFS over face-adjacent cells of `cells` (default: inside)
        reachable from `seeds`. The primitive under fill simulation,
        vent reachability and trapped-air detection."""
        domain = self.inside if cells is None else set(cells)
        frontier = deque(c for c in seeds if c in domain)
        reached = set(frontier)
        while frontier:
            i, j, k = frontier.popleft()
            for di, dj, dk in NEIGHBOURS:
                nxt = (i + di, j + dj, k + dk)
                if nxt in domain and nxt not in reached:
                    reached.add(nxt)
                    frontier.append(nxt)
        return reached

    def connected_components(self, cells=None):
        """Face-connected components of `cells` (default: inside),
        largest first. Two chambers in one mold = two components —
        the question no analytic field answers directly."""
        domain = self.inside if cells is None else set(cells)
        remaining = set(domain)
        components = []
        while remaining:
            seed = next(iter(remaining))
            comp = self.flood_fill((seed,), remaining)
            components.append(comp)
            remaining -= comp
        return sorted(components, key=len, reverse=True)

    def summary(self):
        return {'resolution': self.n, 'bounds': self.bounds,
                'cellVolumeCm3': round(self.cell_volume, 8),
                'occupiedCells': len(self.inside),
                'volumeCm3': round(self.volume_cm3(), 4)}
