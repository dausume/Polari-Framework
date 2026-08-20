"""
@cross-cutting
@module nutrition.meal_basis
@tags @xc:bindings

nmp-4 — meals as data (decisions 1/2/4/5):

  MealTemplate         ONE meal as a template: a set of base recipes
                       plus allowed variations. HARD-bounded at
                       authoring: the gate (meal_analysis.
                       validate_template) computes EVERY variation's
                       rollup and REFUSES the template if any
                       nutrient spikes past the average-person
                       per-meal caps — refusal with named reasons,
                       distinct from the soft warnings on intake.
  VariationDefinition  an allowed variation: food swaps + a portion
                       scale range. A variation is valid only inside
                       the template's bounds.
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
"""

from objectTreeDecorators import treeObject, treeObjectInit

MEAL_SLOTS = ('breakfast', 'lunch', 'dinner', 'brunch', 'linner',
              'snack', 'snack-2')


class MealTemplate(treeObject):
    """One meal template (decision 1): base recipes + bounds."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('chicken-bowl-dinner').
        name: str = '',
        display_name: str = '',
        description: str = '',
        # JSON list of Recipe names composing the meal.
        recipe_names_json: str = '[]',
        # slots this template suits (JSON list of MEAL_SLOTS).
        slots_json: str = '[]',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.recipe_names_json = recipe_names_json
        self.slots_json = slots_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class VariationDefinition(treeObject):
    """One allowed variation of a template (decision 1)."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('chicken-bowl-dinner-tofu').
        name: str = '',
        template_name: str = '',
        display_name: str = '',
        # JSON list of swaps applied to the template's lines:
        # {"from_food", "to_food", "grams"?, "retention_code"?} —
        # grams defaults to the original line's; the retention code
        # NEVER carries over (the original food's R6 row would be
        # dishonest on the substitute) unless explicitly given.
        swaps_json: str = '[]',
        # allowed portion scaling of the whole meal (the slot's
        # calorie band picks the point inside this range).
        scale_min: float = 0.8,
        scale_max: float = 1.2,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.template_name = template_name
        self.display_name = display_name
        self.swaps_json = swaps_json
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


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
        self.serving_split_json = serving_split_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ── demo seeds over the nmp-3 recipes ─────────────────────
SEED_MEAL_TEMPLATES = [
    {'name': 'chicken-bowl-dinner',
     'display_name': 'Chicken rice bowl dinner',
     'description': 'The chicken-rice-bowl recipe as a dinner meal.',
     'recipe_names_json': '["chicken-rice-bowl"]',
     'slots_json': '["dinner", "lunch", "linner"]',
     'is_prior': True, 'provenance_id': 'nmp-4'},
    {'name': 'omelet-breakfast', 'display_name': 'Omelet breakfast',
     'description': 'The spinach omelet as a breakfast.',
     'recipe_names_json': '["spinach-omelet"]',
     'slots_json': '["breakfast", "brunch"]',
     'is_prior': True, 'provenance_id': 'nmp-4'},
]

SEED_VARIATIONS = [
    {'name': 'chicken-bowl-dinner-base', 'display_name': 'As written',
     'template_name': 'chicken-bowl-dinner', 'swaps_json': '[]',
     'scale_min': 0.8, 'scale_max': 1.2, 'is_prior': True,
     'provenance_id': 'nmp-4'},
    # calcium-set tofu is calcium-DENSE — the gate sizes the swap
    # (120 g keeps the meal under the per-meal calcium cap at max
    # scale; the chicken's R6 code does not carry over).
    {'name': 'chicken-bowl-dinner-tofu', 'display_name': 'Tofu swap',
     'template_name': 'chicken-bowl-dinner',
     'swaps_json':
         '[{"from_food": "chicken-breast-raw", "to_food": '
         '"tofu-firm", "grams": 120}]',
     'scale_min': 0.8, 'scale_max': 1.2, 'is_prior': True,
     'provenance_id': 'nmp-4'},
    {'name': 'omelet-breakfast-base', 'display_name': 'As written',
     'template_name': 'omelet-breakfast', 'swaps_json': '[]',
     'scale_min': 0.8, 'scale_max': 1.5, 'is_prior': True,
     'provenance_id': 'nmp-4'},
]
