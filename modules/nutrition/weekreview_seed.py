"""
@module nutrition.weekreview_seed

N5 — the WEEKLY REVIEW page (`mealplan/review`) and its no-code
layer, all data (no new components, no JSON on screen):

  SEED_WEEKREVIEW_TABLES        none new — the page embeds the EXISTING
                                mealplan-waste-standard / -budget- /
                                -work-ledger- / -event-standard tables
                                BY NAME (mealplan_pages_seed)
  SEED_WEEKREVIEW_GRAPHS        none new — the weekly period charts
                                (mealplan-period-calories / -sodium over
                                PeriodIntakeMetric) are reused by name
  SEED_WEEKREVIEW_PAGE_DISPLAYS the review page: headline panel + one
                                structured panel per section + charts +
                                the "Accept next week's proposals" form
                                + the ledgers
  SEED_WEEKREVIEW_ANALYSES      week_review / next_week_proposals /
                                weekly_review_event_proposal as rows
  SEED_WEEKREVIEW_SOLUTIONS     mealplan-accept-next-week (the form:
                                FormSubscription → AnalysisCall(pick
                                proposals) → GenerateEvent(dedupe name)
                                → refresh) and mealplan-weekly-review-
                                event (the Sunday trigger's solution)
  SEED_WEEKREVIEW_TRIGGERS      weekly-review-sunday (schedule, SU 17:00)

Wired by the orchestrator into mealplan_pages_seed / calendar_seed
(the upsert + repoint pass) — this module only DEFINES.

@consumers polariApiServer.mealplan_pages_seed (after wiring),
  nutrition.selftest_weekreview
@see AI-Notes/designs/HOUSEHOLD_APP_PAGES.md §3.6
"""

import json

from polariApiServer.mealplan_pages_seed import (
    HOUSEHOLD, PERSON, PLAN, _egraph, _etable, _form, _sapi,
)
from polariApiServer.module_pages_seed import _page, _row
from polariNoCode import graph_builder as gb
from nutrition.calendar_seed import (
    _solution, _trigger, message_call, refresh_with_message,
)

_MP = '/api/mealplanning'
_REVIEW = f'{_MP}/review?plan={PLAN}&household={HOUSEHOLD}'
PROVENANCE = 'weekreview'

# nothing new: every table / graph the page embeds already exists in
# mealplan_pages_seed (reused by NAME) — kept as lists so the wiring
# is uniform with the other features.
SEED_WEEKREVIEW_TABLES = []
SEED_WEEKREVIEW_GRAPHS = []


def _section(item_id, index, segments, title, section):
    return _sapi(item_id, index, segments, title,
                 f'{_REVIEW}&section={section}', pick='lines')


ACCEPT_FORM = _form(
    'wr-accept-form', 1, 6,
    'Accept next week\'s proposals — writes the purchase / bulk-buy / review '
    'events (deduped by name: accepting twice writes nothing twice)',
    'mealplan-accept-next-week', [
        ('plan', 'Plan', 'string', PLAN, 'MealPlanDefinition name', True),
        ('household', 'Household', 'string', HOUSEHOLD, 'HouseholdProfile name', True),
        ('week_start', 'Reviewed week (blank = the plan\'s days)', 'string', '',
         'ISO date inside the reviewed week; next week follows it', False),
    ], submit_label='Accept proposals')

SEED_WEEKREVIEW_PAGE_DISPLAYS = [
    _page(
        'mealplan-review', 'mealplan/review',
        'N5: the Sunday review — what was planned vs eaten (coverage vs '
        'intake), cost vs budget, waste, fairness, the "consistently" '
        'readings, and next week\'s proposals with one form to accept them. '
        'Composed from the existing analyses; every section says "no data" '
        'honestly. The weekly-review-sunday trigger writes the same headline '
        'as a review event.',
        'MealPlanDefinition',
        [
            _row(0, [
                _sapi('wr-headline', 0, 12,
                      f'This week in one look — {PLAN} / {HOUSEHOLD}',
                      _REVIEW, hide='lines,proposals,honesty'),
            ], min_height=200),
            _row(1, [
                _section('wr-coverage', 0, 6, 'Planned vs eaten (per person; the unplanned '
                         'slots named)', 'coverage'),
                _section('wr-intake', 1, 6, 'How the week read against each person\'s own '
                         'lines — and what is "consistently" so', 'intake'),
            ]),
            _row(2, [
                _section('wr-cost', 0, 4, 'Cost vs budget', 'cost'),
                _section('wr-waste', 1, 4, 'Waste this week', 'waste'),
                _section('wr-fairness', 2, 4, 'Who did the work', 'fairness'),
            ]),
            _row(3, [
                _egraph('wr-cal-week', 0, 6, f'Weekly mean kcal/day — {PERSON}',
                        'mealplan-period-calories', 'PeriodIntakeMetric',
                        'series_key', f'{PERSON}:week'),
                _egraph('wr-sodium-week', 1, 6, f'Weekly mean sodium — {PERSON}',
                        'mealplan-period-sodium', 'PeriodIntakeMetric',
                        'series_key', f'{PERSON}:week'),
            ]),
            _row(4, [
                _sapi('wr-proposals', 0, 6, 'Next week\'s proposals (purchase · bulk buys due · '
                      'the next review)', _REVIEW, pick='proposals'),
                ACCEPT_FORM,
            ]),
            _row(5, [
                _etable('wr-waste-table', 0, 4, f'Waste records — {HOUSEHOLD} (Create New logs one)',
                        'mealplan-waste-standard', 'WasteRecord', 'household_name', HOUSEHOLD),
                _etable('wr-budget-table', 1, 4, f'Budget — {PLAN} (the envelope knob)',
                        'mealplan-budget-standard', 'PlanBudget', 'plan_name', PLAN),
                _etable('wr-ledger-table', 2, 4, f'Work ledger — {HOUSEHOLD}',
                        'mealplan-work-ledger-standard', 'WorkLedger', 'household_name', HOUSEHOLD),
            ]),
            _row(6, [
                _etable('wr-review-events', 0, 6, 'Review events (the Sunday trigger\'s rows)',
                        'mealplan-event-standard', 'CalendarEvent', 'category', 'review'),
                _sapi('wr-honesty', 1, 6, 'What this review leans on (every prior named)',
                      _REVIEW, pick='honesty'),
            ]),
        ]),
]

