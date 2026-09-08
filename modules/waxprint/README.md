# Waxprint (`waxprint`)

Pellet-fed auger-screw wax printer: melt/bead-voxel/movement sim + optimizer.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`DeviceMaterialDefinition`, `MoldLifecycleRecord`, `PrintConditionDefinition`, `PrinterAssemblyDefinition`, `WaxFeedstockDefinition`, `WaxPrintAPI`, `WaxPrintSimAPI`, `WaxPrintSimState`, `WaxReclaimBatch`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `sim_state_basis.py`, `waxprint_basis.py`
- **api** — `sim_api.py`, `waxprint_api.py`
- **seed** — `sim_seed.py`, `sim_step_seed.py`, `waxprint_seed.py`
- **custom** — `custom/auger_melt.py`, `custom/bead_analysis.py`, `custom/bead_cooling.py`, `custom/commands.py`, `custom/melt_analysis.py`, `custom/movement_analysis.py`, `custom/movement_patterns.py`, `custom/print_optimizer.py`, `custom/sim_evaluation.py`, `custom/sim_runner.py`, `custom/voxel_resolution.py`
- **selftests** — `auger_melt_selftest.py`, `bead_voxel_selftest.py`, `movement_selftest.py`, `optimizer_selftest.py`, `sim_selftest.py`, `sim_step_selftest.py`, `wax_print_op_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `waxprint.sim_seed:SEED_WAXPRINT_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest waxprint        # in the running backend
PYTHONPATH=.:modules python3 -m waxprint.auger_melt_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform waxprint`
