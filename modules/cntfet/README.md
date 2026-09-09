# Cntfet (`cntfet`)

Aligned-CNT FET S1: decomposed one-tube device, clean-room VS-CNFET-derived compact model (first open CNFET compact model) + ToB F2 reference + Verilog-A/OSDI twin. Compute (OpenVAF/ngspice/OpenSTA/kwant) delegates to the cnt-engines worker (dist-1): CNTFET_ENGINES_URL knob, else topology provider cntfet.engines, else local ~/tools.

**Kind:** polari-app · **agent tier:** member · **requires:** electrodevice

## Objects

`AlignedCNTFETDevice`, `AlignedCNTFETGeometry`, `BlockFETConfiguration`, `CNTAlignmentProcess`, `CNTCalibrationAnchor`, `CNTCellDefinition`, `CNTContact`, `CNTFETAPI`, `CNTFETMonteCarloRun`, `CNTFETParameterRow`, `CNTFETSimResult`, `CNTMaterialState`, `CNTParasitics`, `CNTPlacementProcess`, `CNTPurificationProcess`, `CNTTransportModel`, `CellCharacterizationRun`, `CellFETConfiguration`, `ComplementaryPair`, `ContactFormationProcess`, `DesignTarget`, `EvidenceItem`, `FETCharacteristic`, `FETFieldBand`, `FETFieldSample`, `FETOperatingState`, `FETOptimizationClass`, `FETRegime`, `FETShapeType`, `FETTargetMapping`, `FunctionalBlock`, `GateStack`, `GateStackProcess`, `LithographyProcess`, `OpenCellLibrary`, `PowerBudget`, `ScatteringMechanism`, `TechnologyIPRecord`, `TransportRegime`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/cnt/AlignedCNTFETDevice.py`, `objects/cnt/AlignedCNTFETGeometry.py`, `objects/cnt/CNTCalibrationAnchor.py`, `objects/cnt/CNTContact.py`, `objects/cnt/CNTFETParameterRow.py`, `objects/cnt/CNTFETSimResult.py`, `objects/cnt/CNTMaterialState.py`, `objects/cnt/CNTParasitics.py`, `objects/cnt/CNTTransportModel.py`, `objects/cnt/GateStack.py`, `objects/cnt/_shared.py`, `objects/cnt_cell_library/CNTCellDefinition.py`, … (36 more)
- **basis** — `cnt_basis.py`, `cnt_cell_library_basis.py`, `cnt_characteristics_basis.py`, `cnt_characterization_basis.py`, `cnt_evidence_basis.py`, `cnt_fields_basis.py`, `cnt_ip_basis.py`, `cnt_power_basis.py`, `cnt_process_basis.py`, `cnt_regimes_basis.py`, `cnt_states_basis.py`, `cnt_targets_basis.py`, … (2 more)
- **api** — `cnt_api.py`
- **endpoints** — `cnt_verilog_a_endpoints.py`
- **seed** — `cnt_app_seed.py`, `cnt_calibration_seed.py`, `cnt_cell_scoring_seed.py`, `cnt_device_viz_seed.py`, `cnt_figures_seed.py`, `cnt_reference_papers_seed.py`, `cnt_scene_seed.py`, `cnt_scoring_seed.py`, `cntfet_data_seed.py`
- **page** — `cnt_block_page.py`, `cnt_blocks_page.py`, `cnt_cell_page.py`, `cnt_open_library_page.py`, `cnt_page.py`
- **remote** — `cnt_remote.py`
- **custom** — `custom/cnt_bandstructure.py`, `custom/cnt_capability.py`, `custom/cnt_cell_advance.py`, `custom/cnt_cell_coverage.py`, `custom/cnt_cells.py`, `custom/cnt_charge.py`, `custom/cnt_citations.py`, `custom/cnt_compare.py`, `custom/cnt_constants.py`, `custom/cnt_derive.py`, `custom/cnt_digitized_fc10.py`, `custom/cnt_extrinsics.py`, … (20 more)
- **selftests** — `block_pages_selftest.py`, `blocks_selftest.py`, `cell_advance_selftest.py`, `cell_pages_selftest.py`, `cells2_selftest.py`, `cntfet_selftest.py`, `evidence_selftest.py`, `fields_selftest.py`, `ip_selftest.py`, `level_scenes_selftest.py`, `logic_selftest.py`, `more_cells_selftest.py`, … (8 more)
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `cntfet.cnt_block_page:SEED_BLOCK_PAGES`
- `cntfet.cnt_blocks_page:SEED_BLOCK_PAGES`
- `cntfet.cnt_cell_page:SEED_CELL_PAGES`
- `cntfet.cnt_open_library_page:SEED_OPEN_LIBRARY_PAGES`
- `cntfet.cnt_page:SEED_CNTFET_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest cntfet        # in the running backend
PYTHONPATH=.:modules python3 -m cntfet.block_pages_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform cntfet`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
