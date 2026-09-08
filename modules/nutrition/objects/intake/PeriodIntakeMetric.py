"""
@module nutrition.objects.intake.PeriodIntakeMetric

Row class PeriodIntakeMetric of the nutrition module — one class per file (design §7), split
from intake_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
        # N6: mean total sugars over the bucket's days WITH sugars
        # data, and which basis the "sweets" readout used
        # ('sugars-total' | 'gl+carbohydrate'). Added 2026-09-03 with
        # defaults — same seed_upsert field-addition caveat as above.
        sugars_g_mean: float = 0.0,
        sweets_basis: str = '',
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
        self.sugars_g_mean = sugars_g_mean
        self.sweets_basis = sweets_basis
        self.max_meal_gl_mean = max_meal_gl_mean
        self.max_meal_acid_share_mean = max_meal_acid_share_mean
        self.weight_kg_mean = weight_kg_mean
        self.weight_kg_delta = weight_kg_delta
        self.verdicts_json = verdicts_json
        self.low_confidence = low_confidence
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
