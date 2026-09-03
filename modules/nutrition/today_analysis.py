"""
@module nutrition.today_analysis

N2 — the TODAY page's arithmetic (HOUSEHOLD_APP_PAGES.md §3.2) and
the owed "done → WorkLedger" auto-write (TESTING_OWED §6):

  person_day(manager, person, day)   one person's CalendarEvent rows
                                     for one day in time order — eating
                                     / meal-prep / pre-prep / packing /
                                     cleanup / purchase, availability
                                     as context — as FLAT records, plus
                                     nextUp, done/planned counts and the
                                     WorkLedger lines already written
                                     for that person-day.
  mark_done_proposal(manager, event, person, minutes_actual)
                                     the proposal an engine solution
                                     consumes: the event → status done
                                     (ModifyEvent), ONE WorkLedger row
                                     (minutes = the actual minutes when
                                     given, else the event's PLANNED
                                     minutes, labelled), and ONE
                                     DurationObservation ONLY when the
                                     person answered "how long did it
                                     take". Never overwrites an existing
                                     ledger row: dedupe by name
                                     `ledger-<event>` — said in the
                                     proposal.

Every number is a labelled prior or derived from rows; every result
is renderable by api-structured-panel (scalars + lists of flat
records; None instead of {}).

@consumers nutrition.today_api, nutrition.today_seed (AnalysisDefinition
  'today-mark-done'), the no-code solutions 'today-mark-done-form' /
  'today-done-to-ledger'
"""

import json
from datetime import date, datetime, timedelta

from household.household_analysis import (
    WTYPE_OF_CATEGORY, _dt, _loads, _rows, method_requirement, safety_check,
)

#: the day list's categories, in the reading a person wants: what
#: they eat, the work around it, and where they are (context).
DAY_CATEGORIES = ('eating', 'meal-prep', 'pre-prep', 'packing', 'cleanup',
                  'purchase', 'bulk-purchase', 'availability')
CONTEXT_CATEGORIES = ('availability',)
#: category → DurationObservation.kind (the refinement loop's vocabulary)
OBS_KIND_OF_CATEGORY = {'meal-prep': 'final-prep', 'pre-prep': 'prep-step',
                        'eating': 'eating', 'packing': 'packing',
                        'cleanup': 'cleanup', 'purchase': 'purchase-trip',
                        'bulk-purchase': 'purchase-trip'}
PLANNED_LABEL = 'planned-minutes prior'
OBSERVED_LABEL = 'observed'


def _payload(ev):
    raw = getattr(ev, 'payload_json', '{}')
    return raw if isinstance(raw, dict) else _loads(raw, {})


def _span(ev):
    raw = getattr(ev, 'span', '{}')
    span = raw if isinstance(raw, dict) else _loads(raw, {})
    return _dt(span.get('start')), _dt(span.get('end') or span.get('start'))


def _day_of(text):
    if isinstance(text, date) and not isinstance(text, datetime):
        return text
    if isinstance(text, datetime):
        return text.date()
    d = _dt(text)
    return d.date() if d else None


def _household_of(manager, person):
    for m in _rows(manager, 'HouseholdMember'):
        if getattr(m, 'person_name', '') == person:
            return getattr(m, 'household_name', '')
    for p in _rows(manager, 'PersonProfile'):
        if getattr(p, 'name', '') == person and getattr(p, 'household_name', ''):
            return p.household_name
    return ''


def planned_minutes(ev):
    """The event's PLANNED minutes: its span, else the generator's
    own number in the payload (a prior either way)."""
    s, e = _span(ev)
    if s and e and e > s:
        return round((e - s).total_seconds() / 60.0, 1)
    payload = _payload(ev)
    for key in ('minutes', 'finalPrepMin', 'eatingMin', 'packMinutesPrior'):
        if payload.get(key):
            return float(payload[key])
    return 0.0


def event_methods(manager, ev):
    """The StepMethod names an event's work goes through: the payload's
    own `method` / `methods` / `steps[].method`, else — for a meal-prep
    block on a MealEntry — the final-prep steps (reheat / assemble)
    the prep profile names."""
    payload = _payload(ev)
    methods = []
    if payload.get('method'):
        methods.append(str(payload['method']))
    for m in payload.get('methods', []) or []:
        methods.append(str(m))
    for st in payload.get('steps', []) or []:
        if isinstance(st, dict) and st.get('method'):
            methods.append(str(st['method']))
    for it in payload.get('items', []) or []:
        for st in (it.get('steps', []) if isinstance(it, dict) else []) or []:
            if isinstance(st, dict) and st.get('method'):
                methods.append(str(st['method']))
    if not methods and getattr(ev, 'category', '') == 'meal-prep' \
            and getattr(ev, 'linked_class', '') == 'MealEntry':
        try:
            from nutrition.logistics_analysis import prep_time_profile
            prof = prep_time_profile(manager, getattr(ev, 'linked_name', ''),
                                     getattr(ev, 'person_name', '') or '')
            if prof.get('ok'):
                methods = [s['method'] for s in prof.get('steps', []) if s.get('method')]
        except Exception:
            methods = ['assemble-plate']
    seen, out = set(), []
    for m in methods:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


