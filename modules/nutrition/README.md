# Nutrition (`nutrition`)

Dietary nutrients, person/household profiling, harvest -> meal-nutrient yield.

**Kind:** polari-app · **agent tier:** member · **requires:** household, mealoptions

## Objects

`ActivityDefinition`, `ActivityLog`, `ConditionSteering`, `CookNowAPI`, `DailyIntakeMetric`, `DietaryNutrient`, `EatingPatternDefinition`, `FoodAisleCategory`, `FoodAllergenFlag`, `FoodItem`, `GardenPlanDefinition`, `HouseholdProfile`, `IntakeRecord`, `KitchenTool`, `MealEntry`, `MealLogistics`, `MealPlanDefinition`, `MealPlanningAPI`, `MealRating`, `MealTimeProfile`, `MethodPreference`, `NutrientContent`, `NutrientReference`, `NutritionAPI`, `NutritionFoodAPI`, `PantryItem`, `PeriodIntakeMetric`, `PersonExclusion`, `PersonProfile`, `PersonThreshold`, `PlanBudget`, `PriceObservation`, `ShoptripAPI`, `SourceLocation`, `StatedCondition`, `StoreAisleOrder`, `TodayAPI`, `ToleranceThreshold`, `ToolAdvisorDismissal`, `UnitWeightPrior`, `UserAccountLink`, `WasteRecord`, `WeekReviewAPI`, `WeightObservation`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/account/UserAccountLink.py`, `objects/account/_shared.py`, `objects/activity/ActivityDefinition.py`, `objects/activity/ActivityLog.py`, `objects/activity/_shared.py`, `objects/budget/PlanBudget.py`, `objects/budget/_shared.py`, `objects/condition/ConditionSteering.py`, `objects/condition/StatedCondition.py`, `objects/condition/_shared.py`, `objects/exclusion/FoodAllergenFlag.py`, `objects/exclusion/PersonExclusion.py`, … (45 more)
- **basis** — `account_basis.py`, `activity_basis.py`, `affinity_basis.py`, `budget_basis.py`, `condition_basis.py`, `exclusion_basis.py`, `food_basis.py`, `fulfillment_basis.py`, `household_basis.py`, `intake_basis.py`, `logistics_basis.py`, `market_basis.py`, … (13 more)
- **api** — `cooknow_api.py`, `food_api.py`, `mealplanning_api.py`, `nutrition_api.py`, `shoptrip_api.py`, `today_api.py`, `weekreview_api.py`
- **seed** — `calendar_seed.py`, `cooknow_seed.py`, `dri_seed.py`, `fdc_seed.py`, `food_seed.py`, `nutrient_seed.py`, `person_seed.py`, `shoptrip_seed.py`, `today_seed.py`, `weekreview_seed.py`
- **custom** — `custom/acidity_analysis.py`, `custom/activity_analysis.py`, `custom/affinity_composer.py`, `custom/budget_analysis.py`, `custom/condition_analysis.py`, `custom/cooknow_analysis.py`, `custom/coverage_analysis.py`, `custom/dga_limits.py`, `custom/exclusion_analysis.py`, `custom/fulfillment_analysis.py`, `custom/harvest_analysis.py`, `custom/household_analysis.py`, … (21 more)
- **selftests** — `acidity_selftest.py`, `activity_selftest.py`, `affinity_selftest.py`, `budget_selftest.py`, `condition_selftest.py`, `cooknow_selftest.py`, `coverage_selftest.py`, `data_selftest.py`, `exclusion_selftest.py`, `fulfillment_selftest.py`, `harvest_selftest.py`, `logistics_selftest.py`, … (20 more)

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `nutrition.cooknow_seed:SEED_COOKNOW_PAGE_DISPLAYS`
- `nutrition.shoptrip_seed:SEED_SHOPTRIP_PAGE_DISPLAYS`
- `nutrition.today_seed:SEED_TODAY_PAGE_DISPLAYS`
- `nutrition.weekreview_seed:SEED_WEEKREVIEW_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest nutrition        # in the running backend
PYTHONPATH=.:modules python3 -m nutrition.acidity_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform nutrition`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->
