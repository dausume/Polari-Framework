"""
@module zones.custom.zone_geometry

The estimate algorithm (AR_ZONE_CAPTURE_PLAN.md arz-2): real distances
between placed points, ground area, overall volume. Two models:

  prism — ground points (≥3, placed walking the perimeter) fit a
          plane; the projected polygon's shoelace area × height above
          the plane. 3 points = the minimal triangle footprint.
  hull  — free points anywhere in the air (≥4 non-coplanar) become a
          convex hull (scipy): the shape-in-the-air. Exactly 3 points
          degrade honestly to a planar triangle (area, volume 0, with
          the suggestion to add a 4th point).

WebXR coordinates are already METRIC — the real error source is
tracking drift, so calibration is a knob: two 'reference' points
across a KNOWN real length set the zone's scale_correction, and every
report says whether it was applied ('calibrated': bool). Distances
scale ×s, areas ×s², volumes ×s³.

@consumers zones.zones_api, zones.custom.zone_packing
@see /AR_ZONE_CAPTURE_PLAN.md
"""

import json
import math
from datetime import datetime, timezone

from scoring.worldview_elections_basis import _by_name, _rows

#: Plane-fit RMS residual above which the capture is suspect (m).
MAX_PLANE_RESIDUAL_M = 0.05

#: Height points aggregate at this percentile (median by default).
HEIGHT_PERCENTILE = 50


def _now():
    return datetime.now(timezone.utc).isoformat()


def zone_points(manager, zone_name, kinds=None):
    pts = [p for p in _rows(manager, 'ZonePoint')
           if getattr(p, 'zone_name', '') == zone_name
           and (kinds is None or getattr(p, 'kind', '') in kinds)]
    return sorted(pts, key=lambda p: getattr(p, 'index', 0))


def _xyz(point):
    return (float(point.x), float(point.y), float(point.z))


def _zone(manager, zone_name):
    return _by_name(manager, 'ZoneDefinition').get(zone_name)


def _scale(zone):
    try:
        s = float(getattr(zone, 'scale_correction', 1.0) or 1.0)
        return s if s > 0 else 1.0
    except Exception:
        return 1.0


def point_distances(manager, zone_name):
    """Perimeter/pairwise metric distances (calibration applied) —
    the live feedback the capture UI shows point-to-point."""
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'"}
    pts = zone_points(manager, zone_name,
                      kinds=('ground', 'free'))
    s = _scale(zone)
    legs = []
    for a, b in zip(pts, pts[1:]):
        ax, ay, az = _xyz(a)
        bx, by, bz = _xyz(b)
        legs.append({
            'fromIndex': a.index, 'toIndex': b.index,
            'meters': s * math.dist((ax, ay, az), (bx, by, bz))})
    return {'ok': True, 'zone': zone_name,
            'calibrated': s != 1.0, 'scaleCorrection': s,
            'legs': legs,
            'perimeterM': sum(l['meters'] for l in legs)}


def calibrate_zone(manager, zone_name, known_length_m):
    """Set scale_correction from the two 'reference' points placed
    across a known real length (e.g. a tape-measured 1.000 m stick)."""
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'"}
    refs = zone_points(manager, zone_name, kinds=('reference',))
    if len(refs) < 2:
        return {'ok': False,
                'error': f'{len(refs)} reference point(s) — '
                         'calibration needs exactly two, placed at '
                         'the ends of a known-length object',
                'suggestion': {
                    'knob': 'ZonePoint(kind=reference)',
                    'action': 'place two reference points across a '
                              'measured length, then calibrate'}}
    try:
        known = float(known_length_m)
    except (TypeError, ValueError):
        known = 0.0
    if known <= 0:
        return {'ok': False,
                'error': 'known_length_m must be a positive number'}
    measured = math.dist(_xyz(refs[0]), _xyz(refs[1]))
    if measured <= 0:
        return {'ok': False,
                'error': 'the two reference points coincide'}
    zone.scale_correction = known / measured
    try:
        manager.db.saveInstanceInDB(zone)
    except Exception:
        pass  # in-memory managers (selftests) have no db
    return {'ok': True, 'zone': zone_name,
            'measuredM': measured, 'knownM': known,
            'scaleCorrection': zone.scale_correction}


