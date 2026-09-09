# Testing (`testing`)

Accountability spine (opt-in: registers only on test builds / explicit POLARI_MODULES).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AccountabilityAPI`, `Acct1ParityProbe`, `Acct2FormatProbe`, `AppBenchmark`, `AppHierarchyNode`, `CapabilityCheck`, `CheckRun`, `CoverageAPI`, `ModuleCoverage`, `StandardComputerBudget`, `TestCoveragePlan`, `TwinLeaseAPI`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/capability/CapabilityCheck.py`, `objects/capability/CheckRun.py`, `objects/capability/_shared.py`, `objects/coverage/AppBenchmark.py`, `objects/coverage/AppHierarchyNode.py`, `objects/coverage/ModuleCoverage.py`, `objects/coverage/StandardComputerBudget.py`, `objects/coverage/TestCoveragePlan.py`, `objects/coverage/_shared.py`, `objects/parity_probe/Acct1ParityProbe.py`, `objects/parity_probe/_shared.py`
- **basis** — `capability_basis.py`, `coverage_basis.py`, `parity_probe_basis.py`
- **api** — `accountability_api.py`, `coverage_api.py`, `twin_lease_api.py`
- **seed** — `testing_seed.py`
- **page** — `coverage_page.py`
- **catalog** — `check_catalog.py`
- **custom** — `custom/absence_probe.py`, `custom/app_benchmark.py`, `custom/app_hierarchy.py`, `custom/check_runners.py`, `custom/matrix_runner.py`, `custom/ncg_split_probe.py`, `custom/nocode_checks.py`, `custom/report_yaml.py`, `custom/run_matrix.py`, `custom/substrate_checks.py`, `custom/substrate_env.py`, `custom/transport_checks.py`, … (4 more)
- **selftests** — `coverage_selftest.py`, `formats_selftest.py`, `ncg_split_selftest.py`, `nocode_matrix_selftest.py`, `stomp_selftest.py`, `substrate_selftest.py`, `testing_selftest.py`, `transports_selftest.py`, `twin_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `testing.coverage_page:SEED_TESTING_COVERAGE_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest testing        # in the running backend
PYTHONPATH=.:modules python3 -m testing.coverage_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform testing`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
