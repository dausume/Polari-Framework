"""
@module polariApiServer.calendarEvent

cal-1 — the generic instance event: the "average user" object a
person puts on a calendar, and the row the no-code GenerateEvent
node writes. Its span IS base Polari's `datetime_duration` type
({"start": ISO, "end": ISO}; an instant carries start only) and its
recurrence IS the `schedule` type — no value shape of its own. A
linked_class/linked_name pair ties it to the row it is about
(a MealEntry, a PantryItem, a CookingWorkflow session…) and
generated_by names the EventTrigger that produced it, so a
generated event is never mistaken for a human's.

@consumers polariApiServer.calendarAPI (through the seeded
  'calendar-events' EventDefinition), polariNoCode event nodes,
  nutrition purchase/prep triggers (cal-4)
"""

from objectTreeDecorators import treeObject, treeObjectInit

EVENT_STATUSES = ('planned', 'done', 'cancelled')


class CalendarEvent(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        title: str = '',
        # CalendarDefinition.name this event belongs to ('' = any
        # calendar whose layers include the 'calendar-events'
        # definition; filters narrow by category/person/household).
        calendar_name: str = '',
        person_name: str = '',
        household_name: str = '',
        # datetime_duration: JSON {"start": ISO, "end": ISO}
        # (semantic type applied at registration — see polariServer).
        span: str = '{}',
        all_day: bool = False,
        # schedule: recurrence JSON (ScheduleDefinition shape).
        recurrence: str = '{}',
        # purchase | bulk-purchase | pre-prep | meal-prep | meal |
        # activity | reminder | ... (free vocabulary; seeds label
        # theirs).
        category: str = '',
        color: str = '',
        # the row this event is about.
        linked_class: str = '',
        linked_name: str = '',
        # planned | done | cancelled (cancel is soft — CancelEvent).
        status: str = 'planned',
        # EventTrigger.name that generated it ('' = a person did).
        generated_by: str = '',
        # free-form JSON the generator attaches (e.g. a shopping
        # list, the foods a bulk buy covers) — rendered structured,
        # never as a blob.
        payload_json: str = '{}',
        is_prior: bool = False,
        provenance_id: str = '',
        notes: str = '',
        manager=None,
    ):
        self.name = name
        self.title = title
        self.calendar_name = calendar_name
        self.person_name = person_name
        self.household_name = household_name
        self.span = span
        self.all_day = all_day
        self.recurrence = recurrence
        self.category = category
        self.color = color
        self.linked_class = linked_class
        self.linked_name = linked_name
        self.status = status
        self.generated_by = generated_by
        self.payload_json = payload_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
