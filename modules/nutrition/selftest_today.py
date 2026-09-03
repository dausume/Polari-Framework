"""
@module nutrition.selftest_today

N2 selftest — the Today page's arithmetic and the owed done → WorkLedger
auto-write, no server: a fake manager with four events for demo-alex on
one day (one already done) + a hazard-tagged step method → ordered
lines, next up, the safety note; the mark-done proposal (planned minutes
labelled, observation only with actual minutes, second call dedupes);
the FORM solution through the REAL engine (status → done, ledger +
observation rows, the object trigger it fires dedupes); the TRIGGER
path from a plain CRUD status edit; the trigger's filter matching done
and not planned; the page seeds (rows sum to 12, ids unique, embeds →
my tables, panels → my routes, forms → my solutions).

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_today
"""

import json
import re
import sys
from datetime import datetime
from types import SimpleNamespace

from household.household_basis import HOUSEHOLD_SEED_PAIRS
from mealoptions.workflow_basis import SEED_STEP_METHODS
from nutrition.today_analysis import (
    OBSERVED_LABEL, PLANNED_LABEL, mark_done_proposal, person_day,
)
from nutrition.today_api import run_mark_done
from nutrition.today_seed import (
    SEED_TODAY_ANALYSES, SEED_TODAY_PAGE_DISPLAYS, SEED_TODAY_SOLUTIONS,
    SEED_TODAY_TABLES, SEED_TODAY_TRIGGERS,
)
from polariNoCode.event_dispatcher import dispatch_object_change

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []
DAY = '2026-09-08'
PERSON = 'demo-alex'


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {f'{i}': SimpleNamespace(id=f'{i}', **r) for i, r in enumerate(seed_list)}


class _DB:
    def saveInstanceInDB(self, inst):
        return True


def _event(name, category, start, end, person='', household='demo-household',
           status='planned', linked=('', ''), payload=None):
    return {'name': name, 'title': name.replace('-', ' '), 'calendar_name': 'mealplan-week',
            'person_name': person, 'household_name': household,
            'span': json.dumps({'start': f'{DAY}T{start}', 'end': f'{DAY}T{end}'}),
            'all_day': False, 'recurrence': '{}', 'category': category, 'color': '',
            'linked_class': linked[0], 'linked_name': linked[1], 'status': status,
            'generated_by': 'coordinate-week-on-plan',
            'payload_json': json.dumps(payload or {}), 'is_prior': False,
            'provenance_id': '', 'notes': ''}


EVENTS = [
    _event('eat-dinner-demo', 'eating', '18:00', '18:30', payload={'eatingMin': 30, 'slot': 'dinner'}),
    _event('pack-lunch-demo', 'packing', '07:30', '07:35', person=PERSON, status='done',
           payload={'workload_type': 'packing', 'packMinutesPrior': 5}),
    _event('mealprep-dinner-demo', 'meal-prep', '17:45', '18:00', person=PERSON,
           payload={'finalPrepMin': 15, 'workload_type': 'meal-prep', 'slot': 'dinner',
                    'steps': [{'method': 'assemble-plate'}]}),
    _event('preprep-dice-demo', 'pre-prep', '16:00', '16:20', person=PERSON,
           payload={'workload_type': 'pre-prep',
                    'items': [{'food': 'onion', 'steps': [{'method': 'dice-knife', 'task': 'dice'}]}]}),
    # context + another person's + another day's: must not count
    _event('work-block-demo', 'availability', '09:00', '17:00', person=PERSON),
    _event('sam-cleanup-demo', 'cleanup', '19:00', '19:15', person='demo-sam',
           payload={'minutes': 15}),
    {**_event('tomorrow-pack-demo', 'packing', '07:30', '07:35', person=PERSON),
     'span': json.dumps({'start': '2026-09-09T07:30', 'end': '2026-09-09T07:35'})},
]


def _manager():
    tables = {cls: _rows(seeds) for cls, _c, seeds in HOUSEHOLD_SEED_PAIRS}
    tables.update({
        'StepMethod': _rows(SEED_STEP_METHODS),
        'CalendarEvent': _rows(EVENTS),
        'AnalysisDefinition': _rows(SEED_TODAY_ANALYSES),
        'SolutionDefinition': _rows(SEED_TODAY_SOLUTIONS),
        'EventTrigger': _rows(SEED_TODAY_TRIGGERS),
        'TriggerFiring': {}, 'WorkLedger': {}, 'PersonProfile': {},
        'MealEntry': {}, 'StorageActionDefinition': {},
    })
    return SimpleNamespace(objectTables=tables, db=_DB())


