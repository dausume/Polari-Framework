"""
@module reticulum.custom.meshsim_placement

CONFIGURABLE MAP SIMULATIONS (ret-1f, plan §5q, Dustin 2026-08-13):
placement solvers, population build mixes and COST over a drawn
geolocation shape.

  (A) plan_cheapest_coverage   given the shape + priced device
                               profiles: rank candidate types by
                               total cost of FEASIBLE coverage,
                               return the winner's node positions.
  (B) assess_fixed_locations   given specified locations: is the
                               shape covered (gaps NAMED with
                               centroids), is the graph connected
                               (isolated nodes NAMED), what
                               bandwidth reaches every node, and the
                               cheapest per-node type assignment
                               that keeps all of it true (greedy v1,
                               stated).
      failure_resilience       remove each node in turn — the ones
                               whose loss partitions the mesh or
                               uncovers area are SINGLE POINTS OF
                               FAILURE, named with what they take
                               down.
      population_mix_report    percentages of people with particular
                               builds — the interop matrix does the
                               honest work (LoRaWAN cannot peer,
                               ham-rx listens one-way, closed-framing
                               pairs only with itself), so the report
                               says who INTERCONNECTS, who hears
                               one-way, and who is ISOLATED.

Coordinates: geojson lon/lat rings are converted to LOCAL METERS by
an equirectangular projection at the centroid — fine at mesh scales,
stated as an assumption. Rings whose coordinates already look like
meters pass through with a note. TERRAIN_DISCLAIMER rides every
result; unpriced or unranged device models REFUSE to be costed.

Pure functions over plain dicts (the meshsim_basis idiom).

@consumers reticulum.reticulum_api (/api/reticulum/meshsim
           'placement' + 'population' sections), the /arch planner
@see modules/reticulum/meshsim_basis.py (range/spacing/relay math),
     device_catalog_basis.py (priced profiles), plan §5q
"""

import math

from reticulum.meshsim_basis import (TERRAIN_DISCLAIMER, flat_range_m,
                                     relay_allowance, _point_in_ring)

EARTH_M_PER_DEG_LAT = 111_320.0

#: Population builds the mix report understands. 'ham-rx' and
#: 'ham-tx' are DISTINCT builds on purpose: receiving needs no
#: licence and is the majority case (§5i); transmitting needs the
#: operator (§5g).
POPULATION_BUILD_VALUES = ('lora', 'ham-rx', 'ham-tx', 'wifi',
                           'wifi-halow', 'lorawan')


def to_local_meters(geojson_polygon):
    """Ring → local meters. lon/lat rings project equirectangularly
    at the centroid; rings that already look like meters (any
    |coordinate| > 1000) pass through. Returns
    (ring_m, area_m2, assumptions) or (None, 0, [reason])."""
    geom = geojson_polygon.get('geometry', geojson_polygon) \
        if isinstance(geojson_polygon, dict) else {}
    if geom.get('type') != 'Polygon':
        return (None, 0.0, ['not a Polygon geojson — nothing to '
                            'simulate on'])
    rings = geom.get('coordinates') or []
    if not rings or len(rings[0]) < 4:
        return (None, 0.0, ['empty/degenerate ring'])
    ring = [(float(p[0]), float(p[1])) for p in rings[0]]
    assumptions = [TERRAIN_DISCLAIMER]
    if any(abs(x) > 1000 or abs(y) > 1000 for x, y in ring):
        ring_m = ring
        assumptions.append('coordinates read as LOCAL METERS '
                           '(values beyond lon/lat bounds)')
    else:
        clat = sum(y for _, y in ring) / len(ring)
        clon = sum(x for x, _ in ring) / len(ring)
        m_per_deg_lon = EARTH_M_PER_DEG_LAT * math.cos(
            math.radians(clat))
        ring_m = [((x - clon) * m_per_deg_lon,
                   (y - clat) * EARTH_M_PER_DEG_LAT)
                  for x, y in ring]
        assumptions.append(
            'lon/lat projected to local meters equirectangularly at '
            'the centroid (%.4f, %.4f) — adequate at mesh scales, '
            'not for surveying' % (clat, clon))
    area = abs(sum(ring_m[i][0] * ring_m[i + 1][1]
                   - ring_m[i + 1][0] * ring_m[i][1]
                   for i in range(len(ring_m) - 1))) / 2.0
    return (ring_m, round(area, 1), assumptions)


