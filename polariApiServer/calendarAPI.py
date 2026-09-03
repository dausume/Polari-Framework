"""
@module polariApiServer.calendarAPI

cal-1 — the calendar/event READ surface (writes stay CRUDE or the
no-code nodes):

  GET  /api/calendar/{name}/events?from=&to=&person=&household=
         a CalendarDefinition's layers resolved into FullCalendar
         EventInput rows (+ per-layer unresolved counts, named)
  GET  /api/calendar/definitions/{class_name}
         the EventDefinitions declared for a class (+ the temporal
         fields the class carries, for the Events tab's pickers)
  GET  /api/calendar/definition/{name}/events?from=&to=…
         one EventDefinition resolved
  POST /api/calendar/preview   {definition: {...}, from, to, person}
         a definition DRAFT against live rows — what it would
         produce; nothing written
  POST /api/calendar/schedule/expand   {schedule: {...}, from, to}
         a `schedule` value → its occurrences (the editor's preview)
  GET  /api/calendar/calendars
         every CalendarDefinition with its layer summary

@consumers embeddedCalendar (cal-3), the Events/Calendars tabs,
  selftests, the nutrition front door (cal-5)
"""

import json
from datetime import datetime, timedelta

import falcon

from objectTreeDecorators import treeObject, treeObjectInit
from polariNoCode.calendar_events import (
    _loads, _rows, calendar_by_name, definition_by_name,
    definitions_for_class, make_definition, resolve_calendar_events,
    resolve_definition_events,
)
from polariNoCode.recurrence import describe_schedule, expand_schedule

TEMPORAL_TYPES = {'date', 'datetime', 'dateTime', 'date_duration',
                  'datetime_duration', 'time', 'time_duration', 'schedule'}


def _window(request):
    """from/to query params; default = this week (Mon..Sun)."""
    frm = request.params.get('from') or ''
    to = request.params.get('to') or ''
    if not frm or not to:
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        frm = frm or monday.isoformat()
        to = to or (monday + timedelta(days=6)).isoformat()
    return frm, to


def _serialize(defn):
    keys = ('name', 'description', 'source_class', 'is_default_event',
            'title_field', 'span_field', 'start_field', 'relative_start_json',
            'time_field', 'slot_field', 'slot_times_json', 'end_field',
            'duration_field', 'duration_unit', 'all_day', 'all_day_field',
            'schedule_field', 'category', 'color', 'color_field',
            'color_map_json', 'filter_json', 'person_field',
            'household_field', 'link_field', 'is_prior', 'provenance_id')
    out = {k: getattr(defn, k, None) for k in keys}
    out['id'] = getattr(defn, 'id', '')
    return out


