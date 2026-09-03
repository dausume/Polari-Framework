"""
@module nutrition.cooknow_seed

N4 — the **Cook now** page as DATA (HOUSEHOLD_APP_PAGES.md §3.4),
route `mealplan/cooknow?object=<PersonProfile.name>`; the display
page substitutes `{object}` (only the object is substituted, so the
person IS the object and the TEMPLATE is a knob: the headline panels
read the default template and the "Step done" form's `template`
field, default 'chicken-bowl-dinner', names it).

  SEED_COOKNOW_TABLES        TableDefinition rows (DurationObservation
                             as the page's log; CookingStep as the
                             recipe as written) — NOT defaults, the
                             household page's tables keep those
  SEED_COOKNOW_GRAPHS        none
  SEED_COOKNOW_PAGE_DISPLAYS the page (rows sum to 12)
  SEED_COOKNOW_ANALYSES      cook_sheet / step_done_proposal by ref
  SEED_COOKNOW_SOLUTIONS     the "Step done" form solution:
                             FormSubscription → AnalysisCall(pick
                             proposals) → GenerateEvent(target
                             DurationObservation, dedupeBy name) →
                             EmitFrontendEvent(refreshDisplay)
  SEED_COOKNOW_TRIGGERS      none — a DurationObservation never applies
                             a factor by itself (refinement is a
                             suggestion; PersonSkill is a knob)

@consumers polariApiServer.mealplan_pages_seed (the orchestrator's
  upsert), nutrition.selftest_cooknow
"""

import json

from polariApiServer.mealplan_pages_seed import (
    _MP, _etable, _form, _sapi, _table_def,
)
from polariApiServer.module_pages_seed import _page, _row
from polariNoCode import graph_builder as gb
from nutrition.calendar_seed import message_call, refresh_with_message

TEMPLATE = 'chicken-bowl-dinner'
RECIPE = 'chicken-rice-bowl'
PERSON = 'demo-alex'

SEED_COOKNOW_TABLES = [
    _table_def('cooknow-duration-obs', 'DurationObservation',
               'Durations observed (cook now)',
               'How long a step took THIS person — the refinement loop\'s facts.',
               [('person_name', 'Person', 'str', 110),
                ('date', 'Date', 'str', 110),
                ('method_name', 'Method', 'str', 150),
                ('skill_name', 'Skill', 'str', 120),
                ('observed_min', 'Observed (min)', 'float', 110),
                ('source', 'Source', 'str', 90),
                ('notes', 'Notes', 'str', 320)], defaults=False),
    _table_def('cooknow-cooking-step', 'CookingStep',
               'Recipe steps as written',
               'The recipe\'s own ordered steps (method + minutes as authored).',
               [('recipe_name', 'Recipe', 'str', 150),
                ('order', 'Step', 'int', 60),
                ('instruction', 'Instruction', 'str', 360),
                ('method', 'Method', 'str', 100),
                ('duration_min', 'Minutes as written', 'float', 120)], defaults=False),
]

SEED_COOKNOW_GRAPHS = []

_SHEET = f'{_MP}/cooknow/{{object}}?template={TEMPLATE}'

