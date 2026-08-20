"""
@cross-cutting
@module nutrition.recipe_basis
@tags @xc:bindings

nmp-3 — recipes as data: Recipe (serves N), IngredientLine (a
FoodItem, an amount, its cooking transform), CookingStep (ordered
instructions with a method + duration). The nutrition ROLLUP
(recipe_analysis) is the build-ourselves engine: per-ingredient
FDC per-100g x amount x YIELD factor x per-nutrient RETENTION
factor, summed to per-serving RecipeNutrition with raw-vs-cooked
provenance labels.

Decision 8 rides here: ingredient lines reference whole FoodItems
(base ingredients + meats) — no packaged products. Q3 (Dustin
default): recipes are hand-authored first; the recipe-scrapers URL
import lands later (the dausume fork-pin already exists).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - nutrition.recipe_analysis, nmp-4 meal templates
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-3
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: Cooking methods a line/step can claim — each maps to R6 retention
#: rows (retention_lookup) and drives the nutrition transform.
#: 'raw' = no transform.
COOKING_METHODS = ('raw', 'boiled', 'steamed', 'baked', 'roasted',
                   'fried', 'sauteed', 'grilled', 'braised',
                   'simmered', 'microwaved')


class Recipe(treeObject):
    """One dish, made of IngredientLines + CookingSteps."""

    @treeObjectInit
    def __init__(
        self,
        # kebab-case unique key ('chicken-rice-bowl').
        name: str = '',
        display_name: str = '',
        description: str = '',
        servings: float = 1.0,
        # free-text author provenance ('hand-authored', 'imported').
        origin: str = 'hand-authored',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.servings = servings
        self.origin = origin
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class IngredientLine(treeObject):
    """One (recipe, food, amount) line with its cooking transform."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('chicken-rice-bowl-chicken').
        name: str = '',
        recipe_name: str = '',
        # a FoodItem name — whole foods only (decision 8).
        food_name: str = '',
        grams: float = 0.0,
        # COOKING_METHODS entry for THIS line (a salad's chicken is
        # grilled while its greens stay raw).
        method: str = 'raw',
        # mass yield % after cooking (100 = unchanged). 0 = ask the
        # engine to suggest one (meat/poultry yields table); the
        # applied value is always reported.
        yield_percent: float = 100.0,
        # R6 retention code applied to vitamins/minerals ('' = none;
        # retention_lookup suggests candidates from the method).
        retention_code: str = '',
        prep_note: str = '',
        order: int = 0,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.recipe_name = recipe_name
        self.food_name = food_name
        self.grams = grams
        self.method = method
        self.yield_percent = yield_percent
        self.retention_code = retention_code
        self.prep_note = prep_note
        self.order = order
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class CookingStep(treeObject):
    """One ordered instruction in a recipe."""

    @treeObjectInit
    def __init__(
        self,
        # unique key ('chicken-rice-bowl-step-1').
        name: str = '',
        recipe_name: str = '',
        order: int = 0,
        instruction: str = '',
        # COOKING_METHODS entry ('raw' for prep-only steps).
        method: str = 'raw',
        duration_min: float = 0.0,
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.recipe_name = recipe_name
        self.order = order
        self.instruction = instruction
        self.method = method
        self.duration_min = duration_min
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


# ── demo seeds (pantry foods only — decision 8 holds) ─────
def _line(recipe, food, grams, method='raw', yield_pct=100.0,
          retention='', order=0, prep=''):
    return {'name': f'{recipe}-{food}', 'recipe_name': recipe,
            'food_name': food, 'grams': grams, 'method': method,
            'yield_percent': yield_pct, 'retention_code': retention,
            'prep_note': prep, 'order': order, 'is_prior': True,
            'provenance_id': 'nmp-3'}


SEED_RECIPES = [
    {'name': 'chicken-rice-bowl', 'display_name': 'Chicken rice bowl',
     'description': 'Grilled chicken over rice with steamed broccoli.',
     'servings': 2.0, 'origin': 'hand-authored', 'is_prior': True,
     'provenance_id': 'nmp-3',
     'notes': 'demo recipe over the FDC starter pantry'},
    {'name': 'spinach-omelet', 'display_name': 'Spinach omelet',
     'description': 'Two-egg omelet with baby spinach in olive oil.',
     'servings': 1.0, 'origin': 'hand-authored', 'is_prior': True,
     'provenance_id': 'nmp-3',
     'notes': 'demo recipe over the FDC starter pantry'},
]

SEED_INGREDIENT_LINES = [
    # chicken-rice-bowl (2 servings)
    _line('chicken-rice-bowl', 'chicken-breast-raw', 300.0,
          method='grilled', yield_pct=70.0, retention='0801',
          order=1, prep='grilled, sliced'),
    _line('chicken-rice-bowl', 'rice-white-raw', 55.0,
          method='boiled', yield_pct=280.0, retention='0432',
          order=2, prep='dry weight; boils up ~2.8x. Portion sized '
                        'so the meal passes the decision-9 GL<=20 '
                        'gate at max scale — white rice is '
                        'high-GI, so the bowl stays rice-light'),
    _line('chicken-rice-bowl', 'broccoli-raw', 200.0,
          method='steamed', yield_pct=95.0, retention='3784',
          order=3),
    _line('chicken-rice-bowl', 'olive-oil', 15.0, order=4),
    # spinach-omelet (1 serving)
    _line('spinach-omelet', 'egg-whole-raw', 100.0,
          method='fried', yield_pct=88.0, retention='0103',
          order=1, prep='two large eggs'),
    _line('spinach-omelet', 'spinach-raw', 60.0,
          method='sauteed', yield_pct=65.0, retention='3004',
          order=2),
    _line('spinach-omelet', 'olive-oil', 10.0, order=3),
]

SEED_COOKING_STEPS = [
    {'name': 'chicken-rice-bowl-step-1',
     'recipe_name': 'chicken-rice-bowl', 'order': 1,
     'instruction': 'Boil the rice in 2:1 water until absorbed.',
     'method': 'boiled', 'duration_min': 18.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'chicken-rice-bowl-step-2',
     'recipe_name': 'chicken-rice-bowl', 'order': 2,
     'instruction': 'Grill the chicken breast until done; slice.',
     'method': 'grilled', 'duration_min': 12.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'chicken-rice-bowl-step-3',
     'recipe_name': 'chicken-rice-bowl', 'order': 3,
     'instruction': 'Steam the broccoli; assemble with the oil.',
     'method': 'steamed', 'duration_min': 6.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'spinach-omelet-step-1',
     'recipe_name': 'spinach-omelet', 'order': 1,
     'instruction': 'Saute the spinach in half the oil; set aside.',
     'method': 'sauteed', 'duration_min': 3.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
    {'name': 'spinach-omelet-step-2',
     'recipe_name': 'spinach-omelet', 'order': 2,
     'instruction': 'Beat the eggs, fry, fold the spinach in.',
     'method': 'fried', 'duration_min': 5.0,
     'is_prior': True, 'provenance_id': 'nmp-3'},
]
