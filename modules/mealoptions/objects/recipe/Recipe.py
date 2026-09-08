"""
@module mealoptions.objects.recipe.Recipe

Row class Recipe of the mealoptions module — one class per file (design §7), split
from recipe_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class Recipe(treeObject):
    """One dish, made of IngredientLines + CookingSteps."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('chicken-rice-bowl').
        name: str = '',
        display_name: str = '',
        description: str = '',
        servings: float = 1.0,
        # free-text author provenance ('hand-authored', 'imported').
        origin: str = 'hand-authored',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.servings = servings
        self.origin = origin
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
