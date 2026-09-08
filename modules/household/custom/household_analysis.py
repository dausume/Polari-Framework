"""
@module household.custom.household_analysis

hh-1 (HOUSEHOLD_APP_PLAN.md) — the household-generic analyses the
meal-logistics round (mlg-1..4, MEAL_LOGISTICS_PLAN.md §3) built,
MOVED here with names unchanged; all PROPOSALS with every rule named:

  availability_windows  PersonSchedule recurrences → busy blocks +
                        free windows per day
  where_is              where a person is at a time
  person_factor /       a person's speed factor for a skill; the
  method_requirement    skills + safety a method needs
  step_minutes          the person's minutes for a step, bounded
                        BELOW by the safety floor (D15)
  safety_check          who may do a hazard step (alone / supervised
                        / not yet)
  refine_speed_factors  DurationObservation → PersonSkill factor
                        (median of ≥ 3, never below SPEED_FACTOR_FLOOR;
                        below-floor observations = a safety question)
  assign_work           the ALLOCATION (D13): every step of every
                        event to a person, minimising total
                        person-minutes within the percentage shares
                        ± tolerance; both allocations reported;
                        purchase-vs-delivery comparison
  fairness_readout      WorkLedger actuals vs the policies' targets

Nothing here imports a meal. The event-category → allocatable-steps
rule is a MODULE-LEVEL registry (`STEP_BUILDERS`, extended with
`register_step_builder`): household registers the generic builders
(a purchase trip, a minutes-carrying chore); nutrition registers the
meal ones (pre-prep items, reheat/assemble, packing) when
nutrition.custom.logistics_analysis imports. `WTYPE_OF_CATEGORY` (event
category → WorkloadType.name) is likewise a module-level dict that a
module extends. The meal-specific analyses (meal_timing_check,
prep_time_profile, portability_plan, dish_plan) stay in
nutrition.custom.logistics_analysis, which re-exports everything here.

@consumers
  - nutrition.custom.logistics_analysis (re-export + the meal builders)
  - AnalysisDefinition rows `household.custom.household_analysis:<fn>`
    (the calendar dispatcher resolves callable refs by string)
  - household.household_selftest
"""

import json
from datetime import date, datetime, timedelta
from statistics import median

from household.household_basis import LEVEL_ORDER, SKILL_FACTORS, SPEED_FACTOR_FLOOR
from polariNoCode.recurrence import expand_schedule


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


def _dt(text):
    try:
        return datetime.fromisoformat(str(text)[:16])
    except (TypeError, ValueError):
        return None


def _d(text, default=None):
    dt = _dt(text)
    return dt.date() if dt else default


def _hhmm(dt):
    return dt.strftime('%H:%M')


def _iso(dt):
    return dt.isoformat(timespec='minutes')


# ---------------------------------------------------------------
# availability (mlg-1)
# ---------------------------------------------------------------

def availability_windows(manager, person, from_date=None, to_date=None):
    """Busy blocks (kind, location) for a person in [from, to]; and
    the free windows between them per day."""
    start = _d(from_date) or date.today()
    end = _d(to_date) or (start + timedelta(days=6))
    blocks, unreadable = [], []
    for s in _rows(manager, 'PersonSchedule'):
        if getattr(s, 'person_name', '') != person:
            continue
        try:
            occ = expand_schedule(getattr(s, 'recurrence', '{}'),
                                  datetime.combine(start, datetime.min.time()) - timedelta(days=1),
                                  datetime.combine(end, datetime.max.time()))
        except ValueError as e:
            unreadable.append({'schedule': s.name, 'why': str(e)})
            continue
        for o in occ:
            e = o['end'] or o['start']
            if e.date() < start or o['start'].date() > end:
                continue
            blocks.append({'schedule': s.name, 'kind': getattr(s, 'kind', ''),
                           'start': _iso(o['start']), 'end': _iso(e),
                           'locationKind': getattr(s, 'location_kind', ''),
                           'location': getattr(s, 'location_name', ''),
                           'flexibilityMin': getattr(s, 'flexibility_min', 0)})
    blocks.sort(key=lambda b: b['start'])
    free = []
    day = start
    while day <= end:
        cursor = datetime.combine(day, datetime.min.time())
        day_end = cursor + timedelta(days=1)
        for b in blocks:
            bs, be = _dt(b['start']), _dt(b['end'])
            if be <= cursor or bs >= day_end:
                continue
            if bs > cursor:
                free.append({'date': day.isoformat(), 'start': _iso(cursor), 'end': _iso(min(bs, day_end))})
            cursor = max(cursor, be)
        if cursor < day_end:
            free.append({'date': day.isoformat(), 'start': _iso(cursor), 'end': _iso(day_end)})
        day += timedelta(days=1)
    return {'ok': True, 'schema': 'availability/1', 'person': person,
            'from': start.isoformat(), 'to': end.isoformat(),
            'busy': blocks, 'free': free, 'unreadable': unreadable,
            'honesty': 'recurrences expanded from PersonSchedule rows; sleep is a block like any other'}


