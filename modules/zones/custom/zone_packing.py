"""
@module zones.custom.zone_packing

Dustin's target simulation (AR_ZONE_CAPTURE_PLAN.md arz-3): populate
the captured zone with 0.25 m cubes, stacked, and report how many fit.
The cubes are PLACEHOLDERS for future real objects, so the result is a
shape-agnostic placement LATTICE (frame + occupied cells + cube size),
not per-cube geometry — a 10k-cube zone stays a small payload and a
future object just swaps what gets instanced per cell.

  prism zones — the footprint polygon is rasterized at cube size in
                the fitted plane's frame; layers stack along the
                plane normal: floor(height / cube).
  hull zones  — a 3D grid over the hull's bounding box; a cell holds
                a cube when it lies inside the hull.

fit_test knob: 'full-cell' (every checked corner inside — honest
default, undercounts edges) | 'center' (cell center only —
overcounts). footprint/volume utilization report the edge loss.

@consumers zones.zones_api
@see /AR_ZONE_CAPTURE_PLAN.md
"""

import math

from zones.custom.zone_geometry import (_plane_fit, _project_to_plane,
                                 _scale, _shoelace, _xyz, _zone,
                                 estimate_planar, estimate_prism,
                                 estimate_zone, zone_points)

DEFAULT_CUBE_M = 0.25
FIT_TESTS = ('full-cell', 'center')

#: Cells listed explicitly before the lattice degrades to counts-only
#: (the frame + counts still let a renderer regenerate coarse layout).
MAX_LISTED_CELLS = 50000


