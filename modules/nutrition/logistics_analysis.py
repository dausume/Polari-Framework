"""
@module nutrition.logistics_analysis

mlg-1..4 — the analyses behind meal logistics (MEAL_LOGISTICS_PLAN
§3), all PROPOSALS with every rule named. hh-1 (HOUSEHOLD_APP_PLAN.md)
MOVED the household-generic half to household.household_analysis with
names unchanged; this module keeps the meal-specific analyses,
registers the MEAL step builders with household's allocation, and
RE-EXPORTS the moved names so every `from nutrition.logistics_analysis
import Y` keeps working:

  meal_timing_check     dinner→sleep spacing (the person's own
                        number, default 120 min), meals inside work
                        blocks → situation must be packed; FLAGS,
                        never blocks
  prep_time_profile     final-prep + eating minutes for a meal, per
                        person: method × the person's factor for
                        the step's skills, bounded BELOW by the
                        safety floor (D15); eating from
                        MealTimeProfile; fidelity labeled
  portability_plan      MealLogistics × MealSituation × schedules ×
                        the tool inventory → pack / freeze-packs
                        events, missing tools NAMED
  dish_plan             DishStrategy × policy × the session's
                        unattended windows → cleanup events
  (moved → household)   availability_windows, where_is, person_factor,
                        method_requirement, step_minutes, safety_check,
                        refine_speed_factors, assign_work,
                        fairness_readout
"""

from datetime import date, datetime, timedelta

from nutrition.logistics_basis import DINNER_TO_SLEEP_DEFAULT_MIN, EATING_PRIORS
# hh-1: the household layer — re-exported (names unchanged).
from household.household_analysis import (  # noqa: F401
    STEP_BUILDERS, WTYPE_OF_CATEGORY, register_step_builder, minutes_steps,
    availability_windows, where_is, person_factor, method_requirement,
    step_minutes, safety_check, refine_speed_factors, assign_work,
    fairness_readout,
    _rows, _named, _loads, _dt, _d, _hhmm, _iso, _sleep_pref,
    _policy_for, _members, _is_free, _steps_of,
)

SLOT_TIMES = {'breakfast': '08:00', 'brunch': '10:30', 'lunch': '12:30',
              'linner': '15:30', 'dinner': '18:30', 'snack': '15:00'}
LOAD_UNITS_PER_EATER = 2.0      # plate + cutlery/glass prior
LOAD_UNITS_PER_TOOL = 1.0       # each pot/pan/board used in a step


# ---------------------------------------------------------------
# the meal step builders (mlg-4 → household's assign_work)
# ---------------------------------------------------------------

def _preprep_steps(event, payload, base_min):
    """A coordinated pre-prep session: every step of every item."""
    return [{'label': f"{st.get('task')} {it.get('food')} ({st.get('method')})",
             'method': st.get('method'),
             'baseMin': float(st.get('activeMin') or 0) or 1.0}
            for it in payload.get('items', []) for st in it.get('steps', [])]


def _mealprep_steps(event, payload, base_min):
    """Final prep right before eating: reheat + assemble."""
    return [{'label': 'reheat', 'method': 'reheat', 'baseMin': 5.0},
            {'label': 'assemble', 'method': 'assemble-plate', 'baseMin': 3.0}]


#: category → WorkloadType.name defaults already live in household
#: (the vocabulary is seeded there); these calls bind the MEAL
#: payload shapes. Importing this module is what registers them —
#: polariServer imports it under the nutrition gate at boot.
MEAL_STEP_BUILDERS = {
    'pre-prep': register_step_builder('pre-prep', _preprep_steps, 'pre-prep'),
    'meal-prep': register_step_builder('meal-prep', _mealprep_steps, 'meal-prep'),
    'packing': register_step_builder('packing', minutes_steps('portion-containers'), 'packing'),
}


# ---------------------------------------------------------------
# mlg-1: timing
# ---------------------------------------------------------------

