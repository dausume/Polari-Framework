"""
@module mathproofs.objects.mathproofs.InferenceRule

Row class InferenceRule of the mathproofs module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class InferenceRule(treeObject):
    """THE LOGIC BETWEEN PARTS OF A TENSORTREE, AS DATA (plan §I.3): a rule that matches a structure in a tree (two
    mappings sharing a node; a mapping of a kind; a node's dims) and DEMANDS a claim about it (a ProofObligation).
    Seeded rules: chain-domain-inclusion, dims-compose, units-compose, evidence-monotone, restriction-idempotent,
    decomposition-reconstructs, operator-linear, operator-symmetry. A rule names the checker that discharges it; its
    knobs live in `params_json` (a policy a person edits — the decomposition bound is one), read by the template by ref."""

    plain_words = ('An inference rule is a piece of logic written as data: whenever the tree has a certain shape (for example '
                   'two mappings in a chain), the rule says what must be true for that shape to be sound, and generates the '
                   'claim to check.')

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        pattern: str = '',
        obligation_kind: str = '',
        checker_default: str = 'numeric',
        template_json: str = '{}',
        params_json: str = '{}',
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
        self.params_json = params_json  # the rule's KNOBS (e.g. {"bound": 0.05}); a template reads them by ref (InferenceRule:<name>.params_json.<key>) so a changed knob makes the runs stale, never a silent re-verdict
        self.rationale = rationale  # why the tree needs this
        self.enabled = enabled
        self.notes = notes
