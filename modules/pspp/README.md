# Pspp (`pspp`)

PSPP foundation: evidence methods, claims-not-values, digitized book datasets + interpolation (PSPP_MATERIALS_PLAN.md).

**Kind:** polari-app · **agent tier:** member · **requires:** materialsScience

## Objects

`BenchmarkCase`, `CeramicSample`, `ChemicalSpecies`, `DigitizedDataset`, `EvidenceMethod`, `ExposureScenario`, `LadderRung`, `MaterialPerformanceScenario`, `MaterialProcessDefinition`, `MaterialProcessExecution`, `MaterialState`, `PrecursorSource`, `ProcessingStage`, `PropertyClaim`, `PsppAPI`, `ReactionRule`, `ReactionWindow`, `ResearchTool`, `ScaleStructureDefinition`, `ScaleTransferDefinition`, `StructureClaim`, `ThresholdReactionWindow`, `ValidationClaim`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/benchmark_cases/BenchmarkCase.py`, `objects/benchmark_cases/_shared.py`, `objects/ceramics_ladder/LadderRung.py`, `objects/ceramics_ladder/_shared.py`, `objects/ceramics_samples/CeramicSample.py`, `objects/ceramics_samples/_shared.py`, `objects/claims/PropertyClaim.py`, `objects/claims/StructureClaim.py`, `objects/claims/ValidationClaim.py`, `objects/claims/_shared.py`, `objects/digitized_datasets/DigitizedDataset.py`, `objects/digitized_datasets/_shared.py`, … (27 more)
- **basis** — `benchmark_cases_basis.py`, `ceramics_ladder_basis.py`, `ceramics_samples_basis.py`, `claims_basis.py`, `digitized_datasets_basis.py`, `evidence_methods_basis.py`, `exposure_scenarios_basis.py`, `material_processes_basis.py`, `material_states_basis.py`, `material_structure_basis.py`, `performance_scenarios_basis.py`, `reaction_network_basis.py`, … (5 more)
- **api** — `pspp_api.py`
- **seed** — `characterization_seed.py`, `cmc_library_seed.py`, `datasets_seed.py`, `sintering_seed.py`
- **page** — `pspp_page.py`
- **custom** — `custom/composition_math.py`, `custom/cure_checkpoints.py`, `custom/dataset_interpolation.py`, `custom/experiment_guidance.py`, `custom/geopolymer_ceramic_transition.py`, `custom/glass_refinement.py`, `custom/network_stepping.py`, `custom/progress_engine.py`, `custom/pspp_views.py`, `custom/q_distribution.py`, `custom/sintering_engine.py`, `custom/sintering_structure.py`, … (10 more)
- **selftests** — `benchmark_cases_selftest.py`, `ceramics_ladder_selftest.py`, `ceramics_samples_selftest.py`, `characterization_selftest.py`, `cmc_library_selftest.py`, `composition_math_selftest.py`, `cure_checkpoints_selftest.py`, `digitized_datasets_selftest.py`, `evidence_claims_selftest.py`, `experiment_guidance_selftest.py`, `geopolymer_ceramic_transition_selftest.py`, `glass_refinement_selftest.py`, … (23 more)

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `pspp.pspp_page:SEED_PSPP_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest pspp        # in the running backend
PYTHONPATH=.:modules python3 -m pspp.benchmark_cases_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform pspp`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
