"""
@cross-cutting
@module nutrition.exclusion_analysis
@tags @xc:bindings

mpb-1 — the exclusion filter: a person's declared exclusions
resolved against the allergen flags, then every meal-planning
surface screens through it. Hard exclusions REFUSE with the
violation NAMED (food, allergen class, the person's own stated
reason); soft ones rank down with a note. Absence honesty: a food
with NO flag rows is reported unverified for allergen screening,
never silently passed as safe.

@consumers
  - nutrition.mealplanning_api, affinity composer callers
  - nutrition.selftest_exclusion
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-1
"""

from nutrition.acidity_analysis import template_portions
from nutrition.exclusion_basis import ALLERGEN_CLASSES
from nutrition.meal_analysis import _named
from nutrition.person_analysis import _f, _rows

_BOUNDARY = ('exclusions are DECLARED by the person, never '
             'inferred or diagnosed; flags are food-identity '
             'facts — cross-contact and processing contamination '
             'are OUT of scope and unverified here')


def person_exclusions(manager, person_name):
    """The person's declared rows, split hard/soft."""
    hard, soft = [], []
    for row in _rows(manager, 'PersonExclusion'):
        if getattr(row, 'person_name', '') != person_name:
            continue
        entry = {
            'name': getattr(row, 'name', ''),
            'allergenClass': getattr(row, 'allergen_class', ''),
            'food': getattr(row, 'food_name', ''),
            'severity': getattr(row, 'severity', ''),
            'statedReason': getattr(row, 'stated_reason', ''),
        }
        (soft if entry['severity'] == 'preference-soft'
         else hard).append(entry)
    return hard, soft


def _flags_by_food(manager):
    flags = {}
    for row in _rows(manager, 'FoodAllergenFlag'):
        flags.setdefault(getattr(row, 'food_name', ''), []).append(
            getattr(row, 'allergen_class', ''))
    return flags


def screen_foods(manager, person_name, food_names):
    """Screen a list of foods for one person.

    Returns hard violations (food × matched exclusion), soft
    notes, and the foods with NO flag rows at all (unverified —
    named, not passed silently)."""
    hard, soft = person_exclusions(manager, person_name)
    flags = _flags_by_food(manager)
    violations, notes, unflagged = [], [], []
    for food in sorted(set(food_names)):
        food_classes = flags.get(food)
        if food_classes is None:
            unflagged.append(food)
            food_classes = []
        for rule_set, sink in ((hard, violations), (soft, notes)):
            for rule in rule_set:
                matched = (
                    (rule['food'] and rule['food'] == food)
                    or (rule['allergenClass']
                        and rule['allergenClass'] in food_classes))
                if matched:
                    sink.append({
                        'food': food,
                        'matched': rule['allergenClass']
                        or rule['food'],
                        'severity': rule['severity'],
                        'statedReason': rule['statedReason'],
                    })
    return {'ok': True, 'person': person_name,
            'violations': violations, 'softNotes': notes,
            'unflaggedFoods': unflagged,
            'boundary': _BOUNDARY}


def screen_template(manager, person_name, template_name,
                    variation_name=''):
    """One template variation vs one person's exclusions."""
    template = _named(manager, 'MealTemplate', template_name)
    if template is None:
        return {'ok': False,
                'error': f'no MealTemplate "{template_name}"'}
    variation = (_named(manager, 'VariationDefinition',
                        variation_name)
                 if variation_name else None)
    portions = template_portions(manager, template, variation)
    if not portions:
        return {'ok': False,
                'error': f'template "{template_name}" resolves no '
                         f'ingredient lines'}
    screen = screen_foods(manager, person_name,
                          [p['food_name'] for p in portions])
    screen.update({'template': template_name,
                   'variation': variation_name,
                   'safeForPerson': not screen['violations']})
    return screen


