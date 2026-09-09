# Isle Guestnet (`isle_guestnet`)

isle-guestnet: an OpenWrt guest (hardware app) serving guest-only WiFi, isolated from the isle; exposures as rows.

**Kind:** polari-app · **agent tier:** member · **requires:** hardwareapps, islemesh

## Objects

`GuestNetworkDefinition`, `GuestNetworkExposure`, `GuestNetworkState`, `IsleGuestnetAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/guestnet/GuestNetworkDefinition.py`, `objects/guestnet/GuestNetworkExposure.py`, `objects/guestnet/GuestNetworkState.py`
- **basis** — `isle_guestnet_basis.py`
- **api** — `isle_guestnet_api.py`
- **page** — `isle_guestnet_page.py`
- **selftests** — `isle_guestnet_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `isle_guestnet.isle_guestnet_page:SEED_ISLE_GUESTNET_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest isle_guestnet        # in the running backend
PYTHONPATH=.:modules python3 -m isle_guestnet.isle_guestnet_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform isle_guestnet`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