SEED_COOKNOW_PAGE_DISPLAYS = [
    _page(
        'mealplan-cooknow', 'mealplan/cooknow',
        'N4: Cook now — the recipe at prep time for ONE person (open with '
        '?object=<person>): the steps in order with THIS person\'s minutes '
        '(method × their skill factor, never below the safety floor — the '
        'basis on every step), attended vs unattended, a timer per '
        'unattended window with the "do dishes now" suggestion, the safety '
        'words for each hazard tag, the ingredients per step scaled to '
        'their portion, ready-by when an event is named; "Step done" logs '
        'the minutes it took as a DurationObservation and shows the speed '
        'factor the refinement loop would suggest (a knob — never applied).',
        'DurationObservation',
        [
            _row(0, [
                _sapi('cn-headline', 0, 6,
                      f'Cook now — {TEMPLATE} for {{object}} (attended / unattended / '
                      'wall-clock minutes; portion; ready-by)',
                      _SHEET, hide='steps,ingredients,safetyLines,dishLines'),
                _sapi('cn-safety', 1, 6, 'Safety words for the hazard steps (cited)',
                      _SHEET, pick='safetyLines'),
            ]),
            _row(1, [
                _sapi('cn-steps', 0, 12,
                      'The steps — your minutes, the basis, timer windows, safety',
                      _SHEET, pick='steps'),
            ]),
            _row(2, [
                _sapi('cn-ingredients', 0, 6, 'Ingredients per step (grams for you)',
                      _SHEET, pick='ingredients'),
                _sapi('cn-dish-windows', 1, 6,
                      'Unattended windows — timers + "do dishes now"',
                      _SHEET, pick='dishLines'),
            ]),
            _row(3, [
                _form('cn-step-done', 0, 12,
                      'Step done — how long did it take? (logs a DurationObservation; '
                      'the same step on the same day is reused)',
                      'cooknow-step-done', [
                          ('template', 'Meal', 'string', TEMPLATE,
                           'a MealTemplate name', True),
                          ('step_order', 'Step number', 'number', 1,
                           '1 = the first step', True),
                          ('person', 'Person', 'string', '{object}', '', True),
                          ('minutes_actual', 'Minutes it took', 'number', 0,
                           'e.g. 6.5', True),
                          ('date_iso', 'Date', 'string', '',
                           'blank = today (YYYY-MM-DD)', False),
                      ], submit_label='Done'),
            ]),
            _row(4, [
                _etable('cn-durations', 0, 6, 'Durations observed — {object}',
                        'cooknow-duration-obs', 'DurationObservation',
                        'person_name', '{object}'),
                _sapi('cn-speed', 1, 6,
                      'Speed factor suggestions — {object} (median of ≥ 3 observations; '
                      'never below the floor; a knob, never applied)',
                      f'{_MP}/speed-refinement?person={{object}}', pick='proposals'),
            ]),
            _row(5, [
                _sapi('cn-speed-questions', 0, 6,
                      'Faster than the safety floor allows? (questions, not verdicts)',
                      f'{_MP}/speed-refinement?person={{object}}', pick='safetyQuestions'),
                _etable('cn-recipe-steps', 1, 6, f'Recipe as written — {RECIPE}',
                        'cooknow-cooking-step', 'CookingStep', 'recipe_name', RECIPE),
            ]),
        ]),
]

SEED_COOKNOW_ANALYSES = [
    {'name': 'cooknow-sheet', 'domain': 'nutrition',
     'callable_ref': 'nutrition.cooknow_analysis:cook_sheet',
     'description': 'The recipe at prep time for one person: steps with their minutes '
                    '(basis labelled), unattended windows + dish suggestion, safety '
                    'lines, ingredients per step, totals, ready-by.',
     'params_json': json.dumps({'template': 'MealTemplate.name', 'person': 'PersonProfile.name',
                                'variation': '', 'event': 'CalendarEvent.name (optional)'}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'cooknow'},
    {'name': 'cooknow-step-done', 'domain': 'nutrition',
     'callable_ref': 'nutrition.cooknow_analysis:step_done_proposal',
     'description': '"Done" → one DurationObservation proposal (dedupe person-template-step-date) '
                    '+ the speed-factor suggestion with it counted (never applied).',
     'params_json': json.dumps({'template': 'MealTemplate.name', 'step_order': 'int',
                                'person': 'PersonProfile.name', 'minutes_actual': 'float',
                                'date_iso': 'YYYY-MM-DD (blank = today)', 'variation': ''}),
     'enabled': True, 'is_prior': True, 'provenance_id': 'cooknow'},
]


def _solution(name, definition, description):
    return {'name': name, 'function_name': name.replace('-', '_'),
            'target_runtime': 'python_backend',
            'definition': json.dumps(definition),
            'contract_json': json.dumps({'description': description,
                                         'executionRights': 'definer'})}


_STEP_DONE_PARAMS = {'template': gb.var_src('template'),
                     'step_order': gb.var_src('step_order'),
                     'person': gb.var_src('person'),
                     'minutes_actual': gb.var_src('minutes_actual'),
                     'date_iso': gb.var_src('date_iso')}

STEP_DONE_SOLUTION = _solution(
    'cooknow-step-done',
    gb.solution(
        'cooknow-step-done',
        gb.node('Start', 'FormSubscription', {}, outs=[['Validate']]),
        gb.node('Validate', 'AnalysisCall',
                {'analysis': 'cooknow-step-done', 'params': _STEP_DONE_PARAMS,
                 'pick': 'proposals', 'resultVariable': 'proposals'}, outs=[['Message']]),
        message_call('Message', 'cooknow-step-done', _STEP_DONE_PARAMS, 'Write'),
        gb.node('Write', 'GenerateEvent',
                {'targetClassName': 'DurationObservation',
                 'eventsFrom': gb.var_src('proposals'),
                 'dedupeBy': 'name', 'fields': {}}, outs=[['Refresh']]),
        refresh_with_message({'written': gb.var_src('generatedEventBatch')}),
    ),
    'Cook now: a step is done → its observed minutes as a DurationObservation '
    '(dedupe by name); the factor suggestion stays a suggestion — said in words '
    '("Step 3 took 12 min; speed suggestion …").')

SEED_COOKNOW_SOLUTIONS = [STEP_DONE_SOLUTION]

#: none: an observation never applies a speed factor by itself.
SEED_COOKNOW_TRIGGERS = []
