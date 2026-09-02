"""
@cross-cutting
@module nutrition.rating_basis
@tags @xc:bindings

mpb-8 — meal ratings as data: the person's own verdict on a meal
they actually ate. Ratings feed suggestion RANKING (the nmp-11
affinity overlay's "household accept/reject history", now with a
number) — they never gate, never block, and a low rating never
deletes anything (tastes change; the history stays).

  MealRating   person × template (× variation) × 1-5 stars ×
               their words, dated. One rating per eating is the
               intent (link the IntakeRecord when there is one).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.rating_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-8
"""

from objectTreeDecorators import treeObject, treeObjectInit

_PROV = 'mpb-8 (MEAL_PLANNING_APP_PLAN §3b)'


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


#: Demo ratings so the ranking surface renders.
SEED_MEAL_RATINGS = [
    {'name': 'demo-alex-bowl-r1', 'person_name': 'demo-alex',
     'template_name': 'chicken-bowl-dinner',
     'variation_name': 'chicken-bowl-dinner-base', 'rating': 4,
     'note': 'demo — solid weeknight dinner', 'date': '2026-08-31',
     'intake_record_name': 'demo-alex-2026-08-31-dinner',
     'is_prior': True, 'provenance_id': _PROV, 'notes': ''},
    {'name': 'demo-alex-omelet-r1', 'person_name': 'demo-alex',
     'template_name': 'omelet-breakfast',
     'variation_name': 'omelet-breakfast-base', 'rating': 5,
     'note': 'demo — favorite breakfast', 'date': '2026-09-01',
     'intake_record_name': 'demo-alex-2026-09-01-breakfast',
     'is_prior': True, 'provenance_id': _PROV, 'notes': ''},
]
