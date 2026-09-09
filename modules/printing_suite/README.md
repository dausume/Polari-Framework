# Printing Suite (`printing_suite`)

@module printing_suite

**Kind:** suite-app · **agent tier:** member · **requires:** suiteapps, hardwareapps, islemesh

## Objects

`GcodeArtifact`, `MaterialLot`, `PrintJob`, `PrintOutcome`, `PrintProfile`, `PrintingSuiteAPI`, `SliceJob`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `printing_suite_basis.py`
- **api** — `printing_suite_api.py`
- **page** — `printing_suite_page.py`
- **selftests** — `printing_suite_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `printing_suite.printing_suite_page:SEED_PRINTING_SUITE_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest printing_suite        # in the running backend
PYTHONPATH=.:modules python3 -m printing_suite.printing_suite_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform printing_suite`