# --------------------------------------------------------------- #
# prism model
# --------------------------------------------------------------- #

def _plane_fit(points):
    """Least-squares plane via SVD: (centroid, unit normal, rms)."""
    import numpy as np
    arr = np.array(points, dtype=float)
    centroid = arr.mean(axis=0)
    _, _, vt = np.linalg.svd(arr - centroid)
    normal = vt[-1]
    if normal[1] < 0:  # orient toward +y (up) when possible
        normal = -normal
    residuals = (arr - centroid) @ normal
    rms = float(np.sqrt((residuals ** 2).mean()))
    return centroid, normal, rms


def _project_to_plane(points, centroid, normal):
    """2D coordinates of each point in an orthonormal in-plane basis."""
    import numpy as np
    arr = np.array(points, dtype=float)
    seed = np.array([1.0, 0.0, 0.0])
    if abs(float(seed @ normal)) > 0.9:
        seed = np.array([0.0, 0.0, 1.0])
    u = seed - (seed @ normal) * normal
    u = u / np.linalg.norm(u)
    v = np.cross(normal, u)
    rel = arr - centroid
    return [(float(r @ u), float(r @ v)) for r in rel], u, v


def _shoelace(poly2d):
    n = len(poly2d)
    total = 0.0
    for i in range(n):
        x1, y1 = poly2d[i]
        x2, y2 = poly2d[(i + 1) % n]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def _segments_cross(a, b, c, d):
    def orient(p, q, r):
        val = ((q[0] - p[0]) * (r[1] - p[1])
               - (q[1] - p[1]) * (r[0] - p[0]))
        return 0 if abs(val) < 1e-12 else (1 if val > 0 else -1)
    return (orient(a, b, c) != orient(a, b, d)
            and orient(c, d, a) != orient(c, d, b))


def _self_intersection(poly2d):
    n = len(poly2d)
    for i in range(n):
        a, b = poly2d[i], poly2d[(i + 1) % n]
        for j in range(i + 1, n):
            if j in (i, (i + 1) % n) or (j + 1) % n == i:
                continue
            c, d = poly2d[j], poly2d[(j + 1) % n]
            if _segments_cross(a, b, c, d):
                return (i, j)
    return None


