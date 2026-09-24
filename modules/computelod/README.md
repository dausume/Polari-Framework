# Compute LOD (`computelod`)

ONE conceptual ladder from C to materials (eleven rungs; die/package hang off microarchitecture through the microchip ladder by design_level_ref), kinds as rows, downward ComputeMappings and upward CharacterizationMappings as evidence-bearing rows, and the compute-lod tech tree of what to learn (plan tt-0).

Plan of record: `AI-Notes/plans/COMPUTE_LOD_TENSOR_PLAN.md` (three rounds with ChatGPT; D1–D7 ratified 2026-09-23). This
module is slice **tt-0** (Phase 1, ontology): rows, validators, seeds, one read/discover API, configured pages.
Nothing is installed by it (no toolchain, no core); tt-1 puts a real tensor (the waxprint thermal field) in it.

**Rows** (one class per file under `objects/computelod/`, re-exported by `computelod_basis.py`, count asserted by the selftest):
- `CharacterizationMapping`
- `CompilerArtifact`
- `ComputeKind`
- `ComputeLOD`
- `ComputeMapping`

**API:** GET /api/computelod · GET /api/computelod/rungs/{name} · GET /api/computelod/walk/{rung}/{ref}?direction=down|up

**Page:** `/display/computelod` — configured tables + structured panels only (no raw JSON).

**Selftest:** `PYTHONPATH=.:modules python3 modules/computelod/computelod_selftest.py` (fake manager) and the live-boot probe
`tests/tensor_liveboot_probe.py` (boots the real server with the three modules and reads them back).
