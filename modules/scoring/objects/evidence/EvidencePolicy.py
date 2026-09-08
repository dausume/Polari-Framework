"""
@module scoring.objects.evidence.EvidencePolicy

Row class EvidencePolicy of the scoring module — one class per file (design §7), split
from evidence_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class EvidencePolicy(treeObject):
    """Editable grade → weight vocabulary (what counts as proof)."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        display_name: str = '',
        description: str = '',
        # Ordered JSON list of {'grade', 'weight'} (0-1). The
        # 'unevidenced' entry is the weight of citing nothing.
        grade_weights_json: str = '[]',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.grade_weights_json = grade_weights_json
        self.notes = notes
