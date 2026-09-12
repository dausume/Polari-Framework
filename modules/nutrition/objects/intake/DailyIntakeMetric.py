"""
@module nutrition.objects.intake.DailyIntakeMetric

Row class DailyIntakeMetric of the nutrition module — one class per file (design §7), split
from intake_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
        # N6: total sugars (FDC 269) summed over the ingredients that
        # carry a row; sugars_basis says whether ANY did ('fdc-269')
        # or the day has no sugars data ('' — then sugars_g 0.0 is an
        # absence, not a zero). Added 2026-09-03 with a default — an
        # existing DB needs the field-addition path in
        # moduleService.seed_upsert (schema change, see the seed gotcha).
        sugars_g: float = 0.0,
        sugars_basis: str = '',
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
        self.sugars_g = sugars_g
        self.sugars_basis = sugars_basis
        self.max_meal_gl = max_meal_gl
        self.max_meal_acid_share = max_meal_acid_share
        self.meals_logged = meals_logged
        self.day_warning_count = day_warning_count
        self.computed_from = computed_from
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
