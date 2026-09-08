"""
@module pspp.objects.evidence_methods.EvidenceMethod

Row class EvidenceMethod of the pspp module — one class per file (design §7), split
from evidence_methods_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class EvidenceMethod(treeObject):
    """One way a value can be known — with what honesty demands of it."""

    @treeObjectInit
    def __init__(
        self,
        # Identifier, kebab-case ('measured', 'rules-of-mixtures').
        name: str = '',
        # 'empirical' | 'derived' | 'derived-model' | 'judgment' | 'unknown'
        category: str = '',
        description: str = '',
        # What provenance a claim using this method MUST carry.
        required_provenance: str = '',
        # Default validation posture for claims made this way.
        default_validation_class: str = 'unvalidated',
        # Whether confidence intervals/distributions are meaningful here.
        supports_uncertainty: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.category = category
        self.description = description
        self.required_provenance = required_provenance
        self.default_validation_class = default_validation_class
        self.supports_uncertainty = supports_uncertainty
        self.provenance_id = provenance_id
        self.notes = notes
