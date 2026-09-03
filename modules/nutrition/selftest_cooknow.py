"""
@module nutrition.selftest_cooknow

N4 selftest (check() style, no server): a fake manager with a 3-step
recipe (one unattended method carrying a hazard tag), two persons with
different speed factors and one safety floor → the minutes differ per
person, the floor binds, the unattended window carries the dish
suggestion, safety lines sit only on the hazard step; the step-done
proposal dedupes; the page seeds are configured displays (rows sum
to 12, ids unique, embeds/panels/forms resolve); the "Step done"
solution runs on the REAL engine and a DurationObservation appears.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_cooknow
"""

import json
import sys
from types import SimpleNamespace

from polariNoCode import graph_builder as gb

from nutrition.cooknow_analysis import cook_sheet, step_done_proposal
from nutrition import cooknow_seed as cs
from nutrition.cooknow_api import CookNowAPI

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures, passes = [], []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    (passes if cond else failures).append(label)


def _rows(seed_list):
    return {f'{i}': SimpleNamespace(id=f'{i}', **r) for i, r in enumerate(seed_list)}


class _DB:
    def saveInstanceInDB(self, inst):
        return True


def _manager():
    recipe = 'test-bowl'
    tables = {
        'PersonProfile': _rows([{'name': 'fast'}, {'name': 'novice'}]),
        'HouseholdMember': _rows([
            {'name': 'hh-fast', 'household_name': 'hh', 'person_name': 'fast'},
            {'name': 'hh-novice', 'household_name': 'hh', 'person_name': 'novice'}]),
        'MealTemplate': _rows([{'name': 'test-dinner', 'recipe_names_json': json.dumps([recipe])}]),
        'VariationDefinition': _rows([
            {'name': 'test-dinner-base', 'template_name': 'test-dinner', 'swaps_json': '[]'},
            {'name': 'test-dinner-tofu', 'template_name': 'test-dinner',
             'swaps_json': json.dumps([{'from_food': 'chicken', 'to_food': 'tofu', 'grams': 120}])}]),
        'Recipe': _rows([{'name': recipe, 'servings': 2.0}]),
        'IngredientLine': _rows([
            {'name': f'{recipe}-chicken', 'recipe_name': recipe, 'food_name': 'chicken', 'grams': 300.0,
             'method': 'baked', 'prep_note': 'sliced', 'order': 1},
            {'name': f'{recipe}-onion', 'recipe_name': recipe, 'food_name': 'onion', 'grams': 100.0,
             'method': 'raw', 'prep_note': '', 'order': 2},
            {'name': f'{recipe}-broccoli', 'recipe_name': recipe, 'food_name': 'broccoli', 'grams': 200.0,
             'method': 'steamed', 'prep_note': '', 'order': 3},
            {'name': f'{recipe}-oil', 'recipe_name': recipe, 'food_name': 'oil', 'grams': 15.0,
             'method': 'raw', 'prep_note': '', 'order': 4}]),
        'CookingStep': _rows([
            {'name': f'{recipe}-step-1', 'recipe_name': recipe, 'order': 1,
             'instruction': 'Dice the onion.', 'method': 'raw', 'duration_min': 4.0},
            {'name': f'{recipe}-step-2', 'recipe_name': recipe, 'order': 2,
             'instruction': 'Bake the chicken on a sheet pan.', 'method': 'baked', 'duration_min': 25.0},
            {'name': f'{recipe}-step-3', 'recipe_name': recipe, 'order': 3,
             'instruction': 'Steam the broccoli; toss with the oil.', 'method': 'steamed', 'duration_min': 6.0}]),
        'StepMethod': _rows([
            {'name': 'dice-knife', 'task_kind': 'dice', 'display_name': 'Hand-dice', 'tool_name': 'chef-knife',
             'base_min': 2.0, 'per_100g_min': 1.5, 'skill_floor': '', 'attended': True},
            {'name': 'bake-oven', 'task_kind': 'bake', 'display_name': 'Bake', 'tool_name': 'oven',
             'base_min': 6.0, 'per_100g_min': 0.2, 'skill_floor': '', 'attended': False},
            {'name': 'steam-pot', 'task_kind': 'steam', 'display_name': 'Steam', 'tool_name': 'pot',
             'base_min': 4.0, 'per_100g_min': 0.4, 'skill_floor': '', 'attended': True}]),
        # ONE hazard step (bake-oven) and ONE safety floor (the bake's
        # hands-on part can never take under 5 min at any skill).
        'MethodSkillRequirement': _rows([
            {'name': 'req-dice-knife', 'method_name': 'dice-knife',
             'skills_json': json.dumps([{'skill': 'knife-work', 'floor': ''}]),
             'safety_floor_min': 0.0, 'hazard_tags_json': '[]'},
            {'name': 'req-bake-oven', 'method_name': 'bake-oven',
             'skills_json': json.dumps([{'skill': 'baking', 'floor': ''}]),
             'safety_floor_min': 5.0, 'hazard_tags_json': json.dumps(['hot-surface'])},
            {'name': 'req-steam-pot', 'method_name': 'steam-pot',
             'skills_json': json.dumps([{'skill': 'heat-control', 'floor': ''}]),
             'safety_floor_min': 0.0, 'hazard_tags_json': '[]'}]),
        'SafetyRule': _rows([
            {'name': 'rule-hot-surface', 'hazard_tag': 'hot-surface', 'skill_name': 'kitchen-safety',
             'required_level': 'intermediate', 'below_floor': 'supervised',
             'rule_text': 'oven mitts, announce hot pans', 'citation': 'FSIS kitchen companion (prior)'}]),
        'PersonSkill': _rows([
            {'name': 'fast-baking', 'person_name': 'fast', 'skill_name': 'baking', 'level': 'experienced',
             'speed_factor': 0.8, 'fidelity': 'estimate'},
            {'name': 'fast-knife', 'person_name': 'fast', 'skill_name': 'knife-work', 'level': 'experienced',
             'speed_factor': 0.8, 'fidelity': 'estimate'},
            {'name': 'fast-heat', 'person_name': 'fast', 'skill_name': 'heat-control', 'level': 'experienced',
             'speed_factor': 0.8, 'fidelity': 'estimate'},
            {'name': 'fast-safety', 'person_name': 'fast', 'skill_name': 'kitchen-safety',
             'level': 'experienced', 'speed_factor': 0.8, 'fidelity': 'estimate'},
            {'name': 'novice-baking', 'person_name': 'novice', 'skill_name': 'baking', 'level': 'novice',
             'speed_factor': 1.3, 'fidelity': 'estimate'},
            {'name': 'novice-safety', 'person_name': 'novice', 'skill_name': 'kitchen-safety',
             'level': 'novice', 'speed_factor': 1.3, 'fidelity': 'estimate'}]),
        'DishStrategy': _rows([
            {'name': 'wash-as-you-go', 'needs_tool': '', 'min_per_load_unit': 1.5, 'setup_min': 2.0,
             'cycle_min': 0.0, 'unload_min': 0.0, 'timing': 'unattended-first'}]),
        'HouseholdDishPolicy': _rows([
            {'name': 'hh-dishes', 'household_name': 'hh', 'preprep_strategy': 'wash-as-you-go',
             'meal_strategy': 'batch-after-meal', 'cooldown_after_eating_min': 10.0}]),
        'MealEntry': _rows([
            {'name': 'wk-d1-dinner', 'plan_name': 'wk', 'day_index': 1, 'slot': 'dinner',
             'template_name': 'test-dinner', 'variation_name': 'test-dinner-base', 'scale': 2.5,
             'serving_split_json': json.dumps({'fast': 1.5, 'novice': 1.0})}]),
        'CalendarEvent': _rows([
            {'name': 'prep-wk-d1-dinner', 'category': 'meal-prep', 'person_name': 'fast',
             'span': json.dumps({'start': '2026-09-03T18:00', 'end': '2026-09-03T18:30'})}]),
        'DurationObservation': {}, 'KitchenTool': {}, 'MethodPreference': {},
        'AnalysisDefinition': _rows(cs.SEED_COOKNOW_ANALYSES),
        'SolutionDefinition': _rows(cs.SEED_COOKNOW_SOLUTIONS),
        'EventTrigger': {}, 'TriggerFiring': {},
    }
    return SimpleNamespace(objectTables=tables, db=_DB())


