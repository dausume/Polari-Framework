"""
@module reticulum.meshsim_basis

MESH SIMULATION (ret-1e, plan §5p, Dustin 2026-08-13): plan an
isle-mesh with KNOWN devices across a map before anyone buys
hardware or walks a field.

⚠ THE STANDING DISCLAIMER, carried on every result:
TERRAIN IS NOT ACCOUNTED FOR YET. v1 predicts on ASSUMED FLAT
TERRAIN (or anchors on measured rows); elevation/terrain modes exist
in the vocabulary and REFUSE — deliberately deferred, and we say so
rather than pretend.

What it computes, all assumptions listed in the result:
  - node SPACING for max spread with the smallest node count (hex
    packing at a safety-margined range),
  - per-node RELAY ALLOWANCE for a target per-peer bandwidth across
    the whole mesh at a given size,
  - per-scenario BEARER budgets (lora-only / halow-only / combos /
    +HAM broadcast / CONFINED variants like wifi-only-mesh-app-
    broadcasting so lighthouse traffic never crowds LoRa transport),
  - per-app SPREAD allowances: max hops, max distance, or a boundary
    SHAPE that derives max hops per direction,
  - INTERFERENCE suspicions from irregular reach (sectors whose
    measured reach falls far short of prediction while others don't).

Pure functions over plain dicts + three rows (scenario / node /
result snapshot). Coordinates are LOCAL METERS (x east, y north) in
v1 — geodesy is part of the terrain feature we are not pretending
to have.

@consumers reticulum.reticulum_api (/api/reticulum/meshsim)
@see modules/reticulum/device_catalog_basis.py (the known devices),
     reticulum_basis.py (measured rows), plan §5p
"""

import json
import math

from objectTreeDecorators import treeObject, treeObjectInit

TERRAIN_DISCLAIMER = (
    'TERRAIN IS NOT ACCOUNTED FOR: predictions assume flat terrain '
    '(or anchor on measured rows). Elevation/terrain modes are '
    'deliberately deferred — treat every predicted range as an '
    'upper bound that real ground will shorten.')

#: The fidelity ladder of prediction. Only the first two work today.
PROPAGATION_MODE_VALUES = ('flat-assumed', 'measured',
                           'average-elevation', 'ideal-elevation')
_IMPLEMENTED_MODES = ('flat-assumed', 'measured')

#: Named bearer sets ("scenarios" pick one or compose their own).
SCENARIO_BEARER_SETS = {
    'lora-only': ('rnode-lora',),
    'halow-only': ('wifi-halow',),
    'lora+halow': ('rnode-lora', 'wifi-halow'),
    'lora+halow+ham': ('rnode-lora', 'wifi-halow', 'ham-broadcast'),
    'wifi-confined-meshapps': ('rnode-lora', 'wifi'),
    'halow+ham': ('wifi-halow', 'ham-broadcast'),
}


def mode_supported(mode):
    """(ok, reason) — elevation modes refuse WITH the disclaimer
    instead of quietly falling back."""
    if mode not in PROPAGATION_MODE_VALUES:
        return (False, 'unknown propagation mode %r' % (mode,))
    if mode not in _IMPLEMENTED_MODES:
        return (False, 'mode %r is deliberately not built yet — %s'
                % (mode, TERRAIN_DISCLAIMER))
    return (True, '')


def flat_range_m(device, practical_margin_db=30.0):
    """Predicted usable range on assumed flat terrain, from the
    device catalog row. Prefers a DECLARED range when the vendor
    stated one (fidelity 'declared'); else a free-space link budget
    with a practical margin knob (fidelity 'derived-flat'). Returns
    (range_m, fidelity, evidence) or (None, 'unknown', reason)."""
    declared = device.get('declared_range_m')
    if declared:
        return (float(declared), 'declared',
                'vendor-declared range %s m' % declared)
    tx = device.get('tx_power_dbm_max')
    sens = device.get('rx_sensitivity_dbm')
    freq = device.get('freq_mhz_lo')
    if tx is None or sens is None or not freq:
        return (None, 'unknown',
                'catalog row lacks tx power / sensitivity / '
                'frequency — no basis to derive a range, and we do '
                'not guess')
    budget = tx - sens - practical_margin_db
    # FSPL(dB) = 20log10(d_km) + 20log10(f_MHz) + 32.44
    d_km = 10 ** ((budget - 32.44 - 20 * math.log10(freq)) / 20.0)
    return (round(d_km * 1000, 1), 'derived-flat',
            'free-space link budget %d dB (tx %s - sens %s - '
            'practical margin %s) at %s MHz' % (budget, tx, sens,
                                                practical_margin_db,
                                                freq))


def spacing_plan(range_m, area_m2, safety_factor=0.7):
    """Max spread with the smallest node count: hex packing at
    spacing = range x safety. Returns spacing, per-node covered
    area, and the node count for the requested area — every factor
    named."""
    spacing = range_m * safety_factor
    cell_area = (3 * math.sqrt(3) / 2) * ((spacing / 2) ** 2) * 2
    nodes = max(1, math.ceil(area_m2 / cell_area)) if area_m2 else 1
    return {
        'spacingM': round(spacing, 1),
        'cellAreaM2': round(cell_area, 1),
        'nodesForArea': nodes,
        'assumptions': [
            'hex packing, uniform device per node',
            'spacing = predicted range x safety %.2f' % safety_factor,
            TERRAIN_DISCLAIMER,
        ],
    }


