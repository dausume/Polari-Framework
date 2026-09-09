# Foodstate (`foodstate`)

Food as PSPP state evolution (fsp arc): food stages/processes/evidence methods as pspp rows + property-domain contracts; transform engines arrive fsp-2 (FOOD_STATE_PSPP_PLAN.md).

**Kind:** polari-app · **agent tier:** member · **requires:** nutrition, pspp

## Objects

`FoodDomainContract`, `FoodMaterial`, `FoodStateAPI`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `food_contracts_basis.py`, `food_materials_basis.py`
- **api** — `food_api.py`
- **seed** — `food_acid_seed.py`, `food_ph_seed.py`, `food_pspp_seed.py`
- **custom** — `custom/export_initial_data.py`, `custom/food_chemistry.py`, `custom/food_composition.py`, `custom/food_transforms.py`
- **selftests** — `food_chemistry_selftest.py`, `food_materials_selftest.py`, `food_transforms_selftest.py`, `foodstate_selftest.py`, `initial_data_selftest.py`
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest foodstate        # in the running backend
PYTHONPATH=.:modules python3 -m foodstate.food_chemistry_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform foodstate`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
