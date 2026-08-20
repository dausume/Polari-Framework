"""
@module nutrition.selftest_workflow

nmp-10 selftest — the prep scheduler: method resolution by tools x
time x skill (pins win with the delta shown; absences say why),
duration models scale with skill and attendance, the optimizer
batches shared prep and compresses into sessions, storage follows
the FSIS windows (fridge <= 4 days, freeze + thaw beyond), user-
authored methods join resolution equally (decision 13), and the
tool advisor shows arithmetic + respects dismissals.

Run from polari-framework/:  python3 -m nutrition.selftest_workflow
"""

from types import SimpleNamespace

from nutrition.meal_basis import (SEED_MEAL_TEMPLATES,
                                  SEED_VARIATIONS)
from nutrition.recipe_basis import (SEED_INGREDIENT_LINES,
                                    SEED_RECIPES)
from nutrition.workflow_basis import (SEED_KITCHEN_TOOLS,
                                      SEED_STEP_METHODS,
                                      SEED_STORAGE_ACTIONS,
                                      SEED_TASK_KINDS)
from nutrition.workflow_analysis import (derive_week_plan,
                                         resolve_method,
                                         tool_advisor)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}'
          + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


PLAN = {'name': 'test-week', 'person_name': 'demo-alex',
        'household_name': '', 'days': 7, 'start_date': ''}
ENTRIES = [
    {'name': f'tw-d{d}-dinner', 'plan_name': 'test-week',
     'day_index': d, 'slot': 'dinner',
     'template_name': 'chicken-bowl-dinner', 'variation_name': '',
     'scale': 1.0, 'time_hhmm': '', 'serving_split_json': ''}
    for d in (1, 2, 6)
]

TOOLS_OWNED = [
    {'name': f'hh-{t}', 'household_name': 'hh', 'tool_name': t,
     'owned': True}
    for t in ('chef-knife', 'pot', 'pan', 'oven', 'fridge',
              'freezer', 'stove-burner', 'sheet-pan')
]

MY_METHOD = [{
    'name': 'dice-my-ulu', 'task_kind': 'dice',
    'display_name': 'My ulu knife rocking cut',
    'tool_name': 'ulu-knife', 'base_min': 1.0, 'per_100g_min': 0.5,
    'skill_floor': '', 'attended': True, 'retention_code': '',
    'provenance': 'mine', 'duration_fidelity': 'estimate',
    'notes': 'decision 13: user-declared tool + method'}]


def _mgr(extra_methods=(), prefs=(), tools=None, dismissals=()):
    tool_rows = TOOLS_OWNED if tools is None else tools
    return SimpleNamespace(objectTables={
        'KitchenToolDefinition': _rows(SEED_KITCHEN_TOOLS),
        'KitchenTool': _rows(tool_rows),
        'CookingTaskDefinition': _rows(SEED_TASK_KINDS),
        'StepMethod': _rows(SEED_STEP_METHODS + list(extra_methods)),
        'StorageActionDefinition': _rows(SEED_STORAGE_ACTIONS),
        'MethodPreference': _rows(list(prefs)),
        'ToolAdvisorDismissal': _rows(list(dismissals)),
        'Recipe': _rows(SEED_RECIPES),
        'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES),
        'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows([PLAN]),
        'MealEntry': _rows(ENTRIES),
    })