def _point_in_polygon(x, y, poly2d):
    inside = False
    n = len(poly2d)
    for i in range(n):
        x1, y1 = poly2d[i]
        x2, y2 = poly2d[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            t = (y - y1) / (y2 - y1)
            if x < x1 + t * (x2 - x1):
                inside = not inside
    return inside


def _cell_fits_polygon(i, j, cube, poly2d, fit_test):
    if fit_test == 'center':
        return _point_in_polygon((i + 0.5) * cube, (j + 0.5) * cube,
                                 poly2d)
    # Corners nudged a hair toward the cell center: a cube whose face
    # lies exactly ON the boundary fits (the strict ray-cast would
    # otherwise drop every edge-flush cube).
    eps = 1e-9
    corners = ((i + eps, j + eps), (i + 1 - eps, j + eps),
               (i + eps, j + 1 - eps), (i + 1 - eps, j + 1 - eps))
    return all(_point_in_polygon(cx * cube, cy * cube, poly2d)
               for cx, cy in corners) \
        and _point_in_polygon((i + 0.5) * cube, (j + 0.5) * cube,
                              poly2d)


def pack_prism(manager, zone_name, cube_size_m=DEFAULT_CUBE_M,
               fit_test='full-cell', default_height_m=0.0):
    estimate = estimate_prism(manager, zone_name,
                              default_height_m=default_height_m)
    if not estimate.get('ok'):
        return estimate
    if estimate['heightM'] <= 0:
        return {'ok': False,
                'error': 'no height — nothing to stack',
                'estimate': estimate,
                'suggestion': {'knob': 'default_height_m',
                               'action': 'place a height point or '
                                         'pass default_height_m'}}
    zone = _zone(manager, zone_name)
    ground = zone_points(manager, zone_name, kinds=('ground',))
    coords = [_xyz(p) for p in ground]
    centroid, normal, _ = _plane_fit(coords)
    poly2d, u, v = _project_to_plane(coords, centroid, normal)
    s = _scale(zone)
    # Work in CALIBRATED meters: scale the polygon once, then the
    # lattice frame carries real-world cell size directly.
    poly2d = [(x * s, y * s) for (x, y) in poly2d]
    cube = float(cube_size_m)
    if cube <= 0:
        return {'ok': False, 'error': 'cube_size_m must be positive'}
    xs = [p[0] for p in poly2d]
    ys = [p[1] for p in poly2d]
    # Anchor the lattice at the footprint's min corner (how a human
    # packs a room) — centroid-multiple anchoring wastes edge space.
    min_x, min_y = min(xs), min(ys)
    shifted = [(x - min_x, y - min_y) for (x, y) in poly2d]
    ni = math.ceil((max(xs) - min_x) / cube)
    nj = math.ceil((max(ys) - min_y) / cube)
    cells = [[i, j]
             for i in range(ni)
             for j in range(nj)
             if _cell_fits_polygon(i, j, cube, shifted, fit_test)]
    # 1e-9 tolerance: plane-fit float noise must not drop a layer
    # whose real height is exactly a cube multiple.
    layers = int((estimate['heightM'] + 1e-9) // cube)
    per_layer = len(cells)
    total = per_layer * layers
    area = estimate['groundAreaM2']
    return {'ok': True, 'zone': zone_name, 'model': 'prism',
            'cubeSizeM': cube, 'fitTest': fit_test,
            'cubesPerLayer': per_layer, 'layers': layers,
            'totalCubes': total,
            'groundAreaM2': area,
            'footprintUtilization': (per_layer * cube * cube / area)
            if area > 0 else 0.0,
            'volumeM3': estimate['volumeM3'],
            'volumeUtilization': (total * cube ** 3
                                  / estimate['volumeM3'])
            if estimate['volumeM3'] > 0 else 0.0,
            'estimate': estimate,
            'lattice': {
                'frame': {'origin': [float(c) for c in centroid],
                          'u': [float(c) for c in u],
                          'v': [float(c) for c in v],
                          'normal': [float(c) for c in normal]},
                # Cell (i,j,layer) sits at origin
                #   + (cellOrigin2d[0] + (i+0.5)·cell)·u
                #   + (cellOrigin2d[1] + (j+0.5)·cell)·v
                #   + (layer+0.5)·cell·normal   (calibrated meters).
                'cellOrigin2d': [min_x, min_y],
                'cellSizeM': cube,
                'cells': cells if len(cells) <= MAX_LISTED_CELLS
                else [],
                'cellsListed': len(cells) <= MAX_LISTED_CELLS,
            }}


def pack_planar(manager, zone_name, cube_size_m=DEFAULT_CUBE_M,
                fit_test='full-cell'):
    """Planar zones extrude between the floor and the averaged plane:
    the horizontal outline is rasterized in XZ and layers stack up
    from the floor (y up)."""
    estimate = estimate_planar(manager, zone_name)
    if not estimate.get('ok'):
        return estimate
    if estimate['heightM'] <= 0:
        return {'ok': False,
                'error': 'the averaged plane sits at/below the floor '
                         '— nothing to stack',
                'estimate': estimate,
                'suggestion': {'knob': 'ZonePoint.y',
                               'action': 'place dots at the intended '
                                         'TOP height of the zone'}}
    zone = _zone(manager, zone_name)
    pts = zone_points(manager, zone_name, kinds=('ground', 'free'))
    s = _scale(zone)
    poly2d = [(float(p.x) * s, float(p.z) * s) for p in pts]
    cube = float(cube_size_m)
    if cube <= 0:
        return {'ok': False, 'error': 'cube_size_m must be positive'}
    xs = [p[0] for p in poly2d]
    ys = [p[1] for p in poly2d]
    min_x, min_y = min(xs), min(ys)
    shifted = [(x - min_x, y - min_y) for (x, y) in poly2d]
    ni = math.ceil((max(xs) - min_x) / cube)
    nj = math.ceil((max(ys) - min_y) / cube)
    cells = [[i, j]
             for i in range(ni)
             for j in range(nj)
             if _cell_fits_polygon(i, j, cube, shifted, fit_test)]
    layers = int((estimate['heightM'] + 1e-9) // cube)
    per_layer = len(cells)
    total = per_layer * layers
    area = estimate['groundAreaM2']
    return {'ok': True, 'zone': zone_name,
            'model': 'planar-extrusion',
            'cubeSizeM': cube, 'fitTest': fit_test,
            'cubesPerLayer': per_layer, 'layers': layers,
            'totalCubes': total,
            'groundAreaM2': area,
            'footprintUtilization': (per_layer * cube * cube / area)
            if area > 0 else 0.0,
            'volumeM3': estimate['volumeM3'],
            'volumeUtilization': (total * cube ** 3
                                  / estimate['volumeM3'])
            if estimate['volumeM3'] > 0 else 0.0,
            'estimate': estimate,
            'lattice': {
                # Horizontal frame: u=x, v=z, layers stack along +y
                # from the floor.
                'frame': {'origin': [0.0, 0.0, 0.0],
                          'u': [1.0, 0.0, 0.0],
                          'v': [0.0, 0.0, 1.0],
                          'normal': [0.0, 1.0, 0.0]},
                'cellOrigin2d': [min_x, min_y],
                'cellSizeM': cube,
                'cells': cells if len(cells) <= MAX_LISTED_CELLS
                else [],
                'cellsListed': len(cells) <= MAX_LISTED_CELLS,
            }}


def pack_hull(manager, zone_name, cube_size_m=DEFAULT_CUBE_M,
              fit_test='full-cell'):
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'"}
    pts = zone_points(manager, zone_name, kinds=('free',))
    if len(pts) < 4:
        return {'ok': False,
                'error': f'{len(pts)} free point(s) — packing a hull '
                         'needs at least 4 (an enclosed volume)'}
    import numpy as np
    from scipy.spatial import ConvexHull
    s = _scale(zone)
    coords = np.array([_xyz(p) for p in pts], dtype=float) * s
    try:
        hull = ConvexHull(coords)
    except Exception as e:
        return {'ok': False,
                'error': f'convex hull failed: {e}'}
    cube = float(cube_size_m)
    if cube <= 0:
        return {'ok': False, 'error': 'cube_size_m must be positive'}

    # hull.equations: rows [a b c d] with a·x + d <= 0 inside.
    def inside(point):
        return bool(np.all(
            hull.equations[:, :3] @ point + hull.equations[:, 3]
            <= 1e-9))

    lo = coords.min(axis=0)
    hi = coords.max(axis=0)
    # Same min-corner anchoring as the prism path; corner tests nudged
    # inward so hull-face-flush cubes count.
    counts = [math.ceil((hi[k] - lo[k]) / cube) for k in range(3)]
    eps = 1e-9
    offsets = ([(0.5, 0.5, 0.5)] if fit_test == 'center' else
               [(a + eps if a == 0 else a - eps,
                 b + eps if b == 0 else b - eps,
                 c + eps if c == 0 else c - eps)
                for a in (0, 1) for b in (0, 1) for c in (0, 1)]
               + [(0.5, 0.5, 0.5)])
    cells = []
    for i in range(counts[0]):
        for j in range(counts[1]):
            for k in range(counts[2]):
                if all(inside(lo + np.array([(i + oa) * cube,
                                             (j + ob) * cube,
                                             (k + oc) * cube]))
                       for oa, ob, oc in offsets):
                    cells.append([i, j, k])
    volume = float(hull.volume)
    total = len(cells)
    return {'ok': True, 'zone': zone_name, 'model': 'hull',
            'cubeSizeM': cube, 'fitTest': fit_test,
            'totalCubes': total,
            'volumeM3': volume,
            'volumeUtilization': (total * cube ** 3 / volume)
            if volume > 0 else 0.0,
            'lattice': {
                # Cell (i,j,k) sits at origin + ((i,j,k)+0.5)·cell
                # along the axes (zone-local calibrated meters).
                'frame': {'origin': [float(c) for c in lo],
                          'u': [1.0, 0.0, 0.0],
                          'v': [0.0, 1.0, 0.0],
                          'normal': [0.0, 0.0, 1.0]},
                'cellSizeM': cube,
                'cells': cells if len(cells) <= MAX_LISTED_CELLS
                else [],
                'cellsListed': len(cells) <= MAX_LISTED_CELLS,
            }}


def pack_zone(manager, zone_name, cube_size_m=DEFAULT_CUBE_M,
              fit_test='full-cell', default_height_m=0.0):
    if fit_test not in FIT_TESTS:
        return {'ok': False,
                'error': f"fit_test must be one of {FIT_TESTS}"}
    zone = _zone(manager, zone_name)
    if zone is None:
        from scoring.worldview_elections_basis import _by_name
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'",
                'knownZones': sorted(
                    _by_name(manager, 'ZoneDefinition'))}
    mode = getattr(zone, 'capture_mode', 'planar')
    if mode == 'hull':
        return pack_hull(manager, zone_name, cube_size_m, fit_test)
    if mode == 'prism':
        return pack_prism(manager, zone_name, cube_size_m, fit_test,
                          default_height_m)
    return pack_planar(manager, zone_name, cube_size_m, fit_test)


def _selection_entry(manager, zone, cube_size_m):
    pack = pack_zone(manager, zone.name, cube_size_m)
    return {'zone': zone.name,
            'captureMode': zone.capture_mode, 'ok': pack.get('ok'),
            'volumeM3': pack.get('volumeM3', 0.0)
            if pack.get('ok') else 0.0,
            'totalCubes': pack.get('totalCubes', 0)
            if pack.get('ok') else 0,
            'error': pack.get('error')}


def room_summary(manager, room_zone_name,
                 cube_size_m=DEFAULT_CUBE_M):
    """BOTH volumes, as Dustin asked: the room's own volume AND the
    volumes/cube counts of the selections inside it. Packing targets
    the SELECTIONS; filling the whole room stays available by packing
    the room zone directly."""
    from scoring.worldview_elections_basis import _by_name, _rows
    room = _by_name(manager, 'ZoneDefinition').get(room_zone_name)
    if room is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named "
                         f"'{room_zone_name}'"}
    estimate = estimate_zone(manager, room_zone_name)
    selections = [
        _selection_entry(manager, zone, cube_size_m)
        for zone in _rows(manager, 'ZoneDefinition')
        if getattr(zone, 'room_zone_name', '') == room_zone_name
        and getattr(zone, 'zone_role', '') == 'selection']
    packed = [s for s in selections if s['ok']]
    return {'ok': True, 'room': room_zone_name,
            'roomLabel': room.room_label,
            'cubeSizeM': cube_size_m,
            'roomVolumeM3': estimate.get('volumeM3', 0.0)
            if estimate.get('ok') else 0.0,
            'roomEstimateOk': estimate.get('ok', False),
            'selections': selections,
            'selectedVolumeM3': sum(s['volumeM3'] for s in packed),
            'selectedCubes': sum(s['totalCubes'] for s in packed)}


def site_summary(manager, site_name, cube_size_m=DEFAULT_CUBE_M):
    """The HOUSE aggregate: every room's own volume + its selections'
    volumes/cube counts, plus free-standing selections. Needs no
    global frame — each zone is metrically sound locally and
    counts/volumes simply sum."""
    from scoring.worldview_elections_basis import _by_name, _rows
    site = _by_name(manager, 'SiteDefinition').get(site_name)
    if site is None:
        return {'ok': False,
                'error': f"no SiteDefinition named '{site_name}'",
                'knownSites': sorted(
                    _by_name(manager, 'SiteDefinition'))}
    zones = [z for z in _rows(manager, 'ZoneDefinition')
             if getattr(z, 'site_name', '') == site_name]
    rooms = [room_summary(manager, z.name, cube_size_m)
             for z in zones if getattr(z, 'zone_role', '') == 'room']
    in_rooms = {s['zone'] for r in rooms for s in r['selections']}
    free_selections = [
        _selection_entry(manager, z, cube_size_m)
        for z in zones
        if getattr(z, 'zone_role', '') == 'selection'
        and z.name not in in_rooms]
    packed_free = [s for s in free_selections if s['ok']]
    return {'ok': True, 'site': site_name,
            'cubeSizeM': cube_size_m,
            'zoneCount': len(zones),
            'rooms': rooms,
            'freeSelections': free_selections,
            'totalRoomVolumeM3': sum(r['roomVolumeM3']
                                     for r in rooms),
            'totalSelectedVolumeM3':
                sum(r['selectedVolumeM3'] for r in rooms)
                + sum(s['volumeM3'] for s in packed_free),
            'totalSelectedCubes':
                sum(r['selectedCubes'] for r in rooms)
                + sum(s['totalCubes'] for s in packed_free)}
