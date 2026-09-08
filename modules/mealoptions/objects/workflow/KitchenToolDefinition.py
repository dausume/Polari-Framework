"""
@module mealoptions.objects.workflow.KitchenToolDefinition

Row class KitchenToolDefinition of the mealoptions module — one class per file (design §7), split
from workflow_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class KitchenToolDefinition(treeObject):
    """One tool the vocabulary knows (seeded or user-declared)."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 category: str = 'hand-tool',
                 provenance: str = 'seeded',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.category = category
        self.provenance = provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