def where_is(manager, person, at):
    """(locationKind, location, kind) for a person at datetime `at`,
    or ('home', '', 'free') when nothing is scheduled."""
    av = availability_windows(manager, person, at.date(), at.date())
    for b in av['busy']:
        if _dt(b['start']) <= at < _dt(b['end']):
            return b['locationKind'], b['location'], b['kind']
    return 'home', '', 'free'


def _sleep_pref(manager, person):
    for p in _rows(manager, 'SleepPreference'):
        if getattr(p, 'person_name', '') == person:
            return p
    return None


# ---------------------------------------------------------------
# skills, safety, refinement (mlg-2)
# ---------------------------------------------------------------

def person_factor(manager, person, skill):
    """(factor, level, fidelity) for a person × skill; the level prior
    when no row (novice — the honest default)."""
    for ps in _rows(manager, 'PersonSkill'):
        if getattr(ps, 'person_name', '') == person and getattr(ps, 'skill_name', '') == skill:
            return (float(getattr(ps, 'speed_factor', 1.0) or 1.0),
                    getattr(ps, 'level', 'novice'), getattr(ps, 'fidelity', 'estimate'))
    return SKILL_FACTORS['novice'], 'novice', 'default'


def method_requirement(manager, method_name):
    for r in _rows(manager, 'MethodSkillRequirement'):
        if getattr(r, 'method_name', '') == method_name:
            return r
    return None


def step_minutes(manager, person, method_name, base_minutes):
    """The person's minutes for a step = max(base × slowest-skill
    factor, safety floor). Returns the number + how it was reached."""
    req = method_requirement(manager, method_name)
    skills = _loads(getattr(req, 'skills_json', '[]'), []) if req else []
    floor = float(getattr(req, 'safety_floor_min', 0) or 0) if req else 0.0
    factors = []
    for s in skills:
        f, level, fid = person_factor(manager, person, s.get('skill', ''))
        factors.append({'skill': s.get('skill'), 'factor': f, 'level': level, 'fidelity': fid,
                        'floorLevel': s.get('floor', '')})
    governing = max((f['factor'] for f in factors), default=1.0)
    raw = float(base_minutes or 0) * governing
    minutes = max(raw, floor)
    return {'minutes': round(minutes, 1), 'raw': round(raw, 1), 'safetyFloorMin': floor,
            'boundedBySafety': minutes > raw + 1e-9, 'factors': factors,
            'governingFactor': governing}


def safety_check(manager, person, method_name):
    """May `person` do this step? alone | supervised | unassigned, with
    the rule that says so."""
    req = method_requirement(manager, method_name)
    hazards = _loads(getattr(req, 'hazard_tags_json', '[]'), []) if req else []
    verdict, reasons = 'alone', []
    for tag in hazards:
        for rule in _rows(manager, 'SafetyRule'):
            if getattr(rule, 'hazard_tag', '') != tag:
                continue
            _, level, _ = person_factor(manager, person, getattr(rule, 'skill_name', 'kitchen-safety'))
            if LEVEL_ORDER.get(level, 0) < LEVEL_ORDER.get(getattr(rule, 'required_level', ''), 0):
                below = getattr(rule, 'below_floor', 'supervised')
                verdict = 'unassigned' if (below == 'unassigned' or verdict == 'unassigned') else 'supervised'
                reasons.append(f"{tag}: {person} is {level} in {rule.skill_name}, the rule wants "
                               f"{rule.required_level} → {below} ({rule.rule_text})")
    # skill floors on the requirement itself
    for s in (_loads(getattr(req, 'skills_json', '[]'), []) if req else []):
        floor = s.get('floor') or ''
        if floor:
            _, level, _ = person_factor(manager, person, s.get('skill', ''))
            if LEVEL_ORDER.get(level, 0) < LEVEL_ORDER.get(floor, 0):
                verdict = 'unassigned' if verdict == 'unassigned' else 'supervised'
                reasons.append(f"{s.get('skill')}: {person} is {level}, the method's floor is {floor}")
    return {'person': person, 'method': method_name, 'verdict': verdict,
            'hazards': hazards, 'reasons': reasons}