def meal_timing_check(manager, plan, week_start=None, persons=None):
    """Per-entry verdicts: dinner→sleep spacing vs the person's own
    number; a meal inside a work block away from home → must be
    packed (a MealLogistics row) or moved. FLAGS + suggests."""
    plan_row = plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)
    if plan_row is None:
        return {'ok': False, 'error': f"MealPlanDefinition '{plan}' not found"}
    start = _d(week_start) or _d(getattr(plan_row, 'start_date', '')) or date.today()
    household = getattr(plan_row, 'household_name', '')
    people = persons or [m.person_name for m in _rows(manager, 'HouseholdMember')
                         if getattr(m, 'household_name', '') == household] \
        or [getattr(plan_row, 'person_name', '')]
    logistics = {(l.entry_name, l.person_name): l for l in _rows(manager, 'MealLogistics')}
    verdicts = []
    for e in _rows(manager, 'MealEntry'):
        if getattr(e, 'plan_name', '') != plan_row.name:
            continue
        day = int(getattr(e, 'day_index', 1) or 1)
        mdate = start + timedelta(days=day - 1)
        slot = getattr(e, 'slot', '')
        at = getattr(e, 'time_hhmm', '') or SLOT_TIMES.get(slot, '12:00')
        meal_dt = datetime.combine(mdate, datetime.strptime(at, '%H:%M').time())
        for person in people:
            v = {'entry': e.name, 'person': person, 'slot': slot, 'mealTime': _iso(meal_dt),
                 'flags': [], 'suggestions': []}
            # where are they?
            loc_kind, loc, kind = where_is(manager, person, meal_dt)
            v['where'] = {'locationKind': loc_kind, 'location': loc, 'during': kind}
            logi = logistics.get((e.name, person))
            if loc_kind in ('workplace', 'away', 'transit') and logi is None:
                v['flags'].append(f'{person} is at {loc or loc_kind} ({kind}) at {at} — this meal '
                                  f'needs a MealLogistics situation (packed) or a different time')
                v['suggestions'].append({'kind': 'situation', 'situation': 'at-workplace-cold'
                                         if loc_kind == 'workplace' else 'packed-no-cooling'})
            if kind == 'sleep':
                v['flags'].append(f'{person} is asleep at {at}')
            # dinner → sleep spacing
            if slot in ('dinner', 'linner'):
                pref = _sleep_pref(manager, person)
                gap_needed = int(getattr(pref, 'dinner_to_sleep_min', DINNER_TO_SLEEP_DEFAULT_MIN)
                                 if pref else DINNER_TO_SLEEP_DEFAULT_MIN)
                bed = getattr(pref, 'bedtime_hhmm', '23:00') if pref else '23:00'
                bed_dt = datetime.combine(mdate, datetime.strptime(bed, '%H:%M').time())
                if bed_dt <= meal_dt:
                    bed_dt += timedelta(days=1)
                eating = _eating_minutes(manager, person, slot)
                gap = (bed_dt - (meal_dt + timedelta(minutes=eating))).total_seconds() / 60.0
                v['dinnerToSleep'] = {'minutes': round(gap), 'needed': gap_needed,
                                      'bedtime': bed, 'eatingMin': eating,
                                      'source': 'the person\'s SleepPreference' if pref else 'default (120 min)',
                                      'citation': getattr(pref, 'citation', '') if pref else ''}
                if gap < gap_needed:
                    latest = bed_dt - timedelta(minutes=gap_needed + eating)
                    v['flags'].append(f'dinner ends {round(gap)} min before {person}\'s bedtime '
                                      f'({bed}); their preference is {gap_needed} min — try to '
                                      f'make meals that do not make this worse')
                    v['suggestions'].append({'kind': 'move', 'latestStart': _iso(latest)})
            verdicts.append(v)
    flagged = [v for v in verdicts if v['flags']]
    return {'ok': True, 'schema': 'meal-timing/1', 'plan': plan_row.name,
            'weekStart': start.isoformat(), 'people': people,
            'verdicts': verdicts, 'flaggedCount': len(flagged),
            'posture': ('comfort heuristics over stated preferences — the default spacing is '
                        '2 h (his call), the cited guidance says ~3 h; nothing here diagnoses '
                        'or blocks; every flag names a move'),
            'honesty': 'meal times are the entry\'s own or the slot prior; eating time is the profile prior'}



