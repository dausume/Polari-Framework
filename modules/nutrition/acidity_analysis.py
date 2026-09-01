"""
@cross-cutting
@module nutrition.acidity_analysis
@tags @xc:bindings

mpa-1 — MEAL ACIDITY, honestly (MEAL_PLANNING_APP_PLAN.md):

  - per-ingredient pH comes from foodstate's literature pH CLAIMS
    (PropertyClaim rows on '<slug>#as-defined', quantity 'pH' — the
    FDA/CFSAN-lineage approximate-pH table, ranges carried in
    value_json). Foods without a claim are reported UNKNOWN, never
    guessed.
  - the meal metric is the decision-9 ACID MASS SHARE: the fraction
    of the meal's ingredient mass whose pH midpoint sits below the
    FDA 21 CFR 114 acidified-foods boundary (pH 4.6 — the canonical
    high-acid/low-acid line). It feeds the seeded low-confidence
    `meal-acid-share` tolerance row via evaluate_tolerances.
  - NO gastric magnitude claims ride this (fsp D6): direction +
    conditions live in the physiological contract; this module only
    reports composition-side facts + the comfort-flag warning.
  - pH DOES NOT AVERAGE (it is logarithmic and buffered): the meal
    gets NO single combined pH number — the per-ingredient list and
    the share are the honest outputs, and the payload says so.

@consumers
  - nutrition.mealplanning_api, tracking_analysis (per-meal series)
  - nutrition.selftest_acidity
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §mpa-1
"""

import json

from nutrition.person_analysis import _f, _rows
from nutrition.tolerance_analysis import evaluate_tolerances

#: FDA 21 CFR 114: foods with equilibrium pH <= 4.6 are "acid/
#: acidified" — the canonical boundary, cited on every payload.
HIGH_ACID_PH_BOUNDARY = 4.6

_BOUNDARY_CITE = ('FDA 21 CFR 114 acidified-foods boundary (pH 4.6); '
                  'ingredient pH: FDA/CFSAN-lineage approximate-pH '
                  'table claims (foodstate mpa-1)')


def food_ph_claims(manager):
    """{food_slug: {'ph','range','provenance'}} from the literature
    pH PropertyClaims on canonical states."""
    out = {}
    for c in _rows(manager, 'PropertyClaim'):
        if getattr(c, 'property_meaning_name', '') != 'pH':
            continue
        subject = getattr(c, 'subject_state_key', '')
        if not subject.endswith('#as-defined'):
            continue
        slug = subject.split('#', 1)[0]
        entry = {'ph': _f(c, 'value', 0.0),
                 'provenance': getattr(c, 'provenance_id', '')}
        try:
            vj = json.loads(getattr(c, 'value_json', '') or '{}')
            if isinstance(vj.get('range'), list):
                entry['range'] = vj['range']
        except ValueError:
            pass
        out[slug] = entry
    return out


def meal_acidity(manager, portions, person=None):
    """The meal-acidity report for one meal's portions
    ([{'food_name','grams'}]) — acid mass share vs the 4.6 boundary,
    per-ingredient pH facts, unknowns named, and the decision-9
    tolerance warning when the share crosses the seeded row."""
    ph_by_food = food_ph_claims(manager)
    total = 0.0
    acid_mass = 0.0
    ingredients, unknown = [], []
    for p in portions:
        fname = p.get('food_name', '')
        grams = float(p.get('grams', 0.0) or 0.0)
        if grams <= 0:
            continue
        total += grams
        claim = ph_by_food.get(fname)
        if claim is None:
            unknown.append(fname)
            continue
        # 21 CFR 114: pH 4.6 OR BELOW = acid food (inclusive).
        is_acid = claim['ph'] <= HIGH_ACID_PH_BOUNDARY
        straddles = ('range' in claim
                     and claim['range'][0] <= HIGH_ACID_PH_BOUNDARY
                     < claim['range'][1])
        if is_acid:
            acid_mass += grams
        entry = {'food': fname, 'grams': round(grams, 1),
                 'ph': claim['ph'],
                 'highAcid': is_acid}
        if 'range' in claim:
            entry['phRange'] = claim['range']
        if straddles:
            entry['note'] = ('published range straddles the 4.6 '
                             'boundary — classified by midpoint')
        ingredients.append(entry)
    if total <= 0:
        return {'ok': False, 'error': 'no portion mass'}
    share = acid_mass / total
    tolerance = evaluate_tolerances(
        manager, {'meal-acidity': share}, 'meal', person=person)
    return {
        'ok': True, 'schema': 'meal-acidity/1',
        'acidMassShare': round(share, 3),
        'acidMassG': round(acid_mass, 1),
        'totalMassG': round(total, 1),
        'boundary': HIGH_ACID_PH_BOUNDARY,
        'ingredients': sorted(ingredients, key=lambda e: e['ph']),
        'unknownPh': unknown,
        'warnings': tolerance['warnings'],
        'source': _BOUNDARY_CITE,
        'honesty': ('pH is logarithmic and buffered — a meal gets NO '
                    'combined pH number; the share + per-ingredient '
                    'facts are the honest outputs. Comfort flags are '
                    'low-confidence general-population heuristics, '
                    'not medical advice (decision 3/9; fsp D6: no '
                    'gastric magnitude claims).'),
    }


def template_portions(manager, template, variation=None, scale=1.0):
    """Per-meal ingredient portions for a template (the same
    grams-per-meal arithmetic the rollup uses: line grams / recipe
    servings × scale, swaps applied)."""
    try:
        recipes = json.loads(
            getattr(template, 'recipe_names_json', '[]') or '[]')
    except ValueError:
        recipes = []
    swaps = {}
    if variation is not None:
        try:
            for sw in json.loads(
                    getattr(variation, 'swaps_json', '[]') or '[]'):
                swaps[sw.get('from_food', '')] = sw
        except ValueError:
            pass
    servings_by_recipe = {
        getattr(r, 'name', ''): max(1.0, _f(r, 'servings', 1.0))
        for r in _rows(manager, 'Recipe')}
    portions = []
    for line in _rows(manager, 'IngredientLine'):
        rname = getattr(line, 'recipe_name', '')
        if rname not in recipes:
            continue
        fname = getattr(line, 'food_name', '')
        grams = _f(line, 'grams', 0.0)
        if fname in swaps:
            sw = swaps[fname]
            fname = sw.get('to_food', fname)
            if 'grams' in sw:
                grams = float(sw['grams'])
        portions.append({
            'food_name': fname,
            'grams': grams / servings_by_recipe.get(rname, 1.0)
            * scale})
    return portions


def template_acidity(manager, template, variation=None, scale=1.0,
                     person=None):
    """meal_acidity over one template variation's per-meal portions."""
    portions = template_portions(manager, template, variation, scale)
    if not portions:
        return {'ok': False,
                'error': f'template '
                         f'"{getattr(template, "name", "")}" '
                         f'resolves no ingredient lines'}
    report = meal_acidity(manager, portions, person=person)
    if report.get('ok'):
        report['template'] = getattr(template, 'name', '')
        report['variation'] = (getattr(variation, 'name', '')
                               if variation is not None else '')
        report['scale'] = scale
    return report
