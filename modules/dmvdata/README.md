# Dmvdata (`dmvdata`)

DMV cost-of-living source catalogs, gov/legal sources, cross-validation.

**Kind:** library · **agent tier:** member · **requires:** scoring

## Objects

`AcademicSource`, `CompanySource`, `GovSource`, `IndividualSource`, `JournalisticSource`, `NonProfitSource`, `PoliticalGroupSource`, `RetrievalConfirmation`, `SourceRetrieval`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `cross_validation_basis.py`, `gov_sources_basis.py`, `legal_sources_basis.py`
- **seed** — `legis_sources_seed.py`, `source_seed.py`
- **custom** — `custom/census_pull.py`
- **selftests** — `cross_validation_selftest.py`, `dmv_sources_selftest.py`, `gov_sources_selftest.py`, `legal_sources_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest dmvdata        # in the running backend
PYTHONPATH=.:modules python3 -m dmvdata.cross_validation_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform dmvdata`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