# ---------------------------------------------------------------
# mlg-2: prep time per person
# ---------------------------------------------------------------

def _eating_minutes(manager, person, slot):
    for p in _rows(manager, 'MealTimeProfile'):
        if getattr(p, 'person_name', '') == person and getattr(p, 'slot', '') == slot:
            return float(getattr(p, 'eating_min', 0) or 0)
    return EATING_PRIORS.get(slot, 30.0)


def prep_time_profile(manager, entry, person, week_plan=None):
    """Final-prep minutes for one MealEntry, for one person, from the
    pre-prep actually planned (reheat / assemble steps), plus the
    eating minutes — each number with its fidelity."""
    e = entry if not isinstance(entry, str) else _named(manager, 'MealEntry', entry)
    if e is None:
        return {'ok': False, 'error': f"MealEntry '{entry}' not found"}
    storage = {getattr(s, 'name', ''): s for s in _rows(manager, 'StorageActionDefinition')}
    methods = {getattr(m, 'name', ''): m for m in _rows(manager, 'StepMethod')}
    steps = []
    # reheat (from pre-prep) when the day's actions say so, else assemble only
    day = int(getattr(e, 'day_index', 1) or 1)
    actions = (week_plan or {}).get('dailyActions', {}) if week_plan else {}
    day_actions = actions.get(day) or actions.get(str(day)) or []
    if any(a.get('action') == 'reheat' for a in day_actions):
        reheat = storage.get('reheat')
        steps.append({'task': 'reheat', 'method': 'reheat',
                      'baseMin': float(getattr(reheat, 'duration_min', 5) or 5) if reheat else 5.0})
    assemble = methods.get('assemble-plate')
    steps.append({'task': 'assemble', 'method': 'assemble-plate',
                  'baseMin': float(getattr(assemble, 'base_min', 3) or 3) if assemble else 3.0})
    total, safety_added = 0.0, 0.0
    for s in steps:
        r = step_minutes(manager, person, s['method'], s['baseMin'])
        s.update(r)
        s['safety'] = safety_check(manager, person, s['method'])
        total += r['minutes']
        safety_added += r['minutes'] - r['raw']
    eating = _eating_minutes(manager, person, getattr(e, 'slot', ''))
    return {'ok': True, 'schema': 'prep-time-profile/1', 'entry': e.name, 'person': person,
            'slot': getattr(e, 'slot', ''), 'steps': steps,
            'finalPrepMin': round(total, 1), 'safetyAddedMin': round(safety_added, 1),
            'eatingMin': eating,
            'fidelity': {'finalPrep': 'observed' if all(f['fidelity'] == 'observed'
                                                        for s in steps for f in s['factors'])
                         and steps else 'estimate', 'eating': 'estimate'},
            'honesty': ('final prep = the steps left after pre-prep (reheat/assemble) × the '
                        'person\'s factor for each step\'s skills, never below the safety floor; '
                        'eating time is a household prior')}



# ---------------------------------------------------------------
# mlg-3: portability
# ---------------------------------------------------------------

