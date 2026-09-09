# Polariapps (`polariapps`)

Polari-Apps: module configurations per use-case, plan-first + exportable.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AppDeploymentPlan`, `AppPermissionProfile`, `AppsAPI`, `PolariAppDefinition`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/apps/AppDeploymentPlan.py`, `objects/apps/PolariAppDefinition.py`, `objects/apps/_shared.py`, `objects/apps_permissions/AppPermissionProfile.py`, `objects/apps_permissions/_shared.py`
- **basis** — `apps_basis.py`, `apps_permissions_basis.py`
- **api** — `apps_api.py`
- **seed** — `apps_seed.py`
- **custom** — `custom/apps_analysis.py`, `custom/apps_nav.py`
- **selftests** — `apps_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest polariapps        # in the running backend
PYTHONPATH=.:modules python3 -m polariapps.apps_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform polariapps`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
