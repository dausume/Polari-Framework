"""
@module mathproofs.objects.mathproofs.ProofObligation

Row class ProofObligation of the mathproofs module — one class per file. The class docstring is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ProofObligation(treeObject):
    """A CLAIM THE RULES DEMANDED for a specific structure of a tree (a chain of two mappings, a mapping, a node).
    `discharged_by` names the MathClaim that answers it; `status` mirrors that claim's proof_status or `open`.
    Discovery REFUSES a candidate whose obligation is refuted (with the counterexample) and SHOWS an open one
    (D-pf-3)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        tree: str = '',
        rule: str = '',
        structure_json: str = '{}',
        about_refs_json: str = '[]',
        discharged_by: str = '',
        status: str = 'open',
        generated_at: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.tree = tree  # TensorTreeDefinition.name
        self.rule = rule  # InferenceRule.name
        self.structure_json = structure_json  # {"chain": [m1, m2], "node": n} — what matched
        self.about_refs_json = about_refs_json
        self.discharged_by = discharged_by  # MathClaim.name
        self.status = status  # open | witnessed | checked-symbolically | decided | proved | refuted | undetermined | unprovable-here | stale
        self.generated_at = generated_at
        self.notes = notes
