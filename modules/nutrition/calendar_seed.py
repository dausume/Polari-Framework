"""
@module nutrition.calendar_seed

cal-4 — the meal-planning app's EVENT LAYER as data:

  EventDefinitions   how the meal-planning classes read as events
                     (MealEntry via plan.start_date + day_index + the
                     slot-time prior; IntakeRecord; ActivityLog with
                     its duration; WeightObservation all-day)
  CalendarDefinition 'mealplan-week' — those layers + the household's
                     CalendarEvents (purchase / bulk-purchase /
                     pre-prep / meal-prep are generated events)
  AnalysisDefinitions the purchase / bulk / coordination analyses
  SolutionDefinitions the NO-CODE event logic (graph_builder shapes;
                     the same JSON the editor shows): AnalysisCall →
                     GenerateEvent(eventsFrom proposals) → EmitEvent
  EventTriggers      his sample: weekly purchase (Saturday 10:00),
                     bulk purchases monthly / 3-month / 6-month /
                     yearly (the 1st), coordination when a plan or an
                     entry changes and every Sunday for the week ahead

Seeded through composition.seed_upsert from seed_mealplan_pages
(converges on edit). After the upsert the coordination trigger is
fired ONCE for the demo plan when no generated events exist yet, so
a fresh node shows the week — recorded as a manual firing like any
other, dedupeBy keeps it idempotent.

@consumers polariApiServer.mealplan_pages_seed.seed_mealplan_pages
"""

import json

from polariNoCode import graph_builder as gb
from nutrition.purchase_analysis import SLOT_TIMES

HOUSEHOLD = 'demo-household'
PERSON = 'demo-alex'
PLAN = 'demo-alex-week'


def _defn(name, source_class, description, **fields):
    row = {'name': name, 'description': description, 'source_class': source_class,
           'is_prior': True, 'provenance_id': 'cal-4'}
    row.update(fields)
    return row


SEED_MEALPLAN_EVENT_DEFINITIONS = [
    _defn('meal-plan-entry', 'MealEntry',
          'A planned meal: plan.start_date + (day_index − 1) days, at the '
          'entry\'s own time or the slot-time PRIOR; coloured by slot.',
          is_default_event=True, title_field='template_name',
          relative_start_json=json.dumps({
              'baseClass': 'MealPlanDefinition', 'baseNameField': 'plan_name',
              'baseDateField': 'start_date', 'offsetField': 'day_index',
              'offsetUnit': 'days', 'offsetBase': 1}),
          time_field='time_hhmm', slot_field='slot',
          slot_times_json=json.dumps(SLOT_TIMES),
          category='meal', color_field='slot',
          color_map_json=json.dumps({'breakfast': '#ffb300', 'brunch': '#ffca28',
                                     'lunch': '#26a69a', 'linner': '#26c6da',
                                     'dinner': '#5e35b1', 'snack': '#8d6e63'}),
          person_field='', household_field='', link_field='name'),
    _defn('intake-record', 'IntakeRecord',
          'What was actually eaten: date + time (or the slot prior).',
          is_default_event=True, title_field='template_name', start_field='date',
          time_field='time_hhmm', slot_field='slot',
          slot_times_json=json.dumps(SLOT_TIMES), category='intake',
          color='#2e7d32', person_field='person_name', household_field=''),
    _defn('activity-log', 'ActivityLog',
          'Logged activity as a span: date + start time + duration_min.',
          is_default_event=True, title_field='activity_name', start_field='date',
          time_field='start_hhmm', duration_field='duration_min',
          duration_unit='minutes', category='activity', color='#00897b',
          person_field='person_name', household_field=''),
    _defn('weight-observation', 'WeightObservation',
          'A measured weight, all-day on its date.',
          is_default_event=True, title_field='', start_field='date', all_day=True,
          category='weight', color='#455a64', person_field='person_name',
          household_field=''),
    # mlg-1: where and when a person is — work, commute, sleep — drawn
    # as a BACKGROUND layer (the calendar config says display=background).
    _defn('person-schedule', 'PersonSchedule',
          'A person\'s recurring commitments (work, commute, sleep) read '
          'through their `schedule` recurrence; the calendar draws them as '
          'background so meals and prep are placed around them.',
          is_default_event=True, title_field='display_name',
          schedule_field='recurrence', category='availability',
          color_field='kind',
          color_map_json=json.dumps({'work': '#cfd8dc', 'commute': '#eceff1',
                                     'school': '#cfd8dc', 'sleep': '#d1c4e9',
                                     'care': '#ffe0b2', 'other': '#eeeeee'}),
          person_field='person_name', household_field='', link_field='name'),
]