def _percentile(values, pct):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    k = (len(ordered) - 1) * pct / 100.0
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def estimate_prism(manager, zone_name, default_height_m=0.0,
                   max_residual_m=MAX_PLANE_RESIDUAL_M,
                   height_percentile=HEIGHT_PERCENTILE):
    """Ground polygon (as placed) × height. 3 ground points is the
    minimal volume capture (a triangle footprint)."""
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'"}
    ground = zone_points(manager, zone_name, kinds=('ground',))
    if len(ground) < 3:
        return {'ok': False,
                'error': f'{len(ground)} ground point(s) — a volume '
                         'needs at least 3 (the minimal triangle '
                         'footprint)',
                'suggestion': {'knob': 'ZonePoint(kind=ground)',
                               'action': 'place at least 3 ground '
                                         'points walking the '
                                         'perimeter'}}
    coords = [_xyz(p) for p in ground]
    centroid, normal, rms = _plane_fit(coords)
    warnings = []
    if rms > max_residual_m:
        warnings.append(
            f'plane-fit RMS residual {rms:.3f} m exceeds '
            f'{max_residual_m} m — ground points may not be on one '
            'floor; consider recapturing')
    poly2d, _, _ = _project_to_plane(coords, centroid, normal)
    crossing = _self_intersection(poly2d)
    if crossing is not None:
        return {'ok': False,
                'error': 'footprint self-intersects between the '
                         f'edges starting at points {crossing[0]} '
                         f'and {crossing[1]} — points are ordered as '
                         'placed',
                'suggestion': {'knob': 'ZonePoint.index',
                               'action': 'reorder the points to walk '
                                         'the perimeter, or '
                                         'recapture'}}
    s = _scale(zone)
    area = _shoelace(poly2d) * s * s

    heights = zone_points(manager, zone_name, kinds=('height',))
    import numpy as np
    if heights:
        elevations = [float((np.array(_xyz(p)) - centroid) @ normal)
                      for p in heights]
        height = _percentile(elevations, height_percentile) * s
        height_source = f'{len(heights)} height point(s), ' \
                        f'p{height_percentile}'
    elif default_height_m > 0:
        height = float(default_height_m)
        height_source = 'ASSUMED default_height_m (no height points)'
        warnings.append('height is an assumed knob value, not a '
                        'captured measurement')
    else:
        height = 0.0
        height_source = 'none captured'
    model = 'prism' if height > 0 else 'footprint-only'
    if height <= 0:
        warnings.append('no height captured — volume unavailable; '
                        'place a height point or pass '
                        'default_height_m')
    return {'ok': True, 'zone': zone_name, 'model': model,
            'groundPoints': len(ground),
            'groundAreaM2': area,
            'heightM': height, 'heightSource': height_source,
            'volumeM3': area * height,
            'planeResidualRmsM': rms,
            'calibrated': s != 1.0, 'scaleCorrection': s,
            'warnings': warnings}


# --------------------------------------------------------------- #
# planar model (the default: imperfect dots -> horizontal plane ->
# extruded to an identical plane on the floor)
# --------------------------------------------------------------- #

#: Dot heights spreading wider than this (RMS) suggest the user was
#: not tracing one level — surfaced as a warning, never a silent fix.
MAX_PLANAR_SPREAD_M = 0.15


def estimate_planar(manager, zone_name,
                    max_spread_m=MAX_PLANAR_SPREAD_M):
    """Dot placement is assumed imperfect: heights are AVERAGED and
    every dot is forced into a horizontal plane at that height. The
    volume is that plane extruded straight down to an identical plane
    on the floor (y=0 in local-floor space)."""
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'"}
    pts = zone_points(manager, zone_name,
                      kinds=('ground', 'free'))
    if len(pts) < 3:
        return {'ok': False,
                'error': f'{len(pts)} point(s) — a planar zone needs '
                         'at least 3 dots tracing its outline',
                'suggestion': {'knob': 'ZonePoint',
                               'action': 'place at least 3 dots '
                                         'around the area at the '
                                         'intended top height'}}
    heights = [float(p.y) for p in pts]
    plane_y = sum(heights) / len(heights)
    spread = (sum((h - plane_y) ** 2 for h in heights)
              / len(heights)) ** 0.5
    warnings = []
    if spread > max_spread_m:
        warnings.append(
            f'dot heights spread {spread:.3f} m RMS around the '
            f'averaged plane (> {max_spread_m} m) — the dots may not '
            'trace one level; the plane is forced to the average '
            'anyway')
    poly2d = [(float(p.x), float(p.z)) for p in pts]
    crossing = _self_intersection(poly2d)
    if crossing is not None:
        return {'ok': False,
                'error': 'outline self-intersects between the edges '
                         f'starting at dots {crossing[0]} and '
                         f'{crossing[1]} — dots are ordered as '
                         'placed',
                'suggestion': {'knob': 'ZonePoint.index',
                               'action': 'reorder or replace the '
                                         'dots to walk the outline'}}
    s = _scale(zone)
    area = _shoelace(poly2d) * s * s
    height = plane_y * s
    if height <= 0:
        warnings.append('the averaged plane sits at/below the floor '
                        '— no volume; place dots at the intended TOP '
                        'height of the zone')
        height = 0.0
    return {'ok': True, 'zone': zone_name,
            'model': 'planar-extrusion',
            'points': len(pts),
            'planeHeightM': height,
            'planarSpreadRmsM': spread,
            'groundAreaM2': area,
            'heightM': height,
            'volumeM3': area * height,
            'calibrated': s != 1.0, 'scaleCorrection': s,
            'warnings': warnings}


