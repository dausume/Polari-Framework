"""
@module reticulum.reticulum_page

The two upper-level topology displays (his ask 2026-09-09: "all three
levels have dedicated topology displays"): /display/topology-archipelago
and /display/topology-mesh. The isle level lives with its owner
(islemesh_page: /display/topology-isle). Configured tables + structured
panels only — no raw JSON. The top panel of each is the level's VPN
placement summary (/api/vpn/topology/<level>); the tables are the
level's own rows (reticulum: archipelago nodes/trust/measurements,
mesh relays/consumers/bindings) and the VPN rows that cross it.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_RETICULUM_PAGE_DISPLAYS = [
    _page(
        'topology-archipelago', 'topology-archipelago',
        'Archipelago topology (.arch): isles federated as one network while '
        'the measured path meets the floor. Nodes and their declared trust, '
        'the link measurements against the floor, the VPN federation links '
        'and relays that carry it, and the apps exposed at .arch.',
        'ArchipelagoNode',
        [
            _row(0, [
                _sapi('topology-arch-summary', 0, 12,
                      'This level — definition, floor, and the VPN kinds usable here with their role',
                      '/api/vpn/topology/archipelago',
                      pick='level,rung,definition,floor,placements'),
            ], min_height=260),
            _row(1, [
                _table('topology-arch-nodes', 0, 6, 'Archipelago nodes (measured reachability)',
                       'ArchipelagoNode',
                       columns='name,arch_name,destination_name,node_kind,vouched_by,'
                               'trust_name,last_heard_ms,hop_count,link_quality,fidelity'),
                _table('topology-arch-trust', 1, 6, 'Declared trust (the other axis)',
                       'ArchipelagoTrust',
                       columns='name,grade,may_ask_json,granted_by,granted_at'),
            ]),
            _row(2, [
                _table('topology-arch-links', 0, 6, 'Link measurements against the floor',
                       'LinkMeasurement',
                       columns='name,destination_name,hop_count,worst_hop_bearer,'
                               'throughput_bps,rtt_ms,loss_rate,measured_at_ms,fidelity'),
                _table('topology-arch-vpn-links', 1, 6,
                       'VPN federation links (gateway to gateway; relay kind = blind by default)',
                       'VpnFederationLink',
                       columns='name,network_name,device_name,provider,kind,label,remote_device,'
                               'remote_network,relay_kind,agreement_id,status,arch_name'),
            ]),
            _row(3, [
                _table('topology-arch-exposures', 0, 6, 'Apps exposed at .arch',
                       'AppArchExposure',
                       columns='name,app_name,arch_name,scope,enabled'),
                _table('topology-arch-placements', 1, 6,
                       'VPN placements (kvm / openwrt-extension / container) and their archipelago role',
                       'VpnPlacement',
                       columns='kind,title,placement,extends,requires_tier,sees_traffic,blind,level_archipelago'),
            ]),
        ]),
    _page(
        'topology-mesh', 'topology-mesh',
        'Mesh topology (.mesh): zero-trust state relays. Consumers are not '
        'peers — they receive state and send returns through the proposal '
        'seam. The relays, their consumers by Reticulum identity, the '
        'transport bindings and interfaces beneath them, and the VPN kinds '
        'that serve as relay bodies, TCP/443 rendezvous and opt-in exits.',
        'MeshAppRelay',
        [
            _row(0, [
                _sapi('topology-mesh-summary', 0, 12,
                      'This level — definition and the VPN kinds usable here with their role',
                      '/api/vpn/topology/mesh',
                      pick='level,rung,definition,placements'),
            ], min_height=240),
            _row(1, [
                _table('topology-mesh-relays', 0, 6, 'Mesh-app relays (the broadcast cores)',
                       'MeshAppRelay',
                       columns='name,app_name,exposure_name,watched_name,cadence_seconds,'
                               'min_cadence_seconds,max_cadence_seconds,prior_states_kept,'
                               'expected_users,kc_link_mode,enabled'),
                _table('topology-mesh-consumers', 1, 6, 'Consumers (by Reticulum identity; pseudonymous first-class)',
                       'MeshConsumer',
                       columns='name,relay_name,first_seen_ms,last_seen_ms,last_return_interval_s,'
                               'returns_in_window,kc_signed'),
            ]),
            _row(2, [
                _table('topology-mesh-bindings', 0, 6, 'Transport bindings (an app\'s asks of the mesh)',
                       'TransportBinding',
                       columns='name,app_name,app_protocol,destination_name,encoding,'
                               'max_message_bytes,max_rate_per_min,priority,direction,enabled'),
                _table('topology-mesh-interfaces', 1, 6, 'Reticulum interfaces (bearers beneath the mesh)',
                       'ReticulumInterface',
                       columns='name,bearer,platform,regulatory_domain,direction,fidelity,'
                               'enabled,idle_policy,tx_legal_confirmed'),
            ]),
            _row(3, [
                _table('topology-mesh-destinations', 0, 6, 'Destinations',
                       'ReticulumDestination',
                       columns='name,identity_name,app_name,aspects,dest_type,scope,direction'),
                _table('topology-mesh-placements', 1, 6,
                       'VPN placements and their mesh role (relay bodies, rendezvous, opt-in exits)',
                       'VpnPlacement',
                       columns='kind,title,placement,requires_tier,sees_traffic,blind,level_mesh'),
            ]),
        ]),
]
