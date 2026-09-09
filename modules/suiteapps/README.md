# Suiteapps (`suiteapps`)

Suite apps: purpose-oriented compositions of apps of every kind (Polari modules, isle containers, hardware KVM guests, extension apps) with the object contracts between parts and a placement plan across devices (sa-1, 2026-09-08).

**Kind:** library · **agent tier:** member · **requires:** islemesh

## Objects

`SuiteAppDefinition`, `SuiteAppsAPI`, `SuiteContract`, `SuitePart`, `SuitePlacement`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/suiteapps/SuiteAppDefinition.py`, `objects/suiteapps/SuiteContract.py`, `objects/suiteapps/SuitePart.py`, `objects/suiteapps/SuitePlacement.py`
- **basis** — `suiteapps_basis.py`
- **api** — `suiteapps_api.py`
- **seed** — `suiteapps_seed.py`
- **page** — `suiteapps_page.py`
- **custom** — `custom/placement.py`
- **selftests** — `suiteapps_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `suiteapps.suiteapps_page:SEED_SUITEAPPS_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest suiteapps        # in the running backend
PYTHONPATH=.:modules python3 -m suiteapps.suiteapps_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform suiteapps`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
