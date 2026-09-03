"""
@cross-cutting
@module nutrition.meal_basis
@tags @xc:bindings

nmp-4 — meals as data (decisions 1/2/4/5). mo-1
(MEAL_OPTIONS_MODULE_PLAN.md) MOVED the shareable half —
MealTemplate, VariationDefinition, MEAL_SLOTS and their seeds — to
mealoptions.meal_basis with names unchanged; this module RE-EXPORTS
them so every `from nutrition.meal_basis import X` keeps working,
and KEEPS the person-side half:

  MealPlanDefinition   a person's/household's plan over N days.
  MealEntry            pattern-consistent slot x template x chosen
                       variation x scale, on one day of the plan.

Slots (decision 5): breakfast, lunch, dinner, brunch, linner, snack
(+ snack-2 for the 5-slot pattern). Days are 1-based indexes — the
calendar mapping is presentation, not data.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.meal_analysis
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-4
@see AI-Notes/plans/MEAL_OPTIONS_MODULE_PLAN.md §mo-1
"""

from objectTreeDecorators import treeObject, treeObjectInit
# mo-1: the shareable meal data — re-exported (names unchanged).
from mealoptions.meal_basis import (  # noqa: F401
    MEAL_SLOTS, MealTemplate, VariationDefinition,
    SEED_MEAL_TEMPLATES, SEED_VARIATIONS,
)


class MealPlanDefinition(treeObject):
    """A plan: person or household x N days of MealEntries."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('alex-week-1').
        name: str = '',
        display_name: str = '',
        # exactly one of these names the owner.
        person_name: str = '',
        household_name: str = '',
        days: int = 7,
        # presentation anchor ('' = unanchored day indexes).
        start_date: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.person_name = person_name
        self.household_name = household_name
        self.days = days
        self.start_date = start_date
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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


# mpa-5: a demo PLAN so the app pages (cost / availability /
# shopping / prep) render end-to-end out of the box — a knob row,
# replace with real weeks.
SEED_MEAL_PLANS = [
    {'name': 'demo-alex-week', 'display_name': "Alex's demo week",
     'person_name': 'demo-alex', 'household_name': 'demo-household',
     'days': 3, 'start_date': '2026-09-01', 'is_prior': True,
     'provenance_id': 'mpa-5',
     'notes': 'demo plan — replace with a real week'},
]

SEED_MEAL_ENTRIES = [
    {'name': f'demo-alex-week-d{d}-{slot}',
     'plan_name': 'demo-alex-week', 'day_index': d, 'slot': slot,
     'template_name': t, 'variation_name': v, 'scale': 1.0,
     'time_hhmm': '', 'serving_split_json': '', 'is_prior': True,
     'provenance_id': 'mpa-5', 'notes': ''}
    for d, slot, t, v in (
        (1, 'breakfast', 'omelet-breakfast', 'omelet-breakfast-base'),
        (1, 'dinner', 'chicken-bowl-dinner',
         'chicken-bowl-dinner-base'),
        (2, 'breakfast', 'omelet-breakfast', 'omelet-breakfast-base'),
        (2, 'dinner', 'chicken-bowl-dinner',
         'chicken-bowl-dinner-tofu'),
        (3, 'dinner', 'chicken-bowl-dinner',
         'chicken-bowl-dinner-base'),
    )
]
