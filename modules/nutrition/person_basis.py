"""
@cross-cutting
@module nutrition.person_basis
@tags @xc:bindings

nut-3 — PersonProfile: body metrics + weight goal + the metabolism /
life-stage factors the user "may not know", surfaced as EXPLICIT tunable
knobs (knobs-and-suggestions — never hidden, honest defaults). The math
(BMR/TDEE/calorie target/per-nutrient needs) lives in person_analysis.py.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.person_analysis, nutrition.household_analysis
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-3
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Physical Activity Level multipliers on BMR -> TDEE.
ACTIVITY_LEVELS = ('sedentary', 'light', 'moderate', 'active',
                   'very-active')
ACTIVITY_PAL = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55,
                'active': 1.725, 'very-active': 1.9}

WEIGHT_GOALS = ('maintain', 'lose', 'gain')


class PersonProfile(treeObject):
    """One household member's nutritional profile."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('alex').
        name: str = '',
        display_name: str = '',
        # 'male' | 'female' (drives sex-specific RDA rows; 'any' allowed
        # when unknown).
        sex: str = 'any',
        age_years: float = 30.0,
        weight_kg: float = 70.0,
        height_cm: float = 170.0,
        # ACTIVITY_LEVELS entry.
        activity_level: str = 'moderate',
        # WEIGHT_GOALS entry.
        goal: str = 'maintain',
        # Target weight-change pace (kg/week) for lose/gain — sets the
        # calorie deficit/surplus. A knob; clamped to a safe floor.
        goal_rate_kg_per_week: float = 0.5,
        # FACTORS THE USER MAY NOT KNOW — explicit knobs, honest
        # defaults (1.0 = neutral). metabolism_factor scales BMR for
        # thyroid/genetic variation; the user tunes it when known.
        metabolism_factor: float = 1.0,
        # Optional body-fat fraction (0-1); when set, enables the more
        # accurate Katch-McArdle BMR (recommended via a suggestion).
        body_fat_fraction: float = 0.0,
        # Life-stage that raises several nutrient needs.
        pregnant_or_lactating: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.sex = sex
        self.age_years = age_years
        self.weight_kg = weight_kg
        self.height_cm = height_cm
        self.activity_level = activity_level
        self.goal = goal
        self.goal_rate_kg_per_week = goal_rate_kg_per_week
        self.metabolism_factor = metabolism_factor
        self.body_fat_fraction = body_fat_fraction
        self.pregnant_or_lactating = pregnant_or_lactating
        self.provenance_id = provenance_id
        self.notes = notes