def relay_allowance(n_nodes, target_per_peer_bps, capacity_bps,
                    utilization=0.5, spatial_reuse=1.0):
    """First-order mesh capacity: every node both originates its
    peers' target traffic and RELAYS others'. avg hops ~ sqrt(n)
    (grid/hex meshes); per-node forwarding burden =
    target x (n-1) x avg_hops / n. Compares against usable capacity
    (capacity x utilization x spatial_reuse) and reports the max
    achievable target when the asked one does not fit. Assumptions
    listed — this is planning math, not a promise."""
    if not n_nodes or n_nodes < 2 or not capacity_bps:
        return {'ok': False,
                'evidence': 'need >=2 nodes and a bearer capacity'}
    avg_hops = max(1.0, math.sqrt(n_nodes) * 0.75)
    burden_bps = target_per_peer_bps * (n_nodes - 1) * avg_hops \
        / n_nodes
    usable = capacity_bps * utilization * spatial_reuse
    fits = burden_bps <= usable
    max_target = usable * n_nodes / ((n_nodes - 1) * avg_hops)
    return {
        'ok': True, 'fits': fits,
        'avgHops': round(avg_hops, 2),
        'relayAllowanceBpsPerNode': round(burden_bps, 1),
        'relayAirtimeShare': round(min(1.0, burden_bps / capacity_bps),
                                   3),
        'usableBps': round(usable, 1),
        'maxAchievablePerPeerBps': round(max_target, 1),
        'verdict': ('fits' if fits else
                    'oversubscribed: per-peer target %s bps needs '
                    '%s bps of relaying per node but only %s bps is '
                    'usable — lower the target to <=%s, shrink the '
                    'mesh, or add a faster bearer'
                    % (target_per_peer_bps, round(burden_bps, 1),
                       round(usable, 1), round(max_target, 1))),
        'assumptions': [
            'uniform any-to-any traffic; avg hops ~ 0.75*sqrt(n)',
            'utilization %.2f (MAC/duty overhead), spatial reuse '
            'factor %.2f (1.0 = none, conservative)' % (utilization,
                                                        spatial_reuse),
            TERRAIN_DISCLAIMER,
        ],
    }


# ---- per-app spread: hops, distance, or a boundary shape ------------

def _ring_of(boundary_geojson):
    geom = boundary_geojson.get('geometry', boundary_geojson)
    if geom.get('type') != 'Polygon':
        return None
    rings = geom.get('coordinates') or []
    return rings[0] if rings else None


def _distance_to_boundary(ring, origin, bearing_deg, step_m=50.0,
                          max_m=100_000.0):
    """March along the bearing until the boundary is crossed. Local
    meters, v1 honesty: a march, not analytic geometry."""
    ox, oy = origin
    dx = math.sin(math.radians(bearing_deg))
    dy = math.cos(math.radians(bearing_deg))
    d = 0.0
    while d < max_m:
        d += step_m
        if not _point_in_ring(ring, (ox + dx * d, oy + dy * d)):
            return d
    return max_m


def _point_in_ring(ring, point):
    x, y = point
    inside = False
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        if (y1 > y) != (y2 > y):
            xInt = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xInt:
                inside = not inside
    return inside


