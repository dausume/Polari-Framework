"""
@module polariApiServer.calendarDefinition

cal-1 — the CALENDAR display kind, beside TableDefinition and
GraphDefinition: a calendar is a composition of EventDefinition
LAYERS plus view options, configured per object (Calendars tab,
cal-3) and embedded into pages by reference (embeddedCalendar) the
way tables and graphs are.

definition JSON:
  {"calendarConfig": {
     "layers": [{"eventDefinition": "<EventDefinition.name>",
                 "visible": true, "color": "#1565c0"}, ...],
     "defaultView": "timeGridWeek" | "dayGridMonth" | "timeGridDay" | "listWeek",
     "editable": false,            # drag/resize → confirm → CRUDE
     "weekStart": 1,               # 0 = Sunday, 1 = Monday
     "slotMinTime": "06:00", "slotMaxTime": "22:00",
     "filters": {}                 # {field: value} applied to every layer
  }}

@consumers polariApiServer.calendarAPI, embeddedCalendar (cal-3),
  nutrition calendar seeds (cal-4)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class CalendarDefinition(treeObject):
    @treeObjectInit
    def __init__(self, name='', description='', source_class='',
                 definition='{}', is_default_calendar=False,
                 is_prior=True, provenance_id='', notes='',
                 manager=None):
        self.name = name
        self.description = description
        # the object this calendar is "about" ('' = a composition).
        self.source_class = source_class
        self.definition = definition
        self.is_default_calendar = is_default_calendar
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes
