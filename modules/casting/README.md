# Casting (`casting`)

Mold nesting: derived negatives, casting chains with derived parity/thermal gates, sprues, fill/demold sims, the nesting wizard. Requires the shape algebra (mathshapes), seed_upsert (composition), the bead model + mold lifecycle (waxprint), wax rankings (waxsupply), and the exotherm/ceramics data (pspp) — admission must order them first (caught live 2026-08-05).

**Kind:** polari-app · **agent tier:** member · **requires:** composition, mathshapes, pspp, waxprint, waxsupply

## Objects

`CastingAPI`, `CastingMaterialThermalProfile`, `CastingRunRecord`, `CastingStageDefinition`, `DemoldPlanDefinition`, `FillInterventionDefinition`, `MasterFeedstockDefinition`, `MoldCoatingDefinition`, `MoldDefinition`, `MoldFillSimState`, `MoldNestingChain`, `NestingPlanDefinition`, `SprueSetInstance`, `SprueStrategyDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `casting_basis.py`, `chain_basis.py`, `coatings_basis.py`, `demold_basis.py`, `fill_sim_basis.py`, `interventions_basis.py`, `nesting_wizard_basis.py`, `sprue_basis.py`
- **api** — `casting_api.py`
- **seed** — `casting_seed.py`, `chain_seed.py`, `sim_seed.py`
- **custom** — `custom/chain_analysis.py`, `custom/mesh_voxelize.py`, `custom/mold_geometry.py`, `custom/pour_loading.py`, `custom/simulation_gaps.py`, `custom/sprue_geometry.py`, `custom/voxel_grid.py`, `custom/wax_feasibility.py`
- **selftests** — `casting_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `casting.sim_seed:SEED_CASTING_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest casting        # in the running backend
PYTHONPATH=.:modules python3 -m casting.casting_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform casting`
