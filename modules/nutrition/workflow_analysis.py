"""
@cross-cutting
@module nutrition.workflow_analysis
@tags @xc:bindings

nmp-10 — the meal-prep scheduler (the judicial-process pattern in
the kitchen):

  resolve_method   decision 12: candidates for a task kind filtered
                   by the household's TOOL INVENTORY and the cook's
                   skill; a stated MethodPreference PINS the choice
                   (time delta shown, not judged); else the most
                   time-efficient ACTIVE-minutes method wins; every
                   skipped method says why ("not in inventory").
  derive_week_plan the optimizer: the plan's entries -> a batched
                   task DAG (chop once for three meals) compressed
                   into 1-2 PrepSessions + a tiny daily action list;
                   storage decided per gap (FSIS windows: fridge
                   <= 4 days, else freeze + a thaw the evening
                   before); total ACTIVE minutes is THE score.
                   Output is a PROPOSAL (+ a CookingWorkflow-shaped
                   DAG) — humans save/edit it; nothing is written.
  tool_advisor     frequency x time-delta evidence: when a NOT-owned
                   tool's method would beat the chosen ones across
                   the plan, accumulate the would-be savings and
                   suggest the purchase with the arithmetic
                   (dismissals remembered; never a nag).

@consumers
  - nutrition.nutrition_api
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-10
"""

from nutrition.meal_analysis import _json_list, _named
from nutrition.person_analysis import _f, _rows
from nutrition.workflow_basis import SKILL_FACTORS

FRIDGE_WINDOW_DAYS = 4.0   # FSIS cooked-leftovers window (seeded row)
SESSION_DAYS = (1, 4)      # the 1-2 prep sessions' default days

# recipe-line cooking methods -> task kinds
METHOD_TO_TASK = {'boiled': 'boil', 'steamed': 'steam',
                  'fried': 'pan-fry', 'sauteed': 'pan-fry',
                  'grilled': 'grill', 'baked': 'bake',
                  'roasted': 'bake', 'simmered': 'boil',
                  'braised': 'boil', 'microwaved': 'boil'}


def _owned_tools(manager, household):
    owned = set()
    for t in _rows(manager, 'KitchenTool'):
        if (getattr(t, 'household_name', '') == household
                and getattr(t, 'owned', True)):
            owned.add(getattr(t, 'tool_name', ''))
    return owned


def _duration(method, grams, skill):
    factor = SKILL_FACTORS.get(skill, 1.0)
    active = _f(method, 'base_min', 0.0)
    work = _f(method, 'per_100g_min', 0.0) * grams / 100.0 * factor
    if getattr(method, 'attended', True):
        active += work
        total = active
    else:
        total = active + work
    return round(active, 1), round(total, 1)


def resolve_method(manager, task_kind, grams, household='',
                   person=None, skill='intermediate'):
    """Decision 12: the method ladder for one task."""
    if person is not None:
        skill = getattr(person, 'cooking_skill', skill) or skill
    owned = _owned_tools(manager, household) if household else None
    pin = None
    for p in _rows(manager, 'MethodPreference'):
        if getattr(p, 'task_kind', '') != task_kind:
            continue
        if (getattr(p, 'household_name', '') == household
                or (person is not None
                    and getattr(p, 'person_name', '')
                    == getattr(person, 'name', ''))):
            pin = getattr(p, 'method_name', '')
    candidates, skipped = [], []
    order = {'novice': 0, '': 0, 'intermediate': 1, 'experienced': 2}
    for m in _rows(manager, 'StepMethod'):
        if getattr(m, 'task_kind', '') != task_kind:
            continue
        tool = getattr(m, 'tool_name', '')
        if owned is not None and tool and tool not in owned:
            skipped.append({'method': getattr(m, 'name', ''),
                            'why': f'{tool} not in inventory'})
            continue
        floor = getattr(m, 'skill_floor', '') or ''
        if order.get(skill, 1) < order.get(floor, 0):
            skipped.append({'method': getattr(m, 'name', ''),
                            'why': f'skill floor {floor}'})
            continue
        active, total = _duration(m, grams, skill)
        candidates.append({'method': getattr(m, 'name', ''),
                           'display': getattr(m, 'display_name', ''),
                           'tool': tool, 'activeMin': active,
                           'totalMin': total,
                           'attended': getattr(m, 'attended', True),
                           'retentionCode':
                               getattr(m, 'retention_code', ''),
                           'provenance':
                               getattr(m, 'provenance', 'seeded'),
                           'fidelity': getattr(
                               m, 'duration_fidelity', 'estimate')})
    if not candidates:
        return {'ok': False, 'taskKind': task_kind,
                'error': 'no usable method (all skipped)',
                'skipped': skipped}
    candidates.sort(key=lambda c: c['activeMin'])
    chosen = candidates[0]
    pinned = False
    if pin:
        pinned_c = next((c for c in candidates
                         if c['method'] == pin), None)
        if pinned_c is not None:
            chosen, pinned = pinned_c, True
    out = {'ok': True, 'taskKind': task_kind, 'grams': grams,
           'skill': skill, 'chosen': chosen,
           'candidates': candidates, 'skipped': skipped}
    if pinned:
        delta = chosen['activeMin'] - candidates[0]['activeMin']
        out['pinned'] = True
        if delta > 0:
            out['pinDelta'] = (f'+{delta:g} min vs the fastest '
                               f'method — your preference, honored')
    return out