SEED_WEEKREVIEW_ANALYSES = [
    {'name': 'mealplan-week-review', 'domain': 'nutrition',
     'callable_ref': 'nutrition.weekreview_analysis:week_review',
     'description': 'The Sunday review: planned vs eaten, "consistently" readings, cost vs '
                    'budget, waste, fairness, next week\'s proposals — flat, every prior named.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name', 'household': '',
                                'week_start': 'ISO date (blank = the plan\'s days)'}),
     'enabled': True, 'is_prior': True, 'provenance_id': PROVENANCE},
    {'name': 'mealplan-next-week-proposals', 'domain': 'nutrition',
     'callable_ref': 'nutrition.weekreview_analysis:next_week_proposals',
     'description': 'Next week\'s CalendarEvent proposals: the weekly purchase, bulk buys whose '
                    '1st falls in the week, the next Sunday review.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name', 'household': '',
                                'week_start': 'ISO date (blank = the plan\'s days)'}),
     'enabled': True, 'is_prior': True, 'provenance_id': PROVENANCE},
    {'name': 'mealplan-week-review-event', 'domain': 'nutrition',
     'callable_ref': 'nutrition.weekreview_analysis:weekly_review_event_proposal',
     'description': 'One review CalendarEvent proposal (Sunday 18:00 prior) carrying the '
                    'headline as payload — what the Sunday trigger generates.',
     'params_json': json.dumps({'plan': 'MealPlanDefinition.name', 'household': '',
                                'week_start': 'ISO date', 'review_date': 'ISO date/datetime '
                                '(the occurrence)', 'review_time': 'HH:MM (default 18:00)'}),
     'enabled': True, 'is_prior': True, 'provenance_id': PROVENANCE},
]

#: the form: FormSubscription → the proposals → CalendarEvent rows
#: (dedupe by name) → the page refreshes — calendar_seed's shape.
_ACCEPT_PARAMS = {'plan': gb.var_src('plan'), 'household': gb.var_src('household'),
                  'week_start': gb.var_src('week_start')}

ACCEPT_NEXT_WEEK_SOLUTION = _solution(
    'mealplan-accept-next-week',
    gb.solution(
        'mealplan-accept-next-week',
        gb.node('Start', 'FormSubscription', {}, outs=[['Propose']]),
        gb.node('Propose', 'AnalysisCall',
                {'analysis': 'mealplan-next-week-proposals', 'params': _ACCEPT_PARAMS,
                 'pick': 'proposals', 'resultVariable': 'proposals'}, outs=[['Message']]),
        message_call('Message', 'mealplan-next-week-proposals', _ACCEPT_PARAMS, 'Write'),
        gb.node('Write', 'GenerateEvent',
                {'targetClassName': 'CalendarEvent', 'eventsFrom': gb.var_src('proposals'),
                 'dedupeBy': 'name', 'fields': {}}, outs=[['Refresh']]),
        refresh_with_message({'written': gb.var_src('generatedEventBatch')}),
    ),
    'Accept next week\'s proposals: purchase / bulk-buy / review events, deduped by name; '
    'says how many were created and how many already existed.')

#: the Sunday trigger's solution: Start → the review-event proposal →
#: one CalendarEvent (dedupe by name) → EmitEvent.
WEEKLY_REVIEW_EVENT_SOLUTION = _solution(
    'mealplan-weekly-review-event',
    gb.solution(
        'mealplan-weekly-review-event',
        gb.entry('Start', nxt='Analyse'),
        gb.node('Analyse', 'AnalysisCall',
                {'analysis': 'mealplan-week-review-event',
                 'params': {'plan': gb.var_src('planName'), 'household': gb.var_src('household'),
                            'review_date': gb.var_src('occurrenceKey')},
                 'pick': 'proposals', 'resultVariable': 'proposals'}, outs=[['Generate']]),
        gb.node('Generate', 'GenerateEvent',
                {'targetClassName': 'CalendarEvent', 'eventsFrom': gb.var_src('proposals'),
                 'dedupeBy': 'name', 'fields': {}}, outs=[['Emit']]),
        gb.node('Emit', 'EmitEvent',
                {'eventName': 'weekly-review-made',
                 'payload': {'generated': gb.var_src('generatedEventBatch')}}),
    ),
    'Every Sunday: write the week\'s review event with the headline as its payload.')

SEED_WEEKREVIEW_SOLUTIONS = [ACCEPT_NEXT_WEEK_SOLUTION, WEEKLY_REVIEW_EVENT_SOLUTION]

SEED_WEEKREVIEW_TRIGGERS = [
    _trigger('weekly-review-sunday', 'schedule',
             {'schedule': {'eventType': 'datetime', 'frequency': 'weekly', 'byDay': ['SU'],
                           'startTime': '17:00', 'rangeStart': '2026-09-06'}},
             'mealplan-weekly-review-event',
             {'planName': PLAN, 'household': HOUSEHOLD},
             'Every Sunday 17:00: compute the week\'s review and write the 18:00 review '
             'event (both times are priors — this row and review_time are the knobs).',
             provenance_id=PROVENANCE),
]
