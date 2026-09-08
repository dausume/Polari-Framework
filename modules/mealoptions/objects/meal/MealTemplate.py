"""
@module mealoptions.objects.meal.MealTemplate

Row class MealTemplate of the mealoptions module — one class per file (design §7), split
from meal_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MealTemplate(treeObject):
    """One meal template (decision 1): base recipes + bounds."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('chicken-bowl-dinner').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list of Recipe names composing the meal.
        recipe_names_json: str = '[]',
        # slots this template suits (JSON list of MEAL_SLOTS).
        slots_json: str = '[]',
        # nmp-11 (decision 11): the DishBase family this template
        # instantiates ('' = unclassified; the composer ranks those
        # low rather than guessing).
        dish_base: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.recipe_names_json = recipe_names_json
        self.slots_json = slots_json
        self.dish_base = dish_base
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