def _session_for(day):
    """The LATEST prep session at or before the meal day — later
    meals cook in the later session (freshness beats freezing when
    the calendar allows; freezing remains for genuinely long gaps)."""
    covering = [d for d in SESSION_DAYS if d <= day]
    return max(covering) if covering else SESSION_DAYS[0]


def _plan_tasks(manager, plan):
    """The week's cook tasks, BATCHED by (food, method, session)."""
    batches = {}
    for e in _rows(manager, 'MealEntry'):
        if getattr(e, 'plan_name', '') != getattr(plan, 'name', ''):
            continue
        template = _named(manager, 'MealTemplate',
                          getattr(e, 'template_name', ''))
        if template is None:
            continue
        day = getattr(e, 'day_index', 1)
        scale = _f(e, 'scale', 1.0)
        session = _session_for(day)
        for rname in _json_list(template, 'recipe_names_json'):
            recipe = _named(manager, 'Recipe', rname)
            if recipe is None:
                continue
            servings = max(1.0, _f(recipe, 'servings', 1.0))
            for line in _rows(manager, 'IngredientLine'):
                if getattr(line, 'recipe_name', '') != rname:
                    continue
                grams = (_f(line, 'grams', 0.0) / servings) * scale
                method = getattr(line, 'method', 'raw')
                food = getattr(line, 'food_name', '')
                key = (food, method, session)
                b = batches.setdefault(key, {
                    'food': food, 'method': method,
                    'session': session, 'grams': 0.0, 'days': set()})
                b['grams'] += grams
                b['days'].add(day)
    return batches