def nodes_to_local(nodes, geojson_polygon):
    """Project node locations into the SAME local frame as the
    polygon: nodes with xM/yM pass through; nodes with lon/lat use
    the polygon's centroid projection (so both layers line up).
    Returns (nodes_m, refusals) — a node with neither form is
    refused by name, never guessed to the origin."""
    geom = geojson_polygon.get('geometry', geojson_polygon) \
        if isinstance(geojson_polygon, dict) else {}
    ring = (geom.get('coordinates') or [[]])[0]
    lonlat_ring = ring and not any(
        abs(p[0]) > 1000 or abs(p[1]) > 1000 for p in ring)
    clat = clon = m_per_deg_lon = None
    if lonlat_ring:
        clat = sum(p[1] for p in ring) / len(ring)
        clon = sum(p[0] for p in ring) / len(ring)
        m_per_deg_lon = EARTH_M_PER_DEG_LAT * math.cos(
            math.radians(clat))
    out, refusals = [], []
    for i, node in enumerate(nodes or []):
        name = node.get('name', f'node-{i}')
        if node.get('xM') is not None and node.get('yM') is not None:
            out.append({'name': name, 'x_m': float(node['xM']),
                        'y_m': float(node['yM'])})
        elif node.get('lon') is not None \
                and node.get('lat') is not None and lonlat_ring:
            out.append({
                'name': name,
                'x_m': (float(node['lon']) - clon) * m_per_deg_lon,
                'y_m': (float(node['lat']) - clat)
                * EARTH_M_PER_DEG_LAT})
        else:
            refusals.append('%s carries neither xM/yM nor lon/lat '
                            'matching the polygon frame' % name)
    return out, refusals


