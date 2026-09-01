"""
@cross-cutting
@module nutrition.intake_basis
@tags @xc:bindings

mpa-4 — what was actually EATEN, over time:

  IntakeRecord   one eaten meal: person × date × slot × template ×
                 variation × scale. A plan is an intention; this is
                 the fact — the tracking series (nutrition, meal
                 acidity, GL over time) roll up from THESE rows.
                 `source` keeps the honesty: 'planned-confirmed'
                 (ate as planned — the A6 default gesture) vs
                 'logged' (entered directly) vs 'estimated'.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.tracking_analysis, mealplanning_api
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-4
"""

from objectTreeDecorators import treeObject, treeObjectInit

INTAKE_SOURCES = ('planned-confirmed', 'logged', 'estimated')

_PROV = 'mpa-4 (MEAL_PLANNING_APP_PLAN.md)'


class IntakeRecord(treeObject):
    """One eaten meal (a fact, never an intention)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-2026-09-01-dinner').
        name: str = '',
        person_name: str = '',
        # ISO date eaten.
        date: str = '',
        # MEAL_SLOTS entry.
        slot: str = 'dinner',
        template_name: str = '',
        variation_name: str = '',
        scale: float = 1.0,
        # clock time ('' = untimed; timing evaluations skip it).
        time_hhmm: str = '',
        # INTAKE_SOURCES entry.
        source: str = 'logged',
        # the MealEntry this confirms ('' = ad-hoc meal).
        plan_entry_name: str = '',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.date = date
        self.slot = slot
        self.template_name = template_name
        self.variation_name = variation_name
        self.scale = scale
        self.time_hhmm = time_hhmm
        self.source = source
        self.plan_entry_name = plan_entry_name
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


def _ir(name, date, slot, template, variation, note=''):
    return {'name': name, 'person_name': 'demo-alex', 'date': date,
            'slot': slot, 'template_name': template,
            'variation_name': variation, 'scale': 1.0,
            'time_hhmm': '', 'source': 'logged',
            'plan_entry_name': '', 'is_prior': True,
            'provenance_id': _PROV,
            'notes': note or 'demo intake — replace with real logs'}


#: Two demo days so the trends page renders series immediately.
SEED_INTAKE_RECORDS = [
    _ir('demo-alex-2026-08-31-breakfast', '2026-08-31', 'breakfast',
        'omelet-breakfast', 'omelet-breakfast-base'),
    _ir('demo-alex-2026-08-31-dinner', '2026-08-31', 'dinner',
        'chicken-bowl-dinner', 'chicken-bowl-dinner-base'),
    _ir('demo-alex-2026-09-01-breakfast', '2026-09-01', 'breakfast',
        'omelet-breakfast', 'omelet-breakfast-base'),
    _ir('demo-alex-2026-09-01-dinner', '2026-09-01', 'dinner',
        'chicken-bowl-dinner', 'chicken-bowl-dinner-tofu'),
]
