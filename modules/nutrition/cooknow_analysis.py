"""
@module nutrition.cooknow_analysis

N4 — the **Cook now** page (HOUSEHOLD_APP_PAGES.md §3.4): the recipe
at prep time, for ONE person, every number a labelled prior or
derived from rows:

  cook_sheet          the template's recipe steps in order, each with
                      THIS person's planned minutes (household
                      step_minutes: method base × the person's slowest
                      skill factor, never below the safety floor —
                      basis labelled), attended vs unattended (the
                      StepMethod row), the unattended WINDOW (a timer)
                      + the "do dishes now" suggestion (the household's
                      pre-prep DishStrategy, the same unattended-first
                      rule dish_plan uses), the safety lines for the
                      step's hazard tags (MethodSkillRequirement ×
                      SafetyRule — words, no diagnosis language), the
                      ingredients per step (grams scaled by the
                      person's serving split when a MealEntry exists),
                      totals and readyBy/startBy when an event is given.
  step_done_proposal  "done" → ONE DurationObservation row proposal
                      (dedupe name <person>-<template>-<step>-<date>)
                      + the speed-factor suggestion the household
                      refinement loop WOULD make with it (evidence
                      named; never applied here — a knob).

Everything is a PROPOSAL / reading; nothing is written by this module.

@consumers
  - nutrition.cooknow_api (GET /api/mealplanning/cooknow/{person},
    POST …/step-done)
  - AnalysisDefinition rows `nutrition.cooknow_analysis:<fn>`
    (the cooknow seeds; the "Step done" form solution)
  - nutrition.selftest_cooknow
"""

import json
import re
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from household.household_analysis import (
    method_requirement, person_factor, refine_speed_factors, safety_check,
    step_minutes,
)
from nutrition.logistics_analysis import LOAD_UNITS_PER_TOOL, _dt, _iso
from nutrition.workflow_analysis import METHOD_TO_TASK, resolve_method

PROV = 'cooknow'
#: a raw (prep-only) step whose instruction says one of these is a
#: DICE task (the knife methods) — a labelled keyword rule, nothing more.
DICE_WORDS = ('dice', 'chop', 'slice', 'mince', 'cube', 'julienne')
#: the tool load a step adds to the dish pile when its method names a
#: tool (the dish_plan prior, reused by name).
DISH_LOAD_PER_TOOL = LOAD_UNITS_PER_TOOL


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', {}) or {}).get(cls, {}) or {}).values())


def _named(manager, cls, name):
    for r in _rows(manager, cls):
        if getattr(r, 'name', '') == name:
            return r
    return None


def _loads(text, default):
    if isinstance(text, (dict, list)):
        return text
    try:
        v = json.loads(text) if text else default
    except (TypeError, ValueError):
        return default
    return v if v not in (None, '') else default


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _household_of(manager, person):
    for m in _rows(manager, 'HouseholdMember'):
        if getattr(m, 'person_name', '') == person:
            return getattr(m, 'household_name', '')
    return ''


def _recipes_of(manager, template_row):
    names = _loads(getattr(template_row, 'recipe_names_json', '[]'), [])
    return [r for n in names for r in [_named(manager, 'Recipe', n)] if r is not None]


def _lines_of(manager, recipe_names, variation_row):
    """IngredientLines of the recipes, the variation's swaps applied
    (grams default to the original line; retention never carries)."""
    swaps = _loads(getattr(variation_row, 'swaps_json', '[]'), []) if variation_row else []
    by_from = {s.get('from_food'): s for s in swaps if isinstance(s, dict)}
    out = []
    for l in sorted(_rows(manager, 'IngredientLine'),
                    key=lambda x: (getattr(x, 'recipe_name', ''), int(getattr(x, 'order', 0) or 0))):
        if getattr(l, 'recipe_name', '') not in recipe_names:
            continue
        food, grams, swapped = getattr(l, 'food_name', ''), _f(getattr(l, 'grams', 0)), ''
        s = by_from.get(food)
        if s:
            swapped = f'{food} → {s.get("to_food")} (variation swap)'
            food = s.get('to_food', food)
            grams = _f(s.get('grams'), grams) if s.get('grams') is not None else grams
        out.append({'recipe': l.recipe_name, 'food': food, 'gramsAsWritten': round(grams, 1),
                    'method': getattr(l, 'method', 'raw') or 'raw',
                    'prepNote': getattr(l, 'prep_note', '') or '', 'swap': swapped,
                    'order': int(getattr(l, 'order', 0) or 0)})
    return out


