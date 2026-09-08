# Testing (`testing`)

Accountability spine (opt-in: registers only on test builds / explicit POLARI_MODULES).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AccountabilityAPI`, `Acct1ParityProbe`, `Acct2FormatProbe`, `CapabilityCheck`, `CheckRun`, `TwinLeaseAPI`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `capability_basis.py`, `parity_probe_basis.py`
- **api** — `accountability_api.py`, `twin_lease_api.py`
- **seed** — `testing_seed.py`
- **catalog** — `check_catalog.py`
- **custom** — `custom/absence_probe.py`, `custom/check_runners.py`, `custom/matrix_runner.py`, `custom/ncg_split_probe.py`, `custom/nocode_checks.py`, `custom/report_yaml.py`, `custom/run_matrix.py`, `custom/substrate_checks.py`, `custom/substrate_env.py`, `custom/transport_checks.py`, `custom/twin_checks.py`, `custom/twin_fixtures.py`, `custom/twin_http.py`, `custom/twin_rehearsal.py`
- **selftests** — `formats_selftest.py`, `ncg_split_selftest.py`, `nocode_matrix_selftest.py`, `stomp_selftest.py`, `substrate_selftest.py`, `testing_selftest.py`, `transports_selftest.py`, `twin_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest testing        # in the running backend
PYTHONPATH=.:modules python3 -m testing.formats_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform testing`
