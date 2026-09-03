"""
@module nutrition.selftest_planning

mpc selftest — the week-planning flow: expected slots per person,
the coverage grid naming every missing meal, per-person PORTION fit
(one recipe, scales from each person's slot share of their target,
clamped to the variation's bounds, the compromise stated), the
apply-meal proposal (any slots × days; existing entries NAMED, never
overwritten), and the seeded no-code form solution writing MealEntry
rows through the REAL engine, after which coverage improves and the
entry trigger re-coordinates the week.

Run from polari-framework/modules/:
  PYTHONPATH=..:../polariApiServer python3 -m nutrition.selftest_planning
"""

import json
import sys
from types import SimpleNamespace

from nutrition.calendar_seed import (
    SEED_MEALPLAN_ANALYSES, SEED_MEALPLAN_CALENDARS,
    SEED_MEALPLAN_EVENT_DEFINITIONS, SEED_MEALPLAN_SOLUTIONS,
    SEED_MEALPLAN_TRIGGERS,
)
from nutrition.fdc_seed import SEED_FDC_FOOD_ITEMS, SEED_FDC_NUTRIENT_CONTENTS
from mealoptions import MEALOPTIONS_SEED_PAIRS
from nutrition.logistics_basis import HOUSEHOLD_SEED_PAIRS, LOGISTICS_SEED_PAIRS
from nutrition.market_basis import (
    SEED_PRICE_OBSERVATIONS, SEED_SOURCE_LOCATIONS, SEED_UNIT_WEIGHTS,
)
from nutrition.meal_basis import (
    SEED_MEAL_ENTRIES, SEED_MEAL_PLANS, SEED_MEAL_TEMPLATES, SEED_VARIATIONS,
)
from nutrition.pantry_basis import SEED_PANTRY_ITEMS
from nutrition.person_seed import SEED_HOUSEHOLDS, SEED_PERSONS
from nutrition.planning_analysis import (
    apply_meal_proposal, expected_slots, portion_fit, week_coverage,
)
from nutrition.purchase_basis import SEED_BULK_STAPLES
from nutrition.recipe_basis import SEED_INGREDIENT_LINES, SEED_RECIPES
from nutrition.threshold_basis import SEED_EATING_PATTERNS
from nutrition.workflow_basis import (
    SEED_KITCHEN_TOOLS, SEED_STEP_METHODS, SEED_STORAGE_ACTIONS, SEED_TASK_KINDS,
)
from polariNoCode import graph_builder as gb
from polariNoCode.calendar_events import SEED_CORE_EVENT_DEFINITIONS

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
failures = []


def check(label, cond, extra=''):
    print(f'  [{PASS if cond else FAIL}] {label}' + (f'  ({extra})' if extra and not cond else ''))
    if not cond:
        failures.append(label)


def _rows(seed_list):
    return {f'{i}': SimpleNamespace(id=f'{i}', **r) for i, r in enumerate(seed_list)}


class _DB:
    def saveInstanceInDB(self, inst):
        return True


def _manager():
    tables = {
        'UnitWeightPrior': _rows(SEED_UNIT_WEIGHTS), 'SourceLocation': _rows(SEED_SOURCE_LOCATIONS),
        'PriceObservation': _rows(SEED_PRICE_OBSERVATIONS), 'PantryItem': _rows(SEED_PANTRY_ITEMS),
        'FoodItem': _rows(SEED_FDC_FOOD_ITEMS), 'NutrientContent': _rows(SEED_FDC_NUTRIENT_CONTENTS),
        'Recipe': _rows(SEED_RECIPES), 'IngredientLine': _rows(SEED_INGREDIENT_LINES),
        'MealTemplate': _rows(SEED_MEAL_TEMPLATES), 'VariationDefinition': _rows(SEED_VARIATIONS),
        'MealPlanDefinition': _rows(SEED_MEAL_PLANS), 'MealEntry': _rows(SEED_MEAL_ENTRIES),
        'PersonProfile': _rows(SEED_PERSONS), 'HouseholdProfile': _rows(SEED_HOUSEHOLDS),
        'EatingPatternDefinition': _rows(SEED_EATING_PATTERNS),
        'BulkStaple': _rows(SEED_BULK_STAPLES),
        'KitchenToolDefinition': _rows(SEED_KITCHEN_TOOLS), 'StepMethod': _rows(SEED_STEP_METHODS),
        'StorageActionDefinition': _rows(SEED_STORAGE_ACTIONS), 'CookingTaskDefinition': _rows(SEED_TASK_KINDS),
        'KitchenTool': {}, 'MethodPreference': {}, 'NutrientReference': {}, 'DietaryNutrient': {},
        'PersonThreshold': {}, 'ToleranceThreshold': {},
        'EventDefinition': _rows(SEED_CORE_EVENT_DEFINITIONS + SEED_MEALPLAN_EVENT_DEFINITIONS),
        'CalendarDefinition': _rows(SEED_MEALPLAN_CALENDARS),
        'AnalysisDefinition': _rows(SEED_MEALPLAN_ANALYSES),
        'SolutionDefinition': _rows(SEED_MEALPLAN_SOLUTIONS),
        'EventTrigger': _rows(SEED_MEALPLAN_TRIGGERS),
        'TriggerFiring': {}, 'CalendarEvent': {},
    }
    # hh-1: the household layer's seeds moved with it; LOGISTICS_SEED_PAIRS
    # is meal-only now.
    # mo-1: the shareable meal data (incl. MealSituation) lives in mealoptions.
    for cls, _c, seeds in HOUSEHOLD_SEED_PAIRS + LOGISTICS_SEED_PAIRS + MEALOPTIONS_SEED_PAIRS:
        tables[cls] = _rows(seeds)
    return SimpleNamespace(objectTables=tables, db=_DB())


