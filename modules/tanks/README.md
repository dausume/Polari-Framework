# Tanks (`tanks`)

Freshwater/saltwater tank ecosystems — the alternate nutrient source.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AquacultureSpecies`, `TankDefinition`, `TankSubstrateDefinition`, `TankSystemAPI`, `TankSystemDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `tank_basis.py`
- **api** — `tank_api.py`
- **seed** — `tank_seed.py`
- **custom** — `custom/tank_analysis.py`
- **selftests** — `tank_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest tanks        # in the running backend
PYTHONPATH=.:modules python3 -m tanks.tank_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform tanks`
