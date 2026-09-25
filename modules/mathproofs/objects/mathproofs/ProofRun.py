"""
@module mathproofs.objects.mathproofs.ProofRun

Row class ProofRun of the mathproofs module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ProofRun(treeObject):
    """ONE EXECUTION of a checker on a claim: which tier and version, the verdict, the output tail, when, and the
    hash of the rows' state it ran against — a changed row makes the run STALE, never silently still proved.
    A budget timeout is `undecided (budget)`, never `refuted` (D-pf-9)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        claim: str = '',
        checker: str = '',
        checker_version: str = '',
        verdict: str = '',
        detail_json: str = '{}',
        output_tail: str = '',
        elapsed_s: float = 0.0,
        rows_state_hash: str = '',
        ran_at: str = '',
        ran_where: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.claim = claim  # MathClaim.name
        self.checker = checker  # numeric | interval | sympy | z3 | lean | human
        self.checker_version = checker_version
        self.verdict = verdict  # holds | refuted | undetermined (not defined here) | undecided (the z3/lean budget ran out — the claim's status is untouched, D-pf-9) | unprovable-here | error
        self.detail_json = detail_json  # what was evaluated: values, the counterexample, the simplified difference…
        self.output_tail = output_tail
        self.elapsed_s = elapsed_s
        self.rows_state_hash = rows_state_hash  # sha256 over the rows the claim names
        self.ran_at = ran_at
        self.ran_where = ran_where  # in-process | <engine placement>
        self.notes = notes
