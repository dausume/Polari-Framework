"""
@module nutrition.selftest_weekreview

N5 selftest — the weekly review composed from the existing analyses on
a fake manager: a partially planned week, two intake days, one waste
row, one budget row, ledger rows for two people → headline numbers,
every section present (lines or an honest "no data" line), proposals
non-empty, honesty naming the priors; the review-event proposal sits
on a Sunday; the page seeds hold (rows sum to 12, ids unique, embeds
name seeded definitions, panel paths are ours, the form links our
solution); the accept solution and the Sunday trigger run through the
REAL engine and dedupe by name.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_weekreview
"""

import json
import sys
from datetime import datetime
from types import SimpleNamespace

from mealoptions import MEALOPTIONS_SEED_PAIRS
from nutrition import weekreview_seed as ws
from nutrition.budget_basis import SEED_PLAN_BUDGETS
from nutrition.calendar_seed import (
    SEED_MEALPLAN_ANALYSES, SEED_MEALPLAN_CALENDARS,
    SEED_MEALPLAN_EVENT_DEFINITIONS, SEED_MEALPLAN_SOLUTIONS,
)
from nutrition.fdc_seed import SEED_FDC_FOOD_ITEMS, SEED_FDC_NUTRIENT_CONTENTS
from nutrition.intake_basis import SEED_INTAKE_RECORDS
from nutrition.logistics_basis import HOUSEHOLD_SEED_PAIRS, LOGISTICS_SEED_PAIRS
from nutrition.market_basis import (
    SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS, SEED_UNIT_WEIGHTS,
)
from nutrition.meal_basis import (
    SEED_MEAL_ENTRIES, SEED_MEAL_PLANS, SEED_MEAL_TEMPLATES, SEED_VARIATIONS,
)
from nutrition.pantry_basis import SEED_PANTRY_ITEMS
from nutrition.person_seed import SEED_HOUSEHOLDS, SEED_PERSONS
from nutrition.purchase_basis import SEED_BULK_STAPLES
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from nutrition.threshold_basis import SEED_EATING_PATTERNS
from nutrition.tolerance_basis import SEED_TOLERANCE_THRESHOLDS
from nutrition.waste_basis import SEED_WASTE_RECORDS
from nutrition.weekreview_analysis import (
    PRIORS, SECTIONS, next_week_proposals, week_review, weekly_review_event_proposal,
)
from nutrition.weekreview_api import ROUTES
from polariApiServer import mealplan_pages_seed as mp
from polariNoCode import graph_builder as gb
from polariNoCode.calendar_events import SEED_CORE_EVENT_DEFINITIONS
from polariNoCode.event_dispatcher import get_dispatcher

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


def _ledger(i, person, wtype, minutes, day):
    return {'name': f'wl-{i}', 'household_name': 'demo-household', 'person_name': person,
            'workload_type': wtype, 'minutes': minutes, 'event_name': '', 'date': day,
            'source': 'selftest', 'is_prior': False, 'provenance_id': 'selftest', 'notes': ''}


