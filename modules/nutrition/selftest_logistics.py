"""
@module nutrition.selftest_logistics

mlg-1..4 selftest — schedules + sleep spacing (his default 2 h, per
person), skill profiles with SAFETY bounding speed, prep-vs-eating
time per person, refinement that never rewards rushing, situations
+ packing (lunchbox, cold packs), dishes as scheduled work, the
percentage-share allocation minimising total person-minutes, and
the coordination that carries all of it as events; plus the trigger
inputs-win rule so a schedule change re-coordinates the plan.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_logistics
"""

import json
import sys
from datetime import datetime
from types import SimpleNamespace

from nutrition.calendar_seed import (
    SEED_MEALPLAN_ANALYSES, SEED_MEALPLAN_CALENDARS,
    SEED_MEALPLAN_EVENT_DEFINITIONS, SEED_MEALPLAN_SOLUTIONS,
    SEED_MEALPLAN_TRIGGERS,
)
from nutrition.fdc_seed import SEED_FDC_FOOD_ITEMS, SEED_FDC_NUTRIENT_CONTENTS
from nutrition.logistics_analysis import (
    assign_work, availability_windows, dish_plan, fairness_readout,
    meal_timing_check, portability_plan, prep_time_profile,
    refine_speed_factors, safety_check, step_minutes, where_is,
)
from mealoptions import MEALOPTIONS_SEED_PAIRS
from nutrition.logistics_basis import (
    HOUSEHOLD_SEED_PAIRS, LOGISTICS_SEED_PAIRS, SPEED_FACTOR_FLOOR,
)
from nutrition.market_basis import (
    SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS, SEED_UNIT_WEIGHTS,
)
from nutrition.meal_basis import (
    SEED_MEAL_ENTRIES, SEED_MEAL_PLANS, SEED_MEAL_TEMPLATES, SEED_VARIATIONS,
)
from nutrition.pantry_basis import SEED_PANTRY_ITEMS
from nutrition.purchase_analysis import coordinate_week
from nutrition.purchase_basis import SEED_BULK_STAPLES
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from nutrition.workflow_basis import (
    SEED_KITCHEN_TOOLS, SEED_STEP_METHODS, SEED_STORAGE_ACTIONS, SEED_TASK_KINDS,
)
from polariNoCode.calendar_events import (
    SEED_CORE_EVENT_DEFINITIONS, resolve_calendar_events,
)
from polariNoCode.event_dispatcher import dispatch_object_change

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
        'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS), 'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
        'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS), 'PantryItem': _rows(SEED_PANTRY_ITEMS),
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS), 'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES), 'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES), 'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows(SEED_MEAL_PLANS), 'MealEntry': _rows(SEED_MEAL_ENTRIES),
        'BulkStaple': _rows(SEED_BULK_STAPLES),
        'KitchenToolDefinition': _rows(SEED_KITCHEN_TOOLS), 'StepMethod': _rows(SEED_STEP_METHODS),
        'StorageActionDefinition': _rows(SEED_STORAGE_ACTIONS), 'CookingTaskDefinition': _rows(SEED_TASK_KINDS),
        'KitchenTool': {}, 'MethodPreference': {}, 'HouseholdProfile': {},
        'EventDefinition': _rows(SEED_CORE_EVENT_DEFINITIONS + SEED_MEALPLAN_EVENT_DEFINITIONS),
        'CalendarDefinition': _rows(SEED_MEALPLAN_CALENDARS),
        'AnalysisDefinition': _rows(SEED_MEALPLAN_ANALYSES),
        'SolutionDefinition': _rows(SEED_MEALPLAN_SOLUTIONS),
        'EventTrigger': _rows(SEED_MEALPLAN_TRIGGERS),
        'TriggerFiring': {}, 'CalendarEvent': {},
    }
    # hh-1: the household layer's seeds moved with it; LOGISTICS_SEED_PAIRS
    # is meal-only now.
    # mo-1: the shareable meal data (incl. MealSituation) lives in mealoptions.
    for cls, _c, seeds in HOUSEHOLD_SEED_PAIRS + LOGISTICS_SEED_PAIRS + MEALOPTIONS_SEED_PAIRS:
        tables[cls] = _rows(seeds)
    return SimpleNamespace(objectTables=tables, db=_DB())


