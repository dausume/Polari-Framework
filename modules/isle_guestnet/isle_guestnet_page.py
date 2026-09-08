"""@module isle_guestnet.isle_guestnet_page — /display/isle-guestnet (tables + structured panel only)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_ISLE_GUESTNET_PAGE_DISPLAYS = [
    _page('isle-guestnet', 'isle-guestnet',
          'Isle guest network: an OpenWrt guest (hardware app) serving guest-only WiFi, isolated from the isle; every host a guest '
          'may reach is an exposure row. Rows define, the isle applies (isle vm).',
          'GuestNetworkDefinition',
          [_row(0, [_sapi('guest-summary', 0, 12, 'Guest networks + readiness', '/api/isle-guestnet/summary', pick='networks')]),
           _row(1, [_table('guest-defs', 0, 5, 'Guest networks', 'GuestNetworkDefinition', columns='name,hardware_app,ssid,vlan,cidr,client_isolation,internet'),
                    _table('guest-exposures', 1, 4, 'Exposures (what guests may reach)', 'GuestNetworkExposure', columns='network,isle_host,app_name,allowed_by,reason,enabled'),
                    _table('guest-state', 2, 3, 'Reported by the guest', 'GuestNetworkState', columns='network,clients,leases,rx_bytes,tx_bytes,observed_at')])]),
]
