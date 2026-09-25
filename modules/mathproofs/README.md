# mathproofs — mathematical proofs as rows (plan §I)

Claims ABOUT rows (a mapping preserves symmetry; a chain's domains compose; two readings agree) in one JSON term
language, checked by tiers that say exactly what they established: numeric witness (never a proof) → interval
decision → SymPy over symbols → Z3 (pf-1) → Lean 4 via the `polari-proof-tools` engines worker (pf-2) → a labelled
human note. Inference rules generate the obligations a TensorTree's structure demands — the logic between its
parts — and discovery refuses a candidate whose obligation is refuted (with the counterexample). Proofs never
change a mapping's `mapping_status` / `evidence_level`; their state is shown ON the mapping (badge, table, `/view`).

    PYTHONPATH=.:modules python3 modules/mathproofs/mathproofs_selftest.py
    GET  /api/mathproofs · /claims/{name} · POST /claims/{name}/check?tier= · /rules · /obligations?tree=|mapping=
    POST /api/mathproofs/trees/{name}/obligations   (generate + run the cheap tiers)   · GET …/aggregate (the time reading)
