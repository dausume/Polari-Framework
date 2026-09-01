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

import json

from polariApiServer.module_pages_seed import (
    _api, _page, _row, _table,
)

#: mpa-5: GraphDefinition rows addressed BY NAME (ids are
#: instance-local — the embeddedGraph component's graphName input,
#: added this arc, is what makes a seeded chart possible at all).
SEED_MEALPLAN_GRAPHS = [
    {'name': 'mealplan-weight-trend',
     'description': 'Measured weights over time for one person '
                    '(facts, never the Hall projection — drift '
                    'between the two lives on the profile page).',
     'source_class': 'WeightObservation',
     'definition': json.dumps({'graphConfig': {
         'renderStyle': 'dot',
         'xDimension': 'date',
         'yDimensions': ['weight_kg'],
         'seriesColors': ['#2e7d32'],
         'options': {
             'width': 800, 'height': 320,
             'marginTop': 20, 'marginRight': 30,
             'marginBottom': 40, 'marginLeft': 60,
             'showLegend': False, 'showGrid': True,
             'xLabel': 'date', 'yLabel': 'weight (kg)',
         },
         'aggregation': {'enabled': False, 'strategy': 'average'},
     }})},
]


def _metric_graph(name, description, y_dims, y_label, colors):
    """mpa-8: day-series charts over the DailyIntakeMetric cache
    rows (derive-on-demand: reading /series refreshes them)."""
    return {'name': name, 'description': description,
            'source_class': 'DailyIntakeMetric',
            'definition': json.dumps({'graphConfig': {
                'renderStyle': 'lineY',
                'xDimension': 'date',
                'yDimensions': list(y_dims),
                'seriesColors': list(colors),
                'options': {
                    'width': 800, 'height': 280,
                    'marginTop': 20, 'marginRight': 30,
                    'marginBottom': 40, 'marginLeft': 60,
                    'showLegend': len(y_dims) > 1,
                    'showGrid': True,
                    'xLabel': 'date', 'yLabel': y_label,
                },
                'aggregation': {'enabled': False,
                                'strategy': 'average'},
            }})}


SEED_MEALPLAN_GRAPHS += [
    _metric_graph('mealplan-calories-trend',
                  'Calories per day from logged intake (cache rows '
                  'refresh when the series is read; gap days have '
                  'no row — honest absence, not zeros).',
                  ['calories'], 'kcal/day', ['#1565c0']),
    _metric_graph('mealplan-gl-trend',
                  'The day\'s MAX per-meal glycemic load (spike '
                  'metric; GL>20 = the published high convention).',
                  ['max_meal_gl'], 'max per-meal GL', ['#ef6c00']),
    _metric_graph('mealplan-acid-trend',
                  'The day\'s MAX per-meal acid mass share '
                  '(fraction of meal mass at pH<=4.6; comfort '
                  'heuristic, not medical advice).',
                  ['max_meal_acid_share'], 'max acid share (0-1)',
                  ['#c62828']),
]


def _graph_item(item_id, index, segments, title, graph_name,
                class_name, filter_field='', filter_value=''):
    return {
        'id': item_id, 'index': index, 'type': 'component',
        'rowSegmentsUsed': segments, 'gridColumnStart': None,
        'title': title, 'visible': True, 'collapsed': False,
        'cssClass': '',
        'componentProps': {
            'componentName': 'embeddedGraph',
            'inputs': {'graphName': graph_name,
                       'className': class_name,
                       'filterField': filter_field,
                       'filterValue': filter_value},
        },
        'item': None, 'nestedRows': [],
    }

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
                _graph_item('mp-calories-chart', 0, 6,
                            'Calories/day — demo-alex',
                            'mealplan-calories-trend',
                            'DailyIntakeMetric',
                            'person_name', 'demo-alex'),
                _graph_item('mp-weight-chart', 1, 6,
                            'Weight over time — demo-alex '
                            '(measured observations)',
                            'mealplan-weight-trend',
                            'WeightObservation',
                            'person_name', 'demo-alex'),
            ], min_height=300),
            _row(3, [
                _graph_item('mp-gl-chart', 0, 6,
                            'Max per-meal GL — demo-alex',
                            'mealplan-gl-trend',
                            'DailyIntakeMetric',
                            'person_name', 'demo-alex'),
                _graph_item('mp-acid-chart', 1, 6,
                            'Max per-meal acid share — demo-alex',
                            'mealplan-acid-trend',
                            'DailyIntakeMetric',
                            'person_name', 'demo-alex'),
            ], min_height=300),
            _row(4, [
                _api('mp-state-chain', 0, 12,
                     'The PSPP state chain behind the meal '
                     '(mass-balance + retention claims; model rungs '
                     'refused by name)',
                     '/api/mealplanning/templates/'
                     'chicken-bowl-dinner/state-chain'),
            ]),
        ]),
]
