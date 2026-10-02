"""
@module mathproofs.mathproofs_basis

The INDEX of the mathproofs rows: classes live one-per-file under objects/mathproofs/; this file re-exports them
and holds the class list the server registers.

Mathematical proofs as rows (plan §I): claims about rows in a small term language, checked by tiers (numeric
witness → interval/decision → SymPy → Z3 → Lean, each honest about what it established), obligations generated
from a TensorTree's structure by inference rules — the logic BETWEEN the parts of a tree.
"""
from mathproofs.objects.mathproofs.MathClaim import MathClaim  # noqa: F401
from mathproofs.objects.mathproofs.ProofRun import ProofRun  # noqa: F401
from mathproofs.objects.mathproofs.InferenceRule import InferenceRule  # noqa: F401
from mathproofs.objects.mathproofs.ProofObligation import ProofObligation  # noqa: F401
from mathproofs.objects.mathproofs.ProofMethodReference import ProofMethodReference  # noqa: F401

#: every row class of the module, in registration order (the selftest asserts the count)
MATHPROOFS_CLASSES = [MathClaim, ProofRun, InferenceRule, ProofObligation, ProofMethodReference]
# sc-0 (FIRMWARE_SCENARIO_PLAN.md §1): `inapplicable` — the statement is not defined on this state space (the scenario's PC / ISR /
# build does not exist), kept apart from `undetermined` (a premise unrecorded / nothing tested) and `refuted` (his vocabulary);
# `safe-under-scenario` claims are written by firmwarefaults' runner with checker `sim` (tier 0: a witness, never a proof)
PROOF_STATUSES = ('conjectured', 'witnessed', 'checked-symbolically', 'decided', 'proved', 'refuted', 'undetermined', 'unprovable-here', 'inapplicable')
CLAIM_KINDS = ('identity', 'inequality', 'domain-inclusion', 'composition', 'conservation', 'symmetry', 'commutation', 'bound', 'well-typed', 'safe-under-scenario')
# sc-2b: `cbmc` — firmwarefaults' FormalCheck (a bounded model check of firmware C): holds → `decided` (bounded, the bound on
# the claim's evidence tier), never `proved`; a counterexample → refuted
CHECKERS = ('numeric', 'interval', 'sympy', 'z3', 'lean', 'human', 'sim', 'cbmc')
#: sc-2: the evidence tiers a claim can carry side by side (MathClaim.evidence_tiers_json) — a tier records what IT found;
#: proof_status is the strongest honest status among them (a refutation outranks everything)
EVIDENCE_TIERS = ('sim', 'statistics', 'formal', 'static')
