# Agro Forestry (`agro_forestry`)

Legacy registry module (user-created example).

**Kind:** library · **agent tier:** member · **requires:** nothing

## Objects

`GardenBoundary`, `GardenBoundaryPost`, `Plant`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/gardenBoundary/GardenBoundary.py`, `objects/gardenBoundaryPost/GardenBoundaryPost.py`, `objects/plant/Plant.py`
- **basis** — `gardenBoundaryPost_basis.py`, `gardenBoundary_basis.py`, `plant_basis.py`
- **seed** — `agro_forestry_data_seed.py`
- **custom** — `custom/registerAgroForestryModule.py`
- **selftests** — `agro_forestry_selftest.py`
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest agro_forestry        # in the running backend
PYTHONPATH=.:modules python3 -m agro_forestry.agro_forestry_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform agro_forestry`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
