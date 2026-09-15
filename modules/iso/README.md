# Polari ISO (`iso`)

Get Polari and Ubuntu onto a new computer: probe a device from a USB stick, derive Ubuntu compatibility, plan its role, build an unattended installer ISO with Polari inside, install from the same Ventoy stick.

**Kind:** polari-app · **agent tier:** core · **requires:** appstore

## Objects

`DeviceProbe`, `IsoAPI`, `IsoBase`, `IsoBuild`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/iso/DeviceProbe.py`, `objects/iso/IsoBase.py`, `objects/iso/IsoBuild.py`
- **basis** — `iso_basis.py`
- **api** — `iso_api.py`
- **endpoints** — `iso_endpoints.py`
- **seed** — `iso_seed.py`
- **page** — `iso_page.py`
- **custom** — `custom/iso_autoinstall.py`, `custom/iso_builder.py`, `custom/iso_compat.py`, `custom/iso_probe_kit.py`
- **selftests** — `iso_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `iso.iso_page:SEED_ISO_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest iso        # in the running backend
PYTHONPATH=.:modules python3 -m iso.iso_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform iso`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
