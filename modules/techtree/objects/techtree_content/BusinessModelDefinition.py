"""
@module techtree.objects.techtree_content.BusinessModelDefinition

Row class BusinessModelDefinition of the techtree module — one class per file (design §7), split
from techtree_content_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class BusinessModelDefinition(treeObject):
    """One business model at an explicit scale on the ladder."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        # BUSINESS_SCALES entry.
        scale: str = 'one-person',
        # JSON list of business-logic policies the model runs on.
        policies_json: str = '[]',
        # JSON unit economics (costs, revenue, break-even).
        unit_economics_json: str = '{}',
        # Evidenced self-sustaining (the done-test gate).
        self_sustaining: bool = False,
        # JSON evidence — typically BusinessOutcome names.
        evidence_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.scale = scale
        self.policies_json = policies_json
        self.unit_economics_json = unit_economics_json
        self.self_sustaining = self_sustaining
        self.evidence_json = evidence_json
        self.notes = notes