def refine_speed_factors(manager, person=None, min_observations=3):
    """DurationObservation → proposed PersonSkill speed factors
    (median of ≥ 3 vs the method's base minutes); never below the
    floor — a would-be-lower factor is a SAFETY QUESTION, not skill.
    Returns proposals; writing them is a person's (or a trigger's)
    act. The method's base minutes are read from the `StepMethod`
    table by name (rows, not an import) — any module that seeds
    methods with a `base_min` joins the loop."""
    methods = {getattr(m, 'name', ''): m for m in _rows(manager, 'StepMethod')}
    groups = {}
    for o in _rows(manager, 'DurationObservation'):
        if getattr(o, 'kind', '') != 'prep-step':
            continue
        if person and getattr(o, 'person_name', '') != person:
            continue
        key = (o.person_name, getattr(o, 'skill_name', ''))
        m = methods.get(getattr(o, 'method_name', ''))
        base = float(getattr(m, 'base_min', 0) or 0) if m else 0.0
        if base <= 0:
            continue
        groups.setdefault(key, []).append(float(getattr(o, 'observed_min', 0) or 0) / base)
    proposals, questions = [], []
    for (p, skill), ratios in groups.items():
        if len(ratios) < min_observations:
            proposals.append({'person': p, 'skill': skill, 'observations': len(ratios),
                              'status': f'needs {min_observations - len(ratios)} more observation(s)'})
            continue
        med = median(ratios)
        current, level, fid = person_factor(manager, p, skill)
        if med < SPEED_FACTOR_FLOOR:
            questions.append({'person': p, 'skill': skill, 'observedFactor': round(med, 2),
                              'floor': SPEED_FACTOR_FLOOR,
                              'question': (f'{p} is observed {round((1 - med) * 100)} % faster than '
                                           f'the method time — faster than the safety floor allows; '
                                           f'is a step being skipped or rushed? Factor stays at '
                                           f'{SPEED_FACTOR_FLOOR}.')})
            med = SPEED_FACTOR_FLOOR
        proposals.append({'person': p, 'skill': skill, 'observations': len(ratios),
                          'currentFactor': current, 'proposedFactor': round(med, 2),
                          'fidelity': 'observed', 'status': 'proposal'})
    return {'ok': True, 'schema': 'speed-refinement/1', 'proposals': proposals,
            'safetyQuestions': questions,
            'honesty': (f'median of at least {min_observations} observations per person × skill; '
                        f'a factor is never refined below {SPEED_FACTOR_FLOOR} — skilled, not fast')}


# ---------------------------------------------------------------
# the allocation (mlg-4)
# ---------------------------------------------------------------

def _policy_for(manager, household, wtype):
    for p in _rows(manager, 'WorkDistributionPolicy'):
        if getattr(p, 'household_name', '') == household and getattr(p, 'workload_type', '') == wtype:
            return p
    return None


def _members(manager, household):
    return [m for m in _rows(manager, 'HouseholdMember') if getattr(m, 'household_name', '') == household]


def _is_free(manager, person, start_dt, end_dt):
    if start_dt is None:
        return True
    for b in availability_windows(manager, person, start_dt.date(), (end_dt or start_dt).date())['busy']:
        if b['kind'] in ('sleep', 'work', 'commute', 'school') and _dt(b['start']) < (end_dt or start_dt) and _dt(b['end']) > start_dt:
            return False
    return True