def hops_toward(boundary_geojson, origin_xy, bearing_deg, spacing_m):
    """Dustin's idea, and it DOES make sense: a boundary shape IS a
    directional hop budget — distance to the shape's edge along a
    bearing, over node spacing, is the allowed hops that way.
    Returns None when the origin is outside its own boundary (a
    policy that excludes its origin allows nothing)."""
    ring = _ring_of(boundary_geojson)
    if not ring or not spacing_m:
        return None
    if not _point_in_ring(ring, tuple(origin_xy)):
        return 0
    dist = _distance_to_boundary(ring, tuple(origin_xy), bearing_deg)
    return int(dist // spacing_m)


def spread_allows(policy, hops, distance_m, bearing_deg=None,
                  origin_xy=(0.0, 0.0), spacing_m=None):
    """One app's spread policy vs one propagation question. Policy
    may carry max_hops, max_distance_m, and/or boundary_geojson —
    ALL present limits apply (the tightest wins). No limits at all
    refuses: unbounded spread must be declared by its absence being
    impossible, not by forgetting. Returns (bool, reason)."""
    limits = 0
    if policy.get('max_hops') is not None:
        limits += 1
        if hops > policy['max_hops']:
            return (False, 'hop %d exceeds max_hops %d'
                    % (hops, policy['max_hops']))
    if policy.get('max_distance_m') is not None:
        limits += 1
        if distance_m > policy['max_distance_m']:
            return (False, 'distance %.0f m exceeds max_distance %.0f '
                    'm' % (distance_m, policy['max_distance_m']))
    if policy.get('boundary_geojson'):
        limits += 1
        if bearing_deg is None or spacing_m is None:
            return (False, 'boundary policy needs a bearing + spacing '
                           'to derive directional hops')
        allowed = hops_toward(policy['boundary_geojson'], origin_xy,
                              bearing_deg, spacing_m)
        if allowed is None:
            return (False, 'boundary shape unusable (not a Polygon?)')
        if hops > allowed:
            return (False, 'hop %d exceeds the shape\'s budget of %d '
                    'toward bearing %.0f°' % (hops, allowed,
                                              bearing_deg))
    if not limits:
        return (False, 'spread policy declares NO limits — unbounded '
                       'spread must be impossible to state by '
                       'accident')
    return (True, '')


def interference_suspicions(reach_samples, predicted_range_m,
                            sectors=8, shortfall_ratio=0.4,
                            healthy_ratio=0.7):
    """Irregular reach → NAMED suspicion: bucket measured reaches by
    bearing; a sector whose best reach falls below shortfall x
    prediction while OTHER sectors demonstrate healthy reach is
    suspicious (uniform shortfall is just optimistic prediction —
    that is a different finding). Derived, never asserted."""
    if not reach_samples or not predicted_range_m:
        return {'suspicions': [], 'note': 'no samples or no '
                'prediction — nothing derivable'}
    width = 360.0 / sectors
    best = {}
    for s in reach_samples:
        if not s.get('success', True):
            continue
        sector = int((s.get('bearing_deg', 0) % 360) // width)
        best[sector] = max(best.get(sector, 0.0),
                           s.get('distance_m', 0.0))
    healthy = [b for b in best.values()
               if b >= healthy_ratio * predicted_range_m]
    suspicions = []
    if healthy:
        for sector in range(sectors):
            reach = best.get(sector)
            if reach is not None \
                    and reach < shortfall_ratio * predicted_range_m:
                suspicions.append({
                    'bearingFromDeg': round(sector * width, 1),
                    'bearingToDeg': round((sector + 1) * width, 1),
                    'bestReachM': reach,
                    'evidence': 'best reach %.0f m vs %.0f m '
                                'predicted (%.0f%%), while %d other '
                                'sector(s) reach healthily — '
                                'IRREGULAR, suspect interference or '
                                'obstruction' % (
                                    reach, predicted_range_m,
                                    100 * reach / predicted_range_m,
                                    len(healthy)),
                    'fidelity': 'derived',
                })
    note = ('' if healthy else
            'ALL sectors fall short — that is a prediction problem '
            '(or terrain, which v1 does not model), not localized '
            'interference; no suspicion derived')
    return {'suspicions': suspicions, 'note': note,
            'disclaimer': TERRAIN_DISCLAIMER}


class MeshSimScenario(treeObject):
    """One planning scenario: bearer set, devices per bearer, target
    bandwidth, app spread policies. Rows so scenarios are compared,
    not re-typed."""

    @treeObjectInit
    def __init__(self, name='', bearer_set='lora-only',
                 propagation_mode='flat-assumed',
                 device_models_json='{}', mesh_size_nodes=5,
                 area_m2=0.0, target_per_peer_bps=500,
                 app_spread_policies_json='{}', notes='',
                 manager=None):
        self.name = name
        self.bearer_set = bearer_set
        self.propagation_mode = propagation_mode
        # {'rnode-lora': 'dsd-tech-sh-l1a', ...} — KNOWN devices only.
        self.device_models_json = device_models_json
        self.mesh_size_nodes = mesh_size_nodes
        self.area_m2 = area_m2
        self.target_per_peer_bps = target_per_peer_bps
        # {app: {bearers, max_airtime_share, max_hops,
        #        max_distance_m, boundary_geojson}}
        self.app_spread_policies_json = app_spread_policies_json
        self.notes = notes


class MeshSimNode(treeObject):
    """A placed node in a scenario: local meters; elevation is
    RECORDED but UNUSED (the disclaimer says why)."""

    @treeObjectInit
    def __init__(self, name='', scenario_name='', x_m=0.0, y_m=0.0,
                 elevation_m=0.0, device_model_name='',
                 role='observer', notes='', manager=None):
        self.name = name
        self.scenario_name = scenario_name
        self.x_m = x_m
        self.y_m = y_m
        self.elevation_m = elevation_m
        self.device_model_name = device_model_name
        self.role = role
        self.notes = notes


class MeshSimResult(treeObject):
    """A computed plan snapshot — inputs, outputs, and the FULL
    assumptions list, so two runs are comparable and nobody mistakes
    planning math for a promise."""

    @treeObjectInit
    def __init__(self, name='', scenario_name='', computed_at='',
                 inputs_json='{}', outputs_json='{}',
                 assumptions_json='[]', disclaimer=TERRAIN_DISCLAIMER,
                 notes='', manager=None):
        self.name = name
        self.scenario_name = scenario_name
        self.computed_at = computed_at
        self.inputs_json = inputs_json
        self.outputs_json = outputs_json
        self.assumptions_json = assumptions_json
        self.disclaimer = disclaimer
        self.notes = notes
