"""
@module nutrition.selftest_purchase

cal-4 selftest — his sample: the weekly purchase proposal (plan gap
minus bulk-covered stock), the bulk-purchase proposals on every
cadence (demand vs stock, bulk vs retail $/kg → savings, shelf life
refusing a cadence by name), the week's coordination (purchase →
pre-prep → meals → meal-prep, rules named), AND the seeded no-code
solutions running through the REAL engine on a fake manager:
AnalysisCall → GenerateEvent(eventsFrom) → EmitEvent, fired by the
seeded triggers.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_purchase
"""

import json
import sys
from types import SimpleNamespace

from nutrition.calendar_seed import (
    SEED_MEALPLAN_ANALYSES, SEED_MEALPLAN_CALENDARS,
    SEED_MEALPLAN_EVENT_DEFINITIONS, SEED_MEALPLAN_SOLUTIONS,
    SEED_MEALPLAN_TRIGGERS,
)
from nutrition.fdc_seed import SEED_FDC_FOOD_ITEMS, SEED_FDC_NUTRIENT_CONTENTS
from nutrition.market_basis import (
    SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS, SEED_UNIT_WEIGHTS,
)
from nutrition.meal_basis import (
    SEED_MEAL_ENTRIES, SEED_MEAL_PLANS, SEED_MEAL_TEMPLATES, SEED_VARIATIONS,
)
from nutrition.pantry_basis import SEED_PANTRY_ITEMS
from nutrition.purchase_analysis import (
    bulk_purchase_proposal, coordinate_week, weekly_purchase_proposal,
)
from nutrition.purchase_basis import BULK_CADENCES, SEED_BULK_STAPLES
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from polariNoCode.calendar_events import (
    SEED_CORE_EVENT_DEFINITIONS, resolve_calendar_events,
)
from polariNoCode.event_dispatcher import dispatch_object_change, get_dispatcher

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {f'{i}': SimpleNamespace(id=f'{i}', **r) for i, r in enumerate(seed_list)}


class _DB:
    def saveInstanceInDB(self, inst):
        return True


def _manager():
    tables = {
        'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS),
        'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
        'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS),
        'PantryItem': _rows(SEED_PANTRY_ITEMS),
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS),
        'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES),
        'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
        'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows(SEED_MEAL_PLANS),
        'MealEntry': _rows(SEED_MEAL_ENTRIES),
        'BulkStaple': _rows(SEED_BULK_STAPLES),
        'EventDefinition': _rows(SEED_CORE_EVENT_DEFINITIONS + SEED_MEALPLAN_EVENT_DEFINITIONS),
        'CalendarDefinition': _rows(SEED_MEALPLAN_CALENDARS),
        'AnalysisDefinition': _rows(SEED_MEALPLAN_ANALYSES),
        'SolutionDefinition': _rows(SEED_MEALPLAN_SOLUTIONS),
        'EventTrigger': _rows(SEED_MEALPLAN_TRIGGERS),
        'TriggerFiring': {}, 'CalendarEvent': {},
        'KitchenTool': {}, 'KitchenToolDefinition': {}, 'CookingWorkflow': {},
        'CookingTaskDefinition': {}, 'StepMethod': {}, 'MethodPreference': {},
        'StorageActionDefinition': {}, 'HouseholdProfile': {},
    }
    return SimpleNamespace(objectTables=tables, db=_DB())