def _person_portion(manager, template, variation, person):
    """(portion, basis) — the person's serving-split fraction from the
    first MealEntry of this template (variation-matched when given)
    that names them; else 1 serving, labelled."""
    for e in _rows(manager, 'MealEntry'):
        if getattr(e, 'template_name', '') != template:
            continue
        if variation and getattr(e, 'variation_name', '') not in ('', variation):
            continue
        split = _loads(getattr(e, 'serving_split_json', '{}'), {})
        if isinstance(split, dict) and person in split:
            return _f(split[person], 1.0), f'MealEntry {e.name} serving_split_json[{person}]'
    return 1.0, 'no MealEntry names this person — one serving (as written ÷ servings)'


def _task_of(step):
    method = getattr(step, 'method', 'raw') or 'raw'
    task = METHOD_TO_TASK.get(method, '')
    basis = f'recipe method {method!r} → task {task!r} (METHOD_TO_TASK)' if task else ''
    if not task and method == 'raw':
        text = (getattr(step, 'instruction', '') or '').lower()
        if any(w in text for w in DICE_WORDS):
            task, basis = 'dice', 'raw step whose instruction names a knife word → task dice (keyword rule)'
    return task, basis


def _safety_lines(manager, person, method_name):
    """The words for a step's hazard tags: the rule text per tag, plus
    the household verdict (alone / supervised / not yet) — never a
    judgement of the person."""
    req = method_requirement(manager, method_name) if method_name else None
    hazards = _loads(getattr(req, 'hazard_tags_json', '[]'), []) if req else []
    lines = []
    for tag in hazards:
        rules = [r for r in _rows(manager, 'SafetyRule') if getattr(r, 'hazard_tag', '') == tag]
        if not rules:
            lines.append({'hazard': tag, 'line': f'{tag}: no SafetyRule row — add one', 'citation': ''})
        for r in rules:
            lines.append({'hazard': tag, 'line': f'{tag}: {getattr(r, "rule_text", "")}',
                          'citation': getattr(r, 'citation', '')})
    verdict = safety_check(manager, person, method_name) if method_name else \
        {'verdict': 'alone', 'reasons': []}
    return hazards, lines, verdict


def _dish_strategy(manager, household):
    """The pre-prep DishStrategy the household's policy names (the
    same lookup dish_plan does), with the fallback named."""
    policy = next((p for p in _rows(manager, 'HouseholdDishPolicy')
                   if getattr(p, 'household_name', '') == household), None)
    name = getattr(policy, 'preprep_strategy', 'wash-as-you-go') if policy else 'wash-as-you-go'
    strat = _named(manager, 'DishStrategy', name)
    owned = {getattr(t, 'tool_name', '') for t in _rows(manager, 'KitchenTool')
             if getattr(t, 'household_name', '') == household and getattr(t, 'owned', True)}
    note = ''
    if strat is not None and getattr(strat, 'needs_tool', '') and strat.needs_tool not in owned:
        note = f'{name} needs a {strat.needs_tool} the household does not own — batch-after-meal instead'
        strat = _named(manager, 'DishStrategy', 'batch-after-meal') or strat
    basis = ('HouseholdDishPolicy.preprep_strategy' if policy else 'default wash-as-you-go (no policy row)')
    return strat, basis, note