#: event category → the allocatable steps inside such an event:
#: `fn(event, payload, base_min) -> [{'label', 'method', 'baseMin'}]`.
#: household registers the generic builders below; a module that
#: generates its own event categories registers theirs at import time
#: (nutrition.custom.logistics_analysis: pre-prep / meal-prep / packing).
STEP_BUILDERS = {}

#: event category → WorkloadType.name (the policy that splits it).
#: The workload-type vocabulary is seeded by household
#: (SEED_WORKLOAD_TYPES), so the defaults live here; a module adds
#: its categories with `WTYPE_OF_CATEGORY.update(...)`.
WTYPE_OF_CATEGORY = {'purchase': 'purchase-trip', 'bulk-purchase': 'purchase-trip',
                     'pre-prep': 'pre-prep', 'meal-prep': 'meal-prep',
                     'packing': 'packing', 'cleanup': 'cleanup'}


def register_step_builder(category, fn, workload_type=None):
    """Register (or replace) the step builder for an event category;
    optionally name the WorkloadType the category's policy is read
    from."""
    STEP_BUILDERS[category] = fn
    if workload_type:
        WTYPE_OF_CATEGORY[category] = workload_type
    return fn


def _purchase_steps(event, payload, base_min):
    return [{'label': 'shop', 'method': '', 'baseMin': base_min}]


def minutes_steps(method=''):
    """A builder for any category whose payload carries `minutes`
    (a chore sized by its generator): one step, optionally bound to
    a method so skills + safety apply."""
    def build(event, payload, base_min):
        return [{'label': event.get('category', ''), 'method': method,
                 'baseMin': float(payload.get('minutes') or base_min)}]
    return build


register_step_builder('purchase', _purchase_steps)
register_step_builder('cleanup', minutes_steps(''))


def _steps_of(event, manager, people):
    """The allocatable steps inside a generated event (via the
    category's registered builder), with each person's minutes +
    safety verdict."""
    cat = event.get('category', '')
    payload = event.get('payload_json') or {}
    if isinstance(payload, str):
        payload = _loads(payload, {})
    span = event.get('span') or {}
    s_dt, e_dt = _dt(span.get('start')), _dt(span.get('end') or span.get('start'))
    base_min = (e_dt - s_dt).total_seconds() / 60.0 if (s_dt and e_dt) else 30.0
    builder = STEP_BUILDERS.get(cat)
    if builder is None:
        return []
    steps = builder(event, payload, base_min)
    for st in steps:
        st['options'] = {}
        for p in people:
            m = step_minutes(manager, p, st['method'], st['baseMin']) if st['method'] else \
                {'minutes': st['baseMin'], 'raw': st['baseMin'], 'boundedBySafety': False, 'factors': []}
            safety = safety_check(manager, p, st['method']) if st['method'] else {'verdict': 'alone', 'reasons': []}
            st['options'][p] = {'minutes': m['minutes'], 'boundedBySafety': m.get('boundedBySafety', False),
                                'verdict': safety['verdict'], 'reasons': safety['reasons'],
                                'free': _is_free(manager, p, s_dt, e_dt)}
    return steps


