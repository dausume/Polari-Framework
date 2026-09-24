# Tensor Tree (`tensortree`)

Rooted, navigable views over tensor state: nodes valid by LOCAL visual coherence (a sim-space binding), typed unresolved spaces anywhere, mappings that may cross branches with two statuses and evidence, selections as mathematical objects, and discovery = hard filters then a configured score (plan tt-0).

Plan of record: `AI-Notes/plans/COMPUTE_LOD_TENSOR_PLAN.md` (three rounds with ChatGPT; D1–D7 ratified 2026-09-23). This
module is slice **tt-0** (Phase 1, ontology): rows, validators, seeds, one read/discover API, configured pages.
Nothing is installed by it (no toolchain, no core); tt-1 puts a real tensor (the waxprint thermal field) in it.

**Rows** (one class per file under `objects/tensortree/`, re-exported by `tensortree_basis.py`, count asserted by the selftest):
- `LocalizedDimension`
- `TensorDiscoveryPolicy`
- `TensorMapping`
- `TensorNode`
- `TensorSelection`
- `TensorTreeDefinition`
- `UnresolvedTensorSpace`

**API:** GET /api/tensortree · GET /api/tensortree/trees/{name} · …/graph · …/validate · POST /api/tensortree/discover {selection, context_node}

**Page:** `/display/tensortree` — configured tables + structured panels only (no raw JSON).

**Selftest:** `PYTHONPATH=.:modules python3 modules/tensortree/tensortree_selftest.py` (fake manager) and the live-boot probe
`tests/tensor_liveboot_probe.py` (boots the real server with the three modules and reads them back).
