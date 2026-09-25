"""
@module mathproofs.mathproofs_page

/display/mathproofs — the claims and their status (configured tables + the summary panel), the rules, the
obligations per tree, the runs with their cost. No raw JSON: every panel is a configured Table or the API summary.
"""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_MATHPROOFS_PAGE_DISPLAYS = [
    _page('mathproofs', 'mathproofs',
          'Mathematical proofs — claims about rows in one term language, checked by tiers that say what they established (a numeric '
          'witness is never a proof); the logic between the parts of a tensor tree as inference rules that generate obligations',
          'MathClaim', [
              _row(0, [_sapi('mathproofs-summary', 0, 12, 'Claims by status, the tiers, and the time reading (what the runs cost; the worst case in aggregate)', '/api/mathproofs', pick='by_status,aggregate,tiers')], min_height=220),
              _row(1, [_table('mathproofs-claims', 0, 12, 'Claims — kind, what they speak of, status by the vocabulary, the checker, evidence, the derived LaTeX, the counterexample when refuted', 'MathClaim',
                              columns='name,kind,about_refs_json,proof_status,checker,evidence_level,statement_latex,counterexample_json,budget_s')]),
              _row(2, [_table('mathproofs-obligations', 0, 7, 'Obligations — what the rules demanded of each tree, and where each stands', 'ProofObligation', columns='tree,rule,name,structure_json,status,discharged_by,generated_at'),
                       _table('mathproofs-rules', 1, 5, 'Inference rules — the logic between parts, as data', 'InferenceRule', columns='name,pattern,obligation_kind,checker_default,enabled,rationale')]),
              _row(3, [_table('mathproofs-runs', 0, 12, 'Proof runs — checker, version, verdict, cost, and the rows-state hash that makes a run stale when a row moves', 'ProofRun',
                              columns='claim,name,checker,checker_version,verdict,elapsed_s,ran_at,rows_state_hash')]),
          ]),
]