def _dish_suggestion(strat, window_min, load_units):
    """What the unattended window is good for, by the strategy's
    timing rule (dish_plan's unattended-first rule, per step)."""
    if strat is None:
        return 'do dishes now: no DishStrategy row — a prior of 2 min + 1.5 min per item', \
            round(min(window_min, 2.0 + 1.5 * load_units), 1)
    timing = getattr(strat, 'timing', '')
    minutes = _f(getattr(strat, 'setup_min', 2), 2.0) + load_units * _f(getattr(strat, 'min_per_load_unit', 1.5), 1.5)
    if timing == 'unattended-first':
        fit = round(min(window_min, minutes), 1)
        return (f'do dishes now: ~{fit:g} of the {window_min:g} min window covers '
                f'{load_units:g} item(s) ({getattr(strat, "name", "")})'), fit
    return (f'window is free — the dish policy ({getattr(strat, "name", "")}) says '
            f'{timing.replace("-", " ")}'), 0.0


def cook_sheet(manager, template, person, variation='', event=None):
    """The recipe at prep time for `person`: ordered steps as flat
    records, ingredients per step, safety lines, dish windows, totals,
    and readyBy / startBy when a CalendarEvent (row or name) is given."""
    t = _named(manager, 'MealTemplate', template)
    if t is None:
        return {'ok': False, 'error': f"MealTemplate '{template}' not found", 'steps': [],
                'ingredients': [], 'safetyLines': [], 'dishLines': []}
    v = _named(manager, 'VariationDefinition', variation) if variation else None
    if variation and v is None:
        return {'ok': False, 'error': f"VariationDefinition '{variation}' not found", 'steps': [],
                'ingredients': [], 'safetyLines': [], 'dishLines': []}
    recipes = _recipes_of(manager, t)
    if not recipes:
        return {'ok': False, 'error': f"template '{template}' names no Recipe rows on this node",
                'steps': [], 'ingredients': [], 'safetyLines': [], 'dishLines': []}
    recipe_names = [r.name for r in recipes]
    servings = sum(_f(getattr(r, 'servings', 1), 1.0) or 1.0 for r in recipes) / len(recipes)
    household = _household_of(manager, person)
    portion, portion_basis = _person_portion(manager, template, variation, person)
    lines = _lines_of(manager, recipe_names, v)
    strat, strat_basis, strat_note = _dish_strategy(manager, household)

    steps_rows = sorted([s for s in _rows(manager, 'CookingStep')
                         if getattr(s, 'recipe_name', '') in recipe_names],
                        key=lambda s: (recipe_names.index(s.recipe_name), int(getattr(s, 'order', 0) or 0)))
    # the inventory filter only when the household HAS inventory rows
    # (no rows = every tool assumed, labelled below).
    inventory = household and any(getattr(t, 'household_name', '') == household
                                  for t in _rows(manager, 'KitchenTool'))
    hh_for_methods = household if inventory else ''
    # which step each ingredient line joins: the first step whose
    # instruction names the food, else the first step with the line's
    # cooking method, else the last step (assembly) — rule named.
    step_of_line = {}
    texts = [(getattr(s, 'instruction', '') or '').lower() for s in steps_rows]
    for j, l in enumerate(lines):
        tokens = [w for w in l['food'].lower().replace('_', '-').split('-') if len(w) > 2 and w != 'raw']
        hit = next((k for k, txt in enumerate(texts)
                    if any(re.search(rf'\b{re.escape(w)}s?\b', txt) for w in tokens)), None)
        if hit is None:
            hit = next((k for k, s in enumerate(steps_rows)
                        if (getattr(s, 'method', 'raw') or 'raw') == l['method'] and l['method'] != 'raw'), None)
        step_of_line[j] = hit if hit is not None else max(len(steps_rows) - 1, 0)
    steps, ingredients, safety_lines, dish_lines = [], [], [], []
    load_units = 0.0
    clock = 0.0          # attended minutes elapsed (steps in order)
    windows_end = 0.0    # the latest unattended window end
    attended_total = unattended_total = 0.0
    for i, s in enumerate(steps_rows, 1):
        order = int(getattr(s, 'order', 0) or i)
        recipe_min = _f(getattr(s, 'duration_min', 0))
        task, task_basis = _task_of(s)
        # the step's ingredient lines: same cooking method; raw lines
        # left over join the LAST step (assembly) — rule named.
        mine = [lines[j] for j in range(len(lines)) if step_of_line[j] == i - 1]
        grams_total = sum(l['gramsAsWritten'] for l in mine)
        method_name, tool, attended, method_basis = '', '', True, ''
        if task:
            res = resolve_method(manager, task, grams_total, hh_for_methods)
            if res.get('ok'):
                c = res['chosen']
                method_name, tool, attended = c['method'], c.get('tool', ''), bool(c.get('attended', True))
                method_basis = (f'{task_basis}; StepMethod {method_name} chosen '
                                f'({"pinned" if res.get("pinned") else "fastest usable"}'
                                f'{", tools filtered by the household inventory" if inventory else ", no inventory rows — every tool assumed"})')
            else:
                method_basis = f'{task_basis}; no usable StepMethod ({res.get("error", "")})'
        else:
            method_basis = 'no task kind for this step (recipe minutes as written)'
        method_row = _named(manager, 'StepMethod', method_name) if method_name else None
        if attended or method_row is None:
            base_min = recipe_min
            base_basis = 'the recipe step\'s duration_min'
        else:
            # unattended: only the method's base minutes are hands-on;
            # the rest of the recipe time is the WINDOW.
            base_min = min(_f(getattr(method_row, 'base_min', 0)), recipe_min) if recipe_min else _f(getattr(method_row, 'base_min', 0))
            base_basis = f'StepMethod {method_name}.base_min (the hands-on part of an unattended step)'
        sm = step_minutes(manager, person, method_name, base_min)
        planned = sm['minutes']
        factor_words = ', '.join(f'{f["skill"]} ×{f["factor"]:g} ({f["level"]}, {f["fidelity"]})'
                                 for f in sm['factors']) or 'no skill row for this step (×1.0)'
        minutes_basis = (f'{base_min:g} min [{base_basis}] × governing factor {sm["governingFactor"]:g} '
                         f'[{factor_words}] = {sm["raw"]:g}'
                         + (f'; raised to the safety floor {sm["safetyFloorMin"]:g} min' if sm['boundedBySafety']
                            else f'; safety floor {sm["safetyFloorMin"]:g} min not binding'))
        window = round(max(recipe_min - base_min, 0.0), 1) if (method_row is not None and not attended) else 0.0
        hazards, lines_for_step, verdict = _safety_lines(manager, person, method_name)
        if tool:
            load_units += DISH_LOAD_PER_TOOL
        # the clock: attended work is sequential; an unattended window
        # runs while the next steps proceed (rule named in `honesty`).
        start_at = clock
        clock += planned
        window_end = clock + window if window else 0.0
        windows_end = max(windows_end, window_end)
        attended_total += planned
        unattended_total += window
        dish_text, dish_fit = ('', 0.0)
        if window:
            dish_text, dish_fit = _dish_suggestion(strat, window, load_units)
            dish_lines.append({'step': order, 'windowMin': window, 'timerMin': window,
                               'startsAtMin': round(clock, 1), 'endsAtMin': round(window_end, 1),
                               'dishItems': load_units, 'dishMinutes': dish_fit,
                               'suggestion': dish_text, 'strategy': getattr(strat, 'name', '') if strat else '',
                               'strategyBasis': strat_basis})
        for l in lines_for_step:
            safety_lines.append({'step': order, 'hazard': l['hazard'], 'line': l['line'],
                                 'citation': l['citation']})
        for l in mine:
            per_serving = l['gramsAsWritten'] / (servings or 1.0)
            ingredients.append({'step': order, 'food': l['food'],
                                'gramsAsWritten': l['gramsAsWritten'],
                                'gramsForPerson': round(per_serving * portion, 1),
                                'portion': portion, 'method': l['method'],
                                'prepNote': l['prepNote'], 'swap': l['swap']})
        steps.append({
            'step': order, 'recipe': s.recipe_name, 'text': getattr(s, 'instruction', ''),
            'recipeMethod': getattr(s, 'method', 'raw') or 'raw', 'task': task,
            'method': method_name, 'tool': tool, 'attended': attended,
            'plannedMin': planned, 'recipeMin': recipe_min,
            'startsAtMin': round(start_at, 1), 'endsAtMin': round(clock, 1),
            'unattendedWindowMin': window, 'timerMin': window,
            'dishSuggestion': dish_text,
            'safety': verdict['verdict'],
            'safetyLines': ' | '.join(l['line'] for l in lines_for_step),
            'hazards': ', '.join(hazards),
            'ingredients': ', '.join(f'{l["food"]} {round(l["gramsAsWritten"] / (servings or 1.0) * portion):g} g'
                                     for l in mine),
            'minutesBasis': minutes_basis, 'methodBasis': method_basis,
            'boundedBySafety': sm['boundedBySafety'],
        })
    wall = round(max(clock, windows_end), 1)
    out = {'ok': True, 'schema': 'cook-sheet/1', 'template': template, 'variation': variation or '',
           'recipe': ', '.join(recipe_names), 'person': person, 'household': household,
           'servingsAsWritten': servings, 'portion': portion, 'portionBasis': portion_basis,
           'stepCount': len(steps), 'attendedMin': round(attended_total, 1),
           'unattendedMin': round(unattended_total, 1), 'wallClockMin': wall,
           'dishStrategy': getattr(strat, 'name', '') if strat else '', 'dishStrategyBasis': strat_basis,
           'dishNote': strat_note, 'readyBy': None, 'startBy': None, 'event': '',
           'steps': steps, 'ingredients': ingredients, 'safetyLines': safety_lines, 'dishLines': dish_lines,
           'honesty': ('minutes = household step_minutes (method base × the person\'s slowest skill '
                       'factor, never below the safety floor); unattended steps count only the '
                       'method\'s hands-on base minutes, the rest is a timer window that later '
                       'steps run inside (wall clock = attended work or the last window, whichever '
                       'ends later); safety lines are the SafetyRule words for the step\'s hazard '
                       'tags; grams for the person = as written ÷ servings × their serving split')}
    if event is not None:
        ev = event if not isinstance(event, str) else _named(manager, 'CalendarEvent', event)
        span = _loads(getattr(ev, 'span', '{}'), {}) if ev is not None else {}
        end = _dt(span.get('end') or span.get('start')) if isinstance(span, dict) else None
        if end is not None:
            out['event'] = getattr(ev, 'name', '')
            out['readyBy'] = _iso(end)
            out['startBy'] = _iso(end - timedelta(minutes=wall))
        else:
            out['event'] = str(event) if isinstance(event, str) else getattr(ev, 'name', '')
            out['readyByNote'] = 'the event has no readable span — no readyBy'
    return out