def _manager():
    tables = {
        'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS), 'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
        'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS), 'PantryItem': _rows(SEED_PANTRY_ITEMS),
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS), 'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES), 'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES), 'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows(SEED_MEAL_PLANS), 'MealEntry': _rows(SEED_MEAL_ENTRIES),
        'PersonProfile': _rows(SEED_PERSONS), 'HouseholdProfile': _rows(SEED_HOUSEHOLDS),
        'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
        'ToleranceThreshold': _rows(SEED_TOLERANCE_THRESHOLDS),
        'IntakeRecord': _rows(SEED_INTAKE_RECORDS),          # Aug 31 + Sep 1 for demo-alex
        'WasteRecord': _rows(SEED_WASTE_RECORDS + [
            {'name': 'w-chicken', 'household_name': 'demo-household', 'food_name': 'chicken-breast-raw',
             'quantity': 1.0, 'unit': 'lb', 'reason': 'over-prepped', 'date': '2026-09-02',
             'pantry_item_name': '', 'is_prior': False, 'provenance_id': '', 'notes': ''}]),
        'PlanBudget': _rows(SEED_PLAN_BUDGETS),
        'BulkStaple': _rows(SEED_BULK_STAPLES),
        'WeightObservation': {}, 'NutrientReference': {}, 'DietaryNutrient': {}, 'PersonThreshold': {},
        'KitchenTool': {}, 'MethodPreference': {}, 'PeriodIntakeMetric': {},
        'EventDefinition': _rows(SEED_CORE_EVENT_DEFINITIONS + SEED_MEALPLAN_EVENT_DEFINITIONS),
        'CalendarDefinition': _rows(SEED_MEALPLAN_CALENDARS),
        'AnalysisDefinition': _rows(SEED_MEALPLAN_ANALYSES + ws.SEED_WEEKREVIEW_ANALYSES),
        'SolutionDefinition': _rows(SEED_MEALPLAN_SOLUTIONS + ws.SEED_WEEKREVIEW_SOLUTIONS),
        'EventTrigger': _rows(ws.SEED_WEEKREVIEW_TRIGGERS),   # ours only: no re-coordination noise
        'TriggerFiring': {}, 'CalendarEvent': {},
    }
    for cls, _c, seeds in HOUSEHOLD_SEED_PAIRS + LOGISTICS_SEED_PAIRS + MEALOPTIONS_SEED_PAIRS:
        tables[cls] = _rows(seeds)
    tables['WorkLedger'] = _rows([
        _ledger(0, 'demo-alex', 'pre-prep', 90.0, '2026-09-01'),
        _ledger(1, 'demo-sam', 'pre-prep', 20.0, '2026-09-02'),
        _ledger(2, 'demo-alex', 'meal-prep', 15.0, '2026-09-02'),
        _ledger(3, 'demo-sam', 'meal-prep', 15.0, '2026-09-03'),
    ])
    return SimpleNamespace(objectTables=tables, db=_DB())


def _items(page):
    for row in json.loads(page['definition'])['rows']:
        for item in row['items']:
            yield row, item


