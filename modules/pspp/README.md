# Pspp (`pspp`)

PSPP foundation: evidence methods, claims-not-values, digitized book datasets + interpolation (PSPP_MATERIALS_PLAN.md).

**Kind:** polari-app · **agent tier:** member · **requires:** materialsScience

## Objects

`BenchmarkCase`, `CeramicSample`, `ChemicalSpecies`, `DigitizedDataset`, `EvidenceMethod`, `ExposureScenario`, `LadderRung`, `MaterialPerformanceScenario`, `MaterialProcessDefinition`, `MaterialProcessExecution`, `MaterialState`, `PrecursorSource`, `ProcessingStage`, `PropertyClaim`, `PsppAPI`, `ReactionRule`, `ReactionWindow`, `ResearchTool`, `ScaleStructureDefinition`, `ScaleTransferDefinition`, `StructureClaim`, `ThresholdReactionWindow`, `ValidationClaim`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `benchmark_cases_basis.py`, `ceramics_ladder_basis.py`, `ceramics_samples_basis.py`, `claims_basis.py`, `digitized_datasets_basis.py`, `evidence_methods_basis.py`, `exposure_scenarios_basis.py`, `material_processes_basis.py`, `material_states_basis.py`, `material_structure_basis.py`, `performance_scenarios_basis.py`, `reaction_network_basis.py`, `reaction_windows_basis.py`, `research_tools_basis.py`, `scale_transfers_basis.py`, `solgel_sourcing_basis.py`, `threshold_windows_basis.py`
- **api** — `pspp_api.py`
- **seed** — `characterization_seed.py`, `cmc_library_seed.py`, `datasets_seed.py`, `sintering_seed.py`
- **page** — `pspp_page.py`
- **custom** — `custom/composition_math.py`, `custom/cure_checkpoints.py`, `custom/dataset_interpolation.py`, `custom/experiment_guidance.py`, `custom/geopolymer_ceramic_transition.py`, `custom/glass_refinement.py`, `custom/network_stepping.py`, `custom/progress_engine.py`, `custom/pspp_views.py`, `custom/q_distribution.py`, `custom/sintering_engine.py`, `custom/sintering_structure.py`, `custom/solgel_network.py`, `custom/solgel_process.py`, `custom/solgel_structure.py`, `custom/state_resolution.py`, `custom/structure_groups.py`, `custom/structure_sampling.py`, `custom/structure_scene.py`, `custom/structure_validation.py`, `custom/viscous_sintering.py`, `custom/wax_states.py`
- **selftests** — `benchmark_cases_selftest.py`, `ceramics_ladder_selftest.py`, `ceramics_samples_selftest.py`, `characterization_selftest.py`, `cmc_library_selftest.py`, `composition_math_selftest.py`, `cure_checkpoints_selftest.py`, `digitized_datasets_selftest.py`, `evidence_claims_selftest.py`, `experiment_guidance_selftest.py`, `geopolymer_ceramic_transition_selftest.py`, `glass_refinement_selftest.py`, `material_processes_selftest.py`, `material_states_selftest.py`, `material_structure_selftest.py`, `network_stepping_selftest.py`, `performance_scenarios_selftest.py`, `pspp_views_selftest.py`, `q_distribution_selftest.py`, `reaction_network_selftest.py`, `reaction_windows_selftest.py`, `research_tools_selftest.py`, `scale_transfers_selftest.py`, `sintering_engine_selftest.py`, `sintering_structure_selftest.py`, `solgel_network_selftest.py`, `solgel_process_selftest.py`, `solgel_sourcing_selftest.py`, `solgel_structure_selftest.py`, `structure_groups_selftest.py`, `structure_sampling_selftest.py`, `structure_validation_selftest.py`, `threshold_windows_selftest.py`, `viscous_sintering_selftest.py`, `wax_states_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `pspp.pspp_page:SEED_PSPP_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest pspp        # in the running backend
PYTHONPATH=.:modules python3 -m pspp.benchmark_cases_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform pspp`