def main():
    mgr = _manager()
    plan = next(iter(mgr.objectTables['MealPlanDefinition'].values()))
    print('mpc — plan the week')

    es = expected_slots(mgr, 'demo-alex')
    check('expected slots: an unstated pattern falls back to the 3-meal default, labeled',
          [s['slot'] for s in es['slots']] == ['breakfast', 'lunch', 'dinner'] and 'default' in es['source'])

    cov = week_coverage(mgr, plan.name)
    check('coverage: 2 members × 3 days × 3 slots = 18 expected; the 5 seeded entries (no serving '
          'split → household-wide) plan 10; 8 missing NAMED; not complete',
          cov['counts'] == {'expected': 18, 'planned': 10, 'missing': 8} and not cov['complete']
          and all({'person', 'day', 'slot'} <= set(m) for m in cov['missing']), str(cov['counts']))
    check('the headline says how many are planned and names days with nothing',
          '10 of 18' in cov['headline'], cov['headline'])

    pf = portion_fit(mgr, 'chicken-bowl-dinner', '', 'dinner', ['demo-alex', 'demo-sam'])
    a = [f for f in pf['fits'] if f['person'] == 'demo-alex'][0]
    s = [f for f in pf['fits'] if f['person'] == 'demo-sam'][0]
    check('portion fit: one recipe, two portions — Alex (80 kg male) IDEALLY needs a larger scale than '
          'Sam (62 kg female); each = slot share of THEIR target ÷ kcal per serving; the small demo '
          'dinner (~380 kcal/serving) pushes both to the variation\'s max → the compromise is STATED',
          pf['ok'] and a['idealScale'] > s['idealScale'] and a['slotFraction'] == 0.40
          and a['kcalAtScale'] > 0 and pf['servingSplit']['demo-alex'] == a['scale']
          and (a['scale'] > s['scale'] or (a['clamped'] and pf['compromises'])),
          f"alex {a.get('idealScale')}→{a.get('scale')} sam {s.get('idealScale')}→{s.get('scale')} "
          f"kcal/serving {pf.get('mealKcalPerServing')} compromises={len(pf.get('compromises', []))}")
    check('scales stay inside the variation\'s bounds and the total scale is the sum of portions',
          all(f['scaleBounds'][0] <= f['scale'] <= f['scaleBounds'][1] for f in pf['fits'])
          and abs(pf['totalScale'] - round(a['scale'] + s['scale'], 2)) < 0.02)
    check('key nutrients at the portion are reported against the slot share of daily needs',
          'protein' in a['nutrients'] and a['nutrients']['protein']['have'] > 0)
    # force a compromise: a tiny variation bound
    var = [v for v in mgr.objectTables['VariationDefinition'].values() if v.name == 'chicken-bowl-dinner-base'][0]
    lo, hi = var.scale_min, var.scale_max
    var.scale_min, var.scale_max = 0.3, 0.4
    pf2 = portion_fit(mgr, 'chicken-bowl-dinner', 'chicken-bowl-dinner-base', 'dinner', ['demo-alex'])
    check('a bound that cannot reach the target CLAMPS the portion and STATES the compromise with a suggestion',
          pf2['fits'][0]['clamped'] and pf2['compromises'] and 'ideal portion' in pf2['compromises'][0]['why']
          and pf2['compromises'][0]['suggestion'], str(pf2['compromises']))
    var.scale_min, var.scale_max = lo, hi

    ap = apply_meal_proposal(mgr, plan.name, 'chicken-bowl-dinner', '', 'lunch,dinner', 'all')
    check('apply-meal: lunch + dinner × 3 days = 6 cells; the 3 planned dinners are NAMED as already '
          'planned; 3 lunch proposals carry per-person serving splits',
          ap['ok'] and ap['counts'] == {'proposed': 3, 'alreadyPlanned': 3}
          and all(p['slot'] == 'lunch' and set(json.loads(p['serving_split_json'])) == {'demo-alex', 'demo-sam'}
                  for p in ap['proposals']), str(ap['counts']))
    ap2 = apply_meal_proposal(mgr, plan.name, 'omelet-breakfast', '', 'dinner', '1')
    check('a slot the template is not written for is a WARNING, not a block',
          ap2['ok'] and ap2['warnings'] and ap2['counts']['proposed'] == 0
          and ap2['alreadyPlanned'], str(ap2['warnings'])[:120])
    ap3 = apply_meal_proposal(mgr, plan.name, 'nope', '', 'all', 'all')
    check('an unknown meal refuses plainly', not ap3['ok'] and 'nope' in ap3['error'])
    ap4 = apply_meal_proposal(mgr, plan.name, 'chicken-bowl-dinner', '', 'lunch', '1,9')
    check('a day outside the plan is named, the valid day still proposed',
          ap4['daysOutOfRange'] == [9] and ap4['counts']['proposed'] == 1, str(ap4['daysOutOfRange']))
    ap5 = apply_meal_proposal(mgr, plan.name, 'chicken-bowl-dinner', '', 'lunch', '2', 'demo-alex', 1.5)
    check('one person + a fixed scale → a single portion at that scale',
          json.loads(ap5['proposals'][0]['serving_split_json']) == {'demo-alex': 1.5}
          and ap5['proposals'][0]['scale'] == 1.5)

    # --- the seeded no-code solution through the real engine -----------
    sol = [s for s in SEED_MEALPLAN_SOLUTIONS if s['name'] == 'mealplan-apply-meal-to-week'][0]
    before = len(mgr.objectTables['MealEntry'])
    trace = gb.execute(json.loads(sol['definition']), manager=mgr,
                       params={'plan': plan.name, 'template': 'chicken-bowl-dinner', 'variation': '',
                               'slots': 'lunch', 'days': 'all', 'person': '', 'scale': 0})
    from polariNoCode.graph_compilers import final_context_of
    ctx = final_context_of(trace) or {}
    made = [e for e in mgr.objectTables['MealEntry'].values() if getattr(e, 'slot', '') == 'lunch']
    check('the "Add to the week" form solution (FormSubscription → AnalysisCall → GenerateEvent MealEntry → '
          'refresh) writes 3 lunch entries with serving splits, through the real engine',
          trace.status == 'completed' and len(mgr.objectTables['MealEntry']) == before + 3
          and all(json.loads(e.serving_split_json).get('demo-sam') for e in made)
          and any(ev.get('name') == 'refreshDisplay' and ev.get('channel') == 'frontend'
                  for ev in ctx.get('_emitted_events', [])),
          f'{trace.status} {trace.error_summary} made={len(made)}')
    cov2 = week_coverage(mgr, plan.name)
    check('coverage improves: 16 of 18 planned (only the two breakfasts of day 3 missing)',
          cov2['counts']['planned'] == 16 and {m['slot'] for m in cov2['missing']} == {'breakfast'},
          str(cov2['counts']))
    trace2 = gb.execute(json.loads(sol['definition']), manager=mgr,
                        params={'plan': plan.name, 'template': 'chicken-bowl-dinner', 'variation': '',
                                'slots': 'lunch', 'days': 'all', 'person': '', 'scale': 0})
    check('running the form again never duplicates (already planned → named; dedupe by name)',
          trace2.status == 'completed' and len(mgr.objectTables['MealEntry']) == before + 3)

    # --- what the form SHOWS: the message (fix 2026-09-03: a submit was a silent no-op) ---
    print('\nthe form message')
    check('apply-meal proposal carries a plain-words message: "Added 3 entries (Tue lunch, …); 3 slots '
          'already planned and kept: Tue dinner (chicken-bowl-dinner), …" — every slot named',
          ap['message'].startswith('Added 3 entries (Tue lunch, Wed lunch, Thu lunch); 3 slots already '
                                   'planned and kept: Tue dinner (chicken-bowl-dinner)'), ap['message'])
    check('a refused proposal\'s message IS its error (no JSON, no diagnosis words)',
          ap3['message'] == ap3['error'] and 'not found' in ap3['message'], ap3['message'])
    msg1 = ctx.get('message')
    refresh1 = next((ev for ev in ctx.get('_emitted_events', []) if ev.get('name') == 'refreshDisplay'), {})
    check('through the engine the FIRST run leaves `message` as a context variable '
          '(steps[-1].contextAfter.variables.message) AND in the refreshDisplay payload: "Added 3 entries"',
          isinstance(msg1, str) and msg1.startswith('Added 3 entries (Tue lunch, Wed lunch, Thu lunch)')
          and refresh1.get('payload', {}).get('message') == msg1, str(msg1))
    msg2 = (final_context_of(trace2) or {}).get('message')
    check('the SECOND run (every lunch already planned) says so in words — "Nothing added — 3 slots '
          'already planned and kept: Tue lunch (chicken-bowl-dinner), …" — never a silent no-op',
          isinstance(msg2, str) and msg2.startswith('Nothing added — 3 slots already planned and kept: '
                                                     'Tue lunch (chicken-bowl-dinner)')
          and 'Wed lunch' in msg2 and 'Thu lunch' in msg2, str(msg2))
    check('the message is the graph\'s last step (Refresh is the terminal EmitFrontendEvent) — a '
          'reader finds it without digging: trace.steps[-1].contextAfter.variables.message.value',
          trace2.steps[-1].state_name == 'Refresh'
          and trace2.steps[-1].context_after.variables['message']['value'] == msg2)
    firings = list(mgr.objectTables['TriggerFiring'].values())
    check('each new MealEntry fired the entry trigger (re-coordination) — audited firings',
          any(f.trigger_name == 'coordinate-week-on-entry' for f in firings), str(len(firings)))

    # --- the portion objective KNOB (TESTING_OWED §7: nutrient-aware portions) ---
    print('\nportion objective knob')
    from nutrition.dri_seed import SEED_DRI_REFERENCES
    from nutrition.nutrient_seed import SEED_DIETARY_NUTRIENTS
    from nutrition.planning_analysis import DEFAULT_FIT_WEIGHTS
    d0 = portion_fit(mgr, 'chicken-bowl-dinner', '', 'dinner', ['demo-alex', 'demo-sam'])
    d1 = portion_fit(mgr, 'chicken-bowl-dinner', '', 'dinner', ['demo-alex', 'demo-sam'], objective='calories')
    check('default objective is calories — the split is byte-identical to the explicit calories fit and '
          'carries no fit lines',
          d0['objective'] == 'calories' and d0['servingSplit'] == d1['servingSplit']
          and not d0['weightsUsed'] and 'fitLines' not in d0['fits'][0], str(d0['servingSplit']))
    bad = portion_fit(mgr, 'chicken-bowl-dinner', '', 'dinner', ['demo-alex'], objective='bogus')
    check('an unknown objective refuses and names the choices', not bad['ok'] and 'nutrients' in bad['error'])
    # the lines the nutrients objective reads: DRI rows (protein target 0.8 g/kg) + a HUMAN
    # override making Alex a high-protein eater (300 g/day — a labelled test override, not advice)
    mgr.objectTables['DietaryNutrient'] = _rows(SEED_DIETARY_NUTRIENTS)
    mgr.objectTables['NutrientReference'] = _rows(list(SEED_DRI_REFERENCES))
    mgr.objectTables['PersonThreshold'] = {'t': SimpleNamespace(
        id='t', name='demo-alex-protein-day', person_name='demo-alex', nutrient_name='protein',
        period='day', min_amount=0.0, target_amount=300.0, max_amount=0.0, unit='g',
        reason='selftest: high-protein training block (a labelled override)', is_prior=False,
        provenance_id='selftest', notes='')}
    var.scale_min, var.scale_max = 0.5, 3.0      # wide bounds so the objectives can differ
    cal = portion_fit(mgr, 'chicken-bowl-dinner', 'chicken-bowl-dinner-base', 'lunch', ['demo-alex'])
    nut = portion_fit(mgr, 'chicken-bowl-dinner', 'chicken-bowl-dinner-base', 'lunch', ['demo-alex'],
                      objective='nutrients')
    nf = nut['fits'][0]
    check('nutrients objective: a high-protein person on the protein-dense bowl gets a LARGER scale than the '
          'calories-only fit (protein pulls up, calories pull down); the driver and the lines are stated',
          nut['ok'] and nf['scale'] > cal['fits'][0]['scale'] and nf['caloriesOnlyScale'] == cal['fits'][0]['scale']
          and nf['fitLines']['protein']['ownIdealScale'] > nf['fitLines']['calories']['ownIdealScale']
          and nf['driver'] == 'protein' and 'protein pulls the portion up' in nf['story']
          and nf['fitLines']['protein']['source'].startswith('person thresholds')
          and nf['fitLines']['calories']['source'] == 'calorie envelope',
          f"cal-only {cal['fits'][0]['scale']} nutrients {nf['scale']} driver={nf['driver']} :: {nf['story']}")
    check('the scale sits on the 0.05 grid inside the bounds; the compromise names the driver with a suggestion',
          abs(nf['scale'] / 0.05 - round(nf['scale'] / 0.05)) < 1e-6 and 0.5 <= nf['scale'] <= 3.0
          and nut['compromises'] and nut['compromises'][0]['driver'] == 'protein'
          and 'protein-rich' in nut['compromises'][0]['suggestion'], str(nut['compromises']))
    check('a nutrient with no line (fiber: no DRI row seeded) is NAMED, never guessed',
          'fiber' in nf['noLine'] and 'fiber' not in nf['fitLines'], str(nf['noLine']))
    w = portion_fit(mgr, 'chicken-bowl-dinner', 'chicken-bowl-dinner-base', 'lunch', ['demo-alex'],
                    objective='nutrients', weights='protein=0.9, sodium:0.2, sugar=1')
    check('weights are a labelled prior, echoed back: overrides applied, the rest default, unknown names named',
          w['weights'] == {**DEFAULT_FIT_WEIGHTS, 'protein': 0.9, 'sodium': 0.2} and w['unknownWeights'] == ['sugar']
          and 'prior' in w['weightsLabel'] and w['weightsUsed']
          and w['fits'][0]['fitLines']['protein']['weight'] == 0.9, str(w['weights']))
    # a sodium-heavy dish: 6 g iodized salt into the 2-serving bowl (~1.2 g sodium per serving)
    mgr.objectTables['PersonThreshold'] = {}
    mgr.objectTables['IngredientLine']['salt'] = SimpleNamespace(
        id='salt', name='chicken-rice-bowl-salt', recipe_name='chicken-rice-bowl', food_name='salt-iodized',
        grams=6.0, method='raw', yield_percent=100.0, retention_code='', prep_note='selftest', order=5,
        is_prior=False, provenance_id='selftest')
    cal2 = portion_fit(mgr, 'chicken-bowl-dinner', 'chicken-bowl-dinner-base', 'lunch', ['demo-alex'])
    salty = portion_fit(mgr, 'chicken-bowl-dinner', 'chicken-bowl-dinner-base', 'lunch', ['demo-alex'],
                        objective='nutrients')
    sf = salty['fits'][0]
    check('a sodium-heavy dish CAPS the scale below the calories-only fit — sodium is a ceiling (excess '
          'penalised, shortfall free) and the story says who caps it',
          sf['scale'] < cal2['fits'][0]['scale'] and sf['fitLines']['sodium']['kind'] == 'ceiling'
          and 'sodium caps it at' in sf['story'] and sf['fitLines']['sodium']['ownIdealScale'] < 1.0
          and sf['fitLines']['sodium']['line'] == round(2300 * 0.35, 1),
          f"cal-only {cal2['fits'][0]['scale']} nutrients {sf['scale']} :: {sf['story']}")
    check('below the ceiling sodium is NOT penalised (the earlier low-salt fit carried a zero sodium term)',
          nf['fitLines']['sodium']['weightedTerm'] == 0 and not nf['fitLines']['sodium']['penalised'])
    del mgr.objectTables['IngredientLine']['salt']
    var.scale_min, var.scale_max = lo, hi

    print(f'\n{len(failures)} failure(s)')
    for f in failures:
        print('  -', f)
    print('PASS: mpc week planning holds together' if not failures else 'FAIL: see above')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
