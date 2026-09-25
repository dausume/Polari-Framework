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

#: every row class of the module, in registration order (the selftest asserts the count)
MATHPROOFS_CLASSES = [MathClaim, ProofRun, InferenceRule, ProofObligation]
PROOF_STATUSES = ('conjectured', 'witnessed', 'checked-symbolically', 'decided', 'proved', 'refuted', 'unprovable-here')
CLAIM_KINDS = ('identity', 'inequality', 'domain-inclusion', 'composition', 'conservation', 'symmetry', 'commutation', 'bound', 'well-typed')
CHECKERS = ('numeric', 'interval', 'sympy', 'z3', 'lean', 'human')