def assign_work(manager, events, household):
    """Allocate every step of every event to a person: minimise total
    person-minutes (skill factors, safety floors), within the policy's
    shares ± tolerance; report BOTH allocations."""
    people = [m.person_name for m in _members(manager, household)]
    if not people:
        return {'ok': False, 'error': f"no HouseholdMember rows for '{household}' — add the people first"}
    per_type = {}
    allocation, pure = [], []
    totals = {p: 0.0 for p in people}
    pure_totals = {p: 0.0 for p in people}
    unassigned = []
    for ev in events:
        wtype = WTYPE_OF_CATEGORY.get(ev.get('category', ''))
        if not wtype:
            continue
        policy = _policy_for(manager, household, wtype)
        mode = getattr(policy, 'mode', 'shares') if policy else 'shares'
        shares = _loads(getattr(policy, 'shares_json', '{}'), {}) if policy else {}
        tol = float(getattr(policy, 'share_tolerance_pct', 10) or 10) if policy else 10.0
        bucket = per_type.setdefault(wtype, {'mode': mode, 'shares': shares, 'tolerance': tol,
                                             'minutes': {p: 0.0 for p in people}, 'pureMinutes': {p: 0.0 for p in people}})
        steps = _steps_of(ev, manager, people)
        if mode == 'everyone' or mode == 'delivery' and wtype == 'purchase-trip':
            # everyone goes (his 2-adult example) / delivery = nobody travels
            who = people if mode == 'everyone' else []
            for st in steps:
                for p in who:
                    mins = st['options'][p]['minutes']
                    bucket['minutes'][p] += mins; totals[p] += mins
                    bucket['pureMinutes'][p] += mins; pure_totals[p] += mins
                allocation.append({'event': ev.get('name'), 'step': st['label'], 'assignees': who,
                                   'minutesEach': {p: st['options'][p]['minutes'] for p in who},
                                   'mode': mode})
            continue
        for st in steps:
            eligible = [(p, o) for p, o in st['options'].items() if o['verdict'] != 'unassigned' and o['free']]
            if not eligible:
                unassigned.append({'event': ev.get('name'), 'step': st['label'],
                                   'why': 'nobody free and safe for it — ' + '; '.join(
                                       f"{p}: {o['verdict']}{'' if o['free'] else ' (busy)'}" for p, o in st['options'].items())})
                continue
            if mode == 'assigned' and getattr(policy, 'assigned_person', ''):
                pick = next(((p, o) for p, o in eligible if p == policy.assigned_person), eligible[0])
            elif mode == 'assigned' and ev.get('person_name') in dict(eligible):
                pick = (ev['person_name'], dict(eligible)[ev['person_name']])
            elif mode == 'rotate':
                order = _loads(getattr(policy, 'rotation_order_json', '[]'), []) or people
                idx = len([a for a in allocation if a.get('mode') == 'rotate']) % len(order)
                pick = next(((p, o) for p, o in eligible if p == order[idx]), eligible[0])
            else:
                # shares: fastest person whose share is still under target (+ tolerance)
                fastest = min(eligible, key=lambda po: po[1]['minutes'])
                bucket['pureMinutes'][fastest[0]] += fastest[1]['minutes']; pure_totals[fastest[0]] += fastest[1]['minutes']
                total_so_far = sum(bucket['minutes'].values()) + fastest[1]['minutes']
                def over(p):
                    target = float(shares.get(p, 100.0 / len(people)))
                    would = (bucket['minutes'][p] + st['options'][p]['minutes']) / total_so_far * 100.0
                    return would - target
                under = [po for po in eligible if over(po[0]) <= tol]
                pick = min(under, key=lambda po: po[1]['minutes']) if under else min(eligible, key=lambda po: over(po[0]))
            p, o = pick
            bucket['minutes'][p] += o['minutes']; totals[p] += o['minutes']
            if mode != 'shares':
                bucket['pureMinutes'][p] += o['minutes']; pure_totals[p] += o['minutes']
            allocation.append({'event': ev.get('name'), 'step': st['label'], 'assignees': [p],
                               'minutesEach': {p: o['minutes']}, 'mode': mode,
                               'supervised': o['verdict'] == 'supervised',
                               'reasons': o['reasons'], 'boundedBySafety': o['boundedBySafety']})
    # per-type share readout
    readout = {}
    for wtype, b in per_type.items():
        tot = sum(b['minutes'].values()) or 1.0
        readout[wtype] = {'mode': b['mode'], 'targetPct': b['shares'], 'tolerancePct': b['tolerance'],
                          'actualPct': {p: round(m / tot * 100.0, 1) for p, m in b['minutes'].items()},
                          'minutes': {p: round(m, 1) for p, m in b['minutes'].items()},
                          'pureMinimumMinutes': {p: round(m, 1) for p, m in b['pureMinutes'].items()}}
    total_min = round(sum(totals.values()), 1)
    pure_min = round(sum(pure_totals.values()), 1)
    # purchase vs delivery comparison
    comparison = None
    policy = _policy_for(manager, household, 'purchase-trip')
    purchase = next((e for e in events if e.get('category') == 'purchase'), None)
    if policy is not None and purchase is not None:
        payload = purchase.get('payload_json') or {}
        if isinstance(payload, str):
            payload = _loads(payload, {})
        basket = float(payload.get('estTotal') or 0)
        shoppers = people if getattr(policy, 'mode', '') == 'everyone' else [people[0]]
        trip_min = float(getattr(policy, 'travel_min_per_trip', 0) or 0) + 60.0
        labor = getattr(policy, 'labor_value_per_hour', '')
        comparison = {'basket': basket, 'shoppers': shoppers,
                      'trip': {'minutesPerPerson': trip_min, 'personMinutes': trip_min * len(shoppers),
                               'travelCost': getattr(policy, 'travel_cost_per_trip', 0.0),
                               'laborValue': round(trip_min * len(shoppers) / 60.0 * float(labor), 2) if labor else None},
                      'delivery': {'fee': getattr(policy, 'delivery_fee', 0.0),
                                   'markup': round(basket * float(getattr(policy, 'delivery_markup_pct', 0) or 0) / 100.0, 2),
                                   'minOrder': getattr(policy, 'delivery_min_order', 0.0),
                                   'meetsMinOrder': basket >= float(getattr(policy, 'delivery_min_order', 0) or 0),
                                   'personMinutes': 10.0},
                      'honesty': ('a COMPARISON — the policy mode decides; labor value is the household\'s '
                                  'own number (empty = minutes only)')}
    return {'ok': True, 'schema': 'work-allocation/1', 'household': household, 'people': people,
            'allocation': allocation, 'unassigned': unassigned, 'readout': readout,
            'totalPersonMinutes': total_min, 'pureMinimumPersonMinutes': pure_min,
            'minutesGivenUpForShares': round(total_min - pure_min, 1),
            'purchaseVsDelivery': comparison,
            'honesty': ('each step goes to the fastest free, safe person whose share stays within '
                        'tolerance; the pure-minimum allocation is shown beside it; a step nobody '
                        'may do alone is supervised or left unassigned and NAMED; skilled, not fast')}


