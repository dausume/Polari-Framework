# Magnetics (`magnetics`)

Magnetic materials Section A: option catalog with realization ladder, functional role taxonomy (derived viability), theoretical powder designer (MAGNETIC_MATERIALS_PLAN.md).

**Kind:** polari-app · **agent tier:** member · **requires:** materialsScience, supplychain

## Objects

`BlockLayoutDefinition`, `BlockPlacement`, `BlockSizeVariant`, `FieldThresholdBand`, `FieldViewDefinition`, `FieldViewGroup`, `FluxNodeDefinition`, `JointMortarAssignment`, `MagneticCircuitDefinition`, `MagneticElementDefinition`, `MagneticMaterialOption`, `MagneticPowderDefinition`, `MagneticsAPI`, `MaterialUseRole`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/field_view/FieldThresholdBand.py`, `objects/field_view/FieldViewDefinition.py`, `objects/field_view/FieldViewGroup.py`, `objects/field_view/_shared.py`, `objects/magnet/MagneticMaterialOption.py`, `objects/magnet/MagneticPowderDefinition.py`, `objects/magnet/MaterialUseRole.py`, `objects/magnet/_shared.py`, `objects/magnet_block/BlockLayoutDefinition.py`, `objects/magnet_block/BlockPlacement.py`, `objects/magnet_block/BlockSizeVariant.py`, `objects/magnet_block/JointMortarAssignment.py`, … (5 more)
- **basis** — `field_view_basis.py`, `magnet_basis.py`, `magnet_block_basis.py`, `magnet_circuit_basis.py`
- **api** — `magnet_api.py`
- **seed** — `magnet_seed.py`, `magnetic_netlist_seed.py`
- **custom** — `custom/field_views.py`, `custom/magnet_analysis.py`, `custom/magnet_layout.py`, `custom/realization_promotion.py`
- **selftests** — `field_views_selftest.py`, `magnet_layout_selftest.py`, `magnetic_circuits_selftest.py`, `magnetics_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest magnetics        # in the running backend
PYTHONPATH=.:modules python3 -m magnetics.field_views_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform magnetics`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