def portability_plan(manager, plan, week_start=None):
    """pack + freeze-packs events for every packed meal; container /
    cold-pack needs against the tool inventory; missing NAMED."""
    plan_row = plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)
    if plan_row is None:
        return {'ok': False, 'error': f"MealPlanDefinition '{plan}' not found", 'proposals': []}
    start = _d(week_start) or _d(getattr(plan_row, 'start_date', '')) or date.today()
    household = getattr(plan_row, 'household_name', '')
    situations = {getattr(s, 'name', ''): s for s in _rows(manager, 'MealSituation')}
    owned = {getattr(t, 'tool_name', '') for t in _rows(manager, 'KitchenTool')
             if getattr(t, 'household_name', '') == household and getattr(t, 'owned', True)}
    entries = {getattr(e, 'name', ''): e for e in _rows(manager, 'MealEntry')
               if getattr(e, 'plan_name', '') == plan_row.name}
    proposals, needs, missing = [], [], []
    for l in _rows(manager, 'MealLogistics'):
        e = entries.get(getattr(l, 'entry_name', ''))
        sit = situations.get(getattr(l, 'situation_name', ''))
        if e is None or sit is None:
            continue
        if getattr(sit, 'eaten_at', 'home') == 'home':
            continue
        day = int(getattr(e, 'day_index', 1) or 1)
        mdate = start + timedelta(days=day - 1)
        person = getattr(l, 'person_name', '') or getattr(plan_row, 'person_name', '')
        container = getattr(l, 'container_tool_name', '') or getattr(sit, 'needs_container', '')
        packs = int(getattr(l, 'cold_pack_count', 0) or getattr(sit, 'cold_pack_count', 0) or 0)
        need = {'entry': e.name, 'person': person, 'situation': sit.name,
                'container': container, 'coldPacks': packs,
                'coldHoursRequired': getattr(sit, 'cold_hours_required', 0.0),
                'citation': getattr(sit, 'citation', '')}
        for tool in [t for t in (container, 'cold-pack' if packs else '') if t]:
            if owned and tool not in owned:
                missing.append({'entry': e.name, 'tool': tool,
                                'why': f'{tool} is not in the household inventory (KitchenTool)'})
        needs.append(need)
        # when do they leave? the first away block that day for the person
        av = availability_windows(manager, person, mdate, mdate)
        leave = next((_dt(b['start']) for b in av['busy']
                      if b['locationKind'] in ('workplace', 'away', 'transit')), None)
        pack_when = getattr(l, 'pack_when', '') or getattr(sit, 'pack_when', 'morning')
        pack_min = float(getattr(sit, 'pack_minutes', 5) or 5)
        if pack_when == 'night-before' or leave is None:
            pack_at = datetime.combine(mdate - timedelta(days=1), datetime.strptime('21:00', '%H:%M').time())
        else:
            pack_at = leave - timedelta(minutes=pack_min + 10)
        proposals.append({
            'name': f'pack-{e.name}-{person}', 'title': f"Pack {getattr(e, 'slot', '')} for {person} ({sit.display_name})",
            'category': 'packing', 'household_name': household, 'person_name': person,
            'span': {'start': _iso(pack_at), 'end': _iso(pack_at + timedelta(minutes=pack_min))},
            'all_day': False, 'color': '#0277bd', 'linked_class': 'MealEntry', 'linked_name': e.name,
            'payload_json': {**need, 'packMinutesPrior': pack_min, 'leaveAt': _iso(leave) if leave else None,
                             'workload_type': 'packing'}})
        if packs:
            freeze_at = datetime.combine(mdate - timedelta(days=1), datetime.strptime('21:30', '%H:%M').time())
            proposals.append({
                'name': f'freeze-packs-{e.name}-{person}',
                'title': f'Freeze {packs} cold pack{"s" if packs != 1 else ""} for {person}\'s {getattr(e, "slot", "")}',
                'category': 'packing', 'household_name': household, 'person_name': person,
                'span': {'start': _iso(freeze_at), 'end': _iso(freeze_at + timedelta(minutes=2))},
                'all_day': False, 'color': '#0277bd', 'linked_class': 'MealEntry', 'linked_name': e.name,
                'payload_json': {'coldPacks': packs, 'citation': getattr(sit, 'citation', ''),
                                 'workload_type': 'packing'}})
    return {'ok': True, 'schema': 'portability/1', 'plan': plan_row.name, 'weekStart': start.isoformat(),
            'needs': needs, 'missingTools': missing, 'proposals': proposals,
            'honesty': ('pack time = leave time − pack minutes − 10 min (priors); cold packs are '
                        'frozen the night before; cold-hours requirements are FSIS-derived priors; '
                        'missing tools are named, never assumed')}


