"""
cal-2 event-trigger selftest (check() style, fake manager, REAL
engine): event logic as no-code — an object change fires a trigger
whose solution GenerateEvents a CalendarEvent; a schedule trigger
fires once per occurrence (idempotent); an emitted event chains into
another trigger and the depth guard stops a loop with a plain
reason; a disabled trigger is refused; cooldown skips; every firing
is a TriggerFiring row; ModifyEvent/CancelEvent/ScheduleOccurrences/
EventWindowQuery behave.

    python3 -m polariNoCode.selftest_event_triggers
"""

import json
import sys
from datetime import datetime
from types import SimpleNamespace

from polariNoCode import graph_builder as gb
from polariNoCode.calendar_events import SEED_CORE_EVENT_DEFINITIONS
from polariNoCode.event_dispatcher import (
    EventDispatcher, dispatch_object_change, get_dispatcher,
)

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra else ''))


class _DB:
    def __init__(self):
        self.saved = []

    def saveInstanceInDB(self, inst):
        self.saved.append(getattr(inst, 'name', '?'))
        return True


def _sol(name, definition):
    return SimpleNamespace(id=name, name=name, definition=json.dumps(definition))


def _trigger(name, kind, source, solution, **extra):
    fields = dict(name=name, description='', enabled=True, source_kind=kind,
                  source_json=json.dumps(source), solution_name=solution,
                  inputs_json='{}', cooldown_s=0.0, max_depth=8, run_as='definer',
                  last_fired='', fire_count=0)
    fields.update(extra)
    return SimpleNamespace(id=name, **fields)


def _manager():
    core = dict(SEED_CORE_EVENT_DEFINITIONS[0])
    mgr = SimpleNamespace(objectTables={
        'SolutionDefinition': {}, 'EventTrigger': {}, 'TriggerFiring': {},
        'CalendarEvent': {}, 'MealPlanDefinition': {},
        'EventDefinition': {'c': SimpleNamespace(id='c', **core)},
        'CalendarDefinition': {},
    }, db=_DB())
    return mgr


