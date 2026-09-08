"""
@module reticulum.custom.arch_topology

The `.arch` TOPOLOGY VIEW assembly (ret-1b, plan §5m): isles as
BLOCKS — the isle-topology idiom one level up — with their radios and
apps inside, measured latency between them, and demand-vs-capacity
per isle with an honest verdict.

Pure functions over plain dicts (the netledger idiom): the API hands
in row tables, this assembles; nothing here reads globals or acts.
Every number says whether it is DECLARED or MEASURED, every
measurement carries freshness, and an isle whose apps ask for more
than its radios carry gets a NAMED oversubscription finding with the
arithmetic shown — never a silent slowdown.

@consumers reticulum.reticulum_api (/api/reticulum/arch-topology),
           the /arch frontend page (ret-1b)
@see modules/reticulum/reticulum_basis.py (rows + path rules),
     modules/islemesh/islemesh_coherence.py (the isle-level blocks)
"""

import json

from reticulum.arch_basis import reachable_now
from reticulum.reticulum_basis import measurement_fresh


def binding_demand(binding):
    """What one binding ASKS for per unit time, from its declared
    admission policy: bytes/min = max_message_bytes x max_rate_per_min.
    Fidelity 'declared' — measured demand (metered from real
    requests) is a named follow-up, and its absence is stated rather
    than faked."""
    size = binding.get('max_message_bytes') or 0
    rate = binding.get('max_rate_per_min') or 0
    return {
        'bytesPerMin': size * rate,
        'messagesPerMin': rate,
        'maxMessageBytes': size,
        'encoding': binding.get('encoding', ''),
        'fidelity': 'declared',
    }


def device_capacity(iface, measurements, budgets, now_ms,
                    horizon_ms=900_000):
    """What one radio/interface can CARRY per unit time: the declared
    air rate beside the measured effective rate (they differ by
    protocol overhead — 62.5k air carried 821 B/s of Resource on the
    desk), plus the airtime budget where one is ledgered."""
    declared_bps = None
    try:
        params = json.loads(iface.get('declared_params_json') or '{}')
        declared_bps = params.get('air_rate_bps') or params.get(
            'bitrate_bps')
    except ValueError:
        pass
    measured = [m for m in measurements
                if m.get('interface_name', '') == iface.get('name')
                or iface.get('name') in json.dumps(
                    m.get('bearer_path_json', ''))]
    fresh = [m for m in measured if measurement_fresh(
        m.get('measured_at_ms', 0), now_ms, horizon_ms)]
    best = max(fresh, key=lambda m: m.get('throughput_bps', 0)) \
        if fresh else None
    budget = next((b for b in budgets
                   if b.get('interface_name') == iface.get('name')),
                  None)
    return {
        'declaredAirRateBps': declared_bps,
        'measuredThroughputBps': best.get('throughput_bps')
        if best else None,
        'measuredFidelity': best.get('fidelity') if best else None,
        'measurementFresh': bool(best),
        'staleMeasurements': len(measured) - len(fresh),
        'airtimeBudget': {
            'windowSeconds': budget.get('window_seconds'),
            'budgetMs': budget.get('budget_ms'),
            'consumedMs': budget.get('consumed_ms'),
        } if budget else None,
        'bytesPerMinUsable': int((best.get('throughput_bps', 0) / 8)
                                 * 60) if best else None,
    }


def _oversubscription(demand_bytes_min, capacity_bytes_min):
    """The demand-vs-capacity verdict for one isle. capacity None =
    no fresh measurement -> 'unknown, measure first', never a guess."""
    if capacity_bytes_min is None:
        return {'state': 'unknown',
                'evidence': 'no fresh capacity measurement on this '
                            'isle\'s radios — measure first'}
    if not demand_bytes_min:
        return {'state': 'idle',
                'evidence': 'no declared demand (and idle radios are '
                            'silent — DECIDED row 19)'}
    ratio = demand_bytes_min / capacity_bytes_min \
        if capacity_bytes_min else float('inf')
    if ratio > 1.0:
        return {'state': 'oversubscribed',
                'evidence': 'declared demand %d B/min exceeds measured '
                            'capacity %d B/min (%.0f%%)'
                            % (demand_bytes_min, capacity_bytes_min,
                               ratio * 100),
                'knob': 'TransportBinding rates/sizes, or a faster '
                        'bearer (§5d)',
                'action': 'lower an app\'s ask, add capacity, or '
                          'accept queueing (ret-7) — chosen, never '
                          'silent'}
    return {'state': 'fits',
            'evidence': 'declared demand %d B/min is %.0f%% of '
                        'measured capacity %d B/min'
                        % (demand_bytes_min, ratio * 100,
                           capacity_bytes_min)}


