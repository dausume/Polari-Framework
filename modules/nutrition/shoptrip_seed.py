"""
@module nutrition.shoptrip_seed

N3 — the SHOPPING TRIP page (HOUSEHOLD_APP_PAGES.md §3.3) as data:
phone-shaped (every row one item, two at most — narrow panels stack):

  row 0  the trip header: store, date, aisle order, totals
  row 1  the checklist in aisle order (structured reading of
         /api/mealplanning/shoptrip/checklist — step, aisle, food,
         quantity, est. cost with age, bought)
  row 2  the "Bought it" FORM → mealplan-shoptrip-bought solution
         (FormSubscription → record proposal → PriceObservation row →
         PantryItem lot → refresh)
  row 3  the pantry lots (put-away) table for the household
  row 4  the store's aisle order + the food → aisle map (the knobs)

Seed lists the orchestrator wires: SEED_SHOPTRIP_TABLES,
SEED_SHOPTRIP_PAGE_DISPLAYS, SEED_SHOPTRIP_ANALYSES,
SEED_SHOPTRIP_SOLUTIONS, SEED_SHOPTRIP_TRIGGERS (empty — the page
writes through its form; no schedule/object trigger is needed).

@consumers polariApiServer.mealplan_pages_seed (wired by the orchestrator)
"""

import json

from polariApiServer.mealplan_pages_seed import (
    _etable, _form, _sapi, _table_def,
)
from polariApiServer.module_pages_seed import _page, _row
from polariNoCode import graph_builder as gb
from nutrition.calendar_seed import message_call, refresh_with_message

HOUSEHOLD = 'demo-household'
PLAN = 'demo-alex-week'
STORE = 'demo-grocery'
_MP = '/api/mealplanning'
_PROV = 'N3 shoptrip'

SEED_SHOPTRIP_TABLES = [
    _table_def('shoptrip-aisle-order-standard', 'StoreAisleOrder',
               'Store aisle orders',
               'The order each store\'s aisles are walked (a per-store knob).',
               [('name', 'Order', 'str', 160),
                ('location_name', 'Store', 'str', 140),
                ('household_name', 'Household', 'str', 130),
                ('aisle_order_json', 'Aisles (in order)', 'str', 320),
                ('is_prior', 'Prior?', 'bool', 70),
                ('notes', 'Notes', 'str', 240)]),
    _table_def('shoptrip-food-aisle-standard', 'FoodAisleCategory',
               'Food aisles',
               'Which aisle each food is found in (a labelled convention).',
               [('food_name', 'Food', 'str', 180),
                ('category', 'Aisle', 'str', 120),
                ('is_prior', 'Prior?', 'bool', 70),
                ('notes', 'Notes', 'str', 260)]),
    # the household's lots as PUT-AWAY rows (not the class default —
    # mealplan-pantry-standard keeps that role).
    _table_def('shoptrip-pantry-lot-standard', 'PantryItem',
               'Put-away lots',
               'Lots put away from shopping trips: food, amount, where it is stored, '
               'what it cost, where it came from.',
               [('food_name', 'Food', 'str', 160),
                ('quantity', 'Qty', 'float', 70),
                ('unit', 'Unit', 'str', 70),
                ('storage_state', 'Stored', 'str', 90),
                ('acquired_date', 'Bought', 'str', 110),
                ('source_location_name', 'Store', 'str', 130),
                ('price_paid', 'Paid', 'float', 80),
                ('notes', 'Notes', 'str', 260)], defaults=False),
]

SEED_SHOPTRIP_GRAPHS = []

SEED_SHOPTRIP_ANALYSES = [
    {'name': 'mealplan-shoptrip-checklist', 'domain': 'nutrition',
     'callable_ref': 'nutrition.shoptrip_analysis:trip_checklist',
     'description': 'The purchase event\'s lines (or the weekly proposal) as a checklist '
                    'in the store\'s aisle order: est. cost from best $/kg (age shown), '
                    'bought where a put-away lot exists; unknown aisles named, last.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name', 'location': 'SourceLocation.name',
                                'event': 'CalendarEvent.name (optional)', 'household': '',
                                'bought_window_days': 6}),
     'enabled': True, 'is_prior': True, 'provenance_id': _PROV},
    {'name': 'mealplan-shoptrip-record', 'domain': 'nutrition',
     'callable_ref': 'nutrition.shoptrip_analysis:record_purchase_proposal',
     'description': 'The "Bought it" form → one PriceObservation proposal (never overwriting '
                    'a same-named one) + one PantryItem put-away lot proposal.',
     'params_json': json.dumps({'food': 'FoodItem.name', 'location': 'SourceLocation.name',
                                'price': 0.0, 'package_quantity': 1.0, 'package_unit': 'lb',
                                'date': 'ISO date (default today)', 'household': HOUSEHOLD,
                                'storage_state': 'pantry|fridge|freezer (blank = aisle prior)'}),
     'enabled': True, 'is_prior': True, 'provenance_id': _PROV},
]


def _solution(name, definition, description):
    return {'name': name, 'function_name': name.replace('-', '_'),
            'target_runtime': 'python_backend',
            'definition': json.dumps(definition),
            'contract_json': json.dumps({'description': description,
                                         'executionRights': 'definer'})}


_RECORD_PARAMS = {'food': gb.var_src('food'), 'location': gb.var_src('location'),
                  'price': gb.var_src('price'), 'package_quantity': gb.var_src('package_quantity'),
                  'package_unit': gb.var_src('package_unit'), 'date': gb.var_src('date'),
                  'household': gb.var_src('household')}

