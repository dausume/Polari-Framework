"""
@module islemesh.islemesh_page

The /display/isle-mesh no-code page: Dustin's verification
instrument for the convergence arc — watch devices, apps and
protocol permits come online layer by layer as the real
functionality is built out.

Row 0 is the summary API panel: it carries `banner`/`mock_network`
so a MOCK ingest is signalled at the very top of the page (real
data never sets it). The Angular console (mac-10) renders the same
payload as a proper large banner; until then the no-code panel is
the honest version.
"""

from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_ISLEMESH_PAGE_DISPLAYS = [
    _page(
        'isle-mesh-home', 'isle-mesh',
        'Isle-mesh convergence: the isle as polari accepts it — '
        'devices, uplinks, mesh-apps and the protocol matrix '
        'derived from the agent proxies. MOCK ingests are flagged '
        'in the summary banner at the top.',
        'IsleDevice',
        [
            # STRUCTURED reading (no JSON wall): the summary renders
            # as chips + a counts key/value block + a devices table;
            # the matrix is picked so each device's permit list is
            # its own table (the bare dict-of-lists would otherwise
            # land in the panel's unrendered-fields expander).
            _row(0, [
                _sapi('islemesh-summary', 0, 7,
                      'Isle summary (mock banner lives here)',
                      '/api/islemesh'),
                _sapi('islemesh-matrix', 1, 5,
                      'Protocol matrix (the proxies ARE the policy)',
                      '/api/islemesh/matrix', pick='matrix'),
            ]),
            _row(1, [
                _table('islemesh-devices', 0, 6, 'Devices',
                       'IsleDevice',
                       columns='name,isle_name,machine_name,'
                               'agent_mode,agent_present,'
                               'hosts_router,router_running,'
                               'connectivity_mode,last_seen,'
                               'is_mock'),
                _table('islemesh-uplinks', 1, 6, 'Uplinks',
                       'IsleUplink',
                       columns='name,kind,interface,link_up,'
                               'latency_ms,jitter_ms,loss_pct,'
                               'measured_at,is_mock'),
            ]),
            _row(2, [
                _table('islemesh-apps', 0, 6, 'Mesh-apps',
                       'IsleApp',
                       columns='name,domain,device_name,'
                               'orchestrator,availability_mode,'
                               'up_trigger,down_trigger,placement,'
                               'status,is_mock'),
                _table('islemesh-services', 1, 6, 'App services',
                       'IsleAppService',
                       columns='name,subdomain,container,port,'
                               'protocol,is_mock'),
            ]),
            _row(3, [
                _table('islemesh-realizations', 0, 6,
                       'Realizations (one app, many deliveries)',
                       'MeshAppRealization',
                       columns='name,kind,url,package_kind,'
                               'hardware_pin_device,status,'
                               'is_mock'),
                _table('islemesh-permits', 1, 6,
                       'Protocol permits (derived, never '
                       'hand-written)', 'IsleProtocolPermit',
                       columns='name,app_name,server_name,'
                               'listen_port,protocol,upstream,'
                               'fragment_ref,is_mock'),
            ]),
            _row(4, [
                _table('islemesh-receipts', 0, 12,
                       'Ingest receipts (mock_network flags the '
                       'sender\'s declaration)',
                       'IsleIngestReceipt',
                       columns='name,device_name,kind,'
                               'payload_sha256,row_counts_json,'
                               'mock_network,ingested_at'),
            ]),
        ]),
]


# vpn-4: the isle-level topology display (his ask 2026-09-09: dedicated
# displays per level; archipelago + mesh live in reticulum_page).
SEED_ISLEMESH_PAGE_DISPLAYS += [
    _page(
        'topology-isle', 'topology-isle',
        'Isle topology (.isle): your own LAN behind the router — devices, '
        'uplinks, the router and its guests (hardware apps), the VPN '
        'networks and peers that extend the isle, and where each VPN '
        'kind runs here (kvm / openwrt-extension / container).',
        'IsleDevice',
        [
            _row(0, [
                _sapi('topology-isle-summary', 0, 12,
                      'This level — definition and the VPN kinds usable here with their role',
                      '/api/vpn/topology/isle', pick='level,rung,definition,placements'),
            ], min_height=240),
            _row(1, [
                _table('topology-isle-devices', 0, 6, 'Devices', 'IsleDevice',
                       columns='name,isle_name,machine_name,agent_mode,hosts_router,'
                               'router_running,connectivity_mode,last_seen'),
                _table('topology-isle-uplinks', 1, 6, 'Uplinks', 'IsleUplink',
                       columns='name,kind,interface,link_up,latency_ms,jitter_ms,loss_pct,measured_at'),
            ]),
            _row(2, [
                _table('topology-isle-guests', 0, 6, 'Router guests and extensions (hardware apps)',
                       'HardwareAppDefinition',
                       columns='name,kind,role,extends,guest_kind,requires_tier,uci_profile,memory_mb,vcpus'),
                _table('topology-isle-guest-state', 1, 6, 'Guest state (as the isle reports it)',
                       'HardwareAppState',
                       columns='name,app,device_name,vm_state,ip,uptime_s,probe_ok,observed_at'),
            ]),
            _row(3, [
                _table('topology-isle-vpn', 0, 6, 'VPN networks on this isle (mirror)', 'VpnNetwork',
                       columns='network_name,device_name,provider,kind,label,mode,cidr,peer_count,status'),
                _table('topology-isle-placements', 1, 6,
                       'VPN placements and their isle role', 'VpnPlacement',
                       columns='kind,title,placement,extends,requires_tier,sees_traffic,blind,level_isle'),
            ]),
        ]),
]
