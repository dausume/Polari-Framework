"""
cal-1 event-resolution selftest (check() style, no server): every
reading an EventDefinition can declare, over fake rows shaped like
the meal-planning classes — span, start, relative start + slot-time
prior, time join, duration, all-day, recurrence, filters, honest
unresolved counts — and a CalendarDefinition merging layers.

    python3 -m polariNoCode.selftest_calendar_events
"""

import json
import sys
from types import SimpleNamespace

from polariNoCode.calendar_events import (
    SEED_CORE_EVENT_DEFINITIONS, make_definition, resolve_calendar_events,
    resolve_definition_events,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra else ''))


def _row(i, **f):
    return SimpleNamespace(id=f'r{i}', **f)


def _manager():
    tables = {
        'MealPlanDefinition': {'p': _row(1, name='demo-alex-week', start_date='2026-09-07',
                                         days=3, person_name='demo-alex')},
        'MealEntry': {
            'e1': _row(2, name='d1-breakfast', plan_name='demo-alex-week', day_index=1,
                       slot='breakfast', template_name='omelet-breakfast', time_hhmm=''),
            'e2': _row(3, name='d1-dinner', plan_name='demo-alex-week', day_index=1,
                       slot='dinner', template_name='chicken-bowl-dinner', time_hhmm='19:15'),
            'e3': _row(4, name='d3-dinner', plan_name='demo-alex-week', day_index=3,
                       slot='dinner', template_name='chicken-bowl-dinner', time_hhmm=''),
            'e4': _row(5, name='orphan', plan_name='no-such-plan', day_index=1,
                       slot='lunch', template_name='x', time_hhmm=''),
        },
        'ActivityLog': {'a': _row(6, name='run', person_name='demo-alex', date='2026-09-08',
                                  start_hhmm='07:00', duration_min=45, activity_name='run'),
                        'b': _row(7, name='walk-other', person_name='demo-bo', date='2026-09-08',
                                  start_hhmm='18:00', duration_min=30, activity_name='walk')},
        'WeightObservation': {'w': _row(8, name='w1', person_name='demo-alex',
                                        date='2026-09-09', weight_kg=80.1)},
        'CalendarEvent': {
            'c1': _row(9, name='groceries', title='Weekly groceries', person_name='demo-alex',
                       household_name='demo-household', all_day=False, color='#1565c0',
                       category='purchase', status='planned', linked_class='', linked_name='',
                       generated_by='', payload_json='{}',
                       span='{}', recurrence=json.dumps({
                           'eventType': 'datetime', 'frequency': 'weekly', 'byDay': ['SA'],
                           'startTime': '10:00', 'rangeStart': '2026-09-05'})),
            'c2': _row(10, name='dentist', title='Dentist', person_name='demo-alex',
                       household_name='demo-household', all_day=False, color='',
                       category='appointment', status='planned', linked_class='',
                       linked_name='', generated_by='', payload_json='{}',
                       span=json.dumps({'start': '2026-09-10T14:00', 'end': '2026-09-10T15:00'}),
                       recurrence='{}'),
            'c3': _row(11, name='broken', title='No span', person_name='demo-alex',
                       household_name='demo-household', all_day=False, color='',
                       category='', status='planned', linked_class='', linked_name='',
                       generated_by='', payload_json='{}', span='{}', recurrence='{}'),
        },
        'EventDefinition': {},
        'CalendarDefinition': {},
    }
    return SimpleNamespace(objectTables=tables)