# --------------------------------------------------------------- #
# hull model (the manual direct-3D mode: the shape in the air)
# --------------------------------------------------------------- #

def estimate_hull(manager, zone_name):
    """Convex hull of the free points: ≥4 non-coplanar points make a
    volume; exactly 3 degrade to a planar triangle (area only)."""
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'"}
    pts = zone_points(manager, zone_name, kinds=('free',))
    if len(pts) < 3:
        return {'ok': False,
                'error': f'{len(pts)} free point(s) — a shape needs '
                         'at least 3',
                'suggestion': {'knob': 'ZonePoint(kind=free)',
                               'action': 'place at least 3 points; 4 '
                                         'non-coplanar points make '
                                         'the first volume'}}
    coords = [_xyz(p) for p in pts]
    s = _scale(zone)
    if len(coords) == 3:
        a, b, c = coords
        import numpy as np
        area = float(np.linalg.norm(
            np.cross(np.array(b) - np.array(a),
                     np.array(c) - np.array(a))) / 2.0) * s * s
        return {'ok': True, 'zone': zone_name,
                'model': 'planar-triangle', 'points': 3,
                'surfaceAreaM2': area, 'volumeM3': 0.0,
                'calibrated': s != 1.0, 'scaleCorrection': s,
                'warnings': ['3 points span a flat triangle — add a '
                             '4th (non-coplanar) point to enclose a '
                             'volume']}
    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(coords)
    except Exception as e:
        return {'ok': False,
                'error': f'convex hull failed: {e} — the points are '
                         'likely coplanar/collinear',
                'suggestion': {'knob': 'ZonePoint(kind=free)',
                               'action': 'spread points out of the '
                                         'shared plane'}}
    return {'ok': True, 'zone': zone_name, 'model': 'hull',
            'points': len(coords),
            'hullVertices': int(len(hull.vertices)),
            'surfaceAreaM2': float(hull.area) * s * s,
            'volumeM3': float(hull.volume) * s * s * s,
            'calibrated': s != 1.0, 'scaleCorrection': s,
            'warnings': []}


def estimate_zone(manager, zone_name, **knobs):
    """Mode dispatch + persisted ZoneEstimateRecord."""
    zone = _zone(manager, zone_name)
    if zone is None:
        return {'ok': False,
                'error': f"no ZoneDefinition named '{zone_name}'",
                'knownZones': sorted(
                    _by_name(manager, 'ZoneDefinition'))}
    mode = getattr(zone, 'capture_mode', 'planar')
    if mode == 'hull':
        report = estimate_hull(manager, zone_name)
    elif mode == 'prism':
        report = estimate_prism(manager, zone_name, **knobs)
    else:
        report = estimate_planar(manager, zone_name)
    if report.get('ok'):
        from zones.zone_basis import ZoneEstimateRecord
        record = ZoneEstimateRecord(
            name=f'est--{zone_name}--{_now()}',
            zone_name=zone_name, model=report['model'],
            ground_area_m2=report.get('groundAreaM2',
                                      report.get('surfaceAreaM2', 0.0)),
            height_m=report.get('heightM', 0.0),
            volume_m3=report.get('volumeM3', 0.0),
            calibrated=report.get('calibrated', False),
            report_json=json.dumps(report), computed_at=_now(),
            manager=manager)
        table = manager.objectTables.setdefault('ZoneEstimateRecord',
                                                {})
        table[record.name] = record
        try:
            manager.db.saveInstanceInDB(record)
        except Exception:
            pass
    return report
