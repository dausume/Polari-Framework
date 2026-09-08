# Waxsupply (`waxsupply`)

Bio wax sources for molds and electronic masks.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`WaxSourceDefinition`, `WaxSupplyAPI`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `wax_basis.py`
- **api** — `wax_api.py`
- **seed** — `wax_seed.py`
- **custom** — `custom/wax_analysis.py`
- **selftests** — `wax_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest waxsupply        # in the running backend
PYTHONPATH=.:modules python3 -m waxsupply.wax_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform waxsupply`
