"""
@module mealoptions.objects.recipe.IngredientLine

Row class IngredientLine of the mealoptions module — one class per file (design §7), split
from recipe_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class IngredientLine(treeObject):
    """One (recipe, food, amount) line with its cooking transform."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('chicken-rice-bowl-chicken').
        name: str = '',
        recipe_name: str = '',
        # a FoodItem name — whole foods only (decision 8).
        food_name: str = '',
        grams: float = 0.0,
        # COOKING_METHODS entry for THIS line (a salad's chicken is
        # grilled while its greens stay raw).
        method: str = 'raw',
        # mass yield % after cooking (100 = unchanged). 0 = ask the
        # engine to suggest one (meat/poultry yields table); the
        # applied value is always reported.
        yield_percent: float = 100.0,
        # R6 retention code applied to vitamins/minerals ('' = none;
        # retention_lookup suggests candidates from the method).
        retention_code: str = '',
        prep_note: str = '',
        order: int = 0,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.recipe_name = recipe_name
        self.food_name = food_name
        self.grams = grams
        self.method = method
        self.yield_percent = yield_percent
        self.retention_code = retention_code
        self.prep_note = prep_note
        self.order = order
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