SEED_MEALPLAN_CALENDARS = [
    {'name': 'mealplan-week', 'source_class': 'MealPlanDefinition',
     'description': 'The household week: planned meals, generated purchase / '
                    'bulk-purchase / pre-prep / meal-prep events, what was '
                    'eaten, activity and weights — one calendar, toggled by layer.',
     'is_default_calendar': True, 'is_prior': True, 'provenance_id': 'cal-4',
     'definition': json.dumps({'calendarConfig': {
         'layers': [
             {'eventDefinition': 'person-schedule', 'visible': True,
              'display': 'background'},
             {'eventDefinition': 'meal-plan-entry', 'visible': True},
             {'eventDefinition': 'calendar-events', 'visible': True},
             {'eventDefinition': 'intake-record', 'visible': True, 'color': '#2e7d32'},
             {'eventDefinition': 'activity-log', 'visible': True, 'color': '#00897b'},
             {'eventDefinition': 'weight-observation', 'visible': True, 'color': '#455a64'},
         ],
         'defaultView': 'timeGridWeek', 'editable': True, 'weekStart': 1,
         'slotMinTime': '06:00', 'slotMaxTime': '22:00', 'filters': {}}})},
]

SEED_MEALPLAN_ANALYSES = [
    {'name': 'mealplan-weekly-purchase', 'domain': 'nutrition',
     'callable_ref': 'nutrition.purchase_analysis:weekly_purchase_proposal',
     'description': 'The week\'s priced shopping gap minus bulk-covered staples → '
                    'one purchase event proposal.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name', 'household': '',
                                'purchase_date': 'ISO date (default plan start)'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'cal-4'},
    {'name': 'mealplan-bulk-purchase', 'domain': 'nutrition',
     'callable_ref': 'nutrition.purchase_analysis:bulk_purchase_proposal',
     'description': 'Staples on one cadence: demand over the period vs stock, bulk '
                    'vs retail $/kg → one bulk-purchase event proposal.',
     'params_json': json.dumps({'household': '', 'cadence_months': '1|3|6|12',
                                'purchase_date': 'ISO date'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'cal-4'},
    {'name': 'mealplan-coordinate-week', 'domain': 'nutrition',
     'callable_ref': 'nutrition.purchase_analysis:coordinate_week',
     'description': 'purchase → pre-prep → meals (+ eating) → meal-prep (per person, '
                    'safety-bounded) + packing + dishes + the work allocation for a '
                    'plan week; every rule named.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name', 'household': '',
                                'week_start': 'ISO date (default plan start)',
                                'plan_from_entry': 'MealEntry.plan_name'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'cal-4'},
    # mpc: plan the week (coverage, portions, apply a meal).
    {'name': 'mealplan-week-coverage', 'domain': 'nutrition',
     'callable_ref': 'nutrition.planning_analysis:week_coverage',
     'description': 'Person × day × slot grid for a plan — planned / missing, named.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'mpc'},
    {'name': 'mealplan-apply-meal', 'domain': 'nutrition',
     'callable_ref': 'nutrition.planning_analysis:apply_meal_proposal',
     'description': 'A meal → MealEntry proposals for slots × days with per-person portions.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name', 'template': 'MealTemplate.name',
                                'variation': '', 'slots': 'csv|all', 'days': 'csv|all',
                                'person': '', 'scale': '0 = fit portions'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'mpc'},
    {'name': 'mealplan-portion-fit', 'domain': 'nutrition',
     'callable_ref': 'nutrition.planning_analysis:portion_fit',
     'description': 'Per-person portion scales for one meal in one slot; the compromise stated. '
                    'objective=calories (default) or nutrients (weighted fit; sodium = ceiling).',
     'params_json': json.dumps({'template': 'MealTemplate.name', 'variation': '', 'slot': '',
                                'persons': 'list', 'household': '',
                                'objective': 'calories|nutrients',
                                'weights': 'calories=1.0,protein=0.7,fiber=0.3,sodium=0.5 (prior)'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'mpc'},
    # mpt: per-person tracking over time + the "log it" forms.
    {'name': 'mealplan-periods', 'domain': 'nutrition',
     'callable_ref': 'nutrition.tracking_periods:period_summary',
     'description': 'Week / month means per logged day vs the person\'s own lines; consistency.',
     'params_json': json.dumps({'person': 'PersonProfile.name', 'kind': 'week|month'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'mpt'},
    {'name': 'mealplan-intake-proposal', 'domain': 'nutrition',
     'callable_ref': 'nutrition.tracking_periods:intake_proposal',
     'description': 'The "log what I ate" form → one validated IntakeRecord row.',
     'params_json': json.dumps({'person': '', 'date_iso': '', 'slot': '', 'template': '',
                                'variation': '', 'scale': 1.0, 'time_hhmm': ''}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'mpt'},
    {'name': 'mealplan-weight-proposal', 'domain': 'nutrition',
     'callable_ref': 'nutrition.tracking_periods:weight_proposal',
     'description': 'The "log my weight" form → one validated WeightObservation row.',
     'params_json': json.dumps({'person': '', 'date_iso': '', 'weight_kg': 0.0, 'context': ''}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'mpt'},
    # mlg-1..4: the logistics analyses, callable from no-code. hh-1:
    # the household-generic ones resolve to household.household_analysis
    # (the upsert rewrites the live rows' callable_ref; names unchanged).
    *[{'name': f'mealplan-{n}', 'domain': 'nutrition',
       'callable_ref': (f'household.household_analysis:{fn}'
                        if fn in ('availability_windows', 'assign_work',
                                  'fairness_readout', 'refine_speed_factors')
                        else f'nutrition.logistics_analysis:{fn}'), 'description': d,
       'params_json': json.dumps(p), 'enabled': True, 'is_prior': True,
       'provenance_id': 'mlg-1'} for n, fn, d, p in (
        ('availability', 'availability_windows', 'A person\'s busy blocks + free windows from their PersonSchedule rows.',
         {'person': 'PersonProfile.name', 'from_date': 'ISO', 'to_date': 'ISO'}),
        ('timing-check', 'meal_timing_check', 'Dinner→sleep spacing + meals inside away blocks; flags, never blocks.',
         {'plan': 'MealPlanDefinition.name', 'week_start': 'ISO'}),
        ('prep-profile', 'prep_time_profile', 'Final-prep + eating minutes for a meal, per person, safety-bounded.',
         {'entry': 'MealEntry.name', 'person': 'PersonProfile.name'}),
        ('portability', 'portability_plan', 'Pack + freeze-packs events for packed meals; missing tools named.',
         {'plan': 'MealPlanDefinition.name', 'week_start': 'ISO'}),
        ('dish-plan', 'dish_plan', 'Cleanup events: unattended windows first, else after eating.',
         {'plan': 'MealPlanDefinition.name', 'week_start': 'ISO'}),
        ('assign-work', 'assign_work', 'The allocation: minimise total person-minutes within the shares.',
         {'events': 'list of event dicts', 'household': 'HouseholdProfile.name'}),
        ('fairness', 'fairness_readout', 'WorkLedger actuals vs the policies\' targets; a suggestion.',
         {'household': 'HouseholdProfile.name'}),
        ('speed-refinement', 'refine_speed_factors', 'DurationObservation → proposed speed factors (never below the floor).',
         {'person': 'PersonProfile.name'}),
    )],
]


def _solution(name, definition, description):
    return {'name': name, 'function_name': name.replace('-', '_'),
            'target_runtime': 'python_backend',
            'definition': json.dumps(definition),
            'contract_json': json.dumps({'description': description,
                                         'executionRights': 'definer'})}


def _proposal_solution(name, analysis, params, event_name, description):
    """Start → AnalysisCall(pick proposals) → GenerateEvent(eventsFrom)
    → EmitEvent — THE shape every event-generating solution here uses."""
    graph = gb.solution(
        name,
        gb.entry('Start', nxt='Analyse'),
        gb.node('Analyse', 'AnalysisCall',
                {'analysis': analysis, 'params': params, 'pick': 'proposals',
                 'resultVariable': 'proposals'}, outs=[['Generate']]),
        gb.node('Generate', 'GenerateEvent',
                {'targetClassName': 'CalendarEvent',
                 'eventsFrom': gb.var_src('proposals'), 'dedupeBy': 'name',
                 'fields': {}}, outs=[['Emit']]),
        gb.node('Emit', 'EmitEvent',
                {'eventName': event_name,
                 'payload': {'generated': gb.var_src('generatedEventBatch')}}),
    )
    return _solution(name, graph, description)


#: Every FORM solution ends with what a person can read: the proposal
#: function's plain-words `message` (picked BEFORE the writes, so
#: "already planned / already logged — kept" is judged against the
#: rows as they stood when the form was submitted) lands in the
#: context as the variable `message` and rides the refreshDisplay
#: payload. The /executeSolutionStepped response therefore carries it
#: at trace.steps[-1].contextAfter.variables.message.value (what the
#: display-solution-runner reads first) and at trace.finalReturnValue.
#: payload.message (EmitFrontendEvent IS the engine's terminal state —
#: a ReturnValue wired after it would never run, so none is). Dotted
#: paths do not walk into dicts, so this is its own AnalysisCall
#: rather than a second pick off the first.
def message_call(name, analysis, params, nxt):
    return gb.node(name, 'AnalysisCall',
                   {'analysis': analysis, 'params': params, 'pick': 'message',
                    'resultVariable': 'message'}, outs=[[nxt]])


def refresh_with_message(payload):
    """The terminal EmitFrontendEvent(refreshDisplay) every form
    solution shares; `message` is always in the payload."""
    return gb.node('Refresh', 'EmitFrontendEvent',
                   {'eventName': 'refreshDisplay',
                    'payload': dict(payload, message=gb.var_src('message'))})


_APPLY_PARAMS = {'plan': gb.var_src('plan'), 'template': gb.var_src('template'),
                 'variation': gb.var_src('variation'), 'slots': gb.var_src('slots'),
                 'days': gb.var_src('days'), 'person': gb.var_src('person'),
                 'scale': gb.var_src('scale')}

#: mpc: the "Add to the week" FORM runs this — FormSubscription entry
#: (the form's fields are the context) → the apply-meal proposal →
#: MealEntry rows (GenerateEvent on a class an EventDefinition reads;
#: dedupe by name never overwrites a planned entry) → the page
#: refreshes → the message ("Added …; … already planned and kept");
#: the MealEntry create trigger re-coordinates the week.
APPLY_MEAL_SOLUTION = _solution(
    'mealplan-apply-meal-to-week',
    gb.solution(
        'mealplan-apply-meal-to-week',
        gb.node('Start', 'FormSubscription', {}, outs=[['Propose']]),
        gb.node('Propose', 'AnalysisCall',
                {'analysis': 'mealplan-apply-meal', 'params': _APPLY_PARAMS,
                 'pick': 'proposals', 'resultVariable': 'proposals'}, outs=[['Message']]),
        message_call('Message', 'mealplan-apply-meal', _APPLY_PARAMS, 'Write'),
        gb.node('Write', 'GenerateEvent',
                {'targetClassName': 'MealEntry', 'eventsFrom': gb.var_src('proposals'),
                 'dedupeBy': 'name', 'fields': {}}, outs=[['Refresh']]),
        refresh_with_message({'written': gb.var_src('generatedEventBatch')}),
    ),
    'Apply a meal to any slots × days of the week as MealEntry rows with per-person portions; '
    'says what was added and which slots were already planned and kept.')

def _log_form_solution(name, analysis, params, target_class, description):
    """FormSubscription → validated proposal → ONE row → refresh →
    the message ("Logged … " / "Already logged … — kept")."""
    return _solution(name, gb.solution(
        name,
        gb.node('Start', 'FormSubscription', {}, outs=[['Validate']]),
        gb.node('Validate', 'AnalysisCall',
                {'analysis': analysis, 'params': params, 'pick': 'proposals',
                 'resultVariable': 'proposals'}, outs=[['Message']]),
        message_call('Message', analysis, params, 'Write'),
        gb.node('Write', 'GenerateEvent',
                {'targetClassName': target_class, 'eventsFrom': gb.var_src('proposals'),
                 'dedupeBy': 'name', 'fields': {}}, outs=[['Refresh']]),
        refresh_with_message({'written': gb.var_src('generatedEventBatch')}),
    ), description)


LOG_INTAKE_SOLUTION = _log_form_solution(
    'mealplan-log-intake', 'mealplan-intake-proposal',
    {'person': gb.var_src('person'), 'date_iso': gb.var_src('date'), 'slot': gb.var_src('slot'),
     'template': gb.var_src('template'), 'variation': gb.var_src('variation'),
     'scale': gb.var_src('scale'), 'time_hhmm': gb.var_src('time')},
    'IntakeRecord', 'Log what a person ate (date × slot × meal) as an IntakeRecord.')
LOG_WEIGHT_SOLUTION = _log_form_solution(
    'mealplan-log-weight', 'mealplan-weight-proposal',
    {'person': gb.var_src('person'), 'date_iso': gb.var_src('date'),
     'weight_kg': gb.var_src('weight_kg'), 'context': gb.var_src('context')},
    'WeightObservation', 'Log a measured weight as a WeightObservation.')

SEED_MEALPLAN_SOLUTIONS = [
    APPLY_MEAL_SOLUTION, LOG_INTAKE_SOLUTION, LOG_WEIGHT_SOLUTION,
    _proposal_solution(
        'mealplan-weekly-purchase-events', 'mealplan-weekly-purchase',
        {'plan': gb.var_src('planName'), 'household': gb.var_src('household'),
         'purchase_date': gb.var_src('occurrenceKey')},
        'purchase-events-made',
        'Generate the week\'s purchase event from the plan\'s shopping gap.'),
    _proposal_solution(
        'mealplan-bulk-purchase-events', 'mealplan-bulk-purchase',
        {'household': gb.var_src('household'), 'cadence_months': gb.var_src('cadenceMonths'),
         'purchase_date': gb.var_src('occurrenceKey')},
        'bulk-purchase-events-made',
        'Generate one bulk-purchase event for the staples on this cadence.'),
    _proposal_solution(
        'mealplan-coordinate-week-events', 'mealplan-coordinate-week',
        {'plan': gb.var_src('instanceName'), 'plan_from_entry': gb.var_src('instance.plan_name'),
         'household': gb.var_src('household'), 'week_start': gb.var_src('weekStart')},
        'week-coordinated',
        'Purchase → pre-prep → meals → meal-prep events for the plan week.'),
]


def _trigger(name, kind, source, solution, inputs, description, **extra):
    row = {'name': name, 'description': description, 'enabled': True,
           'source_kind': kind, 'source_json': json.dumps(source),
           'solution_name': solution, 'inputs_json': json.dumps(inputs),
           'cooldown_s': 0.0, 'max_depth': 8, 'run_as': 'definer',
           'is_prior': True, 'provenance_id': 'cal-4'}
    row.update(extra)
    return row


def _bulk_trigger(months, label):
    return _trigger(
        f'bulk-purchase-{label}', 'schedule',
        {'schedule': {'eventType': 'date', 'frequency': 'monthly', 'interval': months,
                      'byMonthDay': [1], 'rangeStart': '2026-09-01'}},
        'mealplan-bulk-purchase-events',
        {'household': HOUSEHOLD, 'cadenceMonths': months},
        f'Bulk purchase on the {label} cadence (the 1st, every {months} month'
        f'{"s" if months > 1 else ""}) — staples whose shelf life allows it.')


SEED_MEALPLAN_TRIGGERS = [
    _trigger('weekly-purchase', 'schedule',
             {'schedule': {'eventType': 'datetime', 'frequency': 'weekly', 'byDay': ['SA'],
                           'startTime': '10:00', 'rangeStart': '2026-09-05'}},
             'mealplan-weekly-purchase-events',
             {'planName': PLAN, 'household': HOUSEHOLD},
             'Weekly recurring purchase event for food (Saturday 10:00 — a prior).'),
    _bulk_trigger(1, 'monthly'),
    _bulk_trigger(3, '3-month'),
    _bulk_trigger(6, '6-month'),
    _bulk_trigger(12, 'yearly'),
    _trigger('coordinate-week-on-plan', 'object',
             {'class': 'MealPlanDefinition', 'operations': ['create', 'update']},
             'mealplan-coordinate-week-events', {'household': HOUSEHOLD},
             'When a plan is created or changed: regenerate its purchase / '
             'pre-prep / meal-prep events.', cooldown_s=5.0),
    _trigger('coordinate-week-on-entry', 'object',
             {'class': 'MealEntry', 'operations': ['create', 'update']},
             'mealplan-coordinate-week-events', {'household': HOUSEHOLD},
             'When a meal entry changes: re-coordinate its plan\'s week.',
             cooldown_s=5.0),
    # mlg: any logistics knob changing re-coordinates the demo plan's
    # week (inputs_json names the plan — trigger knobs win over the
    # generic object payload).
    *[_trigger(f'coordinate-week-on-{cls.lower()}', 'object',
               {'class': cls, 'operations': ['create', 'update', 'delete']},
               'mealplan-coordinate-week-events',
               {'instanceName': PLAN, 'household': HOUSEHOLD},
               f'When a {cls} row changes: re-coordinate the week (meal-prep '
               f'sizes, packing, dishes, the allocation).', cooldown_s=5.0)
      for cls in ('PersonSchedule', 'SleepPreference', 'MealLogistics',
                  'WorkDistributionPolicy', 'HouseholdDishPolicy', 'PersonSkill',
                  'HouseholdMember')],
    _trigger('coordinate-week-sunday', 'schedule',
             {'schedule': {'eventType': 'datetime', 'frequency': 'weekly', 'byDay': ['SU'],
                           'startTime': '09:00', 'rangeStart': '2026-09-06'}},
             'mealplan-coordinate-week-events',
             {'instanceName': PLAN, 'household': HOUSEHOLD},
             'Every Sunday 09:00: coordinate the demo plan\'s week ahead.'),
]


def seed_mealplan_calendar(manager):
    """Upsert the event layer, then fire the coordination once for
    the demo plan if nothing has been generated yet."""
    from composition.seed_upsert import upsert_seed_pairs
    from polariApiServer.eventDefinition import EventDefinition
    from polariApiServer.calendarDefinition import CalendarDefinition
    from polariApiServer.solutionDefinition import SolutionDefinition
    from polariNoCode.analysis_calls import AnalysisDefinition
    from polariNoCode.event_triggers import EventTrigger

    # Night run 2026-09-03: the view pages' analyses / solutions /
    # triggers ride the same upsert (lazy imports — those modules import
    # page helpers from polariApiServer, so a top-level import would be
    # circular). A missing one is reported, never fatal.
    analyses = list(SEED_MEALPLAN_ANALYSES)
    solutions = list(SEED_MEALPLAN_SOLUTIONS)
    triggers = list(SEED_MEALPLAN_TRIGGERS)
    for _mod, _pre in (('nutrition.today_seed', 'TODAY'),
                       ('nutrition.shoptrip_seed', 'SHOPTRIP'),
                       ('nutrition.cooknow_seed', 'COOKNOW'),
                       ('nutrition.weekreview_seed', 'WEEKREVIEW')):
        try:
            _m = __import__(_mod, fromlist=['x'])
            analyses += list(getattr(_m, f'SEED_{_pre}_ANALYSES', []))
            solutions += list(getattr(_m, f'SEED_{_pre}_SOLUTIONS', []))
            triggers += list(getattr(_m, f'SEED_{_pre}_TRIGGERS', []))
        except Exception as e:  # noqa: BLE001
            print(f'[MealplanCalendarSeed] {_mod} skipped: {e}', flush=True)
    reports = upsert_seed_pairs(manager, [
        ('EventDefinition', EventDefinition, SEED_MEALPLAN_EVENT_DEFINITIONS),
        ('CalendarDefinition', CalendarDefinition, SEED_MEALPLAN_CALENDARS),
        ('AnalysisDefinition', AnalysisDefinition, analyses),
        ('SolutionDefinition', SolutionDefinition, solutions),
        ('EventTrigger', EventTrigger, triggers),
    ], tag='MealplanCalendarSeed')

    tables = getattr(manager, 'objectTables', {}) or {}
    generated = [e for e in (tables.get('CalendarEvent', {}) or {}).values()
                 if getattr(e, 'generated_by', '') == 'coordinate-week-on-plan']
    # fire when nothing was generated yet OR when a newer round added
    # event kinds the live rows lack (mlg: eating / packing / cleanup)
    # — dedupeBy keeps the re-run idempotent.
    have = {getattr(e, 'category', '') for e in generated}
    if not generated or not ({'eating', 'cleanup'} <= have):
        trigger = next((t for t in (tables.get('EventTrigger', {}) or {}).values()
                        if getattr(t, 'name', '') == 'coordinate-week-on-plan'), None)
        if trigger is not None:
            from polariNoCode.event_dispatcher import get_dispatcher
            firing = get_dispatcher(manager).fire(
                trigger, {'instanceName': PLAN, 'household': HOUSEHOLD,
                          'class': 'MealPlanDefinition', 'operation': 'seed'},
                'manual', 'seed:first-coordination')
            print(f'[MealplanCalendarSeed] first coordination for {PLAN}: '
                  f'{firing.status} {firing.error or ""}', flush=True)
    return reports
