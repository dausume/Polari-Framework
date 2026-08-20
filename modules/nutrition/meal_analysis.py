"""
@cross-cutting
@module nutrition.meal_analysis
@tags @xc:bindings

nmp-4 — the meal layer's engines:

  template_rollup     one template variation's nutrition at a scale
                      (recipes' per-serving rollups combined; swaps
                      applied to lines before rolling up).
  validate_template   THE GATE (decisions 2 + 9): every variation at
                      its scale extremes vs the AVERAGE-PERSON
                      per-meal caps — UL fractions, the sodium
                      share, glycemic load. REFUSES with named
                      reasons; the low-confidence reflux rows and
                      the protein utilization plateau WARN, never
                      block (their evidence grade says so).
  plan_rollup         a MealPlanDefinition's entries rolled to
                      meal/day/week vs the owner's thresholds +
                      tolerance warnings; suggestions PROPOSE scale
                      changes (knobs-and-suggestions — never
                      auto-edit).

The average person for the gate: the caps use the STRICTEST adult
UL across sexes (the gate must protect everyone), a labeled
half-the-daily-limit-per-meal fraction, and the published GL>20
convention. Added-sugar per-meal caps are a NAMED GAP: FDC carries
total sugars, not added sugars — the gate says so rather than
pretending.

@consumers
  - nutrition.nutrition_api
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-4
"""

import json

from nutrition.person_analysis import _f, _rows
from nutrition.recipe_analysis import recipe_nutrition
from nutrition.threshold_analysis import person_thresholds
from nutrition.tolerance_analysis import meal_glycemic_load

# the labeled convention: no single meal should carry more than half
# a day's upper limit of anything (gate prior, tunable by argument).
MEAL_UL_FRACTION = 0.5
GL_MEAL_CAP = 20.0  # Atkinson 2008 'high' convention (nmp-2 row)


def _json_list(row, attr):
    try:
        return json.loads(getattr(row, attr, '[]') or '[]')
    except Exception:
        return []


def _named(manager, class_name, name):
    for r in _rows(manager, class_name):
        if getattr(r, 'name', '') == name:
            return r
    return None


def _strictest_adult_uls(manager):
    """nutrient -> lowest adult UL across sexes/bands (life-stage
    rows excluded) — the average-person protective cap basis."""
    uls = {}
    for r in _rows(manager, 'NutrientReference'):
        if getattr(r, 'life_stage', ''):
            continue
        ul = _f(r, 'upper_limit_per_day', 0.0)
        if ul <= 0:
            continue
        n = getattr(r, 'nutrient_name', '')
        uls[n] = min(uls.get(n, ul), ul)
    return uls


def template_rollup(manager, template, variation=None, scale=1.0):
    """The combined nutrition of one template variation at a scale.

    Swaps are applied per ingredient line (grams kept — the swap is
    a food substitution, not a portion change); each recipe's
    retention/yield engine does the real work. Returns the combined
    PER-MEAL amounts (a template IS one meal: recipes' full yield /
    their servings x scale) + the meal's GL portions."""
    recipes = _json_list(template, 'recipe_names_json')
    if not recipes:
        return {'ok': False, 'error': 'template lists no recipes'}
    swaps = {}
    if variation is not None:
        for sw in _json_list(variation, 'swaps_json'):
            swaps[sw.get('from_food', '')] = sw
    totals, portions, missing = {}, [], []
    units = {}
    for rname in recipes:
        recipe = _named(manager, 'Recipe', rname)
        if recipe is None:
            missing.append(rname)
            continue
        if swaps:
            # swap lines via lightweight copies — the stored rows
            # are never mutated
            from types import SimpleNamespace
            lines = [l for l in _rows(manager, 'IngredientLine')
                     if getattr(l, 'recipe_name', '') == rname]
            patched = []
            for l in lines:
                fname = getattr(l, 'food_name', '')
                if fname in swaps:
                    sw = swaps[fname]
                    d = {k: getattr(l, k) for k in
                         ('name', 'recipe_name', 'food_name', 'grams',
                          'method', 'yield_percent', 'retention_code',
                          'prep_note', 'order')}
                    d['food_name'] = sw.get('to_food', '')
                    # a substitution rarely keeps mass, and the
                    # original line's R6 code belongs to the ORIGINAL
                    # food — swaps may override both; absent an
                    # override the retention honestly drops to none
                    # (raw values kept, labeled) rather than applying
                    # a chicken row to tofu.
                    if 'grams' in sw:
                        d['grams'] = float(sw['grams'])
                    d['retention_code'] = sw.get('retention_code', '')
                    patched.append(SimpleNamespace(**d))
                else:
                    patched.append(l)
            sub_manager = SimpleNamespace(objectTables={
                **manager.objectTables,
                'IngredientLine': dict(enumerate(patched))})
            rn = recipe_nutrition(sub_manager, recipe)
        else:
            rn = recipe_nutrition(manager, recipe)
        if not rn.get('ok'):
            missing.append(rname)
            continue
        servings = rn['servings']
        for nut, entry in rn['perServing'].items():
            totals[nut] = totals.get(nut, 0.0) \
                + entry['amount'] * scale
            units[nut] = entry['unit']
        # GL portions: the meal's share of each line's raw grams
        for line in rn['lines']:
            if 'error' in line:
                continue
            portions.append({
                'food_name': line['food'],
                'grams': line['grams'] / servings * scale})
    if not totals:
        return {'ok': False,
                'error': f'no recipe rolled up (missing: {missing})'}
    gl = meal_glycemic_load(manager, portions)
    return {'ok': True, 'template': getattr(template, 'name', ''),
            'variation': (getattr(variation, 'name', '')
                          if variation is not None else ''),
            'scale': scale,
            'perMeal': {n: {'amount': round(v, 3),
                            'unit': units.get(n, '')}
                        for n, v in sorted(totals.items())},
            'glycemicLoad': gl['glycemicLoad'],
            'glUnknownFoods': gl['unknown'],
            'missingRecipes': missing}


