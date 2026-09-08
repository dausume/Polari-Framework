"""@module isle_relay.isle_relay_page — /display/isle-relay (tables + structured panel only)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_ISLE_RELAY_PAGE_DISPLAYS = [
    _page('isle-relay', 'isle-relay',
          'Isle relay: a second OpenWrt guest (hardware app) serving a relay segment that extends the isle; the Reticulum '
          'extension app runs inside it for WiFi-over-Reticulum. Rows define, the isle applies (isle vm).',
          'RelayNodeDefinition',
          [_row(0, [_sapi('relay-summary', 0, 12, 'Relay segments + guest readiness', '/api/isle-relay/summary', pick='relays')]),
           _row(1, [_table('relay-defs', 0, 7, 'Relay segments', 'RelayNodeDefinition', columns='name,hardware_app,vlan,cidr,bearer,ssid,reticulum_bearer,reticulum_port'),
                    _table('relay-state', 1, 5, 'Reported by the guest', 'RelayNodeState', columns='relay,clients,rx_bytes,tx_bytes,peers_heard,observed_at')])]),
]
