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

#: nmp-1 (decision 4): eating patterns are the PERSON'S choice.
EATING_PATTERNS = ('2-meal', '3-meal', '3-small-2-snacks')

#: nmp-1 (decision 3 + nmp-0 DRI rows): the single person-axis beyond
#: age/sex. '' = general; the DRI table carries transcribed
#: pregnancy/lactation rows (this replaces the old x1.3 multiplier
#: when set — the bool field stays as a legacy hint).
LIFE_STAGES = ('', 'pregnancy', 'lactation')


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
        # nmp-1 (decision 4): EATING_PATTERNS entry — how the day's
        # calories are meant to be split into meals.
        eating_pattern: str = '3-meal',
        # nmp-1 (decision 6): activity ASKED as minutes of exercise
        # per week, in felt terms — vigorous = exertion that leaves
        # you out of breath; moderate = brisk but you can hold a
        # conversation (WHO/DGA 150-300 moderate ≍ 75-150 vigorous).
        # When either is > 0, the calorie math uses these instead of
        # the abstract activity_level PAL guess (labeled which).
        weekly_moderate_minutes: float = 0.0,
        weekly_vigorous_minutes: float = 0.0,
        # nmp-1: LIFE_STAGES entry — picks the transcribed DRI
        # pregnancy/lactation rows when set.
        life_stage: str = '',
        # nmp-1: optional waist circumference (cm), a screening knob
        # for the obesity classification (0 = not measured).
        waist_cm: float = 0.0,
        # nmp-10 (decision 12): stated cooking skill — drives the
        # method duration models; refined from observed durations
        # later (labeled which).
        cooking_skill: str = 'intermediate',
        # nmp-11 (decision 11): the cuisine/cultural context that
        # RANKS suggestions — a stated knob, NEVER inferred.
        cuisine_context: str = 'general-western',
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
        self.eating_pattern = eating_pattern
        self.weekly_moderate_minutes = weekly_moderate_minutes
        self.weekly_vigorous_minutes = weekly_vigorous_minutes
        self.life_stage = life_stage
        self.waist_cm = waist_cm
        self.cooking_skill = cooking_skill
        self.cuisine_context = cuisine_context
        self.provenance_id = provenance_id
        self.notes = notes
