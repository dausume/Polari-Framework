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


class DailyIntakeMetric(treeObject):
    """One person-day's derived metrics — a DERIVE-ON-DEMAND CACHE
    row (the D5/level-scenes precedent), upserted when the tracking
    series is computed so class-backed charts (embeddedGraph) can
    render the day series. Never hand-edited: the IntakeRecords are
    the facts; this row is their rollup, recomputed on read."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('demo-alex-2026-09-01').
        name: str = '',
        person_name: str = '',
        date: str = '',
        calories: float = 0.0,
        protein_g: float = 0.0,
        fiber_g: float = 0.0,
        sodium_mg: float = 0.0,
        # spike metrics: the day's MAX per-meal values.
        max_meal_gl: float = 0.0,
        max_meal_acid_share: float = 0.0,
        meals_logged: int = 0,
        day_warning_count: int = 0,
        computed_from: str = 'intake-day rollup (derive-on-demand '
                             'cache — IntakeRecords are the facts)',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.date = date
        self.calories = calories
        self.protein_g = protein_g
        self.fiber_g = fiber_g
        self.sodium_mg = sodium_mg
        self.max_meal_gl = max_meal_gl
        self.max_meal_acid_share = max_meal_acid_share
        self.meals_logged = meals_logged
        self.day_warning_count = day_warning_count
        self.computed_from = computed_from
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


class PeriodIntakeMetric(treeObject):
    """mpt — the WEEK / MONTH condensation of DailyIntakeMetric, a
    derive-on-demand cache row (reading /periods refreshes it) so
    class-backed charts can show means over time. series_key =
    '<person>:<kind>' is the ONE filter an embedded graph takes."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        person_name: str = '',
        period_kind: str = 'week',
        series_key: str = '',
        period_start: str = '',
        period_end: str = '',
        days_logged: int = 0,
        days_in_period: int = 7,
        calories_mean: float = 0.0,
        protein_g_mean: float = 0.0,
        carbohydrate_g_mean: float = 0.0,
        fiber_g_mean: float = 0.0,
        sodium_mg_mean: float = 0.0,
        max_meal_gl_mean: float = 0.0,
        max_meal_acid_share_mean: float = 0.0,
        weight_kg_mean: float = 0.0,
        weight_kg_delta: float = 0.0,
        verdicts_json: str = '[]',
        low_confidence: bool = False,
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.person_name = person_name
        self.period_kind = period_kind
        self.series_key = series_key
        self.period_start = period_start
        self.period_end = period_end
        self.days_logged = days_logged
        self.days_in_period = days_in_period
        self.calories_mean = calories_mean
        self.protein_g_mean = protein_g_mean
        self.carbohydrate_g_mean = carbohydrate_g_mean
        self.fiber_g_mean = fiber_g_mean
        self.sodium_mg_mean = sodium_mg_mean
        self.max_meal_gl_mean = max_meal_gl_mean
        self.max_meal_acid_share_mean = max_meal_acid_share_mean
        self.weight_kg_mean = weight_kg_mean
        self.weight_kg_delta = weight_kg_delta
        self.verdicts_json = verdicts_json
        self.low_confidence = low_confidence
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
