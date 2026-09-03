"""
@module polariNoCode.calendar_events

cal-1 — event RESOLUTION: an EventDefinition + a class's live rows →
concrete calendar events (FullCalendar EventInput dicts) inside a
window, with every row that could NOT be read as an event COUNTED
and NAMED (never silently dropped). A CalendarDefinition's layers
resolve through the same function, merged.

Readings, in the order the definition declares them:
  span_field          {"start", "end"} JSON (date_duration/datetime_duration)
  start_field         a date or datetime value
  relative_start_json base row's date + offset (plan.start_date + day_index)
  time_field / slot_field + slot_times_json  join a time onto a date-only start
  end_field / duration_field + duration_unit  the end
  all_day / all_day_field                      the all-day reading
  schedule_field      a `schedule` value → occurrences (recurrence.py)

@consumers polariApiServer.calendarAPI, the EventWindowQuery node
  (cal-2), the tick dispatcher (window triggers), nutrition seeds
"""

import inspect
import json
from datetime import datetime, time, timedelta
from types import SimpleNamespace

from polariNoCode.recurrence import expand_schedule, _parse_date

DURATION_UNITS = {'seconds': 1, 'minutes': 60, 'hours': 3600,
                  'days': 86400, 'weeks': 604800}
#: fields copied onto extendedProps when the row carries them.
_EXTRA_FIELDS = ('status', 'category', 'linked_class', 'linked_name',
                 'generated_by', 'person_name', 'household_name',
                 'payload_json', 'slot', 'plan_name')


def _loads(text, default):
    if isinstance(text, (dict, list)):
        return text
    try:
        value = json.loads(text) if text else default
    except (TypeError, ValueError):
        return default
    return value if value not in (None, '') else default


def _rows(manager, class_name):
    tables = getattr(manager, 'objectTables', {}) or {}
    return list((tables.get(class_name, {}) or {}).values())


def _by_name(manager, class_name, name):
    for row in _rows(manager, class_name):
        if str(getattr(row, 'name', '')) == str(name):
            return row
    return None


def _coerce_dt(value):
    """value → (datetime, date_only) or (None, False)."""
    if value in (None, ''):
        return None, False
    dt = _parse_date(value)
    if dt is None:
        return None, False
    text = str(value).strip()
    date_only = (len(text) == 10) if isinstance(value, str) else (
        not isinstance(value, datetime))
    return dt, date_only


def _parse_span(value):
    span = _loads(value, {})
    if not isinstance(span, dict):
        return None, None, 'span is not {start,end}'
    start, so = _coerce_dt(span.get('start'))
    if start is None:
        return None, None, 'span has no readable start'
    end, _ = _coerce_dt(span.get('end'))
    return (start, so), end, ''


def make_definition(**fields):
    """An EventDefinition-shaped object WITHOUT a manager (previews,
    selftests): every constructor default, overridden by `fields`."""
    from polariApiServer.eventDefinition import EventDefinition
    sig = inspect.signature(EventDefinition.__init__)
    values = {k: p.default for k, p in sig.parameters.items()
              if k not in ('self', 'manager') and p.default is not inspect._empty}
    values.update(fields)
    return SimpleNamespace(**values)


