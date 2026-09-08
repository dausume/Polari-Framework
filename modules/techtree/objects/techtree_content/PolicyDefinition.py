"""
@module techtree.objects.techtree_content.PolicyDefinition

Row class PolicyDefinition of the techtree module — one class per file (design §7), split
from techtree_content_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class PolicyDefinition(treeObject):
    """Policy that moves a business model's odds of success."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # The policy itself, stated plainly.
        policy: str = '',
        # POLICY_EFFECTS entry — which way it moves the odds.
        effect: str = 'increase',
        # BusinessModelDefinition.name it targets ('' = general).
        target_business_model: str = '',
        # JSON evidence of the effect (examples, outcomes).
        evidence_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.policy = policy
        self.effect = effect
        self.target_business_model = target_business_model
        self.evidence_json = evidence_json
        self.notes = notes
