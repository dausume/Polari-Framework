# mealoptions initial data (module data convention)

Plain-JSON `<Class>.json` payloads (`module-initial-data/1`,
`moduleService/json_seeds.py`) loaded at boot and by
`POST /modules/seed {"moduleId":"mealoptions"}`, served by
`GET /modules/mealoptions/initial-data`, and **written by
`pol modules export mealoptions`** (`POST /modules/export`) — the
reverse path (MEAL_OPTIONS_MODULE_PLAN mo-3). Seeds stay in code
(`SEED_*` in the `*_basis` modules); only `is_prior=False` (user-
authored) rows and the computed `PriceReference` rows land here (D5).

What may live here vs. what never does (plan §1, in two lines):

| here — data ABOUT meals | never here — data about a person, place or day |
|---|---|
| MealTemplate, VariationDefinition, Recipe, IngredientLine, CookingStep, DishBase, IngredientRole, FoodRole, IngredientAffinity, KitchenToolDefinition, CookingTaskDefinition, StepMethod, StorageActionDefinition, CookingWorkflow, MealSituation, BulkStaple (location pointers blank), PriceReference (food × month × source type × chain × coarse region; purchaser, place, day stripped) | MealPlanDefinition, MealEntry, Person*, Household*, PantryItem, SourceLocation, PriceObservation, everything under household/ |

`mealoptions/export_hook.py` enforces the line on every export
(`strip_fields` + `filter_row`); `mealoptions.selftest_privacy` proves
no stripped field name can appear in a written file. Check:
`cd modules && PYTHONPATH=..:../polariApiServer python3 -m mealoptions.selftest_privacy`.
Publish carries these files: `pol modules publish mealoptions`
(or `polari-cli/shells/push-all-dev.sh`).