def _valid_date(text):
    try:
        return date.fromisoformat(str(text)[:10]).isoformat()
    except (TypeError, ValueError):
        return None


def step_done_proposal(manager, template, step_order, person, minutes_actual, date_iso='',
                       variation=''):
    """"Done" → one DurationObservation row proposal for the step's
    method + skill, dedupe name <person>-<template>-<step>-<date>,
    plus the refinement the household loop WOULD propose with this
    observation counted (evidence named, never applied)."""
    problems = []
    people = _rows(manager, 'PersonProfile')
    if not person:
        problems.append('no person')
    elif people and _named(manager, 'PersonProfile', person) is None:
        problems.append(f"person '{person}' is not a PersonProfile")
    try:
        order = int(float(step_order))
    except (TypeError, ValueError):
        problems.append(f"step '{step_order}' is not a number")
        order = 0
    try:
        minutes = float(minutes_actual)
    except (TypeError, ValueError):
        problems.append(f"minutes '{minutes_actual}' is not a number")
        minutes = 0.0
    if minutes <= 0:
        problems.append('minutes must be above 0')
    d = _valid_date(date_iso) or (date.today().isoformat() if not date_iso else None)
    if d is None:
        problems.append(f"date '{date_iso}' is not YYYY-MM-DD")
    sheet = cook_sheet(manager, template, person, variation) if not problems else {'ok': False, 'error': ''}
    if not sheet.get('ok'):
        problems.append(sheet.get('error') or 'no cook sheet')
    step = next((s for s in sheet.get('steps', []) if s['step'] == order), None)
    if sheet.get('ok') and step is None:
        problems.append(f"step {order} is not one of 1..{sheet.get('stepCount')} of '{template}'")
    if problems:
        return {'ok': False, 'error': '; '.join(problems), 'message': '; '.join(problems),
                'proposals': [], 'suggestionLines': [], 'safetyQuestions': []}
    method_name = step['method']
    req = method_requirement(manager, method_name) if method_name else None
    skills = _loads(getattr(req, 'skills_json', '[]'), []) if req else []
    skill = (skills[0].get('skill', '') if skills and isinstance(skills[0], dict) else '')
    row = {'name': f'{person}-{template}-{order}-{d}', 'person_name': person, 'kind': 'prep-step',
           'method_name': method_name, 'skill_name': skill, 'entry_name': '', 'slot': '',
           'observed_min': round(minutes, 1), 'date': d, 'source': 'cook-now',
           'is_prior': False, 'provenance_id': PROV,
           'notes': (f'{template} step {order} ({step["task"] or step["recipeMethod"]}): planned '
                     f'{step["plannedMin"]:g} min, observed {minutes:g} min')}
    # the suggestion: refine_speed_factors over the rows AS IF this
    # observation were written (a shallow view; nothing is written).
    tables = dict(getattr(manager, 'objectTables', {}) or {})
    obs = dict(tables.get('DurationObservation', {}) or {})
    obs['__proposed__'] = SimpleNamespace(id='__proposed__', **row)
    tables['DurationObservation'] = obs
    ref = refine_speed_factors(SimpleNamespace(objectTables=tables), person)
    current, level, fid = person_factor(manager, person, skill) if skill else (1.0, '', '')
    lines = [dict(p, basis='median of observed ÷ StepMethod.base_min per skill, this observation counted')
             for p in ref.get('proposals', [])]
    # the plain words the "Step done" form shows
    existing = _named(manager, 'DurationObservation', row['name'])
    if existing is not None:
        message = (f'Step {order} on {d} was already logged '
                   f'({float(getattr(existing, "observed_min", 0) or 0):g} min) — kept')
    else:
        message = f'Step {order} took {minutes:g} min (planned {step["plannedMin"]:g})'
    mine = next((l for l in lines if l.get('skill') == skill and l.get('status') == 'proposal'), None)
    waiting = next((l for l in lines if l.get('skill') == skill and l.get('status') != 'proposal'), None)
    if mine is not None:
        message += (f'; speed suggestion for {skill}: factor {mine["proposedFactor"]} (now {current}) '
                    f'from {mine["observations"]} observations — a knob, not applied')
    elif waiting is not None:
        message += f'; speed suggestion for {skill}: {waiting["status"]}'
    elif skill:
        message += f'; no speed suggestion for {skill} yet'
    else:
        message += '; the step names no skill, so no speed suggestion'
    return {'ok': True, 'schema': 'step-done/1', 'message': message,
            'template': template, 'step': order, 'person': person,
            'method': method_name, 'skill': skill, 'plannedMin': step['plannedMin'],
            'observedMin': round(minutes, 1),
            'deltaMin': round(minutes - step['plannedMin'], 1),
            'currentFactor': current, 'currentLevel': level, 'currentFidelity': fid,
            'proposals': [row], 'suggestionLines': lines,
            'safetyQuestions': ref.get('safetyQuestions', []),
            'applied': False,
            'honesty': ('one DurationObservation per person × template × step × date (dedupe by name); '
                        'the factor suggestion is what refine_speed_factors would say with this '
                        'observation counted — it is never applied here (PersonSkill is a knob)')}
