"""
@module mathproofs.objects.mathproofs.InferenceRule

Row class InferenceRule of the mathproofs module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class InferenceRule(treeObject):
    """THE LOGIC BETWEEN PARTS OF A TENSORTREE, AS DATA (plan §I.3): a rule that matches a structure in a tree (two
    mappings sharing a node; a mapping of a kind; a node's dims) and DEMANDS a claim about it (a ProofObligation).
    Seeded rules: chain-domain-inclusion, dims-compose, units-compose, evidence-monotone, restriction-idempotent,
    decomposition-reconstructs, operator-linear, operator-symmetry. A rule names the checker that discharges it."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        pattern: str = '',
        obligation_kind: str = '',
        checker_default: str = 'numeric',
        template_json: str = '{}',
        rationale: str = '',
        enabled: bool = True,
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.pattern = pattern  # chain | mapping:<kind> | node | tree — what structure the rule matches (custom/rules.py knows each)
        self.obligation_kind = obligation_kind  # the MathClaim.kind it emits
        self.checker_default = checker_default  # the tier expected to discharge it
        self.template_json = template_json  # the term template with {m1}, {m2}, {node} placeholders
        self.rationale = rationale  # why the tree needs this
        self.enabled = enabled
        self.notes = notes
