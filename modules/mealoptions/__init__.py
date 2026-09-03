"""
@module mealoptions

The MEAL OPTIONS layer (MEAL_OPTIONS_MODULE_PLAN.md, mo-1): the
shareable meal DATA nutrition accumulated — meal templates and their
variations, recipes with ingredient lines and cooking steps, the
composition vocabulary (dish bases, ingredient roles, food roles,
affinity norms), the cooking-workflow vocabulary (tool, task-kind,
step-method and storage-action definitions, saved workflow DAGs),
the meal-situation portability vocabulary, and bulk staples (shelf
life + cadence info).

The line (plan §1): everything here is ABOUT meals; nothing here is
about a person, a household, a place or a day. Person plans and
entries, owned tools, method preferences, advisor dismissals,
source locations, price observations and the whole household layer
stay in nutrition / household. BulkStaple keeps its instance-pointer
fields (household_name, bulk_location_name, observed_date) for
schema compatibility, but every SHIPPED seed leaves them blank — the
offer's location lives on the instance.

mo-1 is a MOVE with names unchanged: live rows, TableDefinitions and
provenance_id values converge through the upsert path. `nutrition`
requires this module and re-exports the moved names from their old
homes, so every existing importer keeps working. This package
imports NOTHING from nutrition or household.
"""

from mealoptions.meal_basis import (  # noqa: F401
    MEAL_SLOTS, MealTemplate, VariationDefinition,
    SEED_MEAL_TEMPLATES, SEED_VARIATIONS,
)
from mealoptions.recipe_basis import (  # noqa: F401
    COOKING_METHODS, Recipe, IngredientLine, CookingStep,
    SEED_RECIPES, SEED_INGREDIENT_LINES, SEED_COOKING_STEPS,
)
from mealoptions.affinity_basis import (  # noqa: F401
    DEFAULT_CONTEXT, DishBase, IngredientRole, FoodRole,
    IngredientAffinity, SEED_DISH_BASES, SEED_INGREDIENT_ROLES,
    SEED_FOOD_ROLES, SEED_INGREDIENT_AFFINITIES,
)
from mealoptions.workflow_basis import (  # noqa: F401
    FIDELITY, PROVENANCES, KitchenToolDefinition,
    CookingTaskDefinition, StepMethod, StorageActionDefinition,
    CookingWorkflow, SEED_KITCHEN_TOOLS, SEED_TASK_KINDS,
    SEED_STEP_METHODS, SEED_STORAGE_ACTIONS,
)
from mealoptions.situation_basis import (  # noqa: F401
    COLD_CHAIN_CITATION, MealSituation, SEED_MEAL_SITUATIONS,
)
from mealoptions.staple_basis import (  # noqa: F401
    BULK_CADENCES, FOODKEEPER, BulkStaple, SEED_BULK_STAPLES,
)
from mealoptions.price_reference_basis import (  # noqa: F401
    OWNERSHIP_KINDS, CHAIN_KINDS, LOCAL_KINDS, PRIVACY_STRIPPED_FIELDS,
    PriceReference, SEED_PRICE_REFERENCES,
)

#: (class name, class, seeds) — the registration list the server
#: consumes (the HOUSEHOLD_SEED_PAIRS shape). Order = parents before
#: the rows that name them: recipes before lines/steps, templates
#: before variations, dish bases + roles before the affinity norms.
MEALOPTIONS_SEED_PAIRS = [
    ('Recipe', Recipe, SEED_RECIPES),
    ('IngredientLine', IngredientLine, SEED_INGREDIENT_LINES),
    ('CookingStep', CookingStep, SEED_COOKING_STEPS),
    ('MealTemplate', MealTemplate, SEED_MEAL_TEMPLATES),
    ('VariationDefinition', VariationDefinition, SEED_VARIATIONS),
    ('KitchenToolDefinition', KitchenToolDefinition, SEED_KITCHEN_TOOLS),
    ('CookingTaskDefinition', CookingTaskDefinition, SEED_TASK_KINDS),
    ('StepMethod', StepMethod, SEED_STEP_METHODS),
    ('StorageActionDefinition', StorageActionDefinition,
     SEED_STORAGE_ACTIONS),
    ('CookingWorkflow', CookingWorkflow, []),
    ('DishBase', DishBase, SEED_DISH_BASES),
    ('IngredientRole', IngredientRole, SEED_INGREDIENT_ROLES),
    ('FoodRole', FoodRole, SEED_FOOD_ROLES),
    ('IngredientAffinity', IngredientAffinity, SEED_INGREDIENT_AFFINITIES),
    ('MealSituation', MealSituation, SEED_MEAL_SITUATIONS),
    ('BulkStaple', BulkStaple, SEED_BULK_STAPLES),
    # mo-2: month-level price references (exported, never hand-seeded).
    ('PriceReference', PriceReference, SEED_PRICE_REFERENCES),
]
MEALOPTIONS_CLASSES = [cls for _, cls, _ in MEALOPTIONS_SEED_PAIRS]
