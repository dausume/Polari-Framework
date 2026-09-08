"""
@module nutrition.objects.rating.MealRating

Row class MealRating of the nutrition module — one class per file (design §7), split
from rating_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class MealRating(treeObject):
    """One person's rating of one eaten meal."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-chicken-bowl-2026-09-01').
        name: str = '',
        person_name: str = '',
        template_name: str = '',
        variation_name: str = '',
        # 1 (never again) … 5 (favorite).
        rating: int = 0,
        # their words ('too salty', 'kids loved it').
        note: str = '',
        # ISO date rated.
        date: str = '',
        # the IntakeRecord this rates ('' = general rating).
        intake_record_name: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.template_name = template_name
        self.variation_name = variation_name
        self.rating = rating
        self.note = note
        self.date = date
        self.intake_record_name = intake_record_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
