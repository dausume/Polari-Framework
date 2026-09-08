"""
@module mealoptions.objects.workflow.StorageActionDefinition

Row class StorageActionDefinition of the mealoptions module — one class per file (design §7), split
from workflow_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class StorageActionDefinition(treeObject):
    """freeze/refrigerate/thaw/reheat with FSIS safety windows."""

    @treeObjectInit
    def __init__(self, name: str = '', display_name: str = '',
                 # state transition per the step contract.
                 input_state: str = 'cooked',
                 output_state: str = 'refrigerated',
                 # the FSIS window this action must respect (days the
                 # resulting state stays SAFE; 0 = not a hold state).
                 safety_window_days: float = 0.0,
                 # quality window (freezer months etc.) — noted, not
                 # a safety bound.
                 quality_window_days: float = 0.0,
                 duration_min: float = 0.0,
                 citation: str = 'USDA FSIS cold storage charts '
                                 '(public domain)',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.display_name = display_name
        self.input_state = input_state
        self.output_state = output_state
        self.safety_window_days = safety_window_days
        self.quality_window_days = quality_window_days
        self.duration_min = duration_min
        self.citation = citation
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
