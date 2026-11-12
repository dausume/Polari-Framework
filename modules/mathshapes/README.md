# Mathshapes (`mathshapes`)

Math-defined shapes (quadric/primitive/CSG), aquaponic towers, CAD import.

**Kind:** polari-app · **agent tier:** member · **requires:** aquaponics, plant_morphology

## Objects

`AnchoredOffset`, `AquaponicTowerAPI`, `AquaponicTowerDefinition`, `CadImportAPI`, `ImportedCadObject`, `MathShapeDefinition`, `MathShapesAPI`, `ShapeAnchor`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/cad/ImportedCadObject.py`, `objects/shape/AnchoredOffset.py`, `objects/shape/MathShapeDefinition.py`, `objects/shape/ShapeAnchor.py`, `objects/shape/_shared.py`, `objects/tower/AquaponicTowerDefinition.py`
- **basis** — `cad_basis.py`, `shape_basis.py`, `tower_basis.py`
- **api** — `cad_api.py`, `shape_api.py`, `tower_api.py`
- **seed** — `shape_anchor_seed.py`, `shape_seed.py`, `tower_seed.py`
- **remote** — `cad_remote.py`
- **custom** — `custom/cad_import.py`, `custom/cad_minio.py`, `custom/gear_geometry.py`, `custom/growth_prediction.py`, `custom/pot_scene.py`, `custom/shape_analysis.py`, `custom/shape_anchor.py`, `custom/shape_anchor_analyses.py`, `custom/shape_equations.py`, `custom/shape_geometry.py`, `custom/shape_modify.py`, `custom/soil_modify.py`, … (3 more)
- **selftests** — `pot_transparency_selftest.py`, `shape2_selftest.py`, `shape3_selftest.py`, `shape4_selftest.py`, `shape_anchor_selftest.py`, `shape_equations_selftest.py`, `shapes_selftest.py`, `soil_selftest.py`, `winding_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## The anchored-offset tool (ms-anchor, MECH_FREECAD_INTERCHANGE_PLAN §8.5)

Its own tool inside mathshapes: `ShapeAnchor` (a point + frame ray-picked on a shape; the
four-way reference toggle toward / away / tangent_toward / tangent_away) and `AnchoredOffset`
(an offset solid G(u, v, w) < 0 written in that frame — planar square / disk, conform, or a
custom expression such as the §8.5 thread — composed with the parent by the CSG algebra).
Engine `custom/shape_anchor.py`; reached the Polari way — no custom API — as AnalysisDefinition
rows (`custom/shape_anchor_analyses.py`: ms-anchor-pick / -frame, ms-offset-evaluate / -sample /
-equations / -result) each with a seeded no-code solution (`ms-run-…`); seeds
`shape_anchor_seed.py` (an M5 internal thread + its bore on demo-cylinder); executor additions
(atan2 / mod / frac / lmin / lmax, the ∇F operand) in `custom/shape_equations.py`.

```
PYTHONPATH=.:modules python3 -m mathshapes.shape_anchor_selftest
```

## Selftest

```
pol modules selftest mathshapes        # in the running backend
PYTHONPATH=.:modules python3 -m mathshapes.pot_transparency_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform mathshapes`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