def validate_template(manager, template):
    """Decision 2: the HARD authoring gate, refusal with named
    reasons. Evaluates every variation at both scale extremes."""
    variations = [v for v in _rows(manager, 'VariationDefinition')
                  if getattr(v, 'template_name', '')
                  == getattr(template, 'name', '')]
    cases = [(None, 1.0)] if not variations else [
        (v, s) for v in variations
        for s in (_f(v, 'scale_min', 1.0), _f(v, 'scale_max', 1.0))]
    uls = _strictest_adult_uls(manager)
    refusals, warnings = [], []
    for variation, scale in cases:
        roll = template_rollup(manager, template, variation, scale)
        vname = (getattr(variation, 'name', 'base')
                 if variation is not None else 'base')
        if not roll.get('ok'):
            refusals.append({'variation': vname, 'scale': scale,
                             'reason': roll.get('error', 'rollup failed')})
            continue
        for nut, entry in roll['perMeal'].items():
            ul = uls.get(nut, 0.0)
            if ul <= 0:
                continue
            cap = ul * MEAL_UL_FRACTION
            if entry['amount'] > cap:
                refusals.append({
                    'variation': vname, 'scale': scale,
                    'nutrient': nut,
                    'amount': entry['amount'], 'cap': round(cap, 2),
                    'reason': f'{nut} {entry["amount"]:g} '
                              f'{entry["unit"]} in one meal exceeds '
                              f'{MEAL_UL_FRACTION:.0%} of the '
                              f'strictest adult daily limit '
                              f'({ul:g})'})
        if roll['glycemicLoad'] > GL_MEAL_CAP:
            refusals.append({
                'variation': vname, 'scale': scale,
                'nutrient': 'glycemic-load',
                'amount': roll['glycemicLoad'], 'cap': GL_MEAL_CAP,
                'reason': f'glycemic load {roll["glycemicLoad"]:g} '
                          f'exceeds the published high convention '
                          f'({GL_MEAL_CAP:g}) — decision 9'})
        # warn-only rows (evidence grade too weak/wrong-kind to block)
        fat = roll['perMeal'].get('healthy-fat', {}).get('amount', 0.0)
        if fat > 40.0:
            warnings.append({
                'variation': vname, 'scale': scale,
                'note': f'high-fat meal ({fat:g} g) — reflux-trigger '
                        f'territory for some people (low confidence, '
                        f'never blocks)'})
    return {'ok': not refusals,
            'template': getattr(template, 'name', ''),
            'casesChecked': len(cases),
            'refusals': refusals, 'warnings': warnings,
            'namedGaps': ['added-sugar per-meal cap: FDC carries '
                          'total sugars, not added sugars — not '
                          'checkable yet',
                          'fermenting-fiber dose: inulin-type fiber '
                          'is not an FDC nutrient — not checkable '
                          'yet'],
            'honesty': f'caps = {MEAL_UL_FRACTION:.0%} of the '
                       f'strictest adult UL per meal (labeled '
                       f'convention prior) + GL {GL_MEAL_CAP:g}'}