def safety_note(manager, person, ev):
    """One line naming every hazard on the event's methods (from the
    MethodSkillRequirement rows) and the verdict for this person, or
    '' when no method carries a hazard tag."""
    notes = []
    for m in event_methods(manager, ev):
        req = method_requirement(manager, m)
        hazards = _loads(getattr(req, 'hazard_tags_json', '[]'), []) if req else []
        if not hazards:
            continue
        verdict = safety_check(manager, person, m) if person else \
            {'verdict': 'unassigned', 'reasons': ['no person named']}
        why = f" — {verdict['reasons'][0]}" if verdict.get('reasons') else ''
        notes.append(f"{m}: {', '.join(hazards)} → {verdict['verdict']}{why}")
    return '; '.join(notes)


def _line(manager, person, ev, now):
    s, e = _span(ev)
    payload = _payload(ev)
    who = payload.get('assignees') or payload.get('assignee') or getattr(ev, 'person_name', '')
    if isinstance(who, list):
        who = ', '.join(str(w) for w in who)
    status = getattr(ev, 'status', 'planned') or 'planned'
    return {'time': s.strftime('%H:%M') if s else 'all day',
            'end': e.strftime('%H:%M') if e else '',
            'title': getattr(ev, 'title', '') or getattr(ev, 'name', ''),
            'category': getattr(ev, 'category', ''),
            'minutes': planned_minutes(ev),
            'status': status,
            'linkedName': getattr(ev, 'linked_name', ''),
            'assignee': str(who or ''),
            'safetyNote': safety_note(manager, person, ev),
            'eventName': getattr(ev, 'name', ''),
            'isContext': getattr(ev, 'category', '') in CONTEXT_CATEGORIES,
            'isPast': bool(e and now and e < now)}


def person_day(manager, person, day=None, now=None):
    """The person's day, in time order, as flat records."""
    the_day = _day_of(day) or date.today()
    now = now if isinstance(now, datetime) else (_dt(now) if now else datetime.now())
    household = _household_of(manager, person)
    rows = []
    for ev in _rows(manager, 'CalendarEvent'):
        cat = getattr(ev, 'category', '')
        if cat not in DAY_CATEGORIES:
            continue
        s, e = _span(ev)
        if s is None or s.date() != the_day:
            continue
        owner = getattr(ev, 'person_name', '') or ''
        hh = getattr(ev, 'household_name', '') or ''
        assignees = _payload(ev).get('assignees') or []
        mine = (owner == person or person in assignees
                or (not owner and not assignees and (not hh or not household or hh == household)))
        if not mine:
            continue
        rows.append((s, ev))
    rows.sort(key=lambda t: (t[0], getattr(t[1], 'name', '')))
    lines = [_line(manager, person, ev, now) for _s, ev in rows]
    work = [l for l in lines if not l['isContext']]
    done = [l for l in work if l['status'] == 'done']
    open_lines = [l for l in work if l['status'] not in ('done', 'cancelled')]
    next_up = None
    for l, (s, ev) in zip(lines, rows):
        if l['isContext'] or l['status'] in ('done', 'cancelled'):
            continue
        _s, e = _span(ev)
        if e is None or e >= now or s.date() > now.date():
            next_up = {k: v for k, v in l.items() if k not in ('isContext', 'isPast')}
            break
    ledger = [{'workloadType': getattr(w, 'workload_type', ''),
               'minutes': float(getattr(w, 'minutes', 0) or 0),
               'eventName': getattr(w, 'event_name', ''),
               'source': getattr(w, 'source', ''),
               'label': (OBSERVED_LABEL if OBSERVED_LABEL in str(getattr(w, 'notes', ''))
                         else PLANNED_LABEL)}
              for w in _rows(manager, 'WorkLedger')
              if getattr(w, 'person_name', '') == person
              and str(getattr(w, 'date', ''))[:10] == the_day.isoformat()]
    ledger.sort(key=lambda l: (l['workloadType'], l['eventName']))
    return {
        'ok': True, 'schema': 'today/1', 'person': person, 'household': household or None,
        'day': the_day.isoformat(), 'now': now.strftime('%Y-%m-%dT%H:%M'),
        'nextUp': next_up,
        'nextUpTitle': next_up['title'] if next_up else 'nothing left today',
        'doneCount': len(done), 'plannedCount': len(work), 'openCount': len(open_lines),
        'remainingMinutes': round(sum(l['minutes'] for l in open_lines), 1),
        'doneMinutes': round(sum(l['minutes'] for l in done), 1),
        'safetyCount': sum(1 for l in work if l['safetyNote']),
        'lines': [{k: v for k, v in l.items() if k not in ('isContext', 'isPast')} for l in lines],
        'ledger': ledger,
        'ledgerMinutes': round(sum(l['minutes'] for l in ledger), 1),
        'honesty': ('minutes are the event spans the generators planned (priors) until a '
                    '"mark done" gives the actual number; safety notes come from the '
                    'MethodSkillRequirement hazard tags of the step methods, with the '
                    'SafetyRule verdict for this person; availability rows are context, '
                    'not work'),
    }