def main():
    mgr = _manager()
    meal = make_definition(
        name='meal-plan-entry', source_class='MealEntry', title_field='template_name',
        relative_start_json=json.dumps({'baseClass': 'MealPlanDefinition',
                                        'baseNameField': 'plan_name',
                                        'baseDateField': 'start_date',
                                        'offsetField': 'day_index',
                                        'offsetUnit': 'days', 'offsetBase': 1}),
        time_field='time_hhmm', slot_field='slot',
        slot_times_json=json.dumps({'breakfast': '08:00', 'dinner': '18:30'}),
        duration_field='', category='meal', color_field='slot',
        color_map_json=json.dumps({'breakfast': '#ffb300', 'dinner': '#6a1b9a'}),
        person_field='', household_field='')
    r = resolve_definition_events(mgr, meal, '2026-09-07', '2026-09-13')
    by = {e['extendedProps']['rowName']: e for e in r['events']}
    check('relative start: plan.start_date + (day_index-1) days, slot-time prior joins '
          '08:00 when the entry states no time',
          by.get('d1-breakfast', {}).get('start') == '2026-09-07T08:00', str(by.get('d1-breakfast')))
    check('an explicit time_hhmm wins over the slot prior',
          by.get('d1-dinner', {}).get('start') == '2026-09-07T19:15')
    check('day 3 lands two days later at the dinner prior',
          by.get('d3-dinner', {}).get('start') == '2026-09-09T18:30')
    check('the orphan entry (plan not found) is COUNTED with its reason, not dropped',
          r['unresolved']['count'] == 1 and 'no-such-plan' in r['unresolved']['reasons'][0],
          str(r['unresolved']))
    check('color map by slot applied', by['d1-dinner']['color'] == '#6a1b9a')
    r2 = resolve_definition_events(mgr, meal, '2026-09-09', '2026-09-13')
    check('window filtering keeps only day 3',
          [e['extendedProps']['rowName'] for e in r2['events']] == ['d3-dinner'])

    act = make_definition(name='activity', source_class='ActivityLog', title_field='activity_name',
                          start_field='date', time_field='start_hhmm',
                          duration_field='duration_min', duration_unit='minutes')
    r = resolve_definition_events(mgr, act, '2026-09-07', '2026-09-13', person='demo-alex')
    check('start_field + time_field + duration_field → a 45-minute span, person-scoped',
          len(r['events']) == 1 and r['events'][0]['start'] == '2026-09-08T07:00'
          and r['events'][0]['end'] == '2026-09-08T07:45' and not r['events'][0]['allDay'],
          str(r['events']))

    weight = make_definition(name='weight', source_class='WeightObservation',
                             start_field='date', all_day=True, title_field='')
    r = resolve_definition_events(mgr, weight, '2026-09-07', '2026-09-13')
    check('date-only start with all_day → an all-day event titled by the row name',
          r['events'] and r['events'][0]['allDay'] and r['events'][0]['start'] == '2026-09-09'
          and r['events'][0]['title'] == 'w1', str(r['events']))

    core = make_definition(**SEED_CORE_EVENT_DEFINITIONS[0])
    r = resolve_definition_events(mgr, core, '2026-09-07', '2026-09-20')
    titles = sorted(e['title'] for e in r['events'])
    check('CalendarEvent rows: recurrence expands (2 Saturdays), span reads, empty span is NAMED',
          titles == ['Dentist', 'Weekly groceries', 'Weekly groceries']
          and r['unresolved']['count'] == 1 and 'broken' in r['unresolved']['reasons'][0],
          f'{titles} {r["unresolved"]}')
    groc = [e for e in r['events'] if e['title'] == 'Weekly groceries']
    check('recurring occurrences carry distinct ids + occurrence index',
          len({e['id'] for e in groc}) == 2 and groc[0]['extendedProps']['occurrence'] is not None)

    # A calendar composed of layers.
    mgr.objectTables['EventDefinition'] = {'m': SimpleNamespace(id='m', **vars(meal)),
                                           'c': SimpleNamespace(id='c', **vars(core))}
    cal = SimpleNamespace(id='cal', name='mealplan-week', definition=json.dumps({
        'calendarConfig': {'layers': [{'eventDefinition': 'meal-plan-entry', 'color': '#333'},
                                      {'eventDefinition': 'calendar-events'},
                                      {'eventDefinition': 'nope'}],
                           'defaultView': 'timeGridWeek'}}))
    r = resolve_calendar_events(mgr, cal, '2026-09-07', '2026-09-13')
    check('calendar layers merge (3 meals + 1 grocery + 1 dentist = 5) and the missing '
          'layer is NAMED',
          r['count'] == 5 and any(l.get('missing') for l in r['layers'])
          and all(e['extendedProps'].get('layer') for e in r['events']), str(r['layers']))
    check('layer colour applies only where the event has none',
          all(e['color'] in ('#ffb300', '#6a1b9a') for e in r['events']
              if e['extendedProps']['layer'] == 'meal-plan-entry'))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