def resolve_row_start(defn, row, manager, slot_times=None):
    """One row → (start: datetime, end: datetime|None, all_day: bool,
    reason: str). reason != '' means the row is NOT an event."""
    start = end = None
    date_only = False
    # 1. where the start comes from
    if getattr(defn, 'span_field', ''):
        raw = getattr(row, defn.span_field, None)
        if raw in (None, '', '{}'):
            return None, None, False, f'{defn.span_field} is empty'
        got, end, reason = _parse_span(raw)
        if reason:
            return None, None, False, reason
        start, date_only = got
    elif getattr(defn, 'start_field', ''):
        start, date_only = _coerce_dt(getattr(row, defn.start_field, None))
        if start is None:
            return None, None, False, f'{defn.start_field} is empty or unreadable'
    else:
        rel = _loads(getattr(defn, 'relative_start_json', '{}'), {})
        if not rel:
            return None, None, False, 'definition names no span, start or relative start'
        base = _by_name(manager, rel.get('baseClass', ''),
                        getattr(row, rel.get('baseNameField', ''), None))
        if base is None:
            return None, None, False, (f"{rel.get('baseClass')} "
                                       f"'{getattr(row, rel.get('baseNameField', ''), '')}' not found")
        start, date_only = _coerce_dt(getattr(base, rel.get('baseDateField', ''), None))
        if start is None:
            return None, None, False, f"{rel.get('baseClass')}.{rel.get('baseDateField')} is empty"
        try:
            offset = float(getattr(row, rel.get('offsetField', ''), 0) or 0)
        except (TypeError, ValueError):
            offset = 0.0
        offset -= float(rel.get('offsetBase', 1) or 0)
        unit = rel.get('offsetUnit', 'days')
        start = start + timedelta(seconds=offset * DURATION_UNITS.get(unit, 86400))
    # 2. join a time onto a date-only start
    if date_only:
        hhmm = ''
        if getattr(defn, 'time_field', ''):
            hhmm = str(getattr(row, defn.time_field, '') or '')
        if not hhmm and getattr(defn, 'slot_field', ''):
            table = dict(_loads(getattr(defn, 'slot_times_json', '{}'), {}))
            table.update(slot_times or {})
            hhmm = str(table.get(str(getattr(row, defn.slot_field, '') or ''), '') or '')
        if hhmm:
            try:
                hh, mm = hhmm.split(':')[:2]
                start = datetime.combine(start.date(), time(int(hh), int(mm)))
                date_only = False
            except ValueError:
                pass
    # 3. the end
    if end is None and getattr(defn, 'end_field', ''):
        end, _ = _coerce_dt(getattr(row, defn.end_field, None))
    if end is None and getattr(defn, 'duration_field', ''):
        try:
            amount = float(getattr(row, defn.duration_field, 0) or 0)
        except (TypeError, ValueError):
            amount = 0.0
        if amount > 0:
            end = start + timedelta(
                seconds=amount * DURATION_UNITS.get(getattr(defn, 'duration_unit', 'minutes'), 60))
    # 4. the all-day reading
    all_day = bool(getattr(defn, 'all_day', False))
    if getattr(defn, 'all_day_field', ''):
        all_day = all_day or bool(getattr(row, defn.all_day_field, False))
    if date_only and end is None:
        all_day = True
    return start, end, all_day, ''


def _color_for(defn, row):
    if getattr(defn, 'color_field', ''):
        value = getattr(row, defn.color_field, '')
        cmap = _loads(getattr(defn, 'color_map_json', '{}'), {})
        if isinstance(cmap, dict) and str(value) in cmap:
            return cmap[str(value)]
        if value and str(value).startswith('#'):
            return str(value)
    return getattr(defn, 'color', '') or ''


def _matches(defn, row, person, household, filters):
    for field, want in (filters or {}).items():
        if str(getattr(row, field, '')) != str(want):
            return False
    pf = getattr(defn, 'person_field', '')
    if person and pf and hasattr(row, pf) and str(getattr(row, pf, '')) != str(person):
        return False
    hf = getattr(defn, 'household_field', '')
    if household and hf and hasattr(row, hf) and str(getattr(row, hf, '')) != str(household):
        return False
    return True


def _iso(dt):
    return dt.isoformat(timespec='minutes') if isinstance(dt, datetime) else None


def event_dict(defn, row, start, end, all_day, occurrence=None):
    title = ''
    if getattr(defn, 'title_field', ''):
        title = str(getattr(row, defn.title_field, '') or '')
    title = title or str(getattr(row, 'name', '') or getattr(defn, 'name', 'event'))
    row_id = str(getattr(row, 'id', '') or getattr(row, 'name', ''))
    ev_id = f'{defn.name}:{row_id}'
    if occurrence is not None:
        ev_id += f':{occurrence}'
    extended = {
        'definition': defn.name, 'class': defn.source_class,
        'rowId': row_id, 'rowName': str(getattr(row, 'name', '')),
        'category': getattr(defn, 'category', '') or str(getattr(row, 'category', '') or ''),
        'occurrence': occurrence,
        'link': str(getattr(row, getattr(defn, 'link_field', '') or 'name', '') or ''),
    }
    for f in _EXTRA_FIELDS:
        if hasattr(row, f) and f not in extended:
            extended[f] = getattr(row, f)
    return {'id': ev_id, 'title': title, 'start': _iso(start) if not all_day else start.strftime('%Y-%m-%d'),
            'end': (_iso(end) if not all_day else (end.strftime('%Y-%m-%d') if end else None)) if end else None,
            'allDay': bool(all_day), 'color': _color_for(defn, row) or None,
            'extendedProps': extended}


def _overlaps(start, end, ws, we):
    last = end or start
    if ws is not None and last < ws:
        return False
    if we is not None and start > we:
        return False
    return True


