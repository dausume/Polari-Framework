"""
@module mealoptions.objects.workflow.CookingTaskDefinition

Row class CookingTaskDefinition of the mealoptions module — one class per file (design §7), split
from workflow_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CookingTaskDefinition(treeObject):
    """A task KIND — WHAT, not HOW (the step contract)."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 # the uniform contract: what comes in / goes out
                 # (state words: raw, prepped, cooked, cooled,
                 # portioned, frozen, thawed, reheated).
                 input_state: str = 'raw',
                 output_state: str = 'prepped',
                 # equipment slot the task occupies while running
                 # ('' = hands only) — the overlap constraint.
                 equipment_slot: str = '',
                 provenance: str = 'seeded',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.input_state = input_state
        self.output_state = output_state
        self.equipment_slot = equipment_slot
        self.provenance = provenance
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
