"""
@module mealoptions.objects.recipe.CookingStep

Row class CookingStep of the mealoptions module — one class per file (design §7), split
from recipe_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CookingStep(treeObject):
    """One ordered instruction in a recipe."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('chicken-rice-bowl-step-1').
        name: str = '',
        recipe_name: str = '',
        order: int = 0,
        instruction: str = '',
        # COOKING_METHODS entry ('raw' for prep-only steps).
        method: str = 'raw',
        duration_min: float = 0.0,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.recipe_name = recipe_name
        self.order = order
        self.instruction = instruction
        self.method = method
        self.duration_min = duration_min
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
