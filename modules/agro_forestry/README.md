# Agro Forestry (`agro_forestry`)

Legacy registry module (user-created example).

**Kind:** library · **agent tier:** member · **requires:** nothing

## Objects

`GardenBoundary`, `GardenBoundaryPost`, `Plant`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `gardenBoundaryPost_basis.py`, `gardenBoundary_basis.py`, `plant_basis.py`
- **seed** — `agro_forestry_data_seed.py`
- **custom** — `custom/registerAgroForestryModule.py`
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest agro_forestry        # in the running backend
PYTHONPATH=.:modules python3 -m agro_forestry.<none yet>   # on the host, from polari-framework/
```

Conformance: `pol modules conform agro_forestry`