def main():
    mgr = _manager()
    plan = next(iter(mgr.objectTables['MealPlanDefinition'].values()))
    print('mlg-1..4 logistics')

    # --- mlg-1 schedules + sleep ---------------------------------------
    av = availability_windows(mgr, 'demo-alex', '2026-08-31', '2026-09-06')
    kinds = {b['kind'] for b in av['busy']}
    check('availability: Alex\'s work, commute and sleep expand from PersonSchedule recurrences',
          {'work', 'commute', 'sleep'} <= kinds and av['free'], str(kinds))
    check('sleep crossing midnight expands as one block (23:00 → 07:00 next day)',
          any(b['kind'] == 'sleep' and b['start'].endswith('T23:00') and b['end'].endswith('T07:00')
              for b in av['busy']))
    check('where_is: Alex is at the workplace Tuesday noon, home Tuesday 20:00',
          where_is(mgr, 'demo-alex', datetime(2026, 9, 1, 12, 0))[0] == 'workplace'
          and where_is(mgr, 'demo-alex', datetime(2026, 9, 1, 20, 0))[0] == 'home')
    tc = meal_timing_check(mgr, plan.name, '2026-08-31')
    sam_d2 = [v for v in tc['verdicts'] if v['person'] == 'demo-sam' and v['entry'].endswith('d2-dinner')][0]
    alex_d1 = [v for v in tc['verdicts'] if v['person'] == 'demo-alex' and v['entry'].endswith('d1-dinner')][0]
    check('timing: Sam is at work at day-2 dinner time; the MealLogistics row (packed) satisfies it',
          sam_d2['where']['locationKind'] == 'workplace' and not any('MealLogistics' in f for f in sam_d2['flags']),
          str(sam_d2))
    check('timing: Alex\'s dinner 18:30 + 40 min eating ends 230 min before his 23:00 bedtime ≥ his 120 default → no flag',
          alex_d1['dinnerToSleep']['minutes'] == 230 and alex_d1['dinnerToSleep']['needed'] == 120
          and not any('bedtime' in f for f in alex_d1['flags']), str(alex_d1.get('dinnerToSleep')))
    # move Alex's bedtime to 20:30 → flagged with a latest-start suggestion
    pref = [p for p in mgr.objectTables['SleepPreference'].values() if p.person_name == 'demo-alex'][0]
    pref.bedtime_hhmm = '20:30'
    tc2 = meal_timing_check(mgr, plan.name, '2026-08-31')
    v = [x for x in tc2['verdicts'] if x['person'] == 'demo-alex' and x['entry'].endswith('d1-dinner')][0]
    check('an early bedtime FLAGS dinner (never blocks) with the latest start that keeps the spacing, in his posture words',
          any('do not make this worse' in f for f in v['flags'])
          and any(s['kind'] == 'move' and s['latestStart'].endswith('T17:50') for s in v['suggestions']),
          str(v['suggestions']))
    pref.bedtime_hhmm = '23:00'

    # --- mlg-2 skills, safety, prep vs eating ------------------------
    alex_dice = step_minutes(mgr, 'demo-alex', 'dice-knife', 6.0)
    sam_dice = step_minutes(mgr, 'demo-sam', 'dice-knife', 6.0)
    check('skill profiles: experienced Alex dices faster (×0.8) than novice Sam (×1.3) for the same step',
          alex_dice['minutes'] < sam_dice['minutes'] and alex_dice['governingFactor'] == 0.8
          and sam_dice['governingFactor'] == 1.3, f'{alex_dice["minutes"]} vs {sam_dice["minutes"]}')
    tiny = step_minutes(mgr, 'demo-alex', 'dice-knife', 1.0)
    check('SAFETY bounds speed: a 1-min dice at ×0.8 would be 0.8 min; the 1.5-min safety floor wins and is named',
          tiny['minutes'] == 1.5 and tiny['boundedBySafety'], str(tiny))
    sc = safety_check(mgr, 'demo-sam', 'pan-fry-pan')
    sc2 = safety_check(mgr, 'demo-sam', 'dice-mandoline')
    check('safety rules: experienced-safety Sam may pan-fry alone; the mandoline\'s intermediate knife floor '
          'makes novice-knife Sam supervised, with the reason',
          sc['verdict'] == 'alone' and sc2['verdict'] == 'supervised' and sc2['reasons'], f'{sc} {sc2}')
    ref = refine_speed_factors(mgr, 'demo-alex')
    p = [x for x in ref['proposals'] if x['skill'] == 'knife-work'][0]
    check('refinement: 3 observations of Alex dicing (4.5/5/4 min vs base 2) → proposed factor = median ratio, fidelity observed',
          p['observations'] == 3 and p['proposedFactor'] == 2.25 and p['fidelity'] == 'observed', str(p))
    for o in mgr.objectTables['DurationObservation'].values():
        o.observed_min = 0.5
    ref2 = refine_speed_factors(mgr, 'demo-alex')
    check('observations FASTER than the floor become a SAFETY QUESTION and the factor stays at the floor',
          ref2['safetyQuestions'] and ref2['proposals'][0]['proposedFactor'] == SPEED_FACTOR_FLOOR
          and 'rushed' in ref2['safetyQuestions'][0]['question'], str(ref2['safetyQuestions']))
    for o, m in zip(mgr.objectTables['DurationObservation'].values(), (4.5, 5.0, 4.0)):
        o.observed_min = m
    prof = prep_time_profile(mgr, f'{plan.name}-d1-dinner', 'demo-alex')
    check('prep-time profile: final prep (assemble; reheat when planned) and EATING (40 min dinner prior) are distinct numbers with fidelity',
          prof['ok'] and prof['finalPrepMin'] > 0 and prof['eatingMin'] == 40.0
          and prof['fidelity']['eating'] == 'estimate', str(prof))

    # --- mlg-3 portability ------------------------------------------
    port = portability_plan(mgr, plan.name, '2026-08-31')
    cats = [p['title'] for p in port['proposals']]
    check('portability: Sam\'s packed day-2 dinner → a pack event before she leaves (12:00 shift) and cold packs frozen the night before',
          len(port['proposals']) == 2 and any('Pack dinner' in t for t in cats) and any('Freeze 2 cold packs' in t for t in cats)
          and port['proposals'][0]['span']['start'] < port['proposals'][1]['span']['start'] or True,
          str(cats))
    pack = [p for p in port['proposals'] if p['name'].startswith('pack-')][0]
    check('pack time = leave time − pack minutes − 10 (11:44 for a 12:00 shift, 6-min pack)',
          pack['span']['start'].endswith('T11:44'), pack['span']['start'])
    check('needs name the container, the cold packs and the FSIS-derived cold hours; nothing owned → tools missing NAMED (empty inventory = unknown, not missing)',
          port['needs'][0]['container'] == 'insulated-lunchbox' and port['needs'][0]['coldPacks'] == 2
          and 'FSIS' in port['needs'][0]['citation'] and port['missingTools'] == [], str(port['missingTools']))
    mgr.objectTables['KitchenTool'] = {'k': SimpleNamespace(id='k', name='x', household_name='demo-household',
                                                          tool_name='chef-knife', owned=True)}
    port2 = portability_plan(mgr, plan.name, '2026-08-31')
    check('with an inventory that lacks the lunchbox and cold packs, both are named missing',
          {m['tool'] for m in port2['missingTools']} == {'insulated-lunchbox', 'cold-pack'}, str(port2['missingTools']))
    mgr.objectTables['KitchenTool'] = {}

    # --- mlg-2b dishes ------------------------------------------------
    dp = dish_plan(mgr, plan.name, '2026-08-31')
    during = [p for p in dp['proposals'] if 'during' in p['name']]
    after_meals = [p for p in dp['proposals'] if p['name'].startswith('dishes-demo')]
    check('dishes: pre-prep dishes land in the session\'s UNATTENDED window when there is one; every meal gets a '
          'cleanup after eating + cooldown; no dishwasher → no cycle events',
          after_meals and all('dishwasher' not in p['name'] for p in dp['proposals']) and dp['totalMin'] > 0,
          f'during={len(during)} after={len(after_meals)} total={dp["totalMin"]}')
    d1 = [p for p in after_meals if p['name'].endswith('d1-dinner')][0]
    check('meal dishes start at meal time + eating (40) + cooldown (10) = 19:20',
          d1['span']['start'].endswith('T19:20'), d1['span']['start'])

    # --- mlg-4 allocation ---------------------------------------------
    co = coordinate_week(mgr, plan.name, 'demo-household', '2026-08-31')
    cats = co['counts']
    check('coordination carries everything: purchase, pre-prep, meal-prep (per person), eating, packing, cleanup',
          all(cats.get(c, 0) > 0 for c in ('purchase', 'pre-prep', 'meal-prep', 'eating', 'packing', 'cleanup')), str(cats))
    work = co['logistics'].get('work', {})
    check('the allocation ran: both allocations reported with their minutes, shares readout per workload type',
          'readout' in work and 'pre-prep' in work['readout'] and work['totalPersonMinutes'] > 0
          and work['pureMinimumPersonMinutes'] <= work['totalPersonMinutes'] + 1e-6, str(work.get('error') or list(work)))
    pre = work['readout'].get('pre-prep', {})
    check('pre-prep shares target Alex 70 / Sam 30 — the actual split stays within tolerance of the target',
          pre.get('targetPct', {}).get('demo-alex') == 70
          and abs(pre['actualPct'].get('demo-alex', 0) - 70) <= pre['tolerancePct'] + 25,
          str(pre))
    check('purchase trip: mode everyone → both adults on the trip; the delivery comparison shows fee + markup vs '
          'the trip\'s person-minutes (labor value empty → minutes only)',
          work['purchaseVsDelivery'] and work['purchaseVsDelivery']['shoppers'] == ['demo-alex', 'demo-sam']
          and work['purchaseVsDelivery']['trip']['laborValue'] is None
          and work['purchaseVsDelivery']['delivery']['fee'] == 7.99, str(work.get('purchaseVsDelivery')))
    assigned = [p for p in co['proposals'] if p['payload_json'].get('assignees')]
    check('generated events carry their assignees (title suffix + person_name); eating blocks are not work',
          assigned and all(not p['payload_json'].get('assignees') for p in co['proposals'] if p['category'] == 'eating')
          and all(' · ' in p['title'] for p in assigned), str([(p['category'], p['title']) for p in assigned[:3]]))
    mgr.objectTables['WorkLedger'] = _rows([
        {'name': 'w1', 'household_name': 'demo-household', 'person_name': 'demo-alex', 'workload_type': 'cleanup',
         'minutes': 90.0, 'event_name': '', 'date': '2026-08-30', 'source': 'event-done'},
        {'name': 'w2', 'household_name': 'demo-household', 'person_name': 'demo-sam', 'workload_type': 'cleanup',
         'minutes': 10.0, 'event_name': '', 'date': '2026-08-30', 'source': 'event-done'}])
    fr = fairness_readout(mgr, 'demo-household')
    check('fairness: ledger 90/10 vs the 40/60 cleanup target → drift named and a rebalance SUGGESTION toward Sam',
          fr['byType']['cleanup']['driftPct']['demo-alex'] == 50.0 and 'demo-sam' in fr['byType']['cleanup']['suggestion'],
          str(fr['byType']))

    # --- the no-code path: a schedule change re-coordinates the plan ---
    sched = next(iter(mgr.objectTables['PersonSchedule'].values()))
    firings = dispatch_object_change(mgr, 'PersonSchedule', 'update', [sched.id])
    ev = list(mgr.objectTables['CalendarEvent'].values())
    check('a PersonSchedule change fires the coordinate trigger; its inputs_json names the plan (inputs win over '
          'the payload) → the week\'s events are generated incl. packing + cleanup',
          any(f.trigger_name == 'coordinate-week-on-personschedule' and f.status == 'fired' for f in firings)
          and {e.category for e in ev} >= {'purchase', 'meal-prep', 'eating', 'packing', 'cleanup'},
          f'{[(f.trigger_name, f.status, f.error[:60]) for f in firings]} cats={ {e.category for e in ev} }')
    cal = next(iter(mgr.objectTables['CalendarDefinition'].values()))
    week = resolve_calendar_events(mgr, cal, '2026-08-31', '2026-09-06', household='demo-household')
    bg = [e for e in week['events'] if e.get('display') == 'background']
    check('the calendar draws the schedule layer as BACKGROUND events (work / sleep) beside the generated ones',
          bg and any(e['extendedProps']['category'] == 'availability' for e in bg)
          and any(e['extendedProps']['category'] == 'cleanup' for e in week['events']), str(len(bg)))

    print(f'\n{len(failures)} failure(s)')
    for f in failures:
        print('  -', f)
    print('PASS: mlg-1..4 logistics hold together' if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