def main():
    mgr = _manager()
    print('N5 — the weekly review')

    # --- the analysis ---------------------------------------------
    rv = week_review(mgr, 'demo-alex-week', 'demo-household', today='2026-09-03')
    check('review window = the plan\'s own days (Sep 1–3) when week_start is blank',
          rv['ok'] and rv['weekStart'] == '2026-09-01' and rv['weekEnd'] == '2026-09-03', str(rv.get('weekStart')))
    check('headline: 18 expected, 10 planned (the 5 household-wide entries × 2 people), coverage 55.6 %',
          rv['expectedSlots'] == 18 and rv['plannedSlots'] == 10 and rv['coveragePct'] == 55.6,
          f"{rv['expectedSlots']} {rv['plannedSlots']} {rv['coveragePct']}")
    check('eaten: Alex\'s Sep 1 breakfast + dinner are in the window; both planned → 2 eaten as planned, '
          '0 off-plan; adherence 20 % of the 10 planned',
          rv['eatenSlots'] == 2 and rv['plannedEatenSlots'] == 2 and rv['unplannedEatenSlots'] == 0
          and rv['adherencePct'] == 20.0, f"{rv['eatenSlots']} {rv['plannedEatenSlots']} {rv['adherencePct']}")
    sections = {l['section'] for l in rv['lines']}
    check('every section is present with lines', set(SECTIONS) <= sections, str(sections))
    check('each line is a flat record (section, subject, text, number, unit, basis)',
          all(set(l) == {'section', 'subject', 'text', 'number', 'unit', 'basis'} for l in rv['lines']))
    check('cost vs budget: the estimate and the $60/week cap prorated to 3 days; the verdict is stated',
          rv['costEstimate'] is not None and rv['budget'] == round(60.0 / 7 * 3, 2)
          and ('within budget' in rv['budgetDeltaText'] or 'over budget' in rv['budgetDeltaText']),
          f"{rv['costEstimate']} {rv['budget']} {rv['budgetDeltaText']}")
    check('waste is WINDOWED: the Sep 2 chicken (453.6 g) counts, the Aug 30 spinach does not',
          abs(rv['wasteGrams'] - 453.6) < 0.5 and not any('spinach' in l['subject'] for l in rv['lines']
                                                            if l['section'] == 'waste'),
          str(rv['wasteGrams']))
    fair = [l for l in rv['lines'] if l['section'] == 'fairness']
    check('fairness: pre-prep 90/20 min vs the 70/30 shares → drift named with a rebalance suggestion; '
          'meal-prep 15/15 vs 50/50 → no drift',
          any('pre-prep' in l['subject'] and 'rebalance' in l['text'] for l in fair)
          and any('meal-prep' in l['subject'] and abs(l['number']) < 1 for l in fair), str(fair)[:200])
    intake = [l for l in rv['lines'] if l['section'] == 'intake']
    check('intake: Alex\'s week is low-confidence (1 logged day in the window) and says so; Sam has no data; '
          'no "consistently" pattern is claimed from that',
          any(l['subject'] == 'demo-alex' and 'low-confidence' in l['text'] for l in intake)
          and any(l['subject'] == 'no data' and 'demo-sam' in l['text'] for l in intake)
          and rv['consistentlyText'] == 'no pattern yet', str(intake)[:300])
    check('a verdict against the person\'s OWN line reads as a comfort reading, never diagnosis',
          all('unhealthy' not in l['text'] for l in rv['lines'])
          and any('your line' in l['text'] for l in intake))
    check('proposals: the next-week purchase (Saturday 10:00 prior) + the next Sunday review; records '
          'carry kind / title / whenText / costText',
          rv['proposalCount'] >= 2 and {p['kind'] for p in rv['proposals']} >= {'purchase', 'review'}
          and all({'kind', 'title', 'whenText', 'costText'} <= set(p) for p in rv['proposals']),
          str(rv['proposals']))
    check('honesty names every prior (window, planned-vs-eaten, consistently, cost, waste, fairness, '
          'next week, review time)',
          [h['prior'] for h in rv['honesty']] == [k for k, _ in PRIORS]
          and any('week_coverage' in h['text'] for h in rv['honesty'])
          and any('fairness_readout' in h['text'] for h in rv['honesty']))
    check('no dict-of-dicts / empty dict at the top level (api-structured-panel safe)',
          all(not isinstance(v, dict) for v in rv.values())
          and all(v != {} and v != [] for k, v in rv.items()))

    # an EMPTY household: every section says "no data" rather than inventing
    empty = SimpleNamespace(objectTables={'HouseholdMember': {}, 'MealPlanDefinition': {}}, db=_DB())
    ev = week_review(empty, 'nope', 'nobody', week_start='2026-09-02')
    check('with no rows at all every section still answers with an honest "no data" line',
          ev['ok'] and not ev['planFound'] and set(SECTIONS) <= {l['section'] for l in ev['lines']}
          and all(any(l['subject'] == 'no data' for l in ev['lines'] if l['section'] == s)
                  for s in ('coverage', 'intake', 'cost', 'waste', 'fairness'))
          and ev['weekStart'] == '2026-08-31', str([(l['section'], l['subject']) for l in ev['lines']]))

    # --- next week + the review event -----------------------------
    nxt = next_week_proposals(mgr, 'demo-alex-week', 'demo-household', today='2026-09-03')
    check('next week = the Monday-start week after the plan\'s (Sep 7–13); the purchase lands on the '
          'Saturday before it (Sep 5) 10:00–11:00',
          nxt['nextWeekStart'] == '2026-09-07' and nxt['nextWeekEnd'] == '2026-09-13'
          and nxt['purchaseDate'] == '2026-09-05'
          and any(p['category'] == 'purchase' and p['span']['start'] == '2026-09-05T10:00'
                  for p in nxt['proposals']),
          f"{nxt['nextWeekStart']} {nxt['purchaseDate']}")
    check('bulk buys appear only when a cadence\'s 1st falls in that week (Sep 7–13: none)',
          not any(p['category'] == 'bulk-purchase' for p in nxt['proposals']))
    oct_ = next_week_proposals(mgr, 'demo-alex-week', 'demo-household', week_start='2026-09-22', today='2026-09-03')
    check('a week containing Oct 1 (Sep 28–Oct 4) proposes the MONTHLY bulk buy only — the 3/6/12-month '
          'cadences count from September (the bulk triggers\' rangeStart), so they are not due',
          [p['payload_json']['cadenceMonths'] for p in oct_['proposals'] if p['category'] == 'bulk-purchase'] == [1],
          str([(p['category'], p['name']) for p in oct_['proposals']]))
    dec = next_week_proposals(mgr, 'demo-alex-week', 'demo-household', week_start='2026-11-24', today='2026-09-03')
    check('a week containing Dec 1 proposes the monthly AND the 3-month bulk buys',
          sorted(p['payload_json']['cadenceMonths'] for p in dec['proposals'] if p['category'] == 'bulk-purchase') == [1, 3],
          str([(p['category'], p['name']) for p in dec['proposals']]))
    rev = weekly_review_event_proposal(mgr, 'demo-alex-week', 'demo-household', today='2026-09-03')
    e = rev['proposals'][0]
    check('the review-event proposal: category review, on the SUNDAY closing the week (Sep 6) 18:00–18:45, '
          'the headline as payload',
          e['category'] == 'review' and e['span'] == {'start': '2026-09-06T18:00', 'end': '2026-09-06T18:45'}
          and datetime.fromisoformat(e['span']['start']).weekday() == 6
          and e['payload_json']['plannedSlots'] == 10, str(e['span']))
    rev2 = weekly_review_event_proposal(mgr, 'demo-alex-week', 'demo-household',
                                        review_date='2026-09-13T17:00', review_time='19:30', today='2026-09-03')
    check('the trigger\'s occurrence (a Sunday 17:00) reviews THAT week and the review_time knob moves the hour',
          rev2['weekStart'] == '2026-09-07' and rev2['proposals'][0]['span']['start'] == '2026-09-13T19:30',
          str(rev2['proposals'][0]['span']))

    # --- the page seeds -------------------------------------------
    print('\npage seeds')
    pages = ws.SEED_WEEKREVIEW_PAGE_DISPLAYS
    check('one page at mealplan/review', len(pages) == 1 and pages[0]['pageRoute'] == 'mealplan/review')
    rows = json.loads(pages[0]['definition'])['rows']
    check('every row\'s items sum to 12 segments',
          all(sum(i['rowSegmentsUsed'] for i in r['items']) == 12 for r in rows),
          str([sum(i['rowSegmentsUsed'] for i in r['items']) for r in rows]))
    ids = [i['id'] for _r, i in _items(pages[0])]
    check('item ids unique (and prefixed wr- so they never collide with the other pages)',
          len(ids) == len(set(ids)) and all(i.startswith('wr-') for i in ids))
    tables = {t['name']: t for t in mp.SEED_MEALPLAN_TABLES + ws.SEED_WEEKREVIEW_TABLES}
    graphs = {g['name']: g for g in mp.SEED_MEALPLAN_GRAPHS + ws.SEED_WEEKREVIEW_GRAPHS}
    bad = []
    for _r, item in _items(pages[0]):
        if item.get('type') == 'form':
            if item['item']['linkedSolutionName'] not in {s['name'] for s in ws.SEED_WEEKREVIEW_SOLUTIONS}:
                bad.append(item['id'])
            continue
        comp = item['componentProps']['componentName']
        inputs = item['componentProps']['inputs']
        if comp == 'embeddedTable':
            target = mp.EMBED_TARGETS.get(item['id'])
            if not target or target[1] not in tables or tables[target[1]]['source_class'] != inputs['className']:
                bad.append(item['id'])
        elif comp == 'embeddedGraph':
            if inputs['graphName'] not in graphs or graphs[inputs['graphName']]['source_class'] != inputs['className']:
                bad.append(item['id'])
        elif comp == 'api-structured-panel':
            if not inputs['path'].startswith(ROUTES[0]) or (not inputs['pick'] and not inputs['hideKeys']):
                bad.append(item['id'])
        else:
            bad.append(item['id'])
    check('every embed names a seeded TableDefinition / GraphDefinition (by NAME, reused), every '
          'structured panel reads OUR route with pick/hideKeys, the form links OUR solution', not bad, str(bad))
    check('AnalysisDefinitions name the three functions with resolvable callable_refs',
          {a['callable_ref'] for a in ws.SEED_WEEKREVIEW_ANALYSES} == {
              'nutrition.weekreview_analysis:week_review',
              'nutrition.weekreview_analysis:next_week_proposals',
              'nutrition.weekreview_analysis:weekly_review_event_proposal'})
    check('the Sunday trigger: schedule SU 17:00 → mealplan-weekly-review-event (a seeded solution)',
          ws.SEED_WEEKREVIEW_TRIGGERS[0]['source_kind'] == 'schedule'
          and json.loads(ws.SEED_WEEKREVIEW_TRIGGERS[0]['source_json'])['schedule']['byDay'] == ['SU']
          and ws.SEED_WEEKREVIEW_TRIGGERS[0]['solution_name'] in {s['name'] for s in ws.SEED_WEEKREVIEW_SOLUTIONS})

    # --- the solutions through the REAL engine --------------------
    print('\nno-code path (real engine)')
    sol = json.loads(ws.ACCEPT_NEXT_WEEK_SOLUTION['definition'])
    params = {'plan': 'demo-alex-week', 'household': 'demo-household', 'week_start': ''}
    t = gb.execute(sol, manager=mgr, params=params)
    events = list(mgr.objectTables['CalendarEvent'].values())
    check('the accept form solution (FormSubscription → AnalysisCall pick proposals → GenerateEvent → '
          'refreshDisplay) writes next week\'s purchase + review events',
          t.status == 'completed' and {e.category for e in events} >= {'purchase', 'review'}
          and len(events) == len(nxt['proposals']), f'{t.status} {t.error_summary} events={len(events)}')
    from polariNoCode.graph_compilers import final_context_of
    ctx = final_context_of(t) or {}
    check('… and asks the page to refresh (frontend event)',
          any(ev.get('name') == 'refreshDisplay' and ev.get('channel') == 'frontend'
              for ev in ctx.get('_emitted_events', [])))
    n = len(events)
    m1 = ctx.get('message')
    t2 = gb.execute(sol, manager=mgr, params=params)
    check('accepting again writes nothing twice (dedupe by name)',
          t2.status == 'completed' and len(mgr.objectTables['CalendarEvent']) == n)
    # the message the form shows (fix 2026-09-03: "Accept proposals" was silent)
    m2 = (final_context_of(t2) or {}).get('message')
    check(f'the first accept says "Created {n} events for the week of 2026-09-07 (…)" — context variable '
          '`message` + the refreshDisplay payload',
          isinstance(m1, str) and m1.startswith(f'Created {n} events for the week of 2026-09-07 (')
          and any(ev.get('payload', {}).get('message') == m1 for ev in ctx.get('_emitted_events', [])), str(m1))
    check(f'accepting again says "Created 0 events for the week of 2026-09-07; {n} already existed and kept"',
          m2 == f'Created 0 events for the week of 2026-09-07; {n} already existed and kept', str(m2))
    check('the review event row carries a JSON span on a Sunday and the headline payload',
          any(e.category == 'review' and json.loads(e.span)['start'].startswith('2026-09-13T18:00')
              and json.loads(e.payload_json).get('weekStart') == '2026-09-07'
              for e in mgr.objectTables['CalendarEvent'].values()),
          str([(e.name, e.span) for e in mgr.objectTables['CalendarEvent'].values() if e.category == 'review']))

    d = get_dispatcher(mgr)
    firings = d.tick(now=datetime(2026, 9, 6, 17, 30), lookback_seconds=3600)
    reviews = [e for e in mgr.objectTables['CalendarEvent'].values() if e.category == 'review']
    check('the weekly-review-sunday trigger (Sep 6 17:00 tick) fires the solution and writes THIS week\'s '
          'review event (Sep 6 18:00) via the proposal, stamped generated_by',
          any(f.status == 'fired' for f in firings)
          and any(json.loads(e.span)['start'] == '2026-09-06T18:00' and e.generated_by == 'weekly-review-sunday'
                  for e in reviews),
          f'{[(f.trigger_name, f.status, f.error) for f in firings]} {[(e.name, e.span) for e in reviews]}')
    m = len(mgr.objectTables['CalendarEvent'])
    d.tick(now=datetime(2026, 9, 6, 17, 30), lookback_seconds=3600)
    check('ticking the same occurrence again is idempotent (already fired + dedupe)',
          len(mgr.objectTables['CalendarEvent']) == m)

    print(f'\n{len(failures)} failure(s)')
    for f in failures:
        print('  -', f)
    print('PASS: N5 weekly review holds together' if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
