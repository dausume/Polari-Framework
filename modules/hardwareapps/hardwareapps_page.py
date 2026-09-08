"""@module hardwareapps.hardwareapps_page — /display/hardware-apps: definitions, render verdicts, twins (tables + structured panels only)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_HARDWAREAPPS_PAGE_DISPLAYS = [
    _page('hardware-apps', 'hardware-apps',
          'Hardware apps: KVM guests the isle defines from these rows (relay, guest network, …; the router itself stays woven '
          'into the isle) and extension apps pushed into them (reticulum). The render verdict says whether the domain XML + '
          'UCI profile are complete; the twin table is what the isle reports back.',
          'HardwareAppDefinition',
          [_row(0, [_sapi('hwapps-list', 0, 12, 'Render verdicts (what isle vm would define)', '/api/hardwareapps', pick='apps')]),
           _row(1, [_table('hwapps-defs', 0, 8, 'Definitions', 'HardwareAppDefinition',
                           columns='name,kind,role,extends,guest_kind,vm_image_ref,memory_mb,vcpus,bridges_json,passthrough_json,uci_profile,requires_tier'),
                    _table('hwapps-state', 1, 4, 'Twins (reported by the isle)', 'HardwareAppState',
                           columns='app,device_name,vm_state,ip,uptime_s,probe_ok,observed_at')])]),
]