def resolve_definition_events(manager, defn, window_start=None, window_end=None,
                              person=None, household=None, filters=None,
                              slot_times=None):
    """Every event `defn` reads out of its class's rows inside the
    window. Returns {definition, class, events, count, unresolved:
    {count, reasons[:10]}, honesty}."""
    ws = _parse_date(window_start) if window_start else None
    we = _parse_date(window_end) if window_end else None
    if we is not None and len(str(window_end)) == 10:
        we = datetime.combine(we.date(), time(23, 59, 59))
    filters = dict(_loads(getattr(defn, 'filter_json', '{}'), {}))
    filters.update(filters or {})
    events, reasons, unresolved = [], [], 0
    for row in _rows(manager, defn.source_class):
        if not _matches(defn, row, person, household, filters):
            continue
        sched_raw = getattr(row, getattr(defn, 'schedule_field', '') or '__none__', None) \
            if getattr(defn, 'schedule_field', '') else None
        if sched_raw not in (None, '', '{}'):
            try:
                occurrences = expand_schedule(sched_raw, ws, we)
            except ValueError as e:
                unresolved += 1
                if len(reasons) < 10:
                    reasons.append(f"{getattr(row, 'name', '?')}: {e}")
                continue
            for occ in occurrences:
                events.append(event_dict(defn, row, occ['start'], occ['end'],
                                         occ['allDay'], occurrence=occ['index']))
            continue
        start, end, all_day, reason = resolve_row_start(defn, row, manager, slot_times)
        if reason:
            unresolved += 1
            if len(reasons) < 10:
                reasons.append(f"{getattr(row, 'name', '?')}: {reason}")
            continue
        if not _overlaps(start, end, ws, we):
            continue
        events.append(event_dict(defn, row, start, end, all_day))
    events.sort(key=lambda e: (e['start'], e['title']))
    return {'definition': getattr(defn, 'name', ''), 'class': defn.source_class,
            'events': events, 'count': len(events),
            'unresolved': {'count': unresolved, 'reasons': reasons},
            'honesty': ('rows that cannot be read as events are counted here '
                        'with the reason, never dropped silently; times are '
                        'local and naive (time zone = named gap)')}


def definitions_for_class(manager, class_name):
    return [d for d in _rows(manager, 'EventDefinition')
            if getattr(d, 'source_class', '') == class_name]


def definition_by_name(manager, name):
    return _by_name(manager, 'EventDefinition', name)


def calendar_by_name(manager, name):
    return _by_name(manager, 'CalendarDefinition', name)


def resolve_calendar_events(manager, calendar, window_start=None, window_end=None,
                            person=None, household=None, slot_times=None):
    """A CalendarDefinition's layers, merged. Layers whose
    EventDefinition is missing are NAMED, not skipped silently."""
    config = _loads(getattr(calendar, 'definition', '{}'), {}).get('calendarConfig', {})
    base_filters = config.get('filters') or {}
    layers, events = [], []
    for layer in config.get('layers') or []:
        dname = layer.get('eventDefinition', '')
        defn = definition_by_name(manager, dname)
        if defn is None:
            layers.append({'eventDefinition': dname, 'missing': True, 'count': 0,
                           'reason': f"EventDefinition '{dname}' is not on this node"})
            continue
        if layer.get('visible', True) is False:
            layers.append({'eventDefinition': dname, 'visible': False, 'count': 0})
            continue
        result = resolve_definition_events(manager, defn, window_start, window_end,
                                           person, household, base_filters, slot_times)
        color = layer.get('color')
        for ev in result['events']:
            if color and not ev.get('color'):
                ev['color'] = color
            ev['extendedProps']['layer'] = dname
            # a layer may draw as FullCalendar 'background' (schedules,
            # sleep) — the config says so, the event carries it.
            if layer.get('display'):
                ev['display'] = layer['display']
        layers.append({'eventDefinition': dname, 'class': result['class'],
                       'count': result['count'], 'unresolved': result['unresolved'],
                       'color': color,
                       # what a drag/resize may WRITE back (cal-3): the
                       # fields the reading came from; a relative or
                       # schedule-derived start is not writable by drag.
                       'mapping': {
                           'spanField': getattr(defn, 'span_field', ''),
                           'startField': getattr(defn, 'start_field', ''),
                           'endField': getattr(defn, 'end_field', ''),
                           'timeField': getattr(defn, 'time_field', ''),
                           'writable': bool(getattr(defn, 'span_field', '')
                                            or getattr(defn, 'start_field', '')),
                       }})
        events.extend(result['events'])
    events.sort(key=lambda e: (e['start'], e['title']))
    return {'calendar': getattr(calendar, 'name', ''), 'config': config,
            'layers': layers, 'events': events, 'count': len(events)}


#: Core seed: CalendarEvent rows read as events through their own
#: span/recurrence fields — the definition kind dogfoods itself.
SEED_CORE_EVENT_DEFINITIONS = [
    {'name': 'calendar-events', 'description':
        'CalendarEvent rows (a person\'s or a trigger\'s events) read '
        'through their datetime_duration span and schedule recurrence.',
     'source_class': 'CalendarEvent', 'is_default_event': True,
     'title_field': 'title', 'span_field': 'span',
     'all_day_field': 'all_day', 'schedule_field': 'recurrence',
     'color_field': 'color', 'category': '', 'link_field': 'name',
     'person_field': 'person_name', 'household_field': 'household_name',
     'is_prior': True, 'provenance_id': 'cal-1'},
]
