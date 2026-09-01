"""
@cross-cutting
@module nutrition.tolerance_analysis
@tags @xc:bindings

nmp-2 — evaluation over the tolerance table: given an intake (a
{substance: amount} mapping for one dose/meal/day), produce WARNINGS
that name the symptom, the threshold, the citation, and the
confidence grade. Warnings never clamp anything — the numbers stay
the person's; the table only speaks (knobs-and-suggestions).

Also the decision-9 glycemic-load helper: GL = GI x available carbs
/ 100 per portion, summed over a meal — GI values are FoodItem knobs
sourced from the published Atkinson 2008 tables (0 = unknown, and
the result says which foods were unknown rather than guessing).

@consumers
  - nutrition.nutrition_api, nmp-4 plan rollups
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-2
"""

from nutrition.person_analysis import _f, _rows


def evaluate_tolerances(manager, intake, period, person=None):
    """Warnings for one exposure window.

    intake: {substance: amount} in each row's unit (callers align
    units; rollups do this from their own provenance-carrying
    sums). period: 'dose' | 'meal' | 'day'. Per-kg rows need a
    person (weight); without one they are skipped and REPORTED as
    skipped rather than silently dropped."""
    warnings, skipped = [], []
    kg = getattr(person, 'weight_kg', 0.0) if person is not None else 0.0
    for row in _rows(manager, 'ToleranceThreshold'):
        if getattr(row, 'period', '') != period:
            continue
        substance = getattr(row, 'substance', '')
        if substance not in intake:
            continue
        amount = intake[substance]
        threshold = _f(row, 'threshold_amount', 0.0)
        if getattr(row, 'per_kg_body_mass', False):
            if kg <= 0:
                skipped.append({
                    'substance': substance,
                    'why': 'per-kg threshold needs a person weight'})
                continue
            threshold = threshold * kg
        # flag rows (threshold 0) warn on any presence
        over = (amount > threshold if threshold > 0
                else bool(amount))
        if not over:
            continue
        warnings.append({
            'substance': substance,
            'symptom': getattr(row, 'symptom', ''),
            'amount': round(amount, 2),
            'threshold': round(threshold, 2),
            'unit': getattr(row, 'unit', ''),
            'period': period,
            'confidence': getattr(row, 'confidence', ''),
            'citation': getattr(row, 'citation', ''),
            'qualifier': getattr(row, 'qualifier', ''),
            'message': (
                f'{substance} {amount:g} {getattr(row, "unit", "")}'
                f' this {period} exceeds the '
                f'{threshold:g} {getattr(row, "unit", "")} the '
                f'literature associates with '
                f'{getattr(row, "symptom", "effects")}'),
        })
    order = {'ul-grade': 0, 'moderate': 1, 'low': 2}
    warnings.sort(key=lambda w: order.get(w['confidence'], 3))
    return {'ok': True, 'period': period, 'warnings': warnings,
            'skipped': skipped,
            'honesty': 'warnings name their evidence grade; nothing '
                       'is clamped or blocked — general-population '
                       'comfort thresholds, not medical advice'}


def meal_glycemic_load(manager, portions):
    """Decision 9: GL for one meal.

    portions: [{'food_name', 'grams'}]. Uses each FoodItem's
    gi_value knob (Atkinson 2008 values; 0 = unknown) and its
    carbohydrate NutrientContent per 100 g. Returns the summed GL,
    the per-food contributions, and the foods honestly skipped for
    lacking a GI value or carb row."""
    foods = {getattr(f, 'name', ''): f
             for f in _rows(manager, 'FoodItem')}
    carbs = {}
    for c in _rows(manager, 'NutrientContent'):
        if getattr(c, 'nutrient_name', '') == 'carbohydrate':
            carbs[getattr(c, 'food_name', '')] = \
                _f(c, 'amount_per_100g', 0.0)
    total, parts, unknown = 0.0, [], []
    for p in portions:
        fname = p.get('food_name', '')
        grams = float(p.get('grams', 0.0) or 0.0)
        food = foods.get(fname)
        gi = _f(food, 'gi_value', 0.0) if food is not None else 0.0
        carb100 = carbs.get(fname, 0.0)
        if food is None or gi <= 0 or carb100 <= 0:
            unknown.append({
                'food': fname,
                'why': ('no such food' if food is None
                        else 'no GI value published/seeded' if gi <= 0
                        else 'no carbohydrate row')})
            continue
        carbs_g = carb100 * grams / 100.0
        gl = gi * carbs_g / 100.0
        total += gl
        parts.append({'food': fname, 'grams': grams,
                      'gi': gi, 'carbsG': round(carbs_g, 1),
                      'gl': round(gl, 1)})
    return {'ok': True, 'glycemicLoad': round(total, 1),
            'contributions': parts, 'unknown': unknown,
            'highConvention': 20.0,
            'source': 'GI values: Atkinson, Foster-Powell & '
                      'Brand-Miller 2008 international tables '
                      '(published paper, not the Sydney database)'}
