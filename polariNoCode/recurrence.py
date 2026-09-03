"""
@module polariNoCode.recurrence

cal-1 — THE recurrence expander base Polari never had: a `schedule`
field value (the frontend's ScheduleDefinition JSON — RFC-5545-style:
eventType, frequency, interval, byDay, byMonthDay, byMonth, bySetPos,
startTime, endTime, rangeStart, rangeEnd, durationDays, count,
excludeDates) → the concrete occurrences inside a window.

Rides python-dateutil's rrule (in the image; dual Apache-2.0/BSD-3)
rather than a hand-rolled calendar — the RFC semantics (bySetPos,
last-Friday, leap handling) are exactly where hand-rolled expanders
go wrong. Naive local datetimes throughout (D9: time zone is a named
gap).

@consumers polariNoCode.calendar_events (schedule_field expansion),
  the ScheduleOccurrences node (cal-2), the tick dispatcher (cal-2)
"""

import json
from datetime import date, datetime, time, timedelta

from dateutil import rrule

_FREQ = {'daily': rrule.DAILY, 'weekly': rrule.WEEKLY,
         'monthly': rrule.MONTHLY, 'yearly': rrule.YEARLY}
_WEEKDAYS = {'MO': rrule.MO, 'TU': rrule.TU, 'WE': rrule.WE,
             'TH': rrule.TH, 'FR': rrule.FR, 'SA': rrule.SA,
             'SU': rrule.SU}
DATE_ONLY_TYPES = ('date', 'date_duration')


def parse_schedule(value):
    """A schedule value (dict or JSON string) → dict, or None when
    empty/unparseable (the caller names the refusal)."""
    if value is None or value == '' or value == '{}':
        return None
    if isinstance(value, dict):
        return value or None
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) and parsed else None


def _parse_hhmm(text, default=None):
    if not text:
        return default
    try:
        hh, mm = str(text).split(':')[:2]
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return default


def _parse_date(text):
    """ISO date or datetime string → datetime (naive)."""
    if isinstance(text, datetime):
        return text
    if isinstance(text, date):
        return datetime(text.year, text.month, text.day)
    text = str(text).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace('Z', ''))
    except ValueError:
        return None


def expand_schedule(schedule, window_start, window_end, max_occurrences=1000):
    """Occurrences of `schedule` overlapping [window_start, window_end].

    Returns a list of dicts {start: datetime, end: datetime|None,
    allDay: bool, index: int}. Raises ValueError with a plain reason
    for a schedule that cannot be read (missing rangeStart, unknown
    frequency) — callers turn that into a NAMED refusal.
    """
    sched = parse_schedule(schedule)
    if sched is None:
        return []
    event_type = sched.get('eventType', 'datetime')
    all_day = event_type in DATE_ONLY_TYPES
    frequency = str(sched.get('frequency', 'once')).lower()
    start_anchor = _parse_date(sched.get('rangeStart'))
    if start_anchor is None:
        raise ValueError('schedule has no rangeStart — when does it begin?')
    start_time = _parse_hhmm(sched.get('startTime'))
    end_time = _parse_hhmm(sched.get('endTime'))
    if not all_day and start_time is not None:
        start_anchor = datetime.combine(start_anchor.date(), start_time)
    elif all_day:
        start_anchor = datetime.combine(start_anchor.date(), time(0, 0))

    # Span of ONE occurrence.
    span = None
    if event_type == 'datetime_duration' and start_time and end_time:
        span = (datetime.combine(date.today(), end_time)
                - datetime.combine(date.today(), start_time))
        if span.total_seconds() < 0:
            span += timedelta(days=1)
    elif event_type == 'date_duration' and sched.get('durationDays'):
        span = timedelta(days=int(sched['durationDays']))
    elif sched.get('durationDays') and frequency == 'once':
        span = timedelta(days=int(sched['durationDays']))

    ws = _parse_date(window_start) if window_start else None
    we = _parse_date(window_end) if window_end else None
    # An occurrence that STARTS before the window but overlaps it
    # still counts — widen the search by the span.
    search_after = (ws - span) if (ws is not None and span) else ws

    if frequency == 'once':
        starts = [start_anchor]
    else:
        if frequency not in _FREQ:
            raise ValueError(f"unknown schedule frequency '{frequency}' "
                             f"— one of once/daily/weekly/monthly/yearly")
        kwargs = {'freq': _FREQ[frequency], 'dtstart': start_anchor,
                  'interval': max(1, int(sched.get('interval') or 1))}
        by_day = [_WEEKDAYS[d] for d in (sched.get('byDay') or [])
                  if d in _WEEKDAYS]
        if by_day:
            kwargs['byweekday'] = by_day
        if sched.get('byMonthDay'):
            kwargs['bymonthday'] = [int(x) for x in sched['byMonthDay']]
        if sched.get('byMonth'):
            kwargs['bymonth'] = [int(x) for x in sched['byMonth']]
        if sched.get('bySetPos'):
            kwargs['bysetpos'] = [int(x) for x in sched['bySetPos']]
        if sched.get('count'):
            kwargs['count'] = int(sched['count'])
        range_end = _parse_date(sched.get('rangeEnd'))
        if range_end is not None:
            kwargs['until'] = datetime.combine(range_end.date(), time(23, 59, 59))
        rule = rrule.rrule(**kwargs)
        if search_after is not None and we is not None:
            starts = list(rule.between(search_after, we, inc=True))
        elif we is not None:
            starts = [s for s in rule if s <= we]
        else:
            starts = list(rule)
        starts = starts[:max_occurrences]

    excluded = {str(x)[:10] for x in (sched.get('excludeDates') or [])}
    out = []
    for i, s in enumerate(starts):
        if s.strftime('%Y-%m-%d') in excluded:
            continue
        e = (s + span) if span else None
        if ws is not None and ((e or s) < ws):
            continue
        if we is not None and s > we:
            continue
        out.append({'start': s, 'end': e, 'allDay': all_day, 'index': i})
    return out


def describe_schedule(schedule):
    """A plain reading of a schedule for labels ('every 2 weeks on
    MO', 'monthly on day 1', 'yearly in Sep'); never raises."""
    sched = parse_schedule(schedule)
    if sched is None:
        return ''
    freq = str(sched.get('frequency', 'once')).lower()
    interval = int(sched.get('interval') or 1)
    parts = []
    if freq == 'once':
        parts.append(f"once on {sched.get('rangeStart', '?')}")
    else:
        unit = {'daily': 'day', 'weekly': 'week', 'monthly': 'month',
                'yearly': 'year'}.get(freq, freq)
        parts.append(f'every {interval} {unit}{"s" if interval > 1 else ""}')
        if sched.get('byDay'):
            parts.append('on ' + ','.join(sched['byDay']))
        if sched.get('byMonthDay'):
            parts.append('on day ' + ','.join(str(x) for x in sched['byMonthDay']))
        if sched.get('bySetPos'):
            parts.append('setpos ' + ','.join(str(x) for x in sched['bySetPos']))
    if sched.get('startTime'):
        parts.append('at ' + str(sched['startTime']))
    return ' '.join(parts)