#: "Bought it": FormSubscription → the record proposal picked three
#: times BEFORE any write (priceProposals / lotProposals — GenerateEvent
#: writes ONE class per node, so two nodes; dedupeBy name never
#: duplicates — and the plain-words message) → refresh → return message.
SHOPTRIP_BOUGHT_SOLUTION = _solution(
    'mealplan-shoptrip-bought',
    gb.solution(
        'mealplan-shoptrip-bought',
        gb.node('Start', 'FormSubscription', {}, outs=[['ProposePrice']]),
        gb.node('ProposePrice', 'AnalysisCall',
                {'analysis': 'mealplan-shoptrip-record', 'params': _RECORD_PARAMS,
                 'pick': 'priceProposals', 'resultVariable': 'priceProposals'},
                outs=[['ProposeLot']]),
        gb.node('ProposeLot', 'AnalysisCall',
                {'analysis': 'mealplan-shoptrip-record', 'params': _RECORD_PARAMS,
                 'pick': 'lotProposals', 'resultVariable': 'lotProposals'},
                outs=[['Message']]),
        message_call('Message', 'mealplan-shoptrip-record', _RECORD_PARAMS, 'WritePrice'),
        gb.node('WritePrice', 'GenerateEvent',
                {'targetClassName': 'PriceObservation',
                 'eventsFrom': gb.var_src('priceProposals'), 'dedupeBy': 'name',
                 'fields': {}, 'resultVariable': 'priceRow'}, outs=[['WriteLot']]),
        gb.node('WriteLot', 'GenerateEvent',
                {'targetClassName': 'PantryItem',
                 'eventsFrom': gb.var_src('lotProposals'), 'dedupeBy': 'name',
                 'fields': {}, 'resultVariable': 'lotRow'}, outs=[['Refresh']]),
        refresh_with_message({'prices': gb.var_src('priceRowBatch'),
                              'lots': gb.var_src('lotRowBatch')}),
    ),
    'Record a bought item: the price as paid → PriceObservation; the package → a '
    'PantryItem put-away lot (grams via weight priors, storage by aisle prior); says '
    'what was recorded and what was already there and kept.')

SEED_SHOPTRIP_SOLUTIONS = [SHOPTRIP_BOUGHT_SOLUTION]

#: no schedule/object trigger: the page writes through its form and
#: the purchase event itself is generated by cal-4's weekly trigger.
SEED_SHOPTRIP_TRIGGERS = []


def _bought_form(item_id, index, segments):
    return _form(
        item_id, index, segments,
        'Bought it — the price as paid → an observation; the package → a put-away lot',
        'mealplan-shoptrip-bought', [
            ('food', 'Food', 'string', '', 'a FoodItem slug from the list (e.g. chicken-breast-raw)', True),
            ('location', 'Store', 'string', STORE, 'SourceLocation name', True),
            ('price', 'Price paid ($)', 'number', 0, 'for ONE package', True),
            ('package_quantity', 'Package quantity', 'number', 1, 'e.g. 2 (lb), 1 (dozen)', True),
            ('package_unit', 'Unit', 'string', 'lb', 'g / kg / lb / oz / each / dozen / bunch …', True),
            ('date', 'Date', 'string', '', 'ISO date; blank = today', False),
            ('household', 'Household', 'string', HOUSEHOLD, '', False),
        ], submit_label='Bought it')


SEED_SHOPTRIP_PAGE_DISPLAYS = [
    _page(
        'mealplan-shoptrip', 'mealplan/shoptrip',
        'N3: the shopping trip on a phone — the purchase event\'s lines as a '
        'checklist in the store\'s aisle order (the store\'s StoreAisleOrder '
        'knob; foods without an aisle walk last, named), estimated cost from '
        'the best observed $/kg with its age, bought where a put-away lot '
        'exists. "Bought it" records the price as paid (PriceObservation, '
        'never overwriting a same-named one) and puts the package away as a '
        'PantryItem lot. Below: the lots, the aisle knobs.',
        'PantryItem',
        [
            _row(0, [
                _sapi('st-trip', 0, 12, f'Trip — {STORE} for {PLAN}',
                      f'{_MP}/shoptrip/checklist?plan={PLAN}&location={STORE}',
                      hide='lines,unknownAisleFoods,honesty,schema'),
            ], min_height=200),
            _row(1, [
                _sapi('st-checklist', 0, 12,
                      'Checklist — in aisle order (step · aisle · food · quantity · '
                      'est. cost · bought)',
                      f'{_MP}/shoptrip/checklist?plan={PLAN}&location={STORE}',
                      pick='lines'),
            ], min_height=420),
            _row(2, [
                _bought_form('st-bought', 0, 12),
            ], min_height=360),
            _row(3, [
                _etable('st-lots', 0, 12, f'Put away — lots in {HOUSEHOLD}',
                        'shoptrip-pantry-lot-standard', 'PantryItem',
                        'household_name', HOUSEHOLD),
            ]),
            _row(4, [
                _etable('st-aisle-order', 0, 6, 'Aisle order per store (knob)',
                        'shoptrip-aisle-order-standard', 'StoreAisleOrder'),
                _etable('st-food-aisles', 1, 6, 'Food → aisle (convention, edit freely)',
                        'shoptrip-food-aisle-standard', 'FoodAisleCategory'),
            ]),
        ]),
]
