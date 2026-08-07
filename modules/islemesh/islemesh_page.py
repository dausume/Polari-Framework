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

from polariApiServer.module_pages_seed import _api, _page, _row, _table

SEED_ISLEMESH_PAGE_DISPLAYS = [
    _page(
        'isle-mesh-home', 'isle-mesh',
        'Isle-mesh convergence: the isle as polari accepts it — '
        'devices, uplinks, mesh-apps and the protocol matrix '
        'derived from the agent proxies. MOCK ingests are flagged '
        'in the summary banner at the top.',
        'IsleDevice',
        [
            _row(0, [
                _api('islemesh-summary', 0, 7,
                     'Isle summary (mock banner lives here)',
                     '/api/islemesh'),
                _api('islemesh-matrix', 1, 5,
                     'Protocol matrix (the proxies ARE the policy)',
                     '/api/islemesh/matrix'),
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
