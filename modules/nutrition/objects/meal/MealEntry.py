"""
@module nutrition.objects.meal.MealEntry

Row class MealEntry of the nutrition module — one class per file (design §7), split
from meal_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MealEntry(treeObject):
    """One planned meal: day x slot x template x variation x scale."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-week-1-d1-dinner').
        name: str = '',
        plan_name: str = '',
        day_index: int = 1,
        # MEAL_SLOTS entry — pattern consistency is checked against
        # the plan owner's eating pattern (a warning, not a block).
        slot: str = 'dinner',
        template_name: str = '',
        # '' = the base template unvaried.
        variation_name: str = '',
        # portion scale actually chosen (clamped into the
        # variation's range by the analysis, reported when clamped).
        scale: float = 1.0,
        # nmp-5b (decision 14): first-class meal time ('' = untimed;
        # the day timeline interleaves meals and exercise by clock).
        time_hhmm: str = '',
        # household plans: this entry's serving split among members,
        # JSON {member_name: fraction}; '' = the plan owner eats it.
        serving_split_json: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.plan_name = plan_name
        self.day_index = day_index
        self.slot = slot
        self.template_name = template_name
        self.variation_name = variation_name
        self.scale = scale
        self.time_hhmm = time_hhmm
        self.serving_split_json = serving_split_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