def _existing(manager, cls, name):
    for r in _rows(manager, cls):
        if getattr(r, 'name', '') == name:
            return r
    return None


def mark_done_proposal(manager, event_name, person=None, minutes_actual=None, day=None):
    """The "mark done" proposal (nothing written here)."""
    from polariNoCode.event_dispatcher import find_instance
    ev = find_instance(manager, 'CalendarEvent', event_name) if event_name else None
    empty = {'ledgerProposals': [], 'observationProposals': [], 'modifyFields': None}
    if ev is None:
        error = f"CalendarEvent '{event_name}' is not on this node"
        return {'ok': False, 'error': error, 'message': error, 'event': event_name, **empty}
    name = getattr(ev, 'name', '') or event_name
    payload = _payload(ev)
    who = person or getattr(ev, 'person_name', '') or ''
    if not who and payload.get('assignees'):
        who = str(payload['assignees'][0])
    category = getattr(ev, 'category', '')
    wtype = payload.get('workload_type') or WTYPE_OF_CATEGORY.get(category, category)
    s, _e = _span(ev)
    the_day = (s.date() if s else (_day_of(day) or date.today())).isoformat()
    planned = planned_minutes(ev)
    actual = None
    if minutes_actual not in (None, ''):
        try:
            actual = float(minutes_actual)
        except (TypeError, ValueError):
            actual = None
    minutes = actual if actual is not None and actual > 0 else planned
    label = OBSERVED_LABEL if actual is not None and actual > 0 else PLANNED_LABEL
    ledger_name = f'ledger-{name}'
    existing = _existing(manager, 'WorkLedger', ledger_name)
    ledger = [] if (existing is not None or not who) else [{
        'name': ledger_name, 'household_name': getattr(ev, 'household_name', '') or _household_of(manager, who),
        'person_name': who, 'workload_type': wtype, 'minutes': minutes,
        'event_name': name, 'date': the_day, 'source': 'event-done',
        'is_prior': label == PLANNED_LABEL, 'provenance_id': 'today-mark-done',
        'notes': f'{label}: {minutes:g} min ({category})'}]
    methods = event_methods(manager, ev)
    obs = []
    if actual is not None and actual > 0:
        obs_name = f'obs-{name}'
        if _existing(manager, 'DurationObservation', obs_name) is None:
            obs.append({
                'name': obs_name, 'person_name': who,
                'kind': OBS_KIND_OF_CATEGORY.get(category, 'prep-step'),
                'method_name': methods[0] if methods else '',
                'skill_name': '', 'entry_name': getattr(ev, 'linked_name', '')
                if getattr(ev, 'linked_class', '') == 'MealEntry' else '',
                'slot': str(payload.get('slot', '') or ''), 'observed_min': actual,
                'date': the_day, 'source': 'logged', 'is_prior': False,
                'provenance_id': 'today-mark-done',
                'notes': f'answered "how long did it take" for {name}'})
    already_done = (getattr(ev, 'status', '') == 'done')
    if existing is not None:
        note = (f"ledger row '{ledger_name}' already exists ({float(getattr(existing, 'minutes', 0) or 0):g} "
                f"min, {getattr(existing, 'notes', '') or 'no label'}) — kept, never overwritten")
    elif not who:
        note = 'no person to credit (the event names nobody and none was given) — no ledger row'
    else:
        note = f"one WorkLedger row '{ledger_name}': {minutes:g} min of {wtype} for {who} ({label})"
    # the plain words the Mark done form shows
    message = f'Marked {name} done'
    if already_done:
        message = f'{name} was already done'
    if existing is not None:
        message += (f'; the ledger already had {float(getattr(existing, "minutes", 0) or 0):g} min '
                    f'for it — kept')
    elif not who:
        message += '; nobody to credit, so no ledger minutes'
    else:
        message += f'; {minutes:g} min to the ledger'
        if label == PLANNED_LABEL:
            message += ' (planned minutes — say how long it took to replace them)'
    if obs:
        message += f'; {actual:g} min observed for {obs[0]["method_name"] or "the step"}'
    return {
        'ok': True, 'schema': 'mark-done/1', 'event': name, 'person': who, 'message': message,
        'category': category, 'workloadType': wtype, 'day': the_day,
        'plannedMinutes': planned, 'minutesActual': actual, 'minutes': minutes,
        'minutesLabel': label, 'alreadyDone': already_done,
        'ledgerExists': existing is not None,
        'modifyFields': {'status': 'done'},
        'ledgerProposals': ledger, 'observationProposals': obs,
        'methods': methods, 'note': note,
        'honesty': ('status → done on the event; the ledger carries the planned minutes '
                    '(a prior) unless the actual minutes were given; a DurationObservation '
                    'is written ONLY from an answered "how long did it take"; the ledger '
                    'row is deduped by name so a second mark-done never double-counts'),
    }
