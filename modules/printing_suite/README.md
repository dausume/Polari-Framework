# Printing Suite (`printing_suite`)

@module printing_suite

**Kind:** suite-app · **agent tier:** member · **requires:** hardwareapps, islemesh, suiteapps

## Objects

`GcodeArtifact`, `MaterialLot`, `PrintJob`, `PrintOutcome`, `PrintProfile`, `PrintingSuiteAPI`, `ProductionRun`, `RunStepRecord`, `SliceJob`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/printing/GcodeArtifact.py`, `objects/printing/MaterialLot.py`, `objects/printing/PrintJob.py`, `objects/printing/PrintOutcome.py`, `objects/printing/PrintProfile.py`, `objects/printing/ProductionRun.py`, `objects/printing/RunStepRecord.py`, `objects/printing/SliceJob.py`
- **basis** — `printing_suite_basis.py`
- **api** — `printing_suite_api.py`
- **page** — `printing_suite_page.py`
- **custom** — `custom/adapters.py`, `custom/pipeline.py`
- **selftests** — `pipeline_selftest.py`, `printing_suite_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `printing_suite.printing_suite_page:SEED_PRINTING_SUITE_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest printing_suite        # in the running backend
PYTHONPATH=.:modules python3 -m printing_suite.pipeline_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform printing_suite`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
