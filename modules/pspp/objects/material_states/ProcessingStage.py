"""
@module pspp.objects.material_states.ProcessingStage

Row class ProcessingStage of the pspp module — one class per file (design §7), split
from material_states_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class ProcessingStage(treeObject):
    """One processing-stage concept — extensible rows, NOT an enum, so
    each material family names its own route stages."""

    @treeObjectInit
    def __init__(
        self,
        # Kebab-case key ('activated-slurry').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # The family that coined it ('geopolymer', 'wax', 'general') —
        # navigation only, any material may use any stage.
        material_family: str = 'general',
        # Typical predecessor stage ('' = route start) — a HINT for
        # pages, never a constraint (routes are data, pspp-4).
        typical_prior_stage: str = '',
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.material_family = material_family
        self.typical_prior_stage = typical_prior_stage
        self.provenance_id = provenance_id
        self.notes = notes
