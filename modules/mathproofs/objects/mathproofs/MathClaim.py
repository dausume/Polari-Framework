"""
@module mathproofs.objects.mathproofs.MathClaim

Row class MathClaim of the mathproofs module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MathClaim(treeObject):
    """A MATHEMATICAL STATEMENT ABOUT ROWS (plan §I.3): what a mapping preserves, whether domains compose along a chain,
    whether two readings agree. The statement is the JSON term language (§I.4) — one spec, lowered by every checker
    tier; LaTeX is derived for people. `proof_status` says WHICH tier established it (a tier-0 witness is never
    called a proof); a refuted claim keeps its counterexample and never deletes the row it speaks of. Proofs never
    change a mapping's `mapping_status` / `evidence_level` (D-pf-8)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        kind: str = 'identity',
        about_refs_json: str = '[]',
        statement_json: str = '{}',
        statement_latex: str = '',
        assumptions_json: str = '[]',
        scope_json: str = '{}',
        proof_status: str = 'conjectured',
        checker: str = '',
        certificate_ref: str = '',
        counterexample_json: str = '{}',
        evidence_level: str = 'none',
        statement_hash: str = '',
        budget_s: float = 10.0,
        provenance: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.kind = kind  # identity | inequality | domain-inclusion | composition | conservation | symmetry | commutation | bound | well-typed
        self.about_refs_json = about_refs_json  # JSON ["<Class>:<name>", …] — the rows this claim speaks of
        self.statement_json = statement_json  # the term (plan §I.4)
        self.statement_latex = statement_latex  # derived from the term, for people
        self.assumptions_json = assumptions_json  # JSON [MathClaim names or plain hypotheses]
        self.scope_json = scope_json  # the validity domain claimed over ({dim: [lo, hi]})
        self.proof_status = proof_status  # conjectured | witnessed | checked-symbolically | decided | proved | refuted | unprovable-here
        self.checker = checker  # numeric | interval | sympy | z3 | lean | human — the tier that set proof_status
        self.certificate_ref = certificate_ref  # a ProofRun name, a .lean path + sha, a signed note
        self.counterexample_json = counterexample_json  # the point that breaks it, when refuted
        self.evidence_level = evidence_level  # analytical for a proof/decision; measured for a witness on data
        self.statement_hash = statement_hash  # sha256 of the canonical term — the bridge to a .lean certificate
        self.budget_s = budget_s  # D-pf-9: the checker time budget (z3/lean); a timeout is `undecided (budget)`, never refuted
        self.provenance = provenance
        self.notes = notes
