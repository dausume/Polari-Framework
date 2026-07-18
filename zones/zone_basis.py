"""
@module zones.zone_basis
@tags @xc:bindings

AR zone capture rows (AR_ZONE_CAPTURE_PLAN.md arz-1, Dustin
2026-07-17): capture a 3D area by placing points in AR — 3 points
minimum for a volume, more to make a shape in the air — then size and
place simulated objects inside it.

  SiteDefinition     — the HOUSE/lot: a named collection of zones
                       captured room-by-room, so "how much fits in the
                       whole house" needs no global coordinate frame.
  ZoneDefinition     — one captured zone. capture_mode 'prism' (ground
                       polygon + height) or 'hull' (free points, the
                       shape-in-the-air). scale_correction is the
                       calibration knob (reference points across a
                       KNOWN real length).
  ZonePoint          — one placed point, METERS in zone-local space
                       (WebXR local-floor is metric, y up). kind
                       'ground' | 'height' | 'free' | 'reference'.
  ZoneEstimateRecord — persisted estimate verdicts so a zone's history
                       stays inspectable.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - zones.zones_api / zone_geometry / zone_packing
@see /AR_ZONE_CAPTURE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: How the zone's boundary is interpreted.
#: 'planar' — the DEFAULT capture: dot placement is assumed imperfect,
#:            so dot heights are AVERAGED and the dots are forced into
#:            a horizontal plane at that height; the volume is that
#:            plane extruded down to an identical plane on the floor.
#: 'hull'   — the manual direct-3D mode: free dots anywhere, forced
#:            into a single 3D shape (convex hull) on finalize.
#: 'prism'  — ground polygon + explicit height points (the original
#:            arz-2 model; kept for captures that measure a slope).
CAPTURE_MODES = ('planar', 'hull', 'prism')

#: What the zone IS: a 'room' (the containing space — its volume is
#: reported, and filling the whole room stays possible) or a
#: 'selection' (the designated sub-area that packing targets).
ZONE_ROLES = ('room', 'selection')

#: Point roles. 'free' points are the hull mode's shape-in-the-air;
#: 'reference' points calibrate (never enter geometry).
POINT_KINDS = ('ground', 'height', 'free', 'reference')

ZONE_STATUSES = ('capturing', 'committed')


class SiteDefinition(treeObject):
    """A named collection of zones (a house, a lot)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.notes = notes


class ZoneDefinition(treeObject):
    """One captured 3D zone."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        # Optional site membership + room label ('kitchen', 'garage').
        site_name: str = '',
        room_label: str = '',
        # ZONE_ROLES entry: 'room' = the containing space, 'selection'
        # = the packed sub-area.
        zone_role: str = 'selection',
        # For selections: which room zone contains this one.
        room_zone_name: str = '',
        # Selections are TIED to a specific simulation (Dustin: zones
        # do not stand on their own); rooms leave this '' — captured
        # reality is shared between simulations.
        simulation_ref: str = '',
        # CAPTURE_MODES entry.
        capture_mode: str = 'planar',
        capture_kind: str = 'desktop-authored',  # | 'ar-headset'
        # Which WebXR reference space captured it ('local-floor' |
        # 'unbounded' | '' for desktop) — accuracy evidence.
        reference_space: str = '',
        # What the zone-local origin anchors to in the real room.
        origin_note: str = '',
        # Calibration factor (known_length / measured_length).
        scale_correction: float = 1.0,
        status: str = 'capturing',
        captured_by: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.site_name = site_name
        self.room_label = room_label
        self.zone_role = zone_role
        self.room_zone_name = room_zone_name
        self.simulation_ref = simulation_ref
        self.capture_mode = capture_mode
        self.capture_kind = capture_kind
        self.reference_space = reference_space
        self.origin_note = origin_note
        self.scale_correction = scale_correction
        self.status = status
        self.captured_by = captured_by
        self.notes = notes


class ZonePoint(treeObject):
    """One placed point, meters in zone-local space (y up)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        zone_name: str = '',
        index: int = 0,
        # POINT_KINDS entry.
        kind: str = 'ground',
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        # 'tracked' (live XR pose) | 'estimated' (desktop-authored).
        confidence: str = 'estimated',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.zone_name = zone_name
        self.index = index
        self.kind = kind
        self.x = x
        self.y = y
        self.z = z
        self.confidence = confidence
        self.notes = notes


class ZoneEstimateRecord(treeObject):
    """A persisted estimate verdict (area/volume + evidence)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        zone_name: str = '',
        # 'prism' | 'hull' | 'planar-triangle' | 'footprint-only'.
        model: str = '',
        ground_area_m2: float = 0.0,
        height_m: float = 0.0,
        volume_m3: float = 0.0,
        calibrated: bool = False,
        report_json: str = '{}',
        computed_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.zone_name = zone_name
        self.model = model
        self.ground_area_m2 = ground_area_m2
        self.height_m = height_m
        self.volume_m3 = volume_m3
        self.calibrated = calibrated
        self.report_json = report_json
        self.computed_at = computed_at
        self.notes = notes


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


# The SAMPLE AR-required simulation (Dustin 2026-07-17): appears in
# the "AR Required Simulations" section; zone capture is part of its
# requirements, its tied selections get block-filled and rendered in
# AR. Same append pattern as newtonian_pendulum_seed.
from simulations.seed_data import SEED_SIMULATION_DEFINITIONS  # noqa: E402

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
