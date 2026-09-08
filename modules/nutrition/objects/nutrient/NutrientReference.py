"""
@module nutrition.objects.nutrient.NutrientReference

Row class NutrientReference of the nutrition module — one class per file (design §7), split
from nutrient_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class NutrientReference(treeObject):
    """The RDA/AI for one nutrient over a demographic band.

    The person profiler matches the row whose (sex, age_min..age_max)
    contains the person, then scales by period. `rda_per_day` is the
    target; `upper_limit_per_day` is the toxicity ceiling (0 = none
    established). `is_prior` flags an AI/estimate vs a firm RDA."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('vitamin-c-female-19-50').
        name: str = '',
        # The DietaryNutrient this bounds (by name).
        nutrient_name: str = '',
        # 'any' | 'male' | 'female'.
        sex: str = 'any',
        age_min: float = 19.0,
        age_max: float = 120.0,
        # Recommended intake per day (in the nutrient's unit).
        rda_per_day: float = 0.0,
        # Tolerable upper intake per day (0 = none established).
        upper_limit_per_day: float = 0.0,
        # For nutrients that scale with body mass (e.g. protein), the
        # per-kg basis the profiler prefers over the flat RDA (0 = use
        # the flat rda_per_day).
        per_kg_body_mass: float = 0.0,
        # nmp-0: Estimated Average Requirement per day (0 = none
        # published — AI-based nutrients have no EAR by definition).
        ear_per_day: float = 0.0,
        # nmp-0: what rda_per_day actually IS for this row — a firm
        # 'rda', an Adequate Intake 'ai', or 'none' (marker rows).
        value_type: str = 'rda',
        # nmp-0: '' = general band; 'pregnancy' | 'lactation' rows
        # replace the nut-3 x1.3 multiplier with transcribed values.
        life_stage: str = '',
        # nmp-0: whose tables these are (DRI values differ by body —
        # EFSA's DRVs are not NASEM's DRIs).
        jurisdiction: str = 'US-NASEM',
        # nmp-0: which edition/table release the value was transcribed
        # from — DRI values change when reports are revised.
        edition: str = '',
        source: str = 'NIH DRI',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.nutrient_name = nutrient_name
        self.sex = sex
        self.age_min = age_min
        self.age_max = age_max
        self.rda_per_day = rda_per_day
        self.upper_limit_per_day = upper_limit_per_day
        self.per_kg_body_mass = per_kg_body_mass
        self.ear_per_day = ear_per_day
        self.value_type = value_type
        self.life_stage = life_stage
        self.jurisdiction = jurisdiction
        self.edition = edition
        self.source = source
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