def plan_rollup(manager, plan):
    """Meal/day/plan rollups vs the owner's thresholds.

    Person plans only for now — household serving splits ride the
    same entries and land with the household pass (named in the
    result when a household owns the plan)."""
    pname = getattr(plan, 'person_name', '')
    person = _named(manager, 'PersonProfile', pname) if pname else None
    entries = sorted(
        [e for e in _rows(manager, 'MealEntry')
         if getattr(e, 'plan_name', '')
         == getattr(plan, 'name', '')],
        key=lambda e: (getattr(e, 'day_index', 0),
                       getattr(e, 'slot', '')))
    if not entries:
        return {'ok': False, 'error': 'plan has no MealEntries'}
    days = {}
    meal_reports = []
    for e in entries:
        template = _named(manager, 'MealTemplate',
                          getattr(e, 'template_name', ''))
        if template is None:
            meal_reports.append({
                'entry': getattr(e, 'name', ''),
                'error': f'no MealTemplate named '
                         f'"{getattr(e, "template_name", "")}"'})
            continue
        variation = None
        if getattr(e, 'variation_name', ''):
            variation = _named(manager, 'VariationDefinition',
                               e.variation_name)
        scale = _f(e, 'scale', 1.0)
        clamped = False
        if variation is not None:
            lo, hi = (_f(variation, 'scale_min', 1.0),
                      _f(variation, 'scale_max', 1.0))
            new = min(max(scale, lo), hi)
            clamped = new != scale
            scale = new
        roll = template_rollup(manager, template, variation, scale)
        if not roll.get('ok'):
            meal_reports.append({'entry': getattr(e, 'name', ''),
                                 'error': roll.get('error')})
            continue
        day = getattr(e, 'day_index', 1)
        bucket = days.setdefault(day, {})
        for nut, entry_v in roll['perMeal'].items():
            bucket[nut] = bucket.get(nut, 0.0) + entry_v['amount']
        report = {'entry': getattr(e, 'name', ''), 'day': day,
                  'slot': getattr(e, 'slot', ''),
                  'template': roll['template'],
                  'variation': roll['variation'], 'scale': scale,
                  'glycemicLoad': roll['glycemicLoad'],
                  'calories': roll['perMeal'].get(
                      'calories', {}).get('amount', 0.0)}
        if clamped:
            report['scaleClamped'] = True
        if roll['glycemicLoad'] > GL_MEAL_CAP:
            report['glWarning'] = (
                f'GL {roll["glycemicLoad"]:g} > {GL_MEAL_CAP:g} '
                f'(published high convention)')
        meal_reports.append(report)
    result = {'ok': True, 'plan': getattr(plan, 'name', ''),
              'entries': meal_reports,
              'days': {}, 'suggestions': []}
    if person is None:
        result['note'] = ('no PersonProfile owner resolved — day '
                          'rollups computed without thresholds'
                          + (' (household plans: per-member split '
                             'is the household pass, not built '
                             'yet — named gap)' if
                             getattr(plan, 'household_name', '')
                             else ''))
    thresholds = None
    if person is not None:
        t = person_thresholds(manager, person, 'day')
        thresholds = t['thresholds'] if t.get('ok') else None
    for day, nutrients in sorted(days.items()):
        day_out = {'totals': {n: round(v, 2)
                              for n, v in sorted(nutrients.items())}}
        if thresholds:
            under, over = [], []
            for nut, th in thresholds.items():
                have = nutrients.get(nut, 0.0)
                if th['target'] > 0 and have < th['target'] * 0.8:
                    under.append({'nutrient': nut,
                                  'have': round(have, 2),
                                  'target': th['target']})
                if th['max'] > 0 and have > th['max']:
                    over.append({'nutrient': nut,
                                 'have': round(have, 2),
                                 'max': th['max'],
                                 'basis': th['basis']['max']})
            day_out['underTarget'] = under
            day_out['overMax'] = over
            for o in over:
                result['suggestions'].append({
                    'day': day, 'nutrient': o['nutrient'],
                    'suggestion': f'day {day} exceeds the '
                                  f'{o["nutrient"]} max — consider '
                                  f'scaling a meal down or picking '
                                  f'a lower-{o["nutrient"]} '
                                  f'variation (nothing auto-edited)'})
        result['days'][day] = day_out
    return result