def main():
    mgr = _manager()
    T = mgr.objectTables

    # --- 1. object trigger → GenerateEvent ---------------------------
    # Solution: Start → GenerateEvent(title from the changed plan) → Emit
    gen = gb.solution(
        'plan-week-events',
        gb.entry('Start', nxt='Make'),
        gb.node('Make', 'GenerateEvent', {
            'targetClassName': 'CalendarEvent',
            'fields': {'title': gb.var_src('instanceName'),
                       'category': 'purchase',
                       'household_name': 'demo-household',
                       'span': {'start': '2026-09-12T10:00', 'end': '2026-09-12T11:00'}},
            'dedupeBy': 'title'}, outs=[['Emit']]),
        gb.node('Emit', 'EmitEvent', {'eventName': 'week-events-made',
                                      'payload': {'plan': gb.var_src('instanceName')}}),
    )
    T['SolutionDefinition']['s1'] = _sol('plan-week-events', gen)
    T['EventTrigger']['t1'] = _trigger(
        'on-plan-created', 'object',
        {'class': 'MealPlanDefinition', 'operations': ['create']}, 'plan-week-events')
    plan = SimpleNamespace(id='p1', name='demo-alex-week', start_date='2026-09-07')
    T['MealPlanDefinition']['p1'] = plan

    firings = dispatch_object_change(mgr, 'MealPlanDefinition', 'create', ['p1'])
    events = list(T['CalendarEvent'].values())
    check('object trigger fired once and its solution GENERATED a CalendarEvent '
          'titled by the plan, category purchase, span as datetime_duration JSON',
          len(firings) == 1 and firings[0].status == 'fired' and len(events) == 1
          and events[0].title == 'demo-alex-week' and events[0].category == 'purchase'
          and json.loads(events[0].span)['start'] == '2026-09-12T10:00',
          f'{[f.status for f in firings]} {[(e.title, e.category) for e in events]}')
    check('the generated event names its trigger (generated_by) and was persisted',
          events[0].generated_by == 'on-plan-created' and events[0].name in mgr.db.saved)
    check('every firing is a TriggerFiring row with the execution id + source ref',
          len(T['TriggerFiring']) == 1 and firings[0].execution_id
          and 'MealPlanDefinition:demo-alex-week:create' in firings[0].source_ref)
    check('trigger row bookkeeping: fire_count=1, last_fired set',
          T['EventTrigger']['t1'].fire_count == 1 and T['EventTrigger']['t1'].last_fired)

    dispatch_object_change(mgr, 'MealPlanDefinition', 'create', ['p1'])
    check('dedupeBy=title: a second firing reuses the existing event (no duplicate)',
          len(T['CalendarEvent']) == 1 and len(T['TriggerFiring']) == 2)
    dispatch_object_change(mgr, 'MealPlanDefinition', 'update', ['p1'])
    check('an operation the trigger does not list (update) does not fire',
          len(T['TriggerFiring']) == 2)

    # --- 2. event chaining + depth guard -----------------------------
    loop = gb.solution(
        'loop-forever',
        gb.entry('Start', nxt='Emit'),
        gb.node('Emit', 'EmitEvent', {'eventName': 'week-events-made', 'payload': {}}),
    )
    T['SolutionDefinition']['s2'] = _sol('loop-forever', loop)
    T['EventTrigger']['t2'] = _trigger(
        'on-week-events', 'event', {'eventName': 'week-events-made'},
        'loop-forever', max_depth=3)
    before = len(T['TriggerFiring'])
    dispatch_object_change(mgr, 'MealPlanDefinition', 'create', ['p1'])
    chain = [f for f in T['TriggerFiring'].values()
             if f.trigger_name == 'on-week-events']
    refused = [f for f in chain if f.status == 'refused']
    check('an emitted event chains into an event trigger; the self-emitting loop is '
          'stopped by max_depth with a plain reason',
          len(chain) >= 3 and len(refused) == 1 and 'max_depth' in refused[0].error,
          f'{[ (f.status, f.depth) for f in chain ]}')

    # --- 3. schedule trigger, idempotent ------------------------------
    T['EventTrigger'].pop('t2')
    remind = gb.solution(
        'bulk-buy-reminder',
        gb.entry('Start', nxt='Make'),
        gb.node('Make', 'GenerateEvent', {
            'fields': {'title': 'Bulk buy: rice + oats', 'category': 'bulk-purchase',
                       'span': {'start': gb.var_src('occurrenceKey')}},
            'dedupeBy': 'span'}),
    )
    T['SolutionDefinition']['s3'] = _sol('bulk-buy-reminder', remind)
    T['EventTrigger']['t3'] = _trigger(
        'quarterly-bulk-buy', 'schedule',
        {'schedule': {'eventType': 'date', 'frequency': 'monthly', 'interval': 3,
                      'byMonthDay': [1], 'rangeStart': '2026-09-01'}},
        'bulk-buy-reminder')
    d = get_dispatcher(mgr)
    n0 = len(T['CalendarEvent'])
    d.tick(now=datetime(2026, 9, 1, 0, 30), lookback_seconds=3600)
    d.tick(now=datetime(2026, 9, 1, 1, 30))
    d.tick(now=datetime(2026, 10, 1, 0, 30))
    d.tick(now=datetime(2026, 12, 1, 0, 30))
    bulk = [e for e in T['CalendarEvent'].values() if e.category == 'bulk-purchase']
    fired = [f for f in T['TriggerFiring'].values()
             if f.trigger_name == 'quarterly-bulk-buy' and f.status == 'fired']
    check('schedule trigger (every 3 months on the 1st) fires on Sep 1 and Dec 1 only, '
          'once each (idempotent by occurrence key), generating bulk-purchase events',
          len(bulk) == 2 and len(fired) == 2
          and sorted(f.occurrence_key for f in fired) == ['2026-09-01T00:00', '2026-12-01T00:00'],
          f'{[f.occurrence_key for f in fired]} bulk={len(bulk)}')

    # --- 4. disabled + cooldown ---------------------------------------
    T['EventTrigger']['t1'].enabled = False
    f = dispatch_object_change(mgr, 'MealPlanDefinition', 'create', ['p1'])[0]
    check('a disabled trigger is REFUSED with the reason on its firing row',
          f.status == 'refused' and 'disabled' in f.error)
    T['EventTrigger']['t1'].enabled = True
    T['EventTrigger']['t1'].cooldown_s = 3600
    T['EventTrigger']['t1'].last_fired = datetime.now().isoformat(timespec='seconds')
    f = dispatch_object_change(mgr, 'MealPlanDefinition', 'create', ['p1'])[0]
    check('cooldown skips with the reason', f.status == 'skipped' and 'cooldown' in f.error)
    T['EventTrigger']['t1'].cooldown_s = 0

    # --- 5. Modify / Cancel / ScheduleOccurrences / EventWindowQuery ---
    ev = [e for e in T['CalendarEvent'].values() if e.category == 'purchase'][0]
    tools = gb.solution(
        'tools',
        gb.entry('Start', nxt='Occ'),
        gb.node('Occ', 'ScheduleOccurrences', {
            'schedule': {'eventType': 'datetime', 'frequency': 'weekly', 'byDay': ['SA'],
                         'startTime': '10:00', 'rangeStart': '2026-09-01'},
            'from': '2026-09-01', 'to': '2026-09-30', 'resultVariable': 'saturdays'},
            outs=[['Win']]),
        gb.node('Win', 'EventWindowQuery', {
            'definition': 'calendar-events', 'from': '2026-09-01', 'to': '2026-12-31',
            'resultVariable': 'found'}, outs=[['Mod']]),
        gb.node('Mod', 'ModifyEvent', {
            'instanceRef': ev.name, 'fields': {'title': 'Weekly groceries (moved)'}},
            outs=[['Cancel']]),
        gb.node('Cancel', 'CancelEvent', {'instanceRef': ev.name, 'reason': 'plan changed'},
                outs=[['Done']]),
        gb.ret('Done', 'saturdaysCount'),
    )
    trace = gb.execute(tools, manager=mgr, params={})
    from polariNoCode.graph_compilers import final_context_of
    ctx = final_context_of(trace) or {}
    check('ScheduleOccurrences → 4 Saturdays into the context (+ count returned)',
          trace.status == 'completed' and ctx.get('saturdaysCount') == 4
          and trace.final_return_value == 4, f'{trace.status} {trace.error_summary} {ctx.get("saturdaysCount")}')
    check('EventWindowQuery over the core calendar-events definition finds the '
          'generated events (purchase + 2 bulk)', ctx.get('foundCount') == 3, str(ctx.get('foundCount')))
    check('ModifyEvent then CancelEvent: title changed, status cancelled, reason in notes',
          ev.title == 'Weekly groceries (moved)' and ev.status == 'cancelled'
          and 'plan changed' in ev.notes)

    # --- 6. honest refusals -------------------------------------------
    bad = gb.solution('bad', gb.entry('Start', nxt='Make'),
                      gb.node('Make', 'GenerateEvent', {'fields': {'category': 'x'}}))
    trace = gb.execute(bad, manager=mgr, params={})
    check('GenerateEvent without a title refuses plainly',
          trace.status != 'completed' and 'title' in str(trace.error_summary),
          str(trace.error_summary))
    T['EventTrigger']['t9'] = _trigger('ghost', 'object', {'class': 'MealPlanDefinition'},
                                       'no-such-solution')
    f = [x for x in dispatch_object_change(mgr, 'MealPlanDefinition', 'delete', ['p1'])
         if x.trigger_name == 'ghost'][0]
    check('a trigger naming a missing solution fails with the name on the row',
          f.status == 'failed' and 'no-such-solution' in f.error)

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())
