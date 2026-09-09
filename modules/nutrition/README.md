# Nutrition (`nutrition`)

Dietary nutrients, person/household profiling, harvest -> meal-nutrient yield.

**Kind:** polari-app · **agent tier:** member · **requires:** household, mealoptions

## Objects

`ActivityDefinition`, `ActivityLog`, `ConditionSteering`, `CookNowAPI`, `DailyIntakeMetric`, `DietaryNutrient`, `EatingPatternDefinition`, `FoodAisleCategory`, `FoodAllergenFlag`, `FoodItem`, `GardenPlanDefinition`, `HouseholdProfile`, `IntakeRecord`, `KitchenTool`, `MealEntry`, `MealLogistics`, `MealPlanDefinition`, `MealPlanningAPI`, `MealRating`, `MealTimeProfile`, `MethodPreference`, `NutrientContent`, `NutrientReference`, `NutritionAPI`, `NutritionFoodAPI`, `PantryItem`, `PeriodIntakeMetric`, `PersonExclusion`, `PersonProfile`, `PersonThreshold`, `PlanBudget`, `PriceObservation`, `ShoptripAPI`, `SourceLocation`, `StatedCondition`, `StoreAisleOrder`, `TodayAPI`, `ToleranceThreshold`, `ToolAdvisorDismissal`, `UnitWeightPrior`, `UserAccountLink`, `WasteRecord`, `WeekReviewAPI`, `WeightObservation`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `account_basis.py`, `activity_basis.py`, `affinity_basis.py`, `budget_basis.py`, `condition_basis.py`, `exclusion_basis.py`, `food_basis.py`, `fulfillment_basis.py`, `household_basis.py`, `intake_basis.py`, `logistics_basis.py`, `market_basis.py`, `meal_basis.py`, `nutrient_basis.py`, `pantry_basis.py`, `person_basis.py`, `purchase_basis.py`, `rating_basis.py`, `recipe_basis.py`, `shoptrip_basis.py`, `threshold_basis.py`, `tolerance_basis.py`, `waste_basis.py`, `weight_basis.py`, `workflow_basis.py`
- **api** — `cooknow_api.py`, `food_api.py`, `mealplanning_api.py`, `nutrition_api.py`, `shoptrip_api.py`, `today_api.py`, `weekreview_api.py`
- **seed** — `calendar_seed.py`, `cooknow_seed.py`, `dri_seed.py`, `fdc_seed.py`, `food_seed.py`, `nutrient_seed.py`, `person_seed.py`, `shoptrip_seed.py`, `today_seed.py`, `weekreview_seed.py`
- **custom** — `custom/acidity_analysis.py`, `custom/activity_analysis.py`, `custom/affinity_composer.py`, `custom/budget_analysis.py`, `custom/condition_analysis.py`, `custom/cooknow_analysis.py`, `custom/coverage_analysis.py`, `custom/dga_limits.py`, `custom/exclusion_analysis.py`, `custom/fulfillment_analysis.py`, `custom/harvest_analysis.py`, `custom/household_analysis.py`, `custom/logistics_analysis.py`, `custom/market_analysis.py`, `custom/meal_analysis.py`, `custom/pantry_analysis.py`, `custom/person_analysis.py`, `custom/planning_analysis.py`, `custom/purchase_analysis.py`, `custom/quick_add.py`, `custom/rating_analysis.py`, `custom/recipe_analysis.py`, `custom/shoptrip_analysis.py`, `custom/threshold_analysis.py`, `custom/today_analysis.py`, `custom/tolerance_analysis.py`, `custom/tracking_analysis.py`, `custom/tracking_periods.py`, `custom/vendor_data.py`, `custom/waste_analysis.py`, `custom/weekreview_analysis.py`, `custom/weight_trajectory.py`, `custom/workflow_analysis.py`
- **selftests** — `acidity_selftest.py`, `activity_selftest.py`, `affinity_selftest.py`, `budget_selftest.py`, `condition_selftest.py`, `cooknow_selftest.py`, `coverage_selftest.py`, `data_selftest.py`, `exclusion_selftest.py`, `fulfillment_selftest.py`, `harvest_selftest.py`, `logistics_selftest.py`, `market_selftest.py`, `meal_selftest.py`, `mealplan_pages_selftest.py`, `pantry_selftest.py`, `person_selftest.py`, `planning_selftest.py`, `purchase_selftest.py`, `quickadd_selftest.py`, `rating_selftest.py`, `recipe_selftest.py`, `shoptrip_selftest.py`, `thresholds_selftest.py`, `today_selftest.py`, `tolerance_selftest.py`, `tracking_periods_selftest.py`, `tracking_selftest.py`, `waste_selftest.py`, `weekreview_selftest.py`, `weight_selftest.py`, `workflow_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

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
