# Resources (`resources`)

Node resource inventory, module profiles, admission advisor. Moves in wave 5; core still imports it statically (drop refuses).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AdmissionAPI`, `ModuleResourceProfile`, `NodeResourcesAPI`, `ResourceProfilesAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/profile/ModuleResourceProfile.py`
- **basis** — `profile_basis.py`
- **api** — `admission_api.py`, `node_resources_api.py`, `profile_api.py`
- **seed** — `profile_seed.py`
- **custom** — `custom/admission_advisor.py`, `custom/node_resources.py`, `custom/profile_analysis.py`, `custom/profile_measure.py`
- **selftests** — `admission_selftest.py`, `measure_selftest.py`, `node_resources_selftest.py`, `profiles_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest resources        # in the running backend
PYTHONPATH=.:modules python3 -m resources.admission_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform resources`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
