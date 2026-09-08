"""@module zones.objects.zone._shared — what the zone row classes share (constants, seeds, helpers); split from zone_basis.py (sap-2c)."""
from simulations.seed_data import SEED_SIMULATION_DEFINITIONS  # noqa: E402

CAPTURE_MODES = ('planar', 'hull', 'prism')
ZONE_ROLES = ('room', 'selection')
POINT_KINDS = ('ground', 'height', 'free', 'reference')
ZONE_STATUSES = ('capturing', 'committed')
def _demo_prism_points():
    """Hand-authored L-shaped room, 2×2 minus a 1×1 corner, 0.5 m
    ceiling point — so /display/zones renders live numbers."""
    ground = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]
    points = [
        {'name': f'demo-room-zone-p{i}', 'zone_name': 'demo-room-zone',
         'index': i, 'kind': 'ground',
         'x': float(x), 'y': 0.0, 'z': float(z)}
        for i, (x, z) in enumerate(ground)
    ]
    points.append(
        {'name': 'demo-room-zone-h0', 'zone_name': 'demo-room-zone',
         'index': len(points), 'kind': 'height',
         'x': 0.5, 'y': 0.5, 'z': 0.5})
    return points
def _demo_hull_points():
    """A 1 m cube's corners as free points — the minimal
    shape-in-the-air demo (hull volume exactly 1)."""
    corners = [(x, y, z) for x in (0, 1) for y in (0, 1)
               for z in (0, 1)]
    return [
        {'name': f'demo-air-shape-p{i}', 'zone_name': 'demo-air-shape',
         'index': i, 'kind': 'free',
         'x': float(x), 'y': float(y), 'z': float(z)}
        for i, (x, y, z) in enumerate(corners)
    ]
def _demo_planar_points():
    """A planar SELECTION inside the demo room: imperfect dots (heights
    jitter around 0.5 m) over a 1×0.5 m rectangle — averages to a
    0.5 m plane, extrudes 0.25 m³ to the floor."""
    outline = [((0.1, 0.1), 0.48), ((1.1, 0.1), 0.52),
               ((1.1, 0.6), 0.50), ((0.1, 0.6), 0.50)]
    return [
        {'name': f'demo-shelf-selection-p{i}',
         'zone_name': 'demo-shelf-selection', 'index': i,
         'kind': 'ground',
         'x': float(x), 'y': float(y), 'z': float(z)}
        for i, ((x, z), y) in enumerate(outline)
    ]
SEED_SITES = [
    {'name': 'demo-house', 'display_name': 'Demo house',
     'notes': 'Seeded site holding the demo zones.'},
]
SEED_ZONES = [
    {'name': 'demo-room-zone', 'display_name': 'Demo room (L-shape)',
     'site_name': 'demo-house', 'room_label': 'demo-room',
     'zone_role': 'room',
     'capture_mode': 'prism', 'capture_kind': 'desktop-authored',
     'status': 'committed',
     'origin_note': 'hand-authored L-shape, 3 m² × 0.5 m'},
    {'name': 'demo-shelf-selection',
     'display_name': 'Demo shelf selection (planar)',
     'site_name': 'demo-house', 'room_label': 'demo-room',
     'zone_role': 'selection', 'room_zone_name': 'demo-room-zone',
     'simulation_ref': 'zone-block-filling',
     'capture_mode': 'planar', 'capture_kind': 'desktop-authored',
     'status': 'committed',
     'origin_note': 'imperfect dots averaging to a 0.5 m plane over '
                    'a 1×0.5 m rectangle'},
    {'name': 'demo-air-shape', 'display_name': 'Demo air shape (1 m³)',
     'site_name': 'demo-house', 'room_label': 'demo-room',
     'zone_role': 'selection', 'room_zone_name': 'demo-room-zone',
     'simulation_ref': 'zone-block-filling',
     'capture_mode': 'hull', 'capture_kind': 'desktop-authored',
     'status': 'committed',
     'origin_note': 'hand-authored cube corners, hull volume 1 m³'},
]
SEED_ZONE_POINTS = (_demo_prism_points() + _demo_planar_points()
                    + _demo_hull_points())
if not any(s.get('name') == 'zone-block-filling'
           for s in SEED_SIMULATION_DEFINITIONS):
    SEED_SIMULATION_DEFINITIONS.append({
        'name': 'zone-block-filling',
        'description': (
            'Sample AR-required simulation: fills its tied captured '
            'zones with 0.25 m blocks (placeholders for future real '
            'objects) and renders them in AR inside the real space. '
            'Requirements: capture at least one zone selection tied '
            'to this simulation. v1 output is the packed lattice; '
            'time-stepped filling rides SimulationRunner later.'),
        'intent': 'observe',
        'time_step_seconds': 1.0,
        'duration_seconds': 60.0,
        'xr_requirement': 'ar-capture',
    })
