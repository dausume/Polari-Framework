"""
@module mealoptions.objects.meal.VariationDefinition

Row class VariationDefinition of the mealoptions module — one class per file (design §7), split
from meal_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class VariationDefinition(treeObject):
    """One allowed variation of a template (decision 1)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('chicken-bowl-dinner-tofu').
        name: str = '',
        template_name: str = '',
        display_name: str = '',
        # JSON list of swaps applied to the template's lines:
        # {"from_food", "to_food", "grams"?, "retention_code"?} —
        # grams defaults to the original line's; the retention code
        # NEVER carries over (the original food's R6 row would be
        # dishonest on the substitute) unless explicitly given.
        swaps_json: str = '[]',
        # allowed portion scaling of the whole meal (the slot's
        # calorie band picks the point inside this range).
        scale_min: float = 0.8,
        scale_max: float = 1.2,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.template_name = template_name
        self.display_name = display_name
        self.swaps_json = swaps_json
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