# ---------------------------------------------------------------
# mlg-2b: dishes
# ---------------------------------------------------------------

def dish_plan(manager, plan, week_start=None, coordination=None):
    """Cleanup events: pre-prep sessions' dishes in their UNATTENDED
    windows first (else right after the session), meal dishes after
    eating (+ cooldown); dishwasher runs as cycle + unload events."""
    plan_row = plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)
    if plan_row is None:
        return {'ok': False, 'error': f"MealPlanDefinition '{plan}' not found", 'proposals': []}
    start = _d(week_start) or _d(getattr(plan_row, 'start_date', '')) or date.today()
    household = getattr(plan_row, 'household_name', '')
    policy = next((p for p in _rows(manager, 'HouseholdDishPolicy')
                   if getattr(p, 'household_name', '') == household), None)
    strategies = {getattr(s, 'name', ''): s for s in _rows(manager, 'DishStrategy')}
    owned = {getattr(t, 'tool_name', '') for t in _rows(manager, 'KitchenTool')
             if getattr(t, 'household_name', '') == household and getattr(t, 'owned', True)}
    methods = {getattr(m, 'name', ''): m for m in _rows(manager, 'StepMethod')}

    def strategy_for(kind):
        name = getattr(policy, 'preprep_strategy' if kind == 'pre-prep' else 'meal_strategy',
                       'wash-as-you-go' if kind == 'pre-prep' else 'batch-after-meal') \
            if policy else ('wash-as-you-go' if kind == 'pre-prep' else 'batch-after-meal')
        s = strategies.get(name)
        note = ''
        if s is not None and getattr(s, 'needs_tool', '') and getattr(s, 'needs_tool') not in owned:
            note = f"{name} needs a {s.needs_tool} the household does not own — falling back"
            s = strategies.get('batch-after-meal') or s
        return s, note

    proposals, notes = [], []
    from nutrition.workflow_analysis import derive_week_plan
    week = derive_week_plan(manager, plan_row, household)
    # 1. pre-prep sessions
    for s in (week.get('sessions', []) if week.get('ok') else []):
        strat, note = strategy_for('pre-prep')
        if note:
            notes.append(note)
        tools = {st.get('method') for it in s.get('items', []) for st in it.get('steps', [])}
        load = sum(LOAD_UNITS_PER_TOOL for m in tools if m and getattr(methods.get(m), 'tool_name', ''))
        minutes = (float(getattr(strat, 'setup_min', 2) or 2) + load * float(getattr(strat, 'min_per_load_unit', 1.5) or 1.5)) if strat else 2 + load * 1.5
        unattended = sum(float(st.get('activeMin') or 0) for it in s.get('items', [])
                         for st in it.get('steps', [])
                         if st.get('method') and getattr(methods.get(st['method']), 'attended', True) is False)
        # the coordinated pre-prep event, if given, anchors the time
        anchor = None
        for p in (coordination or {}).get('proposals', []):
            if p.get('category') == 'pre-prep' and p.get('payload_json', {}).get('sessionDay') == s.get('day'):
                anchor = p
        if anchor:
            base = _dt(anchor['span']['start'])
            end = _dt(anchor['span'].get('end') or anchor['span']['start'])
        else:
            base = datetime.combine(start + timedelta(days=max(0, s.get('day', 1) - 2)), datetime.strptime('15:00', '%H:%M').time())
            end = base + timedelta(minutes=float(s.get('activeMin', 30) or 30))
        in_window = min(minutes, unattended) if getattr(strat, 'timing', '') == 'unattended-first' else 0.0
        after = minutes - in_window
        if in_window > 0:
            proposals.append(_cleanup_event(f'dishes-session-d{s.get("day")}-during', household,
                                            f'Dishes during the simmer (session day {s.get("day")})',
                                            base + timedelta(minutes=5), in_window,
                                            {'loadUnits': load, 'strategy': strat.name if strat else '',
                                             'window': 'unattended step(s)', 'unattendedMin': unattended}))
        if after > 0.5:
            proposals.append(_cleanup_event(f'dishes-session-d{s.get("day")}-after', household,
                                            f'Dishes after pre-prep (session day {s.get("day")})',
                                            end, after, {'loadUnits': load, 'strategy': strat.name if strat else ''}))
    # 2. meals
    strat, note = strategy_for('meal')
    if note:
        notes.append(note)
    eaters = [m.person_name for m in _rows(manager, 'HouseholdMember') if getattr(m, 'household_name', '') == household] \
        or [getattr(plan_row, 'person_name', '')]
    cooldown = float(getattr(policy, 'cooldown_after_eating_min', 10) or 10) if policy else 10.0
    for e in _rows(manager, 'MealEntry'):
        if getattr(e, 'plan_name', '') != plan_row.name:
            continue
        day = int(getattr(e, 'day_index', 1) or 1)
        mdate = start + timedelta(days=day - 1)
        slot = getattr(e, 'slot', '')
        at = getattr(e, 'time_hhmm', '') or SLOT_TIMES.get(slot, '12:00')
        meal_dt = datetime.combine(mdate, datetime.strptime(at, '%H:%M').time())
        eating = max(_eating_minutes(manager, p, slot) for p in eaters)
        load = LOAD_UNITS_PER_EATER * len(eaters) + 1.0  # + a serving pan/pot
        minutes = (float(getattr(strat, 'setup_min', 3) or 3) + load * float(getattr(strat, 'min_per_load_unit', 1.5) or 1.5)) if strat else 3 + load * 1.5
        when = meal_dt + timedelta(minutes=eating + cooldown)
        proposals.append(_cleanup_event(f'dishes-{e.name}', household, f'Dishes after {slot}',
                                        when, minutes, {'loadUnits': load, 'strategy': strat.name if strat else '',
                                                        'eatingMin': eating, 'cooldownMin': cooldown},
                                        linked=('MealEntry', e.name)))
        if strat is not None and getattr(strat, 'cycle_min', 0):
            proposals.append(_cleanup_event(f'dishwasher-run-{e.name}', household, 'Dishwasher run',
                                            when + timedelta(minutes=minutes), float(strat.cycle_min),
                                            {'strategy': strat.name, 'unloadMin': strat.unload_min}))
    return {'ok': True, 'schema': 'dish-plan/1', 'plan': plan_row.name, 'weekStart': start.isoformat(),
            'proposals': proposals, 'notes': notes,
            'totalMin': round(sum(p['payload_json']['minutes'] for p in proposals), 1),
            'honesty': ('load units = tools used per session + 2 per eater + a serving pan (priors); '
                        'minutes per load unit from the strategy row; unattended windows first — '
                        'a simmer is a dish window; cleanup is counted as work')}


def _cleanup_event(name, household, title, at, minutes, payload, linked=('', '')):
    payload = dict(payload, minutes=round(minutes, 1), workload_type='cleanup')
    return {'name': name, 'title': f'{title} (~{round(minutes)} min)', 'category': 'cleanup',
            'household_name': household, 'span': {'start': _iso(at), 'end': _iso(at + timedelta(minutes=minutes))},
            'all_day': False, 'color': '#8d6e63', 'linked_class': linked[0], 'linked_name': linked[1],
            'payload_json': payload}

