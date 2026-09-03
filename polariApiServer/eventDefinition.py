"""
@module polariApiServer.eventDefinition

cal-1 — THE EVENT DEFINITION CAPABILITY: "instances of <class> ARE
events". One row per (class, reading): which fields carry the title,
the span or the start, the end or the duration, an optional time
joined onto a date, a RELATIVE start (plan.start_date + day_index),
a `schedule`-typed field for recurrence, colour, filters and the
slot-time prior. Everything it points at is one of base Polari's
temporal FIELD TYPES (date / datetime / date_duration /
datetime_duration [{start,end}] / time / schedule) — a definition
never introduces a value shape of its own.

Configured per object from the class page (Events tab, cal-3),
composed into CalendarDefinition layers, resolved by
polariNoCode.calendar_events.resolve_definition_events.

@consumers polariApiServer.calendarAPI, polariNoCode.calendar_events,
  the no-code event nodes (cal-2), nutrition event seeds (cal-4)
@see AI-Notes/plans/CALENDAR_EVENTS_PLAN.md §2
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: duration_unit vocabulary → seconds.
DURATION_UNITS = {'seconds': 1, 'minutes': 60, 'hours': 3600,
                  'days': 86400, 'weeks': 604800}


class EventDefinition(treeObject):
    """How one class's instances read as calendar events."""

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # the class whose rows are the events.
        source_class: str = '',
        # the class's default reading (one per class is the knob).
        is_default_event: bool = False,
        # field holding the event title ('' → the row's name).
        title_field: str = '',
        # ONE of: a date_duration/datetime_duration field ({start,end}),
        span_field: str = '',
        # a date/datetime field,
        start_field: str = '',
        # or a relative start: JSON {baseClass, baseNameField,
        # baseDateField, offsetField, offsetUnit ('days'|'hours'|
        # 'minutes'), offsetBase (offset value that means "the base
        # date itself", default 1 for 1-based day indexes)}.
        relative_start_json: str = '{}',
        # a time field ('HH:MM') joined onto a date-only start.
        time_field: str = '',
        # a slot field whose value indexes slot_times_json when the
        # row carries no explicit time ('' = none).
        slot_field: str = '',
        # labeled PRIOR: {"breakfast": "08:00", ...}; a household
        # override row wins where the resolver is handed one.
        slot_times_json: str = '{}',
        # ONE of: an end date/datetime field,
        end_field: str = '',
        # or a numeric duration field + unit.
        duration_field: str = '',
        duration_unit: str = 'minutes',
        # all-day reading: a fixed flag or a boolean field.
        all_day: bool = False,
        all_day_field: str = '',
        # a `schedule`-typed field → recurring occurrences.
        schedule_field: str = '',
        # presentation.
        category: str = '',
        color: str = '',
        color_field: str = '',
        color_map_json: str = '{}',
        # {field: value} exact-match row filter.
        filter_json: str = '{}',
        # which fields scope events to a person / household when the
        # caller asks ('' = the class has no such scope).
        person_field: str = 'person_name',
        household_field: str = 'household_name',
        # which field a click-through opens ('' = the row's name).
        link_field: str = '',
        is_prior: bool = True,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.source_class = source_class
        self.is_default_event = is_default_event
        self.title_field = title_field
        self.span_field = span_field
        self.start_field = start_field
        self.relative_start_json = relative_start_json
        self.time_field = time_field
        self.slot_field = slot_field
        self.slot_times_json = slot_times_json
        self.end_field = end_field
        self.duration_field = duration_field
        self.duration_unit = duration_unit
        self.all_day = all_day
        self.all_day_field = all_day_field
        self.schedule_field = schedule_field
        self.category = category
        self.color = color
        self.color_field = color_field
        self.color_map_json = color_map_json
        self.filter_json = filter_json
        self.person_field = person_field
        self.household_field = household_field
        self.link_field = link_field
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