def _ev(mgr, name):
    return next(e for e in mgr.objectTables['CalendarEvent'].values() if e.name == name)


def _ledgers(mgr, name):
    return [w for w in mgr.objectTables['WorkLedger'].values() if w.name == f'ledger-{name}']


def _obs(mgr, name):
    return [o for o in mgr.objectTables['DurationObservation'].values() if o.name == f'obs-{name}']


def main():
    mgr = _manager()
    now = datetime(2026, 9, 8, 8, 0)
    print('N2 today page + done → ledger')

    day = person_day(mgr, PERSON, DAY, now=now)
    times = [l['time'] for l in day['lines']]
    names = [l['eventName'] for l in day['lines']]
    check('person_day: the four work lines + the availability context, in time order, '
          'demo-sam\'s and tomorrow\'s excluded',
          day['ok'] and times == sorted(times) and set(names) == {
              'pack-lunch-demo', 'work-block-demo', 'preprep-dice-demo',
              'mealprep-dinner-demo', 'eat-dinner-demo'}, str(list(zip(times, names))))
    check('counts: plannedCount 4 (context not counted), doneCount 1, openCount 3',
          day['plannedCount'] == 4 and day['doneCount'] == 1 and day['openCount'] == 3,
          f"{day['plannedCount']}/{day['doneCount']}/{day['openCount']}")
    check('nextUp at 08:00 = the 16:00 pre-prep (the 07:30 packing is done)',
          day['nextUp'] and day['nextUp']['eventName'] == 'preprep-dice-demo',
          str(day['nextUp']))
    later = person_day(mgr, PERSON, DAY, now=datetime(2026, 9, 8, 17, 50))
    check('nextUp at 17:50 = the meal-prep block still running (ends 18:00)',
          later['nextUp'] and later['nextUp']['eventName'] == 'mealprep-dinner-demo')
    dice = next(l for l in day['lines'] if l['eventName'] == 'preprep-dice-demo')
    check('safetyNote on the hazard step: dice-knife carries the knife tag (MethodSkillRequirement) '
          'with the SafetyRule verdict for demo-alex',
          'dice-knife' in dice['safetyNote'] and 'knife' in dice['safetyNote']
          and re.search(r'→ (alone|supervised|unassigned)', dice['safetyNote']),
          dice['safetyNote'])
    plate = next(l for l in day['lines'] if l['eventName'] == 'mealprep-dinner-demo')
    check('no safetyNote where the method carries no hazard (assemble-plate)',
          plate['safetyNote'] == '' and dice['minutes'] == 20.0 and plate['minutes'] == 15.0)
    check('every line is a flat record; nextUp is a flat record; no dict-of-dicts at the top',
          all(not isinstance(v, (dict, list)) for l in day['lines'] for v in l.values())
          and all(not isinstance(v, (dict, list)) for v in day['nextUp'].values())
          and all(not isinstance(v, dict) or v is None for k, v in day.items() if k != 'nextUp'))
    check('ledgerToday empty before any mark-done', day['ledger'] == [] and day['ledgerMinutes'] == 0)

    # --- the proposal ---
    p = mark_done_proposal(mgr, 'preprep-dice-demo', PERSON)
    check('mark-done proposal (no actual minutes): status → done, ONE ledger row with the planned '
          f'20 min labelled "{PLANNED_LABEL}", NO observation',
          p['ok'] and p['modifyFields'] == {'status': 'done'} and len(p['ledgerProposals']) == 1
          and p['ledgerProposals'][0]['minutes'] == 20.0 and p['minutesLabel'] == PLANNED_LABEL
          and PLANNED_LABEL in p['ledgerProposals'][0]['notes']
          and p['ledgerProposals'][0]['workload_type'] == 'pre-prep'
          and p['observationProposals'] == [], json.dumps(p, default=str)[:400])
    p2 = mark_done_proposal(mgr, 'preprep-dice-demo', PERSON, minutes_actual=25)
    check('with actual minutes: ledger 25 min labelled observed + ONE DurationObservation '
          '(kind prep-step, method dice-knife)',
          p2['ledgerProposals'][0]['minutes'] == 25.0 and p2['minutesLabel'] == OBSERVED_LABEL
          and len(p2['observationProposals']) == 1
          and p2['observationProposals'][0]['method_name'] == 'dice-knife'
          and p2['observationProposals'][0]['kind'] == 'prep-step'
          and p2['observationProposals'][0]['observed_min'] == 25.0, str(p2['observationProposals']))
    check('an unknown event is refused by name', not mark_done_proposal(mgr, 'nope', PERSON)['ok'])

    # --- the FORM solution through the REAL engine ---
    r = run_mark_done(mgr, 'preprep-dice-demo', PERSON, 25)
    ev = _ev(mgr, 'preprep-dice-demo')
    check('form solution runs through the engine: completed; the event\'s status is done',
          r['executed'] and r['status'] == 'completed' and ev.status == 'done',
          f"{r.get('status')} {r.get('error')}")
    led = _ledgers(mgr, 'preprep-dice-demo')
    check('ONE WorkLedger row ledger-<event> with the ACTUAL 25 min (the trigger the status '
          'change fired found it and deduped instead of overwriting with the planned prior)',
          len(led) == 1 and float(led[0].minutes) == 25.0 and OBSERVED_LABEL in led[0].notes
          and led[0].person_name == PERSON and led[0].date == DAY,
          str([(w.name, w.minutes, w.notes) for w in led]))
    check('ONE DurationObservation obs-<event> written (actual minutes were given)',
          len(_obs(mgr, 'preprep-dice-demo')) == 1)
    firings = [f for f in mgr.objectTables['TriggerFiring'].values()
               if f.trigger_name == 'today-done-to-ledger']
    check('the object trigger today-done-to-ledger fired on the status change (nested, fired)',
          any(f.status == 'fired' for f in firings), str([(f.status, f.error) for f in firings]))
    r2 = run_mark_done(mgr, 'preprep-dice-demo', PERSON, 40)
    led = _ledgers(mgr, 'preprep-dice-demo')
    check('a second mark-done DEDUPES: still one ledger row, minutes unchanged, proposal says so',
          r2['executed'] and len(led) == 1 and float(led[0].minutes) == 25.0
          and r2['ledgerExists'] and 'never overwritten' in r2['note'], r2['note'])

    # --- the message the form shows (fix 2026-09-03: the form was silent) ---
    check('the proposal\'s message reads "Marked preprep-dice-demo done; 25 min to the ledger; 25 min '
          'observed for dice-knife" — and rides the POST\'s reply',
          r['message'] == 'Marked preprep-dice-demo done; 25 min to the ledger; 25 min observed for dice-knife',
          r['message'])
    check('a second mark-done says the event was already done and the ledger minutes were kept',
          r2['message'].startswith('preprep-dice-demo was already done; the ledger already had 25 min')
          and 'kept' in r2['message'], r2['message'])
    check('a refused mark-done\'s message IS its error',
          mark_done_proposal(mgr, 'nope', PERSON)['message'] == mark_done_proposal(mgr, 'nope', PERSON)['error'])
    from polariNoCode import graph_builder as gb
    from polariNoCode.graph_compilers import final_context_of
    sol = json.loads(next(s for s in SEED_TODAY_SOLUTIONS if s['name'] == 'today-mark-done-form')['definition'])
    t3 = gb.execute(sol, manager=mgr, params={'event': 'preprep-dice-demo', 'person': PERSON, 'minutes_actual': None})
    ctx3 = final_context_of(t3) or {}
    check('through the engine the message is the context variable `message` at the terminal Refresh step '
          'AND in the refreshDisplay payload (steps[-1].contextAfter.variables.message)',
          t3.status == 'completed' and t3.steps[-1].state_name == 'Refresh'
          and ctx3.get('message') == r2['message']
          and any(ev.get('name') == 'refreshDisplay' and ev.get('payload', {}).get('message') == ctx3['message']
                  for ev in ctx3.get('_emitted_events', [])), f'{t3.status} {t3.error_summary} {ctx3.get("message")}')

    # --- the CRUD path: a plain status edit → the trigger → the ledger ---
    prep = _ev(mgr, 'mealprep-dinner-demo')
    prep.status = 'done'
    fired = dispatch_object_change(mgr, 'CalendarEvent', 'update', [prep.id])
    led = _ledgers(mgr, 'mealprep-dinner-demo')
    check('CRUD path: status edited to done → trigger fires → ledger row with the PLANNED '
          f'15 min labelled "{PLANNED_LABEL}", no observation',
          any(f.status == 'fired' for f in fired) and len(led) == 1
          and float(led[0].minutes) == 15.0 and PLANNED_LABEL in led[0].notes
          and not _obs(mgr, 'mealprep-dinner-demo'),
          str([(f.status, f.error) for f in fired]))
    fired = dispatch_object_change(mgr, 'CalendarEvent', 'update', [prep.id])
    check('re-dispatching the same done event never double-writes',
          len(_ledgers(mgr, 'mealprep-dinner-demo')) == 1)
    eat = _ev(mgr, 'eat-dinner-demo')
    fired = dispatch_object_change(mgr, 'CalendarEvent', 'update', [eat.id])
    check('the trigger\'s fieldFilter matches done and NOT a planned event (no firing at all)',
          fired == [] and not _ledgers(mgr, 'eat-dinner-demo'))
    src = json.loads(SEED_TODAY_TRIGGERS[0]['source_json'])
    check('trigger row: object source on CalendarEvent, filter status == done, empty inputs_json '
          '(payload instanceName survives — inputs win over payload)',
          src['class'] == 'CalendarEvent' and src['fieldFilter'] == {'status': 'done'}
          and json.loads(SEED_TODAY_TRIGGERS[0]['inputs_json']) == {})

    after = person_day(mgr, PERSON, DAY, now=now)
    check('person_day after: doneCount 3, ledger lines (pre-prep 25 observed, meal-prep 15 planned)',
          after['doneCount'] == 3 and after['ledgerMinutes'] == 40.0
          and {(l['workloadType'], l['label']) for l in after['ledger']}
          == {('pre-prep', OBSERVED_LABEL), ('meal-prep', PLANNED_LABEL)}, str(after['ledger']))

    # --- page seeds ---
    pages = SEED_TODAY_PAGE_DISPLAYS
    tables = {t['name']: t for t in SEED_TODAY_TABLES}
    solutions = {s['name'] for s in SEED_TODAY_SOLUTIONS}
    routes = [re.sub(r'\{[a-z_]+\}', '{X}', r) for r in
              ('/api/mealplanning/today/{person}', '/api/mealplanning/today/{person}/done')]
    rows = [row for p in pages for row in json.loads(p['definition'])['rows']]
    items = [it for row in rows for it in row['items']]
    ids = [it['id'] for it in items]
    check('page mealplan/today: every row\'s segments sum to 12, ids unique',
          pages[0]['pageRoute'] == 'mealplan/today'
          and all(sum(it['rowSegmentsUsed'] for it in row['items']) == 12 for row in rows)
          and len(ids) == len(set(ids)))
    from polariApiServer.mealplan_pages_seed import EMBED_TARGETS
    embeds = [it for it in items if it.get('type') == 'component'
              and it['componentProps']['componentName'] == 'embeddedTable']
    check('every embeddedTable names one of MY tables whose source_class is the class rendered',
          embeds and all(EMBED_TARGETS.get(it['id'], ('', ''))[1] in tables
                         and tables[EMBED_TARGETS[it['id']][1]]['source_class']
                         == it['componentProps']['inputs']['className'] for it in embeds))
    panels = [it for it in items if it.get('type') == 'component'
              and it['componentProps']['componentName'] == 'api-structured-panel']
    check('every api-structured-panel path is one my API registers',
          panels and all(re.sub(r'\{[a-z_]+\}|\{object\}', '{X}',
                                it['componentProps']['inputs']['path'].split('?')[0]) in routes
                         for it in panels), str([it['componentProps']['inputs']['path'] for it in panels]))
    forms = [it for it in items if it.get('type') == 'form']
    check('the Mark done form links MY solution and defaults person to {object}',
          forms and all(f['item']['linkedSolutionName'] in solutions for f in forms)
          and any(v['variableName'] == 'person' and v['defaultValue'] == '{object}'
                  for v in forms[0]['item']['extraVariables']))
    cal = [it for it in items if it.get('type') == 'component'
           and it['componentProps']['componentName'] == 'embeddedCalendar']
    check('the calendar embeds mealplan-week for {object} in the listDay view',
          cal and cal[0]['componentProps']['inputs']['calendarName'] == 'mealplan-week'
          and cal[0]['componentProps']['inputs']['person'] == '{object}'
          and cal[0]['componentProps']['inputs']['view'] == 'listDay')
    comps = {it['componentProps']['componentName'] for it in items if it.get('type') == 'component'}
    check('no JSON on screens: only embeddedTable / embeddedCalendar / api-structured-panel / form',
          comps <= {'embeddedTable', 'embeddedCalendar', 'api-structured-panel'})
    check('analyses name callables that resolve',
          all(a['callable_ref'].startswith('nutrition.today_analysis:') for a in SEED_TODAY_ANALYSES)
          and {a['name'] for a in SEED_TODAY_ANALYSES} == {'today-person-day', 'today-mark-done'})

    print(f'\n{len(failures)} failure(s)')
    for f in failures:
        print('  -', f)
    print('PASS: N2 today page + done → ledger hold together' if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
