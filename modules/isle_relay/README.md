# Isle Relay (`isle_relay`)

isle-relay: a second OpenWrt guest (hardware app) serving a relay segment that extends the isle; the body for the Reticulum extension app (WiFi over Reticulum).

**Kind:** polari-app · **agent tier:** member · **requires:** hardwareapps, islemesh

## Objects

`IsleRelayAPI`, `RelayNodeDefinition`, `RelayNodeState`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `isle_relay_basis.py`
- **api** — `isle_relay_api.py`
- **page** — `isle_relay_page.py`
- **selftests** — `isle_relay_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `isle_relay.isle_relay_page:SEED_ISLE_RELAY_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest isle_relay        # in the running backend
PYTHONPATH=.:modules python3 -m isle_relay.isle_relay_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform isle_relay`
