# mech — standard mechanical parts, assemblies and motion

Plan: `AI-Notes/plans/MECH_FREECAD_INTERCHANGE_PLAN.md` (suite). What the parts are: `AI-Notes/plans/MECH_KIT_PARTS_CATALOGUE.md`.
Built 2026-11-03 on `dev-mech` (econ-core): mxc-1 (catalogue + materials), mxc-2 (assemblies), mxc-4 (motion), and mathshapes' ms-anchor.

## Rows (one class per file under `objects/<group>/`, re-exported by `mech_<group>_basis.py`; all auto-CRUDE + persisted)

| group | rows | what |
|---|---|---|
| `catalog/` | `DimensionSource`, `MechPartFamily`, `MechPartVariant`, `MechFeature` | 25 families / 401 variants / 1277 features from FreeCAD Fasteners WB (ISO 4762 / 7380-1 / 10642 / 4026 / 4032 / 4035 / 7089 / 7093, DIN 508), NopSCADlib (extrusions, brackets, T-nuts, bearings, bushings, MGN rails, GT2 belts/pulleys, TR8 lead nuts), gridfinity-rebuilt (bins, baseplates), and hand-entered rods + drawer slides (basis `knob`). Every family has a licensed, sha'd `DimensionSource`; features carry key + role (`M5x0.8` male/female, `slot-B6/20` channel/rider, `grid-42` cell …) and `load_rating_json`. `archetype_ref` → composition `PartArchetypeDefinition`. |
| `material/` | `MechMaterialOption`, `MechMaterialPreference` | 53 options mirroring `MagneticMaterialOption` (registered in composition's `MATERIAL_PROPERTY_CLASSES`, so `role_viability` reads them) with density / E / ν / yield / hardness / `friction_json` and the IARC status (polari_preferred · polari_acceptable · legacy_harmful, feedstocks, replaced_by); 35 preferences = part category → default / alternative / legacy ids + composition roles. No fourth material identity (D-mxc-9). |
| `assembly/` | `MechAssembly` (the bound Solution; `system_ref` for the template), `MechPartInstance`, `MechJoint` (thin over composition `InterfaceDefinition`), `MechContact`, `MechConflict` | FreeCAD's joint kinds + `grid`; DOF free = complement of `dof_removed_json`, one writer. Fixtures mfx-1 (2020 beam + 2 brackets + 4 T-nuts + 4 M4 screws), mfx-2 (2×2 bin on a 2×2 baseplate, magnets), mfx-3 (drawer cassette: 2 slides, box, baseplate). |
| `motion/` | `MechLoadCase`, `MechMotionCase`, `MechMotionRun` (over core `SimulationRun`; `inputs_sha256` + `confirmation_json` in the bench arc's shape), `MechMotionSimState` (read by `simulation_series.build_series`), `MechMotionVector` | Load cases from bin contents; motion cases in FreeCAD's Formula syntax so they export; runs are made by the engine, never seeded. |

## Engines (`custom/`, pure; exposed as `AnalysisDefinition` rows + no-code solutions in `mech_analysis_seed.py` — no custom API)

- `catalog_import.py` (stdlib; `python3 -I custom/catalog_import.py --write` regenerates `mech_catalog_seed.py` from `custom/upstream/*` — each with `SOURCE.json` + upstream licence) · `compatibility.py` (feature key/role pairing, advisory thread engagement) · `material_registry.py` (+ `custom/registry/` data and build scripts)
- `joint_interface.py` (joint ↔ composition interface, both ways) · `dof_solver.py` (Grübler COUNT, not a rank test — its note says what it cannot catch) · `fit_checks.py` (thread engagement, ISO 273 clearance, slot/T-nut, grid occupancy, drawer cantilever vs rating; `variant_params` is the ONE catalogue accessor)
- `motion_engine.py` (ONE 1-DOF engine, linear or rotary: velocity-Verlet, Karnopp stick/slip, hard stops, detent; FreeCAD's formula syntax parsed, no eval; `reflected_inertia`, `required_drive`, `quasi_static_pull`, `jerk_profile`) · `motion_runs.py` (resultants, `run_polari`, checks, sha + confirmation, `compare_to_freecad`) · `freecad_motion.py` (the headless FreeCAD Motion relay; reference run in `custom/reference/`)
- `analyses.py`: `mech-catalogue-family/-variant`, `mech-pairing(s)`, `mech-material-preference`, `mech-assembly-dof/-check`, `mech-motion-run`, `mech-freecad-compare` — `fn(manager, **params) -> dict`, refusing by name.

Hand-computed numbers the selftests pin: unloaded drawer opens 250 mm under 5 N in 0.39 s (minimum 3.35 N); loaded (8 bins, 2.64 kg total) needs 3.78 N, tip moment 3.82 N·m vs 220.7 N per-slide rating; the legacy wooden runner needs 62.5 N and has no detent; `100*time` matches FreeCAD 1.1.4 within 1e-14 mm over 16 frames (frame 0 is the pre-motion placement; FreeCAD Motion ignores `LengthMax`).

## Rules carried
Polari is the source of truth (ingest everything, export what we can, no sync); regenerate geometry from parameters (D-mxc-3); FEM is `materialsScience`'s — never FreeCAD's CalculiX (D-mxc-7); joints/assemblies extend composition, materials extend magnetics' shape, runs ride core simulations (D-mxc-8..11); Systems vs Solutions (D-mxc-13); every μ, rating and detent is a KNOB with its basis until a measured run lands.

## Selftests
```
PYTHONPATH=.:modules python3 -m mech.mech_catalog_selftest    # 54
PYTHONPATH=.:modules python3 -m mech.mech_material_selftest   # 53
PYTHONPATH=.:modules python3 -m mech.mech_assembly_selftest   # 63
PYTHONPATH=.:modules python3 -m mech.mech_motion_selftest     # 37
PYTHONPATH=.:modules python3 -m mech.mech_analysis_selftest   # 21 — the engines as rows, over the full real seed set
```
In-container: `pol modules selftest mech`.
