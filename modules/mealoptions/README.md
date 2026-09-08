# Mealoptions (`mealoptions`)

Meal options: templates, variations, recipes, steps, ingredient affinities, cooking methods, tool and task vocabularies, meal situations, bulk staples — the shareable meal data; no person or place data

**Kind:** library · **agent tier:** member · **requires:** nothing

## Objects

`BulkStaple`, `CookingStep`, `CookingTaskDefinition`, `CookingWorkflow`, `DishBase`, `FoodRole`, `IngredientAffinity`, `IngredientLine`, `IngredientRole`, `KitchenToolDefinition`, `MealSituation`, `MealTemplate`, `PriceReference`, `Recipe`, `StepMethod`, `StorageActionDefinition`, `VariationDefinition`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `affinity_basis.py`, `meal_basis.py`, `price_reference_basis.py`, `recipe_basis.py`, `situation_basis.py`, `staple_basis.py`, `workflow_basis.py`
- **seed** — `mealoptions_data_seed.py`
- **custom** — `custom/export_hook.py`, `custom/price_reference_analysis.py`
- **selftests** — `mealoptions_selftest.py`, `price_reference_selftest.py`, `privacy_selftest.py`
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest mealoptions        # in the running backend
PYTHONPATH=.:modules python3 -m mealoptions.mealoptions_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform mealoptions`
