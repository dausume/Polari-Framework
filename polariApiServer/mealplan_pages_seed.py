"""
@module polariApiServer.mealplan_pages_seed

mpa-5 — the meal-planning APP's display pages, all PURE DATA over
the two generic registered components (class-rows-table /
api-json-panel — the module_pages_seed pattern): five interconnected
pages the nutrition-planner app row's nav ties together so the set
reads as ONE app. Demo rows (demo-alex / demo-household /
demo-alex-week) are knobs — repoint by editing the Display row.

Routes: /display/mealplan, /display/mealplan/planner,
/display/mealplan/pantry, /display/mealplan/market,
/display/mealplan/trends.

@consumers
  - polariServer displays seed concat (beside
    SEED_MODULE_PAGE_DISPLAYS)
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-5
"""

from polariApiServer.module_pages_seed import (
    _api, _page, _row, _table,
)

SEED_MEALPLAN_PAGE_DISPLAYS = [
    _page(
        'mealplan-home', 'mealplan',
        'mpa-5: the meal-planning front door — who you are here '
        '(Keycloak link), your latest day, plans, and pantry at a '
        'glance. Every panel links deeper into the app.',
        'MealPlanDefinition',
        [
            _row(0, [
                _api('mp-me', 0, 6, 'Me (this login)',
                     '/api/mealplanning/me'),
                _api('mp-dashboard', 1, 6, 'Dashboard — demo-alex',
                     '/api/mealplanning/users/demo-alex/dashboard'),
            ]),
            _row(1, [
                _table('mp-plans', 0, 6, 'Meal plans',
                       'MealPlanDefinition'),
                _table('mp-links', 1, 6, 'Account links '
                       '(Keycloak → person)', 'UserAccountLink',
                       'name,keycloak_username,person_name,'
                       'household_name,linked_date'),
            ]),
        ]),
    _page(
        'mealplan-planner', 'mealplan/planner',
        'mpa-5: the week being planned — entries, rollup vs '
        'thresholds, what it costs, and whether the pantry covers '
        'it (adjust-by-availability suggestions never auto-edit).',
        'MealEntry',
        [
            _row(0, [
                _table('mp-entries', 0, 6, 'Plan entries',
                       'MealEntry',
                       'name,plan_name,day_index,slot,template_name,'
                       'variation_name,scale'),
                _api('mp-plan-rollup', 1, 6,
                     'Rollup vs thresholds — demo-alex-week',
                     '/api/nutrition/plans/demo-alex-week/rollup'),
            ]),
            _row(1, [
                _api('mp-plan-cost', 0, 6,
                     'Estimated cost — demo-alex-week',
                     '/api/mealplanning/plans/demo-alex-week/cost'),
                _api('mp-plan-avail', 1, 6,
                     'Pantry coverage — demo-alex-week',
                     '/api/mealplanning/plans/demo-alex-week'
                     '/availability'),
            ]),
            _row(2, [
                _api('mp-plan-suggest', 0, 6,
                     'Stock-aware suggestions (yours to apply)',
                     '/api/mealplanning/plans/demo-alex-week'
                     '/suggestions'),
                _api('mp-prep', 1, 6,
                     'Prep schedule (total active minutes minimized)',
                     '/api/nutrition/plans/demo-alex-week'
                     '/prep-schedule'),
            ]),
        ]),
    _page(
        'mealplan-pantry', 'mealplan/pantry',
        'mpa-5: what the household actually has — lots with storage '
        'states and approximate weights (labeled priors), and the '
        'weight-prior vocabulary a kitchen scale can override.',
        'PantryItem',
        [
            _row(0, [
                _table('mp-pantry-items', 0, 6, 'Pantry lots',
                       'PantryItem',
                       'name,food_name,quantity,unit,storage_state,'
                       'acquired_date'),
                _api('mp-pantry-stock', 1, 6,
                     'Resolved stock — demo-household',
                     '/api/mealplanning/pantry/demo-household'),
            ]),
            _row(1, [
                _table('mp-unit-weights', 0, 6,
                       'Approximate unit weights (tunable priors)',
                       'UnitWeightPrior',
                       'food_name,unit_label,grams,household_name',
                       60),
                _api('mp-shopping', 1, 6,
                     'Shopping list — demo-alex-week',
                     '/api/mealplanning/plans/demo-alex-week'
                     '/shopping-list'),
            ]),
        ]),
    _page(
        'mealplan-market', 'mealplan/market',
        'mpa-5: buying — locations with geolocations, observed '
        'prices normalized to $/kg, the per-food price compare, and '
        'the purchase preview that assigns approximate weight + '
        'nutrition + cost to a would-be purchase.',
        'PriceObservation',
        [
            _row(0, [
                _table('mp-locations', 0, 6, 'Source locations',
                       'SourceLocation',
                       'name,kind,region_label,latitude,longitude'),
                _table('mp-prices-raw', 1, 6, 'Price observations',
                       'PriceObservation',
                       'food_name,location_name,price,'
                       'package_quantity,package_unit,'
                       'observed_date'),
            ]),
            _row(1, [
                _api('mp-price-compare', 0, 6,
                     'Price compare (best store named, $/kg)',
                     '/api/mealplanning/prices'),
                _api('mp-purchase-preview', 1, 6,
                     'Purchase preview — a dozen eggs',
                     '/api/mealplanning/purchase-preview'
                     '?food=egg-whole-raw&quantity=1&unit=dozen'),
            ]),
        ]),
    _page(
        'mealplan-trends', 'mealplan/trends',
        'mpa-5: the person over time — day metrics (calories, '
        'protein, fiber, sodium, per-meal GL and acid-share peaks) '
        'with gap days NAMED, weight observations, meal acidity, '
        'and the PSPP state chain behind a meal.',
        'IntakeRecord',
        [
            _row(0, [
                _api('mp-series', 0, 6,
                     'Tracking series — demo-alex',
                     '/api/mealplanning/users/demo-alex/series'),
                _api('mp-day', 1, 6, 'One day — 2026-09-01',
                     '/api/mealplanning/users/demo-alex/day'
                     '/2026-09-01'),
            ]),
            _row(1, [
                _table('mp-intake', 0, 6, 'Intake records',
                       'IntakeRecord',
                       'person_name,date,slot,template_name,'
                       'variation_name,source', 60),
                _api('mp-acidity', 1, 6,
                     'Meal acidity — chicken-bowl-dinner',
                     '/api/mealplanning/templates/'
                     'chicken-bowl-dinner/acidity'),
            ]),
            _row(2, [
                _api('mp-state-chain', 0, 12,
                     'The PSPP state chain behind the meal '
                     '(mass-balance + retention claims; model rungs '
                     'refused by name)',
                     '/api/mealplanning/templates/'
                     'chicken-bowl-dinner/state-chain'),
            ]),
        ]),
]
