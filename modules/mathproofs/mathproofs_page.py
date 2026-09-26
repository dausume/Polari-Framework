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
              # bp-2d: for anyone — each object kind of this page explained without jargon (GET /api/plain reads the classes' plain_words)
              _row(0, [_sapi('mathproofs-plain', 0, 12, 'In plain words — what these objects are, for a non-expert',
                             '/api/plain?classes=MathClaim,InferenceRule,ProofObligation,ProofRun,ProofMethodReference', hide='ok')], min_height=160),
              _row(1, [_sapi('mathproofs-summary', 0, 12, 'Claims by status, the tiers, and the time reading (what the runs cost; the worst case in aggregate)', '/api/mathproofs', pick='by_status,aggregate,tiers')], min_height=220),
              _row(2, [_table('mathproofs-claims', 0, 12, 'Claims — kind, what they speak of, status by the vocabulary, the checker, evidence, the derived LaTeX, the counterexample when refuted', 'MathClaim',
                              columns='name,kind,about_refs_json,proof_status,checker,evidence_level,statement_latex,counterexample_json,budget_s',
                              column_formats='statement_latex:latex,about_refs_json:refs,name:ref:MathClaim')]),
              _row(3, [_table('mathproofs-obligations', 0, 7, 'Obligations — what the rules demanded of each tree, and where each stands', 'ProofObligation', columns='tree,rule,name,about_refs_json,status,discharged_by,generated_at',
                              column_formats='tree:ref:TensorTreeDefinition,rule:ref:InferenceRule,about_refs_json:refs,discharged_by:ref:MathClaim'),
                       _table('mathproofs-rules', 1, 5, 'Inference rules — the logic between parts, as data; params_json holds a rule'"'"'s knobs (the decomposition bound), read by ref', 'InferenceRule', columns='name,pattern,obligation_kind,checker_default,params_json,enabled,rationale', column_formats='name:ref:InferenceRule')]),
              _row(4, [_table('mathproofs-runs', 0, 12, 'Proof runs — checker, version, verdict, cost, and the rows-state hash that makes a run stale when a row moves', 'ProofRun',
                              columns='claim,name,checker,checker_version,verdict,elapsed_s,ran_at,rows_state_hash', column_formats='claim:ref:MathClaim')]),
              # bp-2e: the published sources behind each tier / vocabulary word — the suite's citation shape; verified per row
              _row(5, [_table('mathproofs-sources', 0, 12, 'Sources — why each way of checking can be trusted, and where its authority stops (verified = the DOI was resolved and read back)',
                               'ProofMethodReference', columns='proves,title,parties,ref,date,url,proves_detail,verified,verified_via', column_formats='url:link')]),
          ]),
]
