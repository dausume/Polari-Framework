"""
@module techtree.objects.techtree_content.BusinessOutcome

Row class BusinessOutcome of the techtree module — one class per file (design §7), split
from techtree_content_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BusinessOutcome(treeObject):
    """How one business model actually worked out — evidence."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # BusinessModelDefinition.name this outcome evidences.
        business_model: str = '',
        summary: str = '',
        # 'succeeded' | 'failed' | 'mixed' — honesty over polish.
        outcome: str = 'mixed',
        evidence_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.business_model = business_model
        self.summary = summary
        self.outcome = outcome
        self.evidence_json = evidence_json
        self.notes = notes