def _bounds(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def hex_positions_in_polygon(ring_m, spacing_m):
    """Hex-grid points inside the polygon (max spread: rows offset
    by half a spacing, row pitch spacing×√3/2)."""
    if not spacing_m or spacing_m <= 0:
        return []
    x0, y0, x1, y1 = _bounds(ring_m)
    pitch = spacing_m * math.sqrt(3) / 2.0
    out = []
    row = 0
    y = y0 + pitch / 2
    while y <= y1:
        offset = (spacing_m / 2.0) if row % 2 else 0.0
        x = x0 + offset + spacing_m / 2
        while x <= x1:
            if _point_in_ring(ring_m, (x, y)):
                out.append((round(x, 1), round(y, 1)))
            x += spacing_m
        y += pitch
        row += 1
    return out


def linear_positions(ring_m, spacing_m):
    """A chain along the polygon's LONGEST bounding-box axis through
    the centroid, clipped to the polygon — the corridor case
    (roads/rivers). The chain is the relay stress case and the
    caller's relay math should know it."""
    if not spacing_m or spacing_m <= 0:
        return []
    x0, y0, x1, y1 = _bounds(ring_m)
    cx = sum(p[0] for p in ring_m) / len(ring_m)
    cy = sum(p[1] for p in ring_m) / len(ring_m)
    horizontal = (x1 - x0) >= (y1 - y0)
    out = []
    if horizontal:
        x = x0 + spacing_m / 2
        while x <= x1:
            if _point_in_ring(ring_m, (x, cy)):
                out.append((round(x, 1), round(cy, 1)))
            x += spacing_m
    else:
        y = y0 + spacing_m / 2
        while y <= y1:
            if _point_in_ring(ring_m, (cx, y)):
                out.append((round(cx, 1), round(y, 1)))
            y += spacing_m
    return out


def _option_facts(option, practical_margin_db=30.0):
    """(range_m, price, capacity, refusal_reason|None) for one device
    option dict. Unpriced or unranged REFUSES — a plan costed on a
    guess is worse than no plan."""
    price = option.get('price_usd') or 0
    range_m, fidelity, evidence = flat_range_m(
        option, practical_margin_db=practical_margin_db)
    if not price:
        return (None, None, None,
                'price_usd unstated on %r — the catalog refuses to '
                'cost a guess (date a price onto the DeviceModel '
                'row)' % (option.get('name'),))
    if range_m is None:
        return (None, None, None,
                'no range basis on %r: %s' % (option.get('name'),
                                              evidence))
    return ((range_m, fidelity, evidence), float(price),
            option.get('capacityBps'), None)


#: Antenna options (ret-1f addendum, Dustin 2026-08-13): range
#: extension as a STATED knob. Factors are DECLARED planning numbers
#: leaning on the free-space rule of thumb (+6 dB ≈ ×2 range; a
#: 5-6 dBi omni upgrade ≈ ×1.8, a 12+ dBi yagi ≈ ×3) — sources:
#: tektelic.com/expertise/gateway-antenna-gain,
#: oscarliang.com/how-antenna-gain-affects-range — NOT physics
#: guarantees, and terrain is still disclaimed.
ANTENNA_FACTORS = {'stock': 1.0, 'high-gain-omni': 1.8,
                   'directional': 3.0}

ANTENNA_ASSUMPTION = ('antenna factors are declared planning knobs '
                      '(free-space rule: +6 dB ~ x2 range; '
                      'high-gain-omni x1.8, directional x3.0), not '
                      'guarantees; a DIRECTIONAL antenna is '
                      'point-to-point and serves at most a chain '
                      '(<=2 neighbours), never an omni lattice')


def _antenna_range(range_m, option):
    """(adjusted_range, evidence_suffix, refusal|None). Unknown
    antenna names refuse — a factor is not guessed."""
    antenna = option.get('antenna') or 'stock'
    factor = ANTENNA_FACTORS.get(antenna)
    if factor is None:
        return (None, '',
                'unknown antenna %r on %r — choose from %s'
                % (antenna, option.get('name'),
                   sorted(ANTENNA_FACTORS)))
    if factor == 1.0:
        return (range_m, '', None)
    return (range_m * factor,
            ' x %.1f antenna factor (%s)' % (factor, antenna), None)


#: Loadout ceiling when the device row cannot say better (§5q
#: addendum): several units of one type on one node multiply
#: CAPACITY ~linearly — ONLY on distinct channels; same-channel
#: units contend and buy nothing. Range is NEVER extended by units.
DEFAULT_UNITS_MAX = 4

UNITS_ASSUMPTION = ('multi-unit nodes multiply CAPACITY only, and '
                    'only on DISTINCT channels (same-channel units '
                    'contend and buy nothing); range is never '
                    'extended by adding units')


def _channel_ceiling(option):
    """How many distinct channels the device family offers, when the
    row's frequency range says (1 MHz channel steps, the E220 shape:
    850.125-930.125 -> 81). None when underivable — the caller falls
    back to the unitsMax knob alone."""
    lo, hi = option.get('freq_mhz_lo'), option.get('freq_mhz_hi')
    try:
        if lo and hi and float(hi) > float(lo):
            return max(1, int(round(float(hi) - float(lo))) + 1)
    except (TypeError, ValueError):
        pass
    return None


def _units_cap(option):
    cap = int(option.get('unitsMax') or DEFAULT_UNITS_MAX)
    channels = _channel_ceiling(option)
    return min(cap, channels) if channels else cap


def _relay_verdict(count, target_per_peer_bps, capacity_bps, units,
                   reach_mode):
    """relay_allowance at capacity x units, chain-adjusted for
    linear reach (the stress case: ~n/3 average hops)."""
    relay = relay_allowance(count, target_per_peer_bps,
                            float(capacity_bps) * units)
    relay.pop('assumptions', None)
    if reach_mode == 'linear' and count >= 2 and relay.get('ok'):
        chain_hops = max(1.0, count / 3.0)
        burden = target_per_peer_bps * (count - 1) \
            * chain_hops / count
        relay['avgHops'] = round(chain_hops, 2)
        relay['relayAllowanceBpsPerNode'] = round(burden, 1)
        relay['fits'] = burden <= relay['usableBps']
        relay['verdict'] = ('fits' if relay['fits'] else
                            'oversubscribed on the CHAIN: '
                            'linear meshes relay ~n/3 hops '
                            'and this one does not fit')
    return relay


def _scenario_range(base_range, fidelity, evidence, option,
                    range_scenario='typical', range_override_m=None):
    """The range knob Dustin's pushback earned (2026-08-13): the
    vendor's span becomes pessimistic/typical/optimistic scenarios,
    and an explicit operator override wins over all of them, labelled
    as the assertion it is. Never silently optimistic."""
    if range_override_m:
        return (float(range_override_m), 'operator-override',
                'operator-asserted range %s m (overrides the '
                'catalog; your judgement, on the record)'
                % range_override_m)
    if range_scenario == 'pessimistic':
        lo = option.get('declared_range_min_m') or base_range * 0.6
        return (float(lo), fidelity + '-min',
                evidence + ' — PESSIMISTIC end of the span')
    if range_scenario == 'optimistic':
        hi = option.get('declared_range_max_m') or base_range * 1.5
        return (float(hi), fidelity + '-max',
                evidence + ' — OPTIMISTIC end of the span (clear '
                'urban/elevated placement)')
    return (base_range, fidelity, evidence)


def _grid_samples(ring, step):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    out = []
    y = min(ys)
    while y <= max(ys):
        x = min(xs)
        while x <= max(xs):
            if _point_in_ring(ring, (x, y)):
                out.append((x, y))
            x += step
        y += step
    return out


def _single_node_position(ring, range_m):
    """Can ONE node cover the whole shape? Try the centroid and a
    coarse candidate grid; return the first position whose distance
    to every sample point is within range, else None. The check the
    old solver never made — and the difference between 1 node and 8."""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    span = max(max(xs) - min(xs), max(ys) - min(ys))
    samples = _grid_samples(ring, max(span / 12.0, 25.0))
    if not samples:
        return None
    cx = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
    cy = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    candidates = [(cx, cy)] + _grid_samples(ring, max(span / 6.0, 50.0))
    for cand in candidates:
        if all(math.dist(cand, s) <= range_m for s in samples):
            return cand
    return None


def plan_cheapest_coverage(ring_m, device_options,
                           target_per_peer_bps,
                           reach_mode='max-spread',
                           safety_factor=0.85,
                           practical_margin_db=30.0,
                           range_scenario='typical',
                           range_override_m=None):
    """Sim A: rank candidate device types by TOTAL COST of feasible
    coverage of the shape; the winner returns its actual positions.
    Feasibility = the relay-allowance verdict at the resulting node
    count (needs capacityBps on the option). LOADOUTS: when one unit
    per node cannot carry the target, 2..unitsMax units per node are
    tried (capacity and cost scale, range does NOT) before the
    option is declared infeasible — so ranking by TOTAL cost lets a
    pricier single-unit device honestly beat a cheap one that needs
    three of itself."""
    ranked, refused = [], []
    for option in device_options:
        facts, price, capacity, refusal = _option_facts(
            option, practical_margin_db)
        if refusal:
            refused.append({'model': option.get('name'),
                            'reason': refusal})
            continue
        (base_range, base_fid, base_ev) = facts
        antenna = option.get('antenna') or 'stock'
        if antenna == 'directional' and reach_mode != 'linear':
            refused.append({
                'model': option.get('name'),
                'reason': 'directional antenna with %r reach: a '
                          'directional node is point-to-point and '
                          'cannot serve a lattice of neighbours — '
                          'use linear (chains) or an omni antenna'
                          % reach_mode})
            continue
        (range_m, fidelity, evidence) = _scenario_range(
            base_range, base_fid, base_ev, option, range_scenario,
            range_override_m)
        range_m, ant_suffix, ant_refusal = _antenna_range(range_m,
                                                          option)
        if ant_refusal:
            refused.append({'model': option.get('name'),
                            'reason': ant_refusal})
            continue
        evidence += ant_suffix
        # COVERAGE vs BACKBONE are different constraints (the
        # 8-nodes-for-2km lesson, Dustin 2026-08-13): people reaching
        # a node allows hex spacing up to sqrt(3) x range; nodes
        # reaching EACH OTHER needs spacing <= safety x range. Test
        # the single-node case FIRST — one node that reaches the
        # whole shape needs no backbone at all.
        single = _single_node_position(ring_m, range_m)
        if single is not None and reach_mode != 'linear':
            positions = [single]
            count = 1
            binding = ('coverage — a single node at (%.0f, %.0f) '
                       'reaches the whole shape at range %.0f m; no '
                       'backbone needed' % (single[0], single[1],
                                            range_m))
            spacing = None
        else:
            backbone = range_m * safety_factor
            coverage = range_m * math.sqrt(3)
            spacing = min(backbone, coverage)
            binding = ('backbone-connectivity (spacing %.0f m = '
                       'safety %.2f x range) — coverage alone would '
                       'allow %.0f m spacing'
                       % (backbone, safety_factor, coverage)
                       if backbone < coverage else
                       'coverage (spacing %.0f m)' % coverage)
            positions = (linear_positions(ring_m, spacing)
                         if reach_mode == 'linear'
                         else hex_positions_in_polygon(ring_m,
                                                       spacing))
            count = max(1, len(positions))
        units = 1
        entry = {
            'model': option.get('name'),
            'rangeM': range_m, 'rangeFidelity': fidelity,
            'rangeEvidence': evidence,
            'rangeScenario': ('override' if range_override_m
                              else range_scenario),
            'spacingM': round(spacing, 1) if spacing else None,
            'nodeCount': count,
            'bindingConstraint': binding,
            'unitPriceUsd': price,
            'reachMode': reach_mode,
            'antenna': antenna,
        }
        entry['_positions'] = positions
        if count == 1:
            entry['relay'] = {
                'ok': True, 'fits': True,
                'verdict': 'single node — no mesh relaying; '
                           'per-client bandwidth is capacity x units '
                           'shared among concurrent clients (sized '
                           'by app policies, not mesh math)'}
            entry['feasible'] = capacity is not None and capacity > 0
            if not entry['feasible']:
                entry['relayNote'] = ('no capacityBps — a single '
                                      'node covers, but its client '
                                      'bandwidth is unknowable')
            entry['unitsPerNode'] = 1
            entry['unitsCap'] = _units_cap(option)
        elif capacity:
            cap = _units_cap(option)
            relay = None
            for units in range(1, cap + 1):
                relay = _relay_verdict(count, target_per_peer_bps,
                                       capacity, units, reach_mode)
                if relay.get('fits'):
                    break
            entry['relay'] = relay
            entry['feasible'] = bool(relay and relay.get('fits'))
            entry['unitsPerNode'] = units
            entry['unitsCap'] = cap
        else:
            entry['feasible'] = False
            entry['unitsPerNode'] = 1
            entry['relayNote'] = ('no capacityBps on this option — '
                                  'feasibility unknowable, treated '
                                  'as infeasible rather than hoped')
        entry['perNodeCostUsd'] = round(price * entry['unitsPerNode'],
                                        2)
        entry['totalCostUsd'] = round(
            count * price * entry['unitsPerNode'], 2)
        ranked.append(entry)
    positions_by_model = {e['model']: e.pop('_positions')
                          for e in ranked}
    feasible = sorted([e for e in ranked if e['feasible']],
                      key=lambda e: e['totalCostUsd'])
    infeasible = [e for e in ranked if not e['feasible']]
    winner = None
    if feasible:
        best = feasible[0]
        winner = dict(best, positions=[
            {'xM': x, 'yM': y}
            for x, y in positions_by_model[best['model']]])
    return {
        'ok': True, 'mode': 'cheapest-coverage',
        'reachMode': reach_mode,
        'rangeScenario': ('override' if range_override_m
                          else range_scenario),
        'winner': winner,
        'rankedFeasible': feasible,
        'infeasible': infeasible,
        'refused': refused,
        'disclaimer': TERRAIN_DISCLAIMER,
        'assumptions': [
            'single-node coverage tested first; multi-node backbone '
            'spacing = range x safety %.2f (coverage alone would '
            'allow sqrt(3) x range — the binding constraint is '
            'named per option)' % safety_factor,
            'range scenario %r — pessimistic/typical/optimistic read '
            'the vendor span; override is the operator\'s assertion'
            % ('override' if range_override_m else range_scenario),
            'linear chains relay ~n/3 average hops (the stress '
            'case); spread meshes ~0.75*sqrt(n)',
            UNITS_ASSUMPTION,
            ANTENNA_ASSUMPTION,
            TERRAIN_DISCLAIMER,
        ],
    }


def _link_graph(nodes, ranges):
    """Adjacency by index: an edge when the two nodes are within the
    SMALLER of their two ranges (both must close the link)."""
    n = len(nodes)
    adj = {i: set() for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            d = math.dist((nodes[i]['x_m'], nodes[i]['y_m']),
                          (nodes[j]['x_m'], nodes[j]['y_m']))
            if d <= min(ranges[i], ranges[j]):
                adj[i].add(j)
                adj[j].add(i)
    return adj


def _components(adj):
    seen, comps = set(), []
    for start in adj:
        if start in seen:
            continue
        comp, stack = set(), [start]
        while stack:
            node = stack.pop()
            if node in comp:
                continue
            comp.add(node)
            stack.extend(adj[node] - comp)
        seen |= comp
        comps.append(comp)
    return comps


def _bfs_hops(adj, start):
    dist = {start: 0}
    frontier = [start]
    while frontier:
        nxt = []
        for node in frontier:
            for peer in adj[node]:
                if peer not in dist:
                    dist[peer] = dist[node] + 1
                    nxt.append(peer)
        frontier = nxt
    return dist


def _coverage(ring_m, nodes, ranges, step_m):
    x0, y0, x1, y1 = _bounds(ring_m)
    total, covered, uncovered_pts = 0, 0, []
    y = y0 + step_m / 2
    while y <= y1:
        x = x0 + step_m / 2
        while x <= x1:
            if _point_in_ring(ring_m, (x, y)):
                total += 1
                if any(math.dist((x, y),
                                 (nodes[i]['x_m'], nodes[i]['y_m']))
                       <= ranges[i] for i in range(len(nodes))):
                    covered += 1
                else:
                    uncovered_pts.append((x, y))
            x += step_m
        y += step_m
    return total, covered, uncovered_pts


def _gap_clusters(points, cluster_radius, limit=5):
    clusters = []
    for point in points:
        for cluster in clusters:
            if math.dist(point, cluster['centroid']) <= cluster_radius:
                n = cluster['size']
                cx, cy = cluster['centroid']
                cluster['centroid'] = ((cx * n + point[0]) / (n + 1),
                                       (cy * n + point[1]) / (n + 1))
                cluster['size'] += 1
                break
        else:
            clusters.append({'centroid': point, 'size': 1})
    clusters.sort(key=lambda c: -c['size'])
    return [{'centroidXM': round(c['centroid'][0], 1),
             'centroidYM': round(c['centroid'][1], 1),
             'samplePoints': c['size']} for c in clusters[:limit]]


def assess_fixed_locations(ring_m, nodes, device_options,
                           target_per_peer_bps, sample_step_m=None,
                           practical_margin_db=30.0):
    """Sim B: specified locations — coverage (gaps NAMED), graph
    connectivity (isolated nodes NAMED), bandwidth via MEASURED graph
    hops (BFS all-pairs mean, not the sqrt heuristic), and a greedy
    cheapest-first per-node type assignment (v1, stated)."""
    priced = []
    refused = []
    for option in device_options:
        facts, price, capacity, refusal = _option_facts(
            option, practical_margin_db)
        if refusal:
            refused.append({'model': option.get('name'),
                            'reason': refusal})
            continue
        arange, ant_suffix, ant_refusal = _antenna_range(facts[0],
                                                         option)
        if ant_refusal:
            refused.append({'model': option.get('name'),
                            'reason': ant_refusal})
            continue
        priced.append({'name': option.get('name'),
                       'rangeM': arange, 'price': price,
                       'capacityBps': capacity,
                       'unitsCap': _units_cap(option),
                       'antenna': option.get('antenna') or 'stock'})
    if not priced:
        return {'ok': False,
                'evidence': 'no usable (priced + ranged) device '
                            'options', 'refused': refused,
                'disclaimer': TERRAIN_DISCLAIMER}
    priced.sort(key=lambda o: o['price'])
    if not nodes:
        return {'ok': False, 'evidence': 'no node locations given',
                'disclaimer': TERRAIN_DISCLAIMER}

    # greedy v1: everyone starts on the cheapest type; nodes that are
    # isolated get upgraded to the next-priced type until connected
    # or options run out.
    assign = [0] * len(nodes)

    def ranges():
        return [priced[assign[i]]['rangeM'] for i in range(len(nodes))]

    for _ in range(len(priced)):
        adj = _link_graph(nodes, ranges())
        comps = _components(adj)
        if len(comps) <= 1:
            break
        main = max(comps, key=len)
        upgraded = False
        for comp in comps:
            if comp is main:
                continue
            for i in comp:
                if assign[i] + 1 < len(priced):
                    assign[i] += 1
                    upgraded = True
        if not upgraded:
            break
    adj = _link_graph(nodes, ranges())
    comps = _components(adj)
    main = max(comps, key=len) if comps else set()
    isolated = [nodes[i].get('name', f'node-{i}')
                for i in range(len(nodes)) if i not in main]

    step = sample_step_m or max(25.0,
                                min(o['rangeM'] for o in priced) / 4)
    total, covered, uncovered = _coverage(ring_m, nodes, ranges(),
                                          step)
    covered_pct = round(100.0 * covered / total, 1) if total else 0.0
    gaps = _gap_clusters(uncovered, cluster_radius=step * 2)

    hops_all = []
    diameter = 0
    for i in main:
        dist = _bfs_hops(adj, i)
        vals = [h for j, h in dist.items() if j != i and j in main]
        hops_all.extend(vals)
        diameter = max(diameter, max(vals, default=0))
    avg_hops = (sum(hops_all) / len(hops_all)) if hops_all else 0.0

    # loadouts (§5q addendum): a RANGE/connectivity failure upgrades
    # the TYPE (above); a BANDWIDTH failure adds UNITS of the current
    # type — capacity x units on distinct channels, range unchanged.
    units = [1] * len(nodes)

    def effective_capacity():
        vals = [priced[assign[i]]['capacityBps'] * units[i]
                for i in main
                if priced[assign[i]]['capacityBps']]
        return min(vals) if vals else None

    def relay_at(capacity_eff):
        relay = relay_allowance(len(main), target_per_peer_bps,
                                float(capacity_eff))
        burden = target_per_peer_bps * (len(main) - 1) * avg_hops \
            / len(main)
        relay['avgHops'] = round(avg_hops, 2)
        relay['avgHopsSource'] = 'BFS all-pairs mean on the ACTUAL ' \
                                 'graph (not the sqrt heuristic)'
        relay['relayAllowanceBpsPerNode'] = round(burden, 1)
        relay['fits'] = burden <= relay['usableBps']
        if not relay['fits']:
            relay['verdict'] = ('oversubscribed on the actual graph: '
                                '%.1f bps relay burden vs %.1f usable'
                                % (burden, relay['usableBps']))
        relay.pop('assumptions', None)
        return relay

    relay = None
    capacity = effective_capacity()
    if capacity and len(main) >= 2 and avg_hops:
        relay = relay_at(capacity)
        for _ in range(16):
            if relay['fits']:
                break
            floor = min(priced[assign[i]]['capacityBps'] * units[i]
                        for i in main
                        if priced[assign[i]]['capacityBps'])
            bumped = False
            for i in main:
                option = priced[assign[i]]
                if option['capacityBps'] \
                        and option['capacityBps'] * units[i] == floor \
                        and units[i] < option['unitsCap']:
                    units[i] += 1
                    bumped = True
            if not bumped:
                break
            relay = relay_at(effective_capacity())

    per_node = [{'name': nodes[i].get('name', f'node-{i}'),
                 'xM': nodes[i]['x_m'], 'yM': nodes[i]['y_m'],
                 'type': priced[assign[i]]['name'],
                 'antenna': priced[assign[i]].get('antenna', 'stock'),
                 'units': units[i],
                 'unitPriceUsd': priced[assign[i]]['price'],
                 'costUsd': round(priced[assign[i]]['price']
                                  * units[i], 2)}
                for i in range(len(nodes))]
    # a directional antenna serves a chain, not a lattice: any node
    # assigned one while holding >2 graph neighbours is FLAGGED.
    final_adj = _link_graph(nodes, ranges())
    directional_violations = [
        per_node[i]['name'] for i in range(len(nodes))
        if priced[assign[i]].get('antenna') == 'directional'
        and len(final_adj[i]) > 2]
    return {
        'ok': True, 'mode': 'fixed-locations',
        'directionalViolations': directional_violations,
        'coveredPct': covered_pct,
        'fullyCovered': covered_pct >= 99.9,
        'uncoveredGaps': gaps,
        'connected': not isolated,
        'isolatedNodes': isolated,
        'graphDiameterHops': diameter,
        'perNode': per_node,
        'totalCostUsd': round(sum(p['costUsd'] for p in per_node), 2),
        'relay': relay,
        'refusedOptions': refused,
        'disclaimer': TERRAIN_DISCLAIMER,
        'assumptions': [
            'greedy v1 type assignment: cheapest first, isolated '
            'nodes upgraded until connected or options exhausted — '
            'not a global optimum, stated as such',
            'bandwidth shortfalls add UNITS of the assigned type at '
            'the bottleneck nodes (greedy); range shortfalls upgrade '
            'the TYPE — units never extend range',
            UNITS_ASSUMPTION,
            ANTENNA_ASSUMPTION,
            'coverage sampled on a %.0f m grid' % step,
            TERRAIN_DISCLAIMER,
        ],
    }


def failure_resilience(ring_m, nodes, device_options,
                       sample_step_m=None, coverage_drop_pct=5.0,
                       practical_margin_db=30.0):
    """Remove each node in turn: articulation findings name the nodes
    whose loss PARTITIONS the mesh or drops coverage by more than
    coverage_drop_pct — single points of failure, with what they take
    down."""
    base = assess_fixed_locations(ring_m, nodes, device_options, 0,
                                  sample_step_m, practical_margin_db)
    if not base.get('ok'):
        return base
    findings = []
    for i in range(len(nodes)):
        remaining = nodes[:i] + nodes[i + 1:]
        if not remaining:
            continue
        after = assess_fixed_locations(ring_m, remaining,
                                       device_options, 0,
                                       sample_step_m,
                                       practical_margin_db)
        newly_isolated = [n for n in after.get('isolatedNodes', [])
                          if n not in base.get('isolatedNodes', [])]
        coverage_lost = round(base['coveredPct']
                              - after.get('coveredPct', 0.0), 1)
        if newly_isolated or coverage_lost > coverage_drop_pct:
            findings.append({
                'node': nodes[i].get('name', f'node-{i}'),
                'partitionsNodes': newly_isolated,
                'coverageLostPct': max(coverage_lost, 0.0),
                'evidence': 'removing %r isolates %s and uncovers '
                            '%.1f%% of the shape — a single point of '
                            'failure' % (
                                nodes[i].get('name', f'node-{i}'),
                                newly_isolated or 'nobody',
                                max(coverage_lost, 0.0)),
            })
    return {'ok': True, 'mode': 'resilience',
            'baseCoveredPct': base['coveredPct'],
            'articulationFindings': findings,
            'disclaimer': TERRAIN_DISCLAIMER,
            'assumptions': base['assumptions']}


def _parse_kit(kit):
    """(devices, error): a kit dict validated against the build
    vocabulary; unknown builds refuse by name."""
    bad = [b for b in (kit or {}) if b not in POPULATION_BUILD_VALUES]
    if bad or not kit:
        return (None, 'kit carries unknown build(s) %s — knowns: %s'
                % (bad or '(none)', POPULATION_BUILD_VALUES))
    return ({b: int(n) for b, n in kit.items() if int(n) > 0}, None)


def population_cohorts_report(cohorts, profiles=None,
                              device_models=None):
    """COUNTS-FIRST population report (Dustin 2026-08-13): specific
    numbers of people with particular kit configurations — cohorts =
    [{'profile': 'everyday-node', 'count': 12} |
     {'kit': {'lora': 1, 'ham-rx': 1}, 'count': 3, 'label': 'x'}].
    Profile names resolve from KitProfile rows (handed in as
    {name: devices dict}); unknown profiles refuse by name in their
    row. Percentages appear ONLY as derived analytics
    (pctOfPopulation) — counts are the truth, pct is a view."""
    profiles = profiles or {}
    entries, errors = {}, {}
    for i, cohort in enumerate(cohorts or []):
        label = cohort.get('label') or cohort.get('profile') \
            or 'cohort-%d' % (i + 1)
        count = int(cohort.get('count') or 0)
        if cohort.get('profile'):
            devices = profiles.get(cohort['profile'])
            if devices is None:
                errors[label] = {
                    'error': 'unknown kit profile %r — no KitProfile '
                             'row by that name' % cohort['profile']}
                continue
            devices, err = _parse_kit(devices)
        else:
            devices, err = _parse_kit(cohort.get('kit'))
        if err:
            errors[label] = {'error': err}
            continue
        entries[label] = {'devices': devices, 'count': count,
                          'is_kit': True,
                          'profile': cohort.get('profile', '')}
    population_n = sum(e['count'] for e in entries.values())
    out = _population_report_core(entries, errors, population_n)
    for label, e in entries.items():
        row = out['builds'].get(label)
        if row is not None:
            row['pctOfPopulation'] = round(
                100.0 * e['count'] / population_n, 1) \
                if population_n else 0.0
            if e['profile']:
                row['profile'] = e['profile']
    out['countsFirst'] = True
    out['pctNote'] = ('percentages are DERIVED analytics; the counts '
                      'are the configuration')
    return out


def population_mix_report(mix, population_n, device_models=None):
    """LEGACY percentage form ({build: pct} or {label: {kit, pct}}
    with a population n) — kept accepted, converted to counts and
    flagged legacyPctForm. Counts-first (population_cohorts_report)
    is the primary form."""
    entries, errors = {}, {}
    for label, value in (mix or {}).items():
        if isinstance(value, dict):
            devices, err = _parse_kit(value.get('kit'))
            if err:
                errors[label] = {'error': err}
                continue
            entries[label] = {
                'devices': devices,
                'count': int(round(population_n
                                   * float(value.get('pct') or 0)
                                   / 100.0)),
                'is_kit': True}
        else:
            if label not in POPULATION_BUILD_VALUES:
                errors[label] = {
                    'error': 'unknown build %r — knowns: %s'
                             % (label, POPULATION_BUILD_VALUES)}
                continue
            entries[label] = {
                'devices': {label: 1},
                'count': int(round(population_n * float(value)
                                   / 100.0)),
                'is_kit': False}
    out = _population_report_core(entries, errors, population_n)
    out['legacyPctForm'] = True
    return out


def _population_report_core(entries, errors, population_n):
    """Who actually interconnects. The matrix is the suite's interop
    truth: LoRaWAN cannot peer (DECIDED row 9 — gateways + a join
    server), ham-rx LISTENS one-way to ham-tx (§5g/§5i), everyone
    else peers within their own build; a KIT's connectivity is the
    UNION of its parts, and multi-unit parts multiply CAPACITY only,
    on distinct channels."""
    peers_within = {'lora', 'wifi', 'wifi-halow', 'ham-tx'}
    report = dict(errors)
    # who carries a TRANSMITTING part of each build, across pure
    # entries and kits alike — the union is what makes kits bridge.
    carriers = {b: sum(e['count'] for e in entries.values()
                       if b in e['devices'])
                for b in POPULATION_BUILD_VALUES}
    ham_tx_present = carriers.get('ham-tx', 0) > 0
    for label, e in entries.items():
        devices, count = e['devices'], e['count']
        entry = {'count': count, 'peersWith': [],
                 'oneWayListensTo': [], 'isolated': False}
        if e['is_kit']:
            entry['devices'] = dict(devices)
        entry['peersWith'] = sorted(
            b for b in devices
            if b in peers_within and carriers.get(b, 0) >= 2)
        multi = {b: n for b, n in devices.items() if n > 1}
        if multi:
            entry['capacityNote'] = (
                '%s: multiple units multiply CAPACITY only, on '
                'DISTINCT channels — same-channel units contend and '
                'buy nothing; range is unchanged'
                % ', '.join('%dx %s' % (n, b)
                            for b, n in sorted(multi.items())))
        if 'ham-rx' in devices:
            if ham_tx_present:
                entry['oneWayListensTo'] = ['ham-tx']
                entry['note'] = ('receive-only over ham: hears the '
                                 'licensed ham core, answers nothing '
                                 'over ham (§5g) — carrying a '
                                 'receiver never makes you a '
                                 'broadcaster')
        if not entry['peersWith'] and not entry['oneWayListensTo']:
            entry['isolated'] = count > 0
            if not entry['isolated']:
                pass
            elif devices == {'ham-rx': 1}:
                entry['why'] = ('ham-rx with NO ham-tx in the '
                                'population: everyone is listening '
                                'and nobody is broadcasting — the '
                                '§5g core needs at least one '
                                'licensed operator')
            elif devices == {'lorawan': 1}:
                entry['why'] = ('LoRaWAN is not peer-to-peer (DECIDED '
                                'row 9): star-of-stars via gateways + '
                                'a join server — these people connect '
                                'to INFRASTRUCTURE, not to each other')
            elif not e['is_kit'] and count == 1:
                entry['why'] = 'only one person carries this build'
            else:
                entry['why'] = ('no part of this loadout reaches '
                                'anyone: %s (lorawan cannot peer — '
                                'row 9; ham-rx needs a ham-tx to '
                                'hear; peer builds need a second '
                                'carrier)'
                                % sorted(devices))
        report[label] = entry
    interconnected = max((carriers.get(b, 0) for b in peers_within
                          if carriers.get(b, 0) >= 2), default=0)
    isolated_n = sum(e['count'] for label, e in entries.items()
                     if report.get(label, {}).get('isolated'))
    return {
        'ok': True, 'populationN': population_n,
        'builds': report,
        'largestInterconnected': interconnected,
        'isolatedShare': round(100.0 * isolated_n / population_n, 1)
        if population_n else 0.0,
        'note': ('builds interconnect WITHIN themselves at this '
                 'layer (a KIT joins every build it carries a '
                 'transmitter for); bridging between builds is an '
                 'isle/gateway role, which is exactly what the '
                 'placement sims place'),
        'disclaimer': TERRAIN_DISCLAIMER,
    }