def derive_week_plan(manager, plan, household='',
                     skill='intermediate'):
    """The optimizer: batched tasks -> 1-2 sessions + daily list."""
    batches = _plan_tasks(manager, plan)
    if not batches:
        return {'ok': False, 'error': 'plan has no derivable tasks'}
    storage = {getattr(s, 'name', ''): s
               for s in _rows(manager, 'StorageActionDefinition')}
    sessions = {d: [] for d in SESSION_DAYS}
    daily, total_active = {}, 0.0
    notes = []
    for (food, method, session_day), b in sorted(batches.items()):
        days = sorted(b['days'])
        steps = []
        # prep (dice) + cook (per the line's method) as one batch
        prep = resolve_method(manager, 'dice', b['grams'],
                              household, skill=skill)
        if prep.get('ok'):
            steps.append(('dice', prep))
        task_kind = METHOD_TO_TASK.get(method)
        if task_kind:
            cook = resolve_method(manager, task_kind, b['grams'],
                                  household, skill=skill)
            steps.append((task_kind, cook))
        batch_active = 0.0
        for kind, res in steps:
            if res.get('ok'):
                batch_active += res['chosen']['activeMin']
            else:
                notes.append(f'{food}/{kind}: {res.get("error")}')
        sessions[session_day].append({
            'food': food, 'method': method,
            'grams': round(b['grams'], 0),
            'forDays': days,
            'steps': [{'task': k,
                       'method': r.get('chosen', {}).get('method'),
                       'activeMin':
                           r.get('chosen', {}).get('activeMin'),
                       'pinned': r.get('pinned', False)}
                      for k, r in steps],
            'activeMin': round(batch_active, 1)})
        total_active += batch_active
        # storage per consuming day: gap decides fridge vs freeze
        for day in days:
            gap = day - session_day
            if gap <= 0:
                continue
            if gap <= FRIDGE_WINDOW_DAYS:
                action, why = 'refrigerate', (
                    f'{gap:g}-day gap fits the FSIS fridge window '
                    f'({FRIDGE_WINDOW_DAYS:g} d)')
            else:
                action, why = 'freeze', (
                    f'{gap:g}-day gap exceeds the fridge window — '
                    f'freeze, thaw the evening before')
                daily.setdefault(day - 1, []).append({
                    'action': 'thaw-fridge',
                    'food': food,
                    'note': f'move day-{day} {food} freezer->fridge '
                            f'(FSIS safe default)'})
            row = storage.get(action)
            daily.setdefault(day, []).append({
                'action': 'reheat', 'food': food,
                'note': storage.get('reheat').citation
                if storage.get('reheat') else 'reheat fully'})
            sessions[session_day].append({
                'storage': action, 'food': food, 'why': why,
                'citation': getattr(row, 'citation', '')
                if row is not None else ''})
    dag = {'nodes': [], 'edges': []}
    nid = 0
    for sday, items in sessions.items():
        for it in items:
            dag['nodes'].append({'id': f'n{nid}', 'day': sday, **{
                k: v for k, v in it.items()
                if k in ('food', 'method', 'storage', 'grams')}})
            nid += 1
    result = {
        'ok': True, 'plan': getattr(plan, 'name', ''),
        'sessions': [
            {'day': d, 'items': items,
             'activeMin': round(sum(i.get('activeMin', 0.0)
                                    for i in items), 1)}
            for d, items in sessions.items() if items],
        'dailyActions': {d: acts for d, acts in sorted(daily.items())},
        'totalActiveMin': round(total_active, 1),
        'workflowDag': dag,
        'notes': notes,
        'honesty': 'a PROPOSAL — save it as a CookingWorkflow to '
                   'keep/edit it (graphs-as-data on the no-code '
                   'editor); active minutes is the score being '
                   'minimized; storage choices cite their FSIS '
                   'windows',
    }
    return result


def tool_advisor(manager, plan, household, skill='intermediate',
                 min_weekly_minutes=5.0):
    """Frequency x time-delta = purchase evidence (never a nag).
    min_weekly_minutes: the suggestion floor (a knob) — below it the
    would-be savings stay silent."""
    batches = _plan_tasks(manager, plan)
    dismissed = {getattr(d, 'tool_name', '')
                 for d in _rows(manager, 'ToolAdvisorDismissal')
                 if getattr(d, 'household_name', '') == household}
    owned = _owned_tools(manager, household)
    savings = {}
    for (food, method, _session), b in batches.items():
        for task_kind in ('dice', METHOD_TO_TASK.get(method, '')):
            if not task_kind:
                continue
            res = resolve_method(manager, task_kind, b['grams'],
                                 household, skill=skill)
            if not res.get('ok'):
                continue
            have = res['chosen']['activeMin']
            # what would the UNOWNED tools' methods do?
            for m in _rows(manager, 'StepMethod'):
                if getattr(m, 'task_kind', '') != task_kind:
                    continue
                tool = getattr(m, 'tool_name', '')
                if not tool or tool in owned or tool in dismissed:
                    continue
                active, _total = _duration(m, b['grams'], skill)
                if active < have:
                    s = savings.setdefault(tool, {
                        'tool': tool, 'weeklyMinutesSaved': 0.0,
                        'tasks': []})
                    s['weeklyMinutesSaved'] += have - active
                    s['tasks'].append(
                        {'food': food, 'task': task_kind,
                         'nowMin': have, 'wouldMin': active})
    suggestions = []
    for tool, s in sorted(savings.items()):
        weekly = round(s['weeklyMinutesSaved'], 1)
        if weekly < min_weekly_minutes:
            continue
        suggestions.append({
            'tool': tool, 'weeklyMinutesSaved': weekly,
            'yearlyHoursSaved': round(weekly * 52 / 60.0, 1),
            'evidence': s['tasks'],
            'note': f'a {tool} would save ~{weekly:g} min/week '
                    f'(~{weekly * 52 / 60.0:.0f} h/year) across '
                    f'this plan — a suggestion with the arithmetic '
                    f'shown, never a nag; dismiss to stop seeing it'})
    return {'ok': True, 'plan': getattr(plan, 'name', ''),
            'household': household, 'suggestions': suggestions,
            'dismissed': sorted(dismissed)}
