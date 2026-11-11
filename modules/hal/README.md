# HAL (`hal`)

The generalized hardware abstraction layer: chip-independent HAL operations, their bindings to each SoC's registers, the access mechanisms that decide how code is generated, and the step-by-step trace of every generated line

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`HalAPI`, `HalRecord`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/hal/HalRecord.py`
- **basis** — `hal_basis.py`
- **api** — `hal_api.py`
- **endpoints** — `hal_endpoints.py`
- **seed** — `hal_seed.py`
- **page** — `hal_page.py`
- **selftests** — `hal_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `hal.hal_page:SEED_HAL_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest hal        # in the running backend
PYTHONPATH=.:modules python3 -m hal.hal_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform hal`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