def fairness_readout(manager, household, from_date=None, to_date=None):
    """WorkLedger actuals vs the policies' targets."""
    rows = [w for w in _rows(manager, 'WorkLedger') if getattr(w, 'household_name', '') == household]
    if from_date:
        rows = [w for w in rows if str(getattr(w, 'date', '')) >= str(from_date)]
    if to_date:
        rows = [w for w in rows if str(getattr(w, 'date', '')) <= str(to_date)]
    by = {}
    for w in rows:
        by.setdefault(w.workload_type, {}).setdefault(w.person_name, 0.0)
        by[w.workload_type][w.person_name] += float(getattr(w, 'minutes', 0) or 0)
    # one flat record per (workload type, person) — renders as a table,
    # never as a JSON expander; `byType` keeps the grouped reading.
    lines, out = [], {}
    for wtype, mins in by.items():
        policy = _policy_for(manager, household, wtype)
        shares = _loads(getattr(policy, 'shares_json', '{}'), {}) if policy else {}
        tot = sum(mins.values()) or 1.0
        actual = {p: round(m / tot * 100.0, 1) for p, m in mins.items()}
        drift = {p: round(actual.get(p, 0.0) - float(shares.get(p, 0)), 1) for p in set(actual) | set(shares)}
        suggestion = (f"rebalance toward {min(drift, key=drift.get)}" if drift and max(drift.values()) > 10 else '')
        out[wtype] = {'minutes': mins, 'actualPct': actual, 'targetPct': shares, 'driftPct': drift,
                      'suggestion': suggestion}
        for p in sorted(set(actual) | set(shares)):
            lines.append({'workload': wtype, 'person': p, 'minutes': round(mins.get(p, 0.0), 1),
                          'actualPct': actual.get(p, 0.0), 'targetPct': shares.get(p, 0),
                          'driftPct': drift.get(p, 0.0), 'suggestion': suggestion})
    return {'ok': True, 'schema': 'fairness/2', 'household': household, 'lines': lines,
            'byType': out if out else None,
            'records': len(rows),
            'status': ('no WorkLedger rows yet — mark generated events done (or log minutes) '
                       'and the readout fills' if not rows else f'{len(rows)} ledger row(s)'),
            'honesty': 'actuals from WorkLedger rows (done events, logs); a suggestion, never a reassignment'}