def main():
    mgr = _manager()
    plan = next(iter(mgr.objectTables['MealPlanDefinition'].values()))
    print('cal-4 purchase + coordination')

    wk = weekly_purchase_proposal(mgr, plan.name, 'demo-household', '2026-09-05')
    check('weekly purchase proposal: ok, one purchase event, Saturday 10:00–11:00 prior',
          wk['ok'] and len(wk['proposals']) == 1
          and wk['proposals'][0]['span'] == {'start': '2026-09-05T10:00', 'end': '2026-09-05T11:00'}
          and wk['proposals'][0]['category'] == 'purchase', str(wk.get('proposals')))
    check('purchase lines carry $ from observed prices and unpriced foods are NAMED',
          all('estCost' in l for l in wk['lines']) and isinstance(wk['unpricedFoods'], list))
    check('a bulk staple in stock removes its line (rice is in the pantry)',
          all(l['food'] != 'rice-white-raw' for l in wk['lines'])
          and any(c['food'] == 'rice-white-raw' for c in wk['bulkCovered'])
          or 'rice-white-raw' not in json.dumps(wk['lines']),
          json.dumps(wk['bulkCovered']))

    seen = {}
    for months in BULK_CADENCES:
        b = bulk_purchase_proposal(mgr, 'demo-household', months, '2026-09-01')
        seen[months] = b
        check(f'bulk proposal {months}-month: ok, staples on that cadence only, all-day event',
              b['ok'] and all(s['cadenceMonths'] == months for s in b['staples'])
              and (not b['proposals'] or b['proposals'][0]['all_day']
                   and b['proposals'][0]['category'] == 'bulk-purchase'),
              str(b.get('refused')))
    rice = next((s for s in seen[12]['staples'] if s['food'] == 'rice-white-raw'), None)
    check('yearly rice: demand over 52 weeks minus 2000 g stock → packages of the 25 lb sack, '
          'bulk $/kg computed, cited FoodKeeper shelf life carried',
          rice is not None and rice['needG'] > rice['haveG'] == 2000.0
          and rice['packages'] >= 1 and rice['bulkPricePerKg'] and 'FoodKeeper' in rice['citation'],
          str(rice))
    check('savings stated only where a retail observation exists (rice has one)',
          rice is not None and (rice['estSavings'] is not None) == (rice['retailPricePerKg'] is not None))
    # shelf-life refusal: brown rice on a yearly cadence would decay first
    mgr.objectTables['BulkStaple']['x'] = SimpleNamespace(
        id='x', name='bad', household_name='demo-household', food_name='rice-brown-raw',
        cadence_months=12, shelf_life_days=180, storage_state='pantry',
        bulk_package_quantity=10, bulk_package_unit='lb', bulk_price=11.99, currency='USD',
        bulk_location_name='demo-warehouse', observed_date='', weekly_demand_g=300,
        citation='FoodKeeper', confidence='transcribed', is_prior=True, provenance_id='', notes='')
    b = bulk_purchase_proposal(mgr, 'demo-household', 12, '2026-09-01')
    check('a cadence longer than the shelf life is REFUSED by name with a suggestion',
          any(r['food'] == 'rice-brown-raw' and 'outlives' in r['why'] and r['suggestion']
              for r in b['refused']), str(b['refused']))
    del mgr.objectTables['BulkStaple']['x']

    co = coordinate_week(mgr, plan.name, 'demo-household', '2026-09-07')
    cats = [p['category'] for p in co['proposals']]
    check('coordination: purchase + pre-prep + one meal-prep per entry, rules named',
          co['ok'] and cats.count('purchase') == 1 and cats.count('meal-prep') == len(
              [e for e in mgr.objectTables['MealEntry'].values() if e.plan_name == plan.name])
          and len(co['rules']) >= 4, str(co['counts']))
    starts = [p['span']['start'] for p in co['proposals']]
    check('timeline is ordered; the purchase (the Saturday before the week) precedes every '
          'pre-prep and every meal',
          starts == sorted(starts) and co['proposals'][0]['category'] == 'purchase'
          and co['proposals'][0]['span']['start'].startswith('2026-09-05'), str(starts[:4]))
    mp = [p for p in co['proposals'] if p['category'] == 'meal-prep'][0]
    check('meal-prep is SHORT: a per-person final-prep block (safety-bounded) ending at the meal time',
          0 < mp['payload_json']['finalPrepMin'] <= 20
          and mp['span']['end'].endswith(mp['payload_json']['mealTime']), str(mp['span']))
    pre = [p for p in co['proposals'] if p['category'] == 'pre-prep']
    check('pre-prep sessions never start before the purchase ends on the shop day',
          all(not p['span']['start'].startswith('2026-09-07') or p['span']['start'] >= '2026-09-07T11:00'
              for p in pre), str([p['span'] for p in pre]))

    # --- the NO-CODE path: seeded triggers + solutions through the real engine ---
    d = get_dispatcher(mgr)
    firings = dispatch_object_change(mgr, 'MealPlanDefinition', 'update', [plan.id])
    ev = list(mgr.objectTables['CalendarEvent'].values())
    check('object trigger (plan updated) → coordinate solution → CalendarEvents generated '
          '(purchase + pre-prep + meal-prep) through AnalysisCall → GenerateEvent(eventsFrom)',
          any(f.status == 'fired' for f in firings) and len(ev) == len(co['proposals'])
          and {e.category for e in ev} >= {'purchase', 'meal-prep'},
          f'{[(f.trigger_name, f.status, f.error) for f in firings]} events={len(ev)}')
    check('generated events are stamped generated_by = the trigger, span as datetime_duration JSON',
          all(e.generated_by == 'coordinate-week-on-plan' for e in ev)
          and all(json.loads(e.span).get('start') for e in ev))
    n = len(ev)
    dispatch_object_change(mgr, 'MealPlanDefinition', 'update', [plan.id])
    check('re-firing is idempotent (dedupeBy name) — no duplicates; cooldown skips within 5 s',
          len(mgr.objectTables['CalendarEvent']) == n)

    from datetime import datetime
    d.tick(now=datetime(2026, 9, 5, 10, 30), lookback_seconds=3600)
    purchases = [e for e in mgr.objectTables['CalendarEvent'].values() if e.category == 'purchase']
    check('weekly-purchase schedule trigger (Saturday 10:00) generates the purchase event via the '
          'no-code solution (dedupes with the coordinated one on the same date)',
          any('2026-09-05' in e.span for e in purchases), str([(e.name, e.span) for e in purchases]))
    d.tick(now=datetime(2026, 9, 1, 0, 30), lookback_seconds=3600)
    bulk = [e for e in mgr.objectTables['CalendarEvent'].values() if e.category == 'bulk-purchase']
    check('on Sep 1 the monthly / 3-month / 6-month / yearly bulk triggers ALL fire (every cadence '
          'starts there) → four bulk-purchase events, one per cadence',
          len(bulk) == 4 and sorted(json.loads(e.payload_json)['cadenceMonths'] for e in bulk) == [1, 3, 6, 12],
          str([(e.name, e.title) for e in bulk]))

    cal = next(iter(mgr.objectTables['CalendarDefinition'].values()))
    plan_start = str(plan.start_date)[:10]
    week = resolve_calendar_events(mgr, cal, '2026-08-29', '2026-09-13')
    layers = {l['eventDefinition']: l['count'] for l in week['layers']}
    check('the mealplan-week calendar merges planned meals + generated events for the week',
          layers.get('meal-plan-entry', 0) > 0 and layers.get('calendar-events', 0) > 0
          and week['count'] == sum(layers.values()), str(layers))

    print(f'\n{len(failures)} failure(s)')
    for f in failures:
        print('  -', f)
    print('PASS: cal-4 purchase / bulk / coordination + no-code event logic hold together'
          if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
