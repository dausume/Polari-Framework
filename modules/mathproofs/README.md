# mathproofs — mathematical proofs as rows (plan §I)

Claims ABOUT rows (a mapping preserves symmetry; a chain's domains compose; two readings agree) in one JSON term
language, checked by tiers that say exactly what they established: numeric witness (never a proof) → interval
decision → SymPy over symbols → Z3 over the continuum and the machine integers, within each claim's `budget_s`
(a model of the negation is the counterexample; a timeout is `undecided`, never refuted) → Lean 4 + Mathlib through
the `polari-proof-tools` engines worker (a committed `.lean` certificate whose header cites the claim's
`statement_hash`; `proved` only when lean accepts it AND the hash matches; never run automatically — ask
`?tier=lean`; the ladder PROOF_ENGINES_URL → local project → local image → `pol allocate mathproofs.engines` →
refusal answers at `GET /api/mathproofs/engines`) → a labelled human note. Inference rules generate the obligations a TensorTree's structure demands — the logic between its
parts — and discovery refuses a candidate whose obligation is refuted (with the counterexample). Proofs never
change a mapping's `mapping_status` / `evidence_level`; their state is shown ON the mapping (badge, table, `/view`).

    PYTHONPATH=.:modules python3 modules/mathproofs/mathproofs_selftest.py
    GET  /api/mathproofs · /claims/{name} · POST /claims/{name}/check?tier= · /rules · /obligations?tree=|mapping=
    POST /api/mathproofs/trees/{name}/obligations   (generate + run the cheap tiers)   · GET …/aggregate (the time reading)
    POST …/claims · POST …/terms/preview · POST …/obligations/propose (pf-3: the doors a person writes through)
    GET  …/engines (where lean would run) · GET …/knowledge (pf-4: the tensor-proofs tree joined live to the claims)

At boot (`custom/boot.py`) every seeded tree's obligations are generated and every never-run claim is checked once
through its cheapest tier (z3 inside its budget), so the panel's badges exist without a POST; the pass is bounded by
the aggregate's worst case. A rule's knobs (`params_json` — the decomposition bound) are read by the template by ref,
so turning one makes its obligations stale, never a silent re-verdict. Requires `z3-solver` (MIT, pip; in-process).