def _items(page):
    for row in json.loads(page['definition'])['rows']:
        for item in row['items']:
            yield row, item


def main():
    mgr = _manager()
    print('N4 cook now')

    # --- the sheet, per person ------------------------------------------
    fast = cook_sheet(mgr, 'test-dinner', 'fast')
    nov = cook_sheet(mgr, 'test-dinner', 'novice')
    check('cook sheet: ok, 3 ordered steps, every step a flat record with text/method/tool/minutes/basis',
          fast['ok'] and [s['step'] for s in fast['steps']] == [1, 2, 3]
          and all(isinstance(s[k], (str, int, float, bool)) for s in fast['steps'] for k in s),
          str(fast.get('error')))
    check('no dict-of-dicts / empty dict at the top level (api-structured-panel renderable)',
          not any(isinstance(v, dict) for v in fast.values()) and all(v != {} for v in fast.values()))
    check('methods resolved: raw "dice" keyword → dice-knife, baked → bake-oven, steamed → steam-pot',
          [s['method'] for s in fast['steps']] == ['dice-knife', 'bake-oven', 'steam-pot'],
          str([s['method'] for s in fast['steps']]))
    f2, n2 = fast['steps'][1], nov['steps'][1]
    check('minutes differ per person: the experienced cook is faster on every skilled step',
          fast['steps'][0]['plannedMin'] < nov['steps'][0]['plannedMin']
          and f2['plannedMin'] < n2['plannedMin']
          and fast['attendedMin'] < nov['attendedMin'],
          f"fast={[s['plannedMin'] for s in fast['steps']]} novice={[s['plannedMin'] for s in nov['steps']]}")
    check('the bake\'s hands-on part = StepMethod.base_min × factor: novice 6×1.3 = 7.8, '
          'experienced 6×0.8 = 4.8 → raised to the 5 min safety floor (the floor binds)',
          n2['plannedMin'] == 7.8 and not n2['boundedBySafety']
          and f2['plannedMin'] == 5.0 and f2['boundedBySafety']
          and 'safety floor' in f2['minutesBasis'],
          f'{f2["plannedMin"]} {f2["boundedBySafety"]} {n2["plannedMin"]}')
    check('the novice is "supervised" on the hazard step (kitchen-safety novice < intermediate), '
          'the experienced cook works alone — words, no judgement',
          n2['safety'] == 'supervised' and f2['safety'] == 'alone'
          and nov['steps'][0]['safety'] == 'alone')
    check('unattended step carries the window: recipe 25 min − 6 hands-on = 19 min timer',
          not f2['attended'] and f2['unattendedWindowMin'] == 19.0 and f2['timerMin'] == 19.0
          and fast['steps'][0]['unattendedWindowMin'] == 0.0 and fast['steps'][2]['attended'])
    check('the window carries the "do dishes now" suggestion from the household\'s pre-prep '
          'strategy (wash-as-you-go, unattended-first): 2 + 1.5 × 2 tools = 5 min inside the 19',
          len(fast['dishLines']) == 1 and fast['dishLines'][0]['step'] == 2
          and fast['dishLines'][0]['dishMinutes'] == 5.0 and 'do dishes now' in f2['dishSuggestion']
          and fast['dishStrategy'] == 'wash-as-you-go', str(fast['dishLines']))
    check('safety lines only on the hazard step (hot-surface: the SafetyRule words, cited)',
          [l['step'] for l in fast['safetyLines']] == [2]
          and 'oven mitts' in fast['safetyLines'][0]['line'] and fast['safetyLines'][0]['citation']
          and f2['hazards'] == 'hot-surface' and not fast['steps'][0]['safetyLines']
          and not fast['steps'][2]['safetyLines'])
    check('totals: attended = sum of planned; unattended = the window; wall clock = later of the '
          'attended work and the window end (steam runs inside the bake window)',
          fast['attendedMin'] == round(sum(s['plannedMin'] for s in fast['steps']), 1)
          and fast['unattendedMin'] == 19.0
          and fast['wallClockMin'] == max(fast['attendedMin'], fast['steps'][1]['endsAtMin'] + 19.0),
          f"{fast['attendedMin']} {fast['unattendedMin']} {fast['wallClockMin']}")
    check('ingredients per step: chicken with the bake, onion with the dice, broccoli + the raw oil '
          'with the last step; grams scaled by the person\'s serving split (fast 1.5 of 2 servings)',
          [(i['step'], i['food']) for i in fast['ingredients']]
          == [(1, 'onion'), (2, 'chicken'), (3, 'broccoli'), (3, 'oil')]
          and fast['portion'] == 1.5 and 'wk-d1-dinner' in fast['portionBasis']
          and next(i for i in fast['ingredients'] if i['food'] == 'chicken')['gramsForPerson'] == 225.0
          and next(i for i in nov['ingredients'] if i['food'] == 'chicken')['gramsForPerson'] == 150.0,
          str([(i['step'], i['food'], i['gramsForPerson']) for i in fast['ingredients']]))
    tofu = cook_sheet(mgr, 'test-dinner', 'fast', 'test-dinner-tofu')
    check('a variation swaps the line (chicken → tofu 120 g) and says so',
          tofu['ok'] and any(i['food'] == 'tofu' and i['gramsAsWritten'] == 120.0 and 'swap' in i['swap']
                             for i in tofu['ingredients']))
    nobody = cook_sheet(mgr, 'test-dinner', 'nobody')
    check('a person no MealEntry names gets one serving, labelled; no skill rows → novice prior, labelled',
          nobody['portion'] == 1.0 and 'no MealEntry' in nobody['portionBasis']
          and 'novice' in nobody['steps'][1]['minutesBasis'])
    ev = cook_sheet(mgr, 'test-dinner', 'fast', event='prep-wk-d1-dinner')
    check('readyBy from the event\'s span end; startBy = readyBy − wall clock',
          ev['readyBy'] == '2026-09-03T18:30' and ev['startBy'].startswith('2026-09-03T')
          and ev['event'] == 'prep-wk-d1-dinner', str((ev['readyBy'], ev['startBy'])))
    check('unknown template / variation refuse by name with empty lists',
          not cook_sheet(mgr, 'nope', 'fast')['ok'] and cook_sheet(mgr, 'nope', 'fast')['steps'] == []
          and not cook_sheet(mgr, 'test-dinner', 'fast', 'nope')['ok'])

    # --- step done → DurationObservation proposal + the suggestion -------
    p = step_done_proposal(mgr, 'test-dinner', 2, 'fast', 6.5, '2026-09-03')
    check('step-done proposal: one DurationObservation row (prep-step, bake-oven, baking, 6.5 min), '
          'dedupe name <person>-<template>-<step>-<date>, delta vs planned',
          p['ok'] and len(p['proposals']) == 1
          and p['proposals'][0]['name'] == 'fast-test-dinner-2-2026-09-03'
          and p['proposals'][0]['method_name'] == 'bake-oven' and p['proposals'][0]['skill_name'] == 'baking'
          and p['proposals'][0]['observed_min'] == 6.5 and p['proposals'][0]['kind'] == 'prep-step'
          and p['deltaMin'] == 1.5, str(p.get('error')))
    check('the suggestion counts this observation but writes nothing: 1 observation → "needs 2 more"; '
          'applied=False; the manager\'s table is untouched',
          p['applied'] is False and p['suggestionLines'] and 'needs 2 more' in p['suggestionLines'][0]['status']
          and not mgr.objectTables['DurationObservation'])
    p_same = step_done_proposal(mgr, 'test-dinner', '2', 'fast', '7', '2026-09-03')
    check('the same step on the same day proposes the same name (dedupe) — string form values accepted',
          p_same['ok'] and p_same['proposals'][0]['name'] == p['proposals'][0]['name'])
    bad = step_done_proposal(mgr, 'test-dinner', 2, 'fast', 0, 'not-a-date')
    bad_step = step_done_proposal(mgr, 'test-dinner', 9, 'fast', 3, '2026-09-03')
    check('bad step / zero minutes / bad date / unknown person are refused, every problem named',
          not bad['ok'] and 'minutes' in bad['error'] and 'date' in bad['error']
          and not bad_step['ok'] and 'step 9' in bad_step['error'] and bad_step['proposals'] == []
          and not step_done_proposal(mgr, 'test-dinner', 1, 'ghost', 3)['ok'],
          f"{bad.get('error')} | {bad_step.get('error')}")

    # --- page seeds -----------------------------------------------------
    print('\npage seeds')
    pages = cs.SEED_COOKNOW_PAGE_DISPLAYS
    check('one page at mealplan/cooknow', [p_['pageRoute'] for p_ in pages] == ['mealplan/cooknow'])
    check('every row\'s items sum to 12 segments',
          all(sum(i['rowSegmentsUsed'] for i in r['items']) == 12
              for p_ in pages for r in json.loads(p_['definition'])['rows']))
    ids = [i['id'] for p_ in pages for _r, i in _items(p_)]
    check('item ids unique', len(ids) == len(set(ids)))
    tables = {t['name']: t for t in cs.SEED_COOKNOW_TABLES}
    allowed = {'embeddedTable', 'embeddedGraph', 'embeddedCalendar', 'embeddedMap', 'api-structured-panel'}
    comps = [i['componentProps']['componentName'] for p_ in pages for _r, i in _items(p_) if i['type'] != 'form']
    check('no JSON on screens: only embeds, structured panels and forms', set(comps) <= allowed, str(set(comps)))
    embeds = [i for p_ in pages for _r, i in _items(p_)
              if i['type'] != 'form' and i['componentProps']['componentName'] == 'embeddedTable']
    from polariApiServer.mealplan_pages_seed import EMBED_TARGETS
    check('every embeddedTable names one of OUR TableDefinitions with the class it renders',
          embeds and all(EMBED_TARGETS.get(e['id'], ('', ''))[1] in tables
                         and tables[EMBED_TARGETS[e['id']][1]]['source_class']
                         == e['componentProps']['inputs']['className'] for e in embeds))
    check('our tables are not defaults (the household page keeps the class defaults)',
          all(not t['is_default_table'] for t in tables.values()))
    api = CookNowAPI(polServer=None, manager=None)
    routes = {'/api/mealplanning/cooknow/{person}', '/api/mealplanning/speed-refinement'}
    panels = [i['componentProps']['inputs'] for p_ in pages for _r, i in _items(p_)
              if i['type'] != 'form' and i['componentProps']['componentName'] == 'api-structured-panel']
    check('every api-structured-panel path is one our API registers (or the existing '
          'speed-refinement route), with {object} = the person',
          panels and all(x['path'].split('?')[0].replace('{object}', '{person}') in routes
                         and '{object}' in x['path'] for x in panels)
          and hasattr(api, 'on_get_sheet') and hasattr(api, 'on_post_step_done'),
          str([x['path'] for x in panels]))
    check('every structured panel picks or hides so nothing lands in the JSON expander',
          all(x['pick'] or x['hideKeys'] for x in panels))
    forms = [i for p_ in pages for _r, i in _items(p_) if i['type'] == 'form']
    sols = {s['name'] for s in cs.SEED_COOKNOW_SOLUTIONS}
    check('the Step done form links our solution; person defaults to {object}; template defaults to the demo',
          len(forms) == 1 and forms[0]['item']['linkedSolutionName'] in sols
          and any(v['variableName'] == 'person' and v['defaultValue'] == '{object}'
                  for v in forms[0]['item']['extraVariables'])
          and any(v['variableName'] == 'template' and v['defaultValue'] == 'chicken-bowl-dinner'
                  for v in forms[0]['item']['extraVariables']))
    check('the analyses resolve to our module and the solution\'s AnalysisCall names a seeded analysis',
          all(a['callable_ref'].startswith('nutrition.cooknow_analysis:') for a in cs.SEED_COOKNOW_ANALYSES)
          and 'cooknow-step-done' in {a['name'] for a in cs.SEED_COOKNOW_ANALYSES})

    # --- the solution on the REAL engine ---------------------------------
    print('\nno-code')
    sol = json.loads(cs.STEP_DONE_SOLUTION['definition'])
    params = {'template': 'test-dinner', 'step_order': 2, 'person': 'fast', 'minutes_actual': 6.5,
              'date_iso': '2026-09-03'}
    trace = gb.execute(sol, manager=mgr, params=params)
    from polariNoCode.graph_compilers import final_context_of
    ctx = final_context_of(trace) or {}
    obs = list(mgr.objectTables['DurationObservation'].values())
    check('FormSubscription → AnalysisCall(pick proposals) → GenerateEvent(DurationObservation) → '
          'refreshDisplay: one observation row appears through the real engine',
          trace.status == 'completed' and len(obs) == 1
          and obs[0].name == 'fast-test-dinner-2-2026-09-03' and obs[0].observed_min == 6.5
          and any(e.get('name') == 'refreshDisplay' and e.get('channel') == 'frontend'
                  for e in ctx.get('_emitted_events', [])),
          f'{trace.status} {trace.error_summary} obs={len(obs)}')
    trace2 = gb.execute(sol, manager=mgr, params=dict(params, minutes_actual=9))
    check('the same step on the same day again → reused, not duplicated (dedupeBy name)',
          trace2.status == 'completed' and len(mgr.objectTables['DurationObservation']) == 1)
    for i, m in enumerate((5.0, 5.5), 4):
        gb.execute(sol, manager=mgr, params=dict(params, minutes_actual=m, date_iso=f'2026-09-0{i}'))
    p3 = step_done_proposal(mgr, 'test-dinner', 2, 'fast', 4.0, '2026-09-06')
    line = next((l for l in p3['suggestionLines'] if l.get('status') == 'proposal'), None)
    check('after three logged days a fourth "done" carries a real proposal: median(6.5,5,5.5,4)/6 = '
          '5.25/6 → 0.88 vs the current 0.8 — a suggestion with its evidence, still not applied',
          len(mgr.objectTables['DurationObservation']) == 3 and line is not None
          and line['observations'] == 4 and line['proposedFactor'] == 0.88 and line['currentFactor'] == 0.8
          and p3['applied'] is False
          and next(s for s in mgr.objectTables['PersonSkill'].values() if s.name == 'fast-baking').speed_factor == 0.8,
          str(p3['suggestionLines']))
    bad_trace = gb.execute(sol, manager=mgr, params=dict(params, step_order=9))
    check('a refused proposal writes nothing (empty proposals list → zero rows)',
          bad_trace.status == 'completed' and len(mgr.objectTables['DurationObservation']) == 3,
          f'{bad_trace.status} {bad_trace.error_summary}')
    # the message the form shows (fix 2026-09-03: "Step done" was silent)
    m1 = ctx.get('message')
    m2 = (final_context_of(trace2) or {}).get('message')
    m3 = (final_context_of(bad_trace) or {}).get('message')
    check('the first "Step done" says "Step 2 took 6.5 min (planned …); speed suggestion for baking: …" '
          '— context variable `message` + the refreshDisplay payload',
          isinstance(m1, str) and m1.startswith('Step 2 took 6.5 min (planned ')
          and 'speed suggestion for baking' in m1
          and any(e.get('payload', {}).get('message') == m1 for e in ctx.get('_emitted_events', [])), str(m1))
    check('the same step on the same day again says it was already logged (6.5 min) and kept',
          isinstance(m2, str) and m2.startswith('Step 2 on 2026-09-03 was already logged (6.5 min) — kept'), str(m2))
    check('a refused step names the problem in the message ("step 9 is not one of 1..N")',
          isinstance(m3, str) and 'step 9 is not one of' in m3, str(m3))
    check('with three days logged the fourth message carries the suggestion in words: "factor 0.88 (now 0.8) '
          'from 4 observations — a knob, not applied"',
          'speed suggestion for baking: factor 0.88 (now 0.8) from 4 observations — a knob, not applied'
          in p3['message'], p3['message'])

    print(f'\n{len(passes)}/{len(passes) + len(failures)} checks passed')
    for f in failures:
        print('  -', f)
    print('PASS: N4 cook now holds together' if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
