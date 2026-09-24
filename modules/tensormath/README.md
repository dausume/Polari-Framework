# Tensor Math (`tensormath`)

Arbitrary-rank tensors as rows with values by reference (a rank-N MatrixDefinition, a DigitizedDataset, an engine state or a PropertyClaim), named dimensions, tensor expressions delegating rank<=2 to the matrix module, operators, and the compute implementations an operator has (plan COMPUTE_LOD_TENSOR_PLAN.md, tt-0).

Plan of record: `AI-Notes/plans/COMPUTE_LOD_TENSOR_PLAN.md` (three rounds with ChatGPT; D1–D7 ratified 2026-09-23). This
module is slice **tt-0** (Phase 1, ontology): rows, validators, seeds, one read/discover API, configured pages.
Nothing is installed by it (no toolchain, no core); tt-1 puts a real tensor (the waxprint thermal field) in it.

**Rows** (one class per file under `objects/tensormath/`, re-exported by `tensormath_basis.py`, count asserted by the selftest):
- `ComputeImplementation`
- `Tensor`
- `TensorDecomposition`
- `TensorDimension`
- `TensorMathExpression`
- `TensorOperator`

**API:** GET /api/tensormath · GET /api/tensormath/tensors/{name} · POST /api/tensormath/evaluate {expression} · GET /api/tensormath/operators/{name}

**Page:** `/display/tensormath` — configured tables + structured panels only (no raw JSON).

**Selftest:** `PYTHONPATH=.:modules python3 modules/tensormath/tensormath_selftest.py` (fake manager) and the live-boot probe
`tests/tensor_liveboot_probe.py` (boots the real server with the three modules and reads them back).
