# Polariapps (`polariapps`)

Polari-Apps: module configurations per use-case, plan-first + exportable.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AppDeploymentPlan`, `AppPermissionProfile`, `AppsAPI`, `PolariAppDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `apps_basis.py`, `apps_permissions_basis.py`
- **api** — `apps_api.py`
- **seed** — `apps_seed.py`
- **custom** — `custom/apps_analysis.py`, `custom/apps_nav.py`
- **selftests** — `apps_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest polariapps        # in the running backend
PYTHONPATH=.:modules python3 -m polariapps.apps_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform polariapps`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
