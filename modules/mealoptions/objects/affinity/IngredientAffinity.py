"""
@module mealoptions.objects.affinity.IngredientAffinity

Row class IngredientAffinity of the mealoptions module — one class per file (design §7), split
from affinity_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from mealoptions.objects.affinity._shared import DEFAULT_CONTEXT

class IngredientAffinity(treeObject):
    """(role-or-food x dish base x context) -> a norm weight 0..1."""

    @treeObjectInit
    def __init__(self, name: str = '',
                 # a FoodRole role name OR a FoodItem name — direct
                 # food rows outrank role rows at resolution.
                 subject: str = '',
                 dish_base: str = '',
                 context: str = DEFAULT_CONTEXT,
                 weight: float = 0.5,
                 source: str = 'curated norm',
                 is_prior: bool = True, provenance_id: str = '',
                 notes: str = '', manager=None):
        self.name = name
        self.subject = subject
        self.dish_base = dish_base
        self.context = context
        self.weight = weight
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