def assemble_arch_topology(tables, instance_name, now_ms,
                           horizon_ms=900_000):
    """The whole view, from plain row-dict lists in `tables`:
    interfaces, device_links, device_models, bindings, budgets,
    measurements, arch_nodes, trusts, isle_devices (islemesh).
    Returns the nested block structure the /arch page renders."""
    models = {m.get('name'): m for m in tables.get('device_models', [])}
    links = {d.get('interface_name'): d
             for d in tables.get('device_links', [])}
    measurements = tables.get('measurements', [])
    budgets = tables.get('budgets', [])

    # --- the LOCAL isle block -----------------------------------------
    devices = []
    capacity_total = None
    for iface in tables.get('interfaces', []):
        cap = device_capacity(iface, measurements, budgets, now_ms,
                              horizon_ms)
        link = links.get(iface.get('name'), {})
        model = models.get(link.get('device_model_name', ''), {})
        devices.append({
            'name': iface.get('name'),
            'bearer': iface.get('bearer'),
            'direction': iface.get('direction'),
            'regulatoryDomain': iface.get('regulatory_domain'),
            'idlePolicy': iface.get('idle_policy', 'silent'),
            'enabled': bool(iface.get('enabled')),
            'model': model.get('display_name') or None,
            'modelInterop': model.get('interop') or None,
            'capacity': cap,
        })
        if cap['bytesPerMinUsable'] is not None:
            capacity_total = (capacity_total or 0) \
                + cap['bytesPerMinUsable']

    apps = {}
    for b in tables.get('bindings', []):
        app = b.get('app_name') or '(unattributed)'
        entry = apps.setdefault(app, {'name': app, 'bindings': [],
                                      'bytesPerMin': 0})
        demand = binding_demand(b)
        entry['bindings'].append({
            'name': b.get('name'),
            'protocol': b.get('app_protocol'),
            'destination': b.get('destination_name'),
            'enabled': bool(b.get('enabled')),
            'demand': demand,
        })
        if b.get('enabled'):
            entry['bytesPerMin'] += demand['bytesPerMin']
    demand_total = sum(a['bytesPerMin'] for a in apps.values())

    local_isle = {
        'name': instance_name,
        'kind': 'local',
        'devices': devices,
        'apps': sorted(apps.values(), key=lambda a: a['name']),
        'demandBytesPerMin': demand_total,
        'capacityBytesPerMin': capacity_total,
        'verdict': _oversubscription(demand_total, capacity_total),
    }

    # --- peer isle blocks (.arch nodes) + islemesh devices -------------
    isles = [local_isle]
    for node in tables.get('arch_nodes', []):
        fact = {'last_heard_ms': node.get('last_heard_ms', 0)}
        isles.append({
            'name': node.get('arch_name') or node.get('name'),
            'kind': node.get('node_kind', 'peer-isle'),
            'reachableNow': reachable_now(fact, now_ms, horizon_ms),
            'lastHeardMs': node.get('last_heard_ms', 0),
            'hopCount': node.get('hop_count', 0),
            'trust': node.get('trust_name', ''),
            'devices': [], 'apps': [],
            'note': 'a peer isle reports its own inventory when the '
                    'gossip payload lands (assumed first payload, '
                    '§6) — an empty block is honest, not final',
        })
    for d in tables.get('isle_devices', []):
        isles.append({
            'name': d.get('name'),
            'kind': 'isle-device',
            'devices': [],
            'apps': [{'name': a.get('name', ''),
                      'domain': a.get('domain', '')}
                     for a in (d.get('apps') or [])],
            'note': 'from the islemesh ingest (isle stays '
                    'authoritative over networking)',
        })

    # --- edges: measured paths, freshness-honest ------------------------
    paths = []
    for m in measurements:
        fresh = measurement_fresh(m.get('measured_at_ms', 0), now_ms,
                                  horizon_ms)
        paths.append({
            'from': instance_name,
            'to': m.get('destination_name'),
            'bearerPath': m.get('bearer_path_json'),
            'worstHopBearer': m.get('worst_hop_bearer'),
            'hopCount': m.get('hop_count'),
            'rttMs': m.get('rtt_ms'),
            'throughputBps': m.get('throughput_bps'),
            'lossRate': m.get('loss_rate'),
            'fidelity': m.get('fidelity'),
            'fresh': fresh,
            'measuredAtMs': m.get('measured_at_ms'),
        })

    return {
        'ok': True,
        'nowMs': now_ms,
        'isles': isles,
        'paths': paths,
        'notes': [
            'demand is DECLARED (binding policy); metered demand from '
            'real request traffic is a named follow-up',
            'capacity pairs the declared air rate with the MEASURED '
            'effective rate — protocol overhead is real (62.5k air '
            'carried 821 B/s on the desk)',
            'stale measurements are not shown as capacity — unknown, '
            'measure first',
        ],
    }