class CalendarAPI(treeObject):
    """Calendar + event read routes (cal-1)."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/calendar'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/calendar/calendars', self, suffix='calendars')
            add('/api/calendar/definitions/{class_name}', self,
                suffix='definitions')
            add('/api/calendar/definition/{name}/events', self,
                suffix='definition_events')
            add('/api/calendar/preview', self, suffix='preview')
            add('/api/calendar/schedule/expand', self,
                suffix='schedule_expand')
            # cal-2: the no-code event logic, visible + runnable.
            add('/api/calendar/triggers', self, suffix='triggers')
            add('/api/calendar/triggers/{name}/fire', self,
                suffix='trigger_fire')
            add('/api/calendar/firings', self, suffix='firings')
            add('/api/calendar/{name}/events', self, suffix='events')

    # ---- calendars ------------------------------------------------
    def on_get_calendars(self, request, response):
        rows = []
        for cal in _rows(self.manager, 'CalendarDefinition'):
            config = _loads(getattr(cal, 'definition', '{}'), {}).get('calendarConfig', {})
            rows.append({'name': cal.name, 'description': getattr(cal, 'description', ''),
                         'source_class': getattr(cal, 'source_class', ''),
                         'is_default_calendar': getattr(cal, 'is_default_calendar', False),
                         'layers': [l.get('eventDefinition') for l in config.get('layers') or []],
                         'defaultView': config.get('defaultView', 'timeGridWeek')})
        response.media = {'ok': True, 'schema': 'calendars/1', 'count': len(rows),
                          'calendars': rows}

    def on_get_events(self, request, response, name):
        cal = calendar_by_name(self.manager, name)
        if cal is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': f"CalendarDefinition '{name}' is not on this node",
                              'known': sorted(c.name for c in _rows(self.manager, 'CalendarDefinition'))}
            return
        frm, to = _window(request)
        result = resolve_calendar_events(
            self.manager, cal, frm, to,
            person=request.params.get('person') or None,
            household=request.params.get('household') or None)
        result.update({'ok': True, 'schema': 'calendar-events/1', 'from': frm, 'to': to,
                       'honesty': ('every layer reports the rows it could not read '
                                   'as events, with reasons; times are local, naive')})
        response.media = result

    # ---- definitions ----------------------------------------------
    def on_get_definitions(self, request, response, class_name):
        typing = (getattr(self.manager, 'objectTypingDict', None) or {}).get(class_name)
        temporal = []
        if typing is not None:
            for var_name, var in (getattr(typing, 'polyTypedVarsDict', {}) or {}).items():
                t = str(getattr(var, 'pythonTypeDefault', '') or getattr(var, 'variablePythonType', ''))
                if t in TEMPORAL_TYPES:
                    temporal.append({'field': var_name, 'type': t})
        defs = [_serialize(d) for d in definitions_for_class(self.manager, class_name)]
        response.media = {'ok': True, 'schema': 'event-definitions/1', 'class': class_name,
                          'known_class': typing is not None,
                          'definitions': defs, 'temporalFields': temporal,
                          'honesty': ('temporalFields lists the fields typed as one of the '
                                      'base temporal types; a str field holding an ISO date '
                                      'also resolves — the picker just cannot promise it')}

    def on_get_definition_events(self, request, response, name):
        defn = definition_by_name(self.manager, name)
        if defn is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': f"EventDefinition '{name}' is not on this node"}
            return
        frm, to = _window(request)
        result = resolve_definition_events(
            self.manager, defn, frm, to,
            person=request.params.get('person') or None,
            household=request.params.get('household') or None)
        result.update({'ok': True, 'schema': 'definition-events/1', 'from': frm, 'to': to})
        response.media = result

    def on_post_preview(self, request, response):
        body = request.get_media() or {}
        draft = body.get('definition') or {}
        if not isinstance(draft, dict) or not draft.get('source_class'):
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'preview needs definition.source_class'}
            return
        draft.setdefault('name', 'preview')
        defn = make_definition(**{k: v for k, v in draft.items() if k != 'id'})
        result = resolve_definition_events(
            self.manager, defn, body.get('from'), body.get('to'),
            person=body.get('person') or None, household=body.get('household') or None)
        result.update({'ok': True, 'schema': 'definition-preview/1', 'written': False})
        response.media = result

    # ---- triggers (cal-2) -----------------------------------------
    def on_get_triggers(self, request, response):
        rows = []
        for t in _rows(self.manager, 'EventTrigger'):
            rows.append({'name': t.name, 'enabled': getattr(t, 'enabled', True),
                         'source_kind': getattr(t, 'source_kind', ''),
                         'source': _loads(getattr(t, 'source_json', '{}'), {}),
                         'solution_name': getattr(t, 'solution_name', ''),
                         'cooldown_s': getattr(t, 'cooldown_s', 0),
                         'fire_count': getattr(t, 'fire_count', 0),
                         'last_fired': getattr(t, 'last_fired', ''),
                         'description': getattr(t, 'description', '')})
        response.media = {'ok': True, 'schema': 'event-triggers/1', 'count': len(rows),
                          'triggers': rows,
                          'honesty': ('object triggers fire from the CRUDE lifecycle hook, '
                                      'event triggers from EmitEvent outputs, schedule/window '
                                      'triggers from the tick thread; every firing is a '
                                      'TriggerFiring row')}

    def on_post_trigger_fire(self, request, response, name):
        """Run a trigger NOW with the posted payload (a person's
        explicit act — recorded like any firing, source 'manual')."""
        from polariNoCode.event_dispatcher import get_dispatcher
        trigger = None
        for t in _rows(self.manager, 'EventTrigger'):
            if t.name == name:
                trigger = t
                break
        if trigger is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': f"EventTrigger '{name}' is not on this node"}
            return
        body = request.get_media() or {}
        payload = body.get('payload') if isinstance(body.get('payload'), dict) else body
        d = get_dispatcher(self.manager)
        firing = d.fire(trigger, payload or {}, 'manual',
                        f'manual:{getattr(request.context, "user_info", None) or "anonymous"}')
        response.media = {'ok': firing.status == 'fired', 'schema': 'trigger-firing/1',
                          'firing': {'name': firing.name, 'status': firing.status,
                                     'execution_id': firing.execution_id,
                                     'outcome': _loads(firing.outcome_json, {}),
                                     'error': firing.error}}

    def on_get_firings(self, request, response):
        limit = int(request.params.get('limit') or 50)
        trigger = request.params.get('trigger') or ''
        rows = [f for f in _rows(self.manager, 'TriggerFiring')
                if not trigger or getattr(f, 'trigger_name', '') == trigger]
        rows.sort(key=lambda f: getattr(f, 'fired_at', ''), reverse=True)
        response.media = {'ok': True, 'schema': 'trigger-firings/1', 'count': len(rows),
                          'firings': [{'name': f.name, 'trigger_name': f.trigger_name,
                                       'fired_at': f.fired_at, 'status': f.status,
                                       'source_kind': f.source_kind, 'source_ref': f.source_ref,
                                       'depth': f.depth, 'execution_id': f.execution_id,
                                       'outcome': _loads(f.outcome_json, {}), 'error': f.error}
                                      for f in rows[:limit]]}

    def on_post_schedule_expand(self, request, response):
        body = request.get_media() or {}
        try:
            occ = expand_schedule(body.get('schedule'), body.get('from'), body.get('to'))
        except ValueError as e:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': str(e)}
            return
        response.media = {'ok': True, 'schema': 'schedule-expand/1',
                          'reading': describe_schedule(body.get('schedule')),
                          'count': len(occ),
                          'occurrences': [{'start': o['start'].isoformat(timespec='minutes'),
                                           'end': o['end'].isoformat(timespec='minutes') if o['end'] else None,
                                           'allDay': o['allDay']} for o in occ]}
