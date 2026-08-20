"""
@cross-cutting
@module nutrition.recipe_analysis
@tags @xc:bindings

nmp-3 — the recipe-nutrition rollup: per ingredient line,
FDC per-100g x raw grams -> raw amounts; the line's R6 retention
row scales the nutrients R6 covers (vitamins/minerals — the USDA
true-retention method: retained nutrient = raw amount x
retention%); the line's YIELD percent scales the cooked MASS.
Macros (protein/carbs/fat/calories) have no R6 rows — kept at the
raw amount with the gap named (fat rendering losses are real for
meats; the yields table's fat-change column is a later refinement).
Every nutrient in the result carries its provenance label.

This is the build-ourselves engine nothing OSS provides
(plan §research): FDC match + retention/yield, per serving.

@consumers
  - nutrition.nutrition_api, nmp-4 meal templates + rollups
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-3
"""

from nutrition.person_analysis import _f, _rows
from nutrition import vendor_data

# canonical nutrient -> R6 nutrient_code, for the codes R6 actually
# carries (301..432 family; R6 has NO rows for energy/macros, vit D,
# vit E, vit K, selenium, iodine, chromium, molybdenum — those keep
# their raw values, labeled).
R6_CODE_BY_NUTRIENT = {
    'calcium': '301', 'iron': '303', 'magnesium': '304',
    'potassium': '306', 'sodium': '307', 'zinc': '309',
    'copper': '312', 'vitamin-c': '401', 'vitamin-b1': '404',
    'vitamin-b2': '405', 'vitamin-b3': '406', 'vitamin-b6': '415',
    'vitamin-b9': '417', 'vitamin-b12': '418',
}

_retention_cache = {}


def retention_rows(code):
    """{nutrient_code: percent} for one R6 retention code."""
    if not _retention_cache:
        for r in vendor_data.retention_factors():
            pct = (r['retention_percent'] or '').strip()
            if not pct:
                continue
            _retention_cache.setdefault(r['retention_code'], {})[
                r['nutrient_code']] = float(pct)
    return _retention_cache.get(code, {})


def retention_description(code):
    for r in vendor_data.retention_factors():
        if r['retention_code'] == code:
            return r['retention_description']
    return ''


def retention_candidates(query):
    """R6 codes whose description contains the query (UI helper for
    picking a line's retention_code — honest search, no guessing)."""
    q = query.upper()
    out, seen = [], set()
    for r in vendor_data.retention_factors():
        code = r['retention_code']
        if code in seen or q not in r['retention_description']:
            continue
        seen.add(code)
        out.append({'code': code,
                    'description': r['retention_description']})
    return out


def recipe_nutrition(manager, recipe):
    """Per-serving nutrition for one Recipe, provenance-labeled."""
    rname = getattr(recipe, 'name', '')
    servings = max(1.0, _f(recipe, 'servings', 1.0))
    lines = sorted(
        [l for l in _rows(manager, 'IngredientLine')
         if getattr(l, 'recipe_name', '') == rname],
        key=lambda l: getattr(l, 'order', 0))
    if not lines:
        return {'ok': False,
                'error': f'recipe "{rname}" has no ingredient lines'}
    contents = {}
    units = {}
    for c in _rows(manager, 'NutrientContent'):
        contents.setdefault(getattr(c, 'food_name', ''), {})[
            getattr(c, 'nutrient_name', '')] = \
            _f(c, 'amount_per_100g', 0.0)
        units[getattr(c, 'nutrient_name', '')] = getattr(c, 'unit', '')
    foods = {getattr(f, 'name', ''): f
             for f in _rows(manager, 'FoodItem')}
    totals, labels, line_reports = {}, {}, []
    cooked_mass = 0.0
    for line in lines:
        fname = getattr(line, 'food_name', '')
        grams = _f(line, 'grams', 0.0)
        method = getattr(line, 'method', 'raw')
        yld = _f(line, 'yield_percent', 100.0) or 100.0
        code = getattr(line, 'retention_code', '') or ''
        food_contents = contents.get(fname)
        if food_contents is None:
            line_reports.append({
                'food': fname, 'grams': grams,
                'error': 'no NutrientContent rows for this food'})
            continue
        ret = retention_rows(code) if code else {}
        cooked_mass += grams * yld / 100.0
        applied, kept_raw = [], []
        for nut, per100 in food_contents.items():
            raw_amt = per100 * grams / 100.0
            r6code = R6_CODE_BY_NUTRIENT.get(nut)
            if code and r6code and r6code in ret:
                amt = raw_amt * ret[r6code] / 100.0
                applied.append(nut)
                label = f'cooked (R6 {code} retention applied)'
            else:
                amt = raw_amt
                if method != 'raw':
                    kept_raw.append(nut)
                    label = ('cooked, raw value kept (no R6 row '
                             'for this nutrient)')
                else:
                    label = 'raw'
            totals[nut] = totals.get(nut, 0.0) + amt
            prev = labels.get(nut)
            labels[nut] = label if prev in (None, label) else 'mixed'
        line_reports.append({
            'food': fname, 'grams': grams, 'method': method,
            'yieldPercent': yld,
            'cookedMassG': round(grams * yld / 100.0, 1),
            'retentionCode': code,
            'retentionDescription':
                retention_description(code) if code else '',
            'nutrientsWithRetention': sorted(applied),
            'nutrientsKeptRaw': sorted(kept_raw),
        })
    per_serving = {
        nut: {'amount': round(val / servings, 3),
              'unit': units.get(nut, ''),
              'provenance': labels.get(nut, 'raw')}
        for nut, val in sorted(totals.items())}
    return {
        'ok': True, 'recipe': rname, 'servings': servings,
        'cookedMassG': round(cooked_mass, 1),
        'perServingMassG': round(cooked_mass / servings, 1),
        'perServing': per_serving,
        'total': {nut: round(val, 3)
                  for nut, val in sorted(totals.items())},
        'lines': line_reports,
        'honesty': 'macros keep raw values (R6 covers vitamins/'
                   'minerals only; meat fat-rendering is a named '
                   'gap); retention applies the USDA true-retention '
                   'method per line',
    }