def main():
    m = _mgr()
    print('nmp-10 method resolution (decision 12)')
    r = resolve_method(m, 'dice', 400.0, household='hh')
    check('fastest OWNED method wins (knife; no processor owned)',
          r['ok'] and r['chosen']['method'] == 'dice-knife')
    check('unowned food processor SKIPPED with the reason',
          any('not in inventory' in s['why'] for s in r['skipped']))
    check('mandoline skipped only by inventory here, skill floor '
          'wording exists for novices',
          resolve_method(m, 'dice', 400.0, household='hh',
                         skill='novice')['ok'])
    r_all = resolve_method(m, 'dice', 400.0)
    check('no household -> all tools assumed (processor wins big '
          'batches)', r_all['chosen']['method'] == 'dice-processor')
    nov = resolve_method(m, 'dice', 400.0, skill='novice')
    exp = resolve_method(m, 'dice', 400.0, skill='experienced')
    knife_n = next(c for c in nov['candidates']
                   if c['method'] == 'dice-knife')
    knife_e = next(c for c in exp['candidates']
                   if c['method'] == 'dice-knife')
    check('skill scales the duration model (novice > experienced)',
          knife_n['activeMin'] > knife_e['activeMin'])
    pref = [{'name': 'hh-dice', 'person_name': '',
             'household_name': 'hh', 'task_kind': 'dice',
             'method_name': 'dice-knife'}]
    rp = resolve_method(_mgr(prefs=pref), 'dice', 400.0,
                        household='hh')
    check('a stated pin is honored (its delta shown when slower)',
          rp.get('pinned') is True)
    rc = resolve_method(m, 'boil', 300.0, household='hh')
    check('unattended rice cooker not owned -> pot; attended '
          'minutes are the score',
          rc['chosen']['method'] == 'boil-pot')
    check('method carries its own retention code (bake != fry)',
          rc['chosen']['retentionCode'] == '0432')

    print('nmp-10 decision 13: user-authored joins equally')
    r13 = resolve_method(_mgr(extra_methods=MY_METHOD), 'dice',
                         400.0)
    check('a user-declared tool+method WINS when fastest, '
          'provenance mine',
          r13['chosen']['method'] == 'dice-my-ulu'
          and r13['chosen']['provenance'] == 'mine')

    print('nmp-10 the optimizer')
    w = derive_week_plan(m, SimpleNamespace(**PLAN), household='hh')
    check('sessions derived with a total active-minutes score',
          w['ok'] and w['totalActiveMin'] > 0
          and len(w['sessions']) >= 1)
    s1 = next(s for s in w['sessions'] if s['day'] == 1)
    chicken = next((i for i in s1['items']
                    if i.get('food') == 'chicken-breast-raw'
                    and 'grams' in i), None)
    check('shared prep BATCHED (days 1+2 chicken in one session '
          'batch, 300 g)',
          chicken is not None and chicken['grams'] == 300.0
          and chicken['forDays'] == [1, 2])
    check('day-2 meal within the fridge window -> refrigerate, '
          'FSIS cited',
          any(i.get('storage') == 'refrigerate'
              and 'FSIS' in i.get('citation', '')
              for i in s1['items']))
    day6 = next(s for s in w['sessions'] if s['day'] == 4)
    check('day-6 meal cooked in the day-4 session (2-day gap '
          'fits the fridge window)',
          any(i.get('food') == 'chicken-breast-raw'
              for i in day6['items']))
    check('daily actions include reheat notes',
          any(any(a['action'] == 'reheat' for a in acts)
              for acts in w['dailyActions'].values()))
    check('the output is a PROPOSAL with a workflow DAG for the '
          'no-code editor',
          'PROPOSAL' in w['honesty']
          and len(w['workflowDag']['nodes']) > 0)

    print('nmp-10 the tool advisor')
    adv = tool_advisor(m, SimpleNamespace(**PLAN), 'hh',
                       min_weekly_minutes=2.0)
    fp = next((s for s in adv['suggestions']
               if s['tool'] == 'food-processor'), None)
    check('unowned processor suggested with weekly + yearly '
          'arithmetic',
          fp is not None and fp['weeklyMinutesSaved'] > 0
          and 'never a nag' in fp['note'])
    dism = [{'name': 'hh-fp', 'household_name': 'hh',
             'tool_name': 'food-processor'}]
    adv2 = tool_advisor(_mgr(dismissals=dism),
                        SimpleNamespace(**PLAN), 'hh',
                        min_weekly_minutes=2.0)
    check('dismissal remembered — no more processor suggestions',
          not any(s['tool'] == 'food-processor'
                  for s in adv2['suggestions'])
          and 'food-processor' in adv2['dismissed'])

    print()
    if failures:
        print(f'{FAIL}: {len(failures)} check(s) failed')
        raise SystemExit(1)
    print(f'{PASS}: nmp-10 prep scheduler holds together')


if __name__ == '__main__':
    main()