def screen_plan(manager, plan, person_name=None):
    """Every entry of a plan vs the owner's (or a named person's)
    exclusions — the per-entry verdicts a planner page shows."""
    person = person_name or getattr(plan, 'person_name', '')
    if not person:
        return {'ok': False,
                'error': 'no person to screen for — plan has no '
                         'person owner and none was named'}
    entries = [e for e in _rows(manager, 'MealEntry')
               if getattr(e, 'plan_name', '')
               == getattr(plan, 'name', '')]
    if not entries:
        return {'ok': False, 'error': 'plan has no MealEntries'}
    reports, violating = [], 0
    for entry in sorted(entries,
                        key=lambda e: (getattr(e, 'day_index', 0),
                                       getattr(e, 'slot', ''))):
        screen = screen_template(
            manager, person, getattr(entry, 'template_name', ''),
            getattr(entry, 'variation_name', ''))
        report = {'entry': getattr(entry, 'name', ''),
                  'day': getattr(entry, 'day_index', 0),
                  'slot': getattr(entry, 'slot', '')}
        if not screen.get('ok'):
            report['error'] = screen.get('error')
        else:
            report['safeForPerson'] = screen['safeForPerson']
            report['violations'] = screen['violations']
            report['softNotes'] = screen['softNotes']
            if not screen['safeForPerson']:
                violating += 1
        reports.append(report)
    hard, soft = person_exclusions(manager, person)
    return {'ok': True, 'schema': 'plan-exclusion-screen/1',
            'plan': getattr(plan, 'name', ''), 'person': person,
            'declaredExclusions': {'hard': hard, 'soft': soft},
            'entries': reports,
            'entriesViolating': violating,
            'verdict': ('every entry clears the declared '
                        'exclusions' if violating == 0 else
                        f'{violating} entries VIOLATE a declared '
                        f'hard exclusion — swap or re-plan them '
                        f'(the plan stays yours; nothing is '
                        f'auto-edited)'),
            'boundary': _BOUNDARY}


def exclusion_safe_swaps(manager, plan, person_name=None):
    """For each violating entry: sibling variations that clear the
    person's exclusions — suggestions with reasons, never applied."""
    screen = screen_plan(manager, plan, person_name)
    if not screen.get('ok'):
        return screen
    person = screen['person']
    suggestions = []
    for report in screen['entries']:
        if report.get('safeForPerson', True):
            continue
        entry = _named(manager, 'MealEntry', report['entry'])
        tname = getattr(entry, 'template_name', '')
        for variation in _rows(manager, 'VariationDefinition'):
            if getattr(variation, 'template_name', '') != tname:
                continue
            vname = getattr(variation, 'name', '')
            if vname == getattr(entry, 'variation_name', ''):
                continue
            alt = screen_template(manager, person, tname, vname)
            if alt.get('ok') and alt['safeForPerson']:
                suggestions.append({
                    'entry': report['entry'],
                    'switchToVariation': vname,
                    'because': f'clears the declared exclusion '
                               f'that {report["violations"][0]["food"]} '
                               f'violates',
                    'appliedBy': 'you — suggestions never edit '
                                 'the plan'})
    return {'ok': True, 'schema': 'exclusion-swaps/1',
            'plan': screen['plan'], 'person': person,
            'suggestions': suggestions,
            'entriesViolating': screen['entriesViolating'],
            'note': ('' if suggestions or
                     not screen['entriesViolating'] else
                     'no existing variation clears the exclusion — '
                     'authoring a new variation is the fix'),
            'boundary': _BOUNDARY}


def validate_exclusion_row(row):
    """Authoring honesty for PersonExclusion rows (CRUDE-side
    helper): exactly one target, a known class, a stated reason."""
    allergen = getattr(row, 'allergen_class', '')
    food = getattr(row, 'food_name', '')
    problems = []
    if bool(allergen) == bool(food):
        problems.append('exactly ONE of allergen_class / food_name '
                        'must be set')
    if allergen and allergen not in ALLERGEN_CLASSES:
        problems.append(f'unknown allergen class "{allergen}" — '
                        f'one of {list(ALLERGEN_CLASSES)}')
    if not getattr(row, 'stated_reason', ''):
        problems.append('stated_reason is required — the '
                        'declaration is the person\'s, in their '
                        'words')
    return {'ok': not problems, 'problems': problems}
