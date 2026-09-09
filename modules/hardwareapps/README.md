# Hardwareapps (`hardwareapps`)

Hardware apps as rows: KVM guests the isle defines (relay, guest network, …) and extension apps pushed into them; pure renderers for the libvirt domain XML (the router template generalised) and OpenWrt UCI profiles (hw-app-1, 2026-09-08).

**Kind:** polari-app · **agent tier:** member · **requires:** islemesh

## Objects

`HardwareAppDefinition`, `HardwareAppState`, `HardwareAppsAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/hardwareapps/HardwareAppDefinition.py`, `objects/hardwareapps/HardwareAppState.py`
- **basis** — `hardwareapps_basis.py`
- **api** — `hardwareapps_api.py`
- **page** — `hardwareapps_page.py`
- **custom** — `custom/domain_xml.py`, `custom/uci_profiles.py`
- **selftests** — `hardwareapps_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `hardwareapps.hardwareapps_page:SEED_HARDWAREAPPS_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest hardwareapps        # in the running backend
PYTHONPATH=.:modules python3 -m hardwareapps.hardwareapps_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform hardwareapps`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
