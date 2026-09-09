# Mathshapes (`mathshapes`)

Math-defined shapes (quadric/primitive/CSG), aquaponic towers, CAD import.

**Kind:** polari-app · **agent tier:** member · **requires:** aquaponics, plant_morphology

## Objects

`AquaponicTowerAPI`, `AquaponicTowerDefinition`, `CadImportAPI`, `ImportedCadObject`, `MathShapeDefinition`, `MathShapesAPI`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `cad_basis.py`, `shape_basis.py`, `tower_basis.py`
- **api** — `cad_api.py`, `shape_api.py`, `tower_api.py`
- **seed** — `shape_seed.py`, `tower_seed.py`
- **remote** — `cad_remote.py`
- **custom** — `custom/cad_import.py`, `custom/cad_minio.py`, `custom/gear_geometry.py`, `custom/growth_prediction.py`, `custom/pot_scene.py`, `custom/shape_analysis.py`, `custom/shape_equations.py`, `custom/shape_geometry.py`, `custom/shape_modify.py`, `custom/soil_modify.py`, `custom/spool_geometry.py`, `custom/tower_analysis.py`, `custom/winding_geometry.py`
- **selftests** — `pot_transparency_selftest.py`, `shape2_selftest.py`, `shape3_selftest.py`, `shape4_selftest.py`, `shape_equations_selftest.py`, `shapes_selftest.py`, `soil_selftest.py`, `winding_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest mathshapes        # in the running backend
PYTHONPATH=.:modules python3 -m mathshapes.pot_transparency_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform mathshapes`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
