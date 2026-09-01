"""
@cross-cutting
@module nutrition.person_analysis
@tags @xc:bindings

nut-3 math — BMR / TDEE / calorie target / per-nutrient needs for a
PersonProfile. Duck-typed manager (anything with .objectTables) so
selftests run stdlib-only.

BMR: Mifflin-St Jeor by default; Katch-McArdle when body_fat_fraction
is set (more accurate — recommended via a suggestion when absent).
metabolism_factor scales BMR (the thyroid/genetic knob). TDEE = BMR ×
PAL(activity). Calorie target adjusts TDEE for the weight goal, clamped
to a safe floor (never below BMR × SAFETY_FLOOR) — a breach WARNS
rather than starving (knobs-and-suggestions). Per-nutrient needs scale
from nut-1 NutrientReference rows (matched to the person's sex/age
band), with protein per-kg and calories computed.

@consumers
  - nutrition.household_analysis, nutrition.fulfillment_analysis
  - nutrition.person_api
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-3
"""

from nutrition.person_basis import ACTIVITY_PAL

#: kcal per kg of body fat (the deficit-to-weight-loss conversion).
KCAL_PER_KG_FAT = 7700.0
#: Never target below BMR × this (safe-deficit floor).
SAFETY_FLOOR = 1.0
DAYS_PER_WEEK = 7.0
DAYS_PER_MONTH = 30.0
PERIOD_DAYS = {'day': 1.0, 'week': DAYS_PER_WEEK, 'month': DAYS_PER_MONTH}


def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) \
        else list(table)


def _f(row, attr, default=0.0):
    value = getattr(row, attr, default)
    try:
        return float(default if value is None else value)
    except (TypeError, ValueError):
        return float(default)


def bmr(person):
    """Basal metabolic rate (kcal/day) + how it was derived.

    Returns {'value', 'formula', 'metabolismFactor', 'suggestion'?}."""
    weight = _f(person, 'weight_kg', 70.0)
    height = _f(person, 'height_cm', 170.0)
    age = _f(person, 'age_years', 30.0)
    sex = getattr(person, 'sex', 'any')
    factor = _f(person, 'metabolism_factor', 1.0) or 1.0
    body_fat = _f(person, 'body_fat_fraction', 0.0)

    suggestion = None
    if body_fat and 0.0 < body_fat < 0.75:
        # Katch-McArdle: 370 + 21.6 × lean mass (kg).
        lean = weight * (1.0 - body_fat)
        base = 370.0 + 21.6 * lean
        formula = 'Katch-McArdle (lean mass)'
    else:
        # Mifflin-St Jeor.
        base = 10.0 * weight + 6.25 * height - 5.0 * age
        base += 5.0 if sex == 'male' else (-161.0 if sex == 'female'
                                           else -78.0)  # 'any' = midpoint
        formula = 'Mifflin-St Jeor'
        suggestion = {
            'knob': 'PersonProfile.body_fat_fraction',
            'action': 'set body_fat_fraction for a more accurate '
                      'Katch-McArdle BMR',
            'evidence': 'lean-mass BMR is more accurate than a '
                        'height/weight estimate'}
    return {'value': round(base * factor, 1), 'formula': formula,
            'metabolismFactor': factor, 'suggestion': suggestion}


# nmp-1 (decision 6): mid-band MET conventions for the ASKED weekly
# minutes — moderate activity spans 3-6 METs, vigorous 6+ (2024 Adult
# Compendium bands); 4 and 8 are labeled mid-band priors, and the
# arithmetic is the standard kcal = MET x kg x hours with the resting
# 1 MET netted out (the sedentary baseline already pays for rest).
MET_MODERATE_PRIOR = 4.0
MET_VIGOROUS_PRIOR = 8.0
SEDENTARY_PAL = 1.2


def tdee(person):
    """Total daily energy expenditure (kcal/day).

    Two labeled modes: when the profile carries weekly exercise
    MINUTES (decision 6 — the felt-terms question), TDEE = BMR x
    sedentary PAL + net exercise kcal from the minutes; otherwise
    the abstract activity_level PAL guess (the nut-3 original)."""
    base = bmr(person)
    mod = max(0.0, getattr(person, 'weekly_moderate_minutes', 0.0) or 0.0)
    vig = max(0.0, getattr(person, 'weekly_vigorous_minutes', 0.0) or 0.0)
    if mod > 0 or vig > 0:
        kg = getattr(person, 'weight_kg', 70.0)
        extra_per_day = (
            (MET_MODERATE_PRIOR - 1.0) * kg * (mod / 60.0)
            + (MET_VIGOROUS_PRIOR - 1.0) * kg * (vig / 60.0)) / 7.0
        value = base['value'] * SEDENTARY_PAL + extra_per_day
        return {'value': round(value, 1), 'pal': SEDENTARY_PAL,
                'activityLevel': 'from-weekly-minutes',
                'mode': 'minutes',
                'weeklyModerateMinutes': mod,
                'weeklyVigorousMinutes': vig,
                'exerciseKcalPerDay': round(extra_per_day, 1),
                'metPriors': {'moderate': MET_MODERATE_PRIOR,
                              'vigorous': MET_VIGOROUS_PRIOR},
                'bmr': base['value'], 'bmrFormula': base['formula']}
    activity = getattr(person, 'activity_level', 'moderate')
    pal = ACTIVITY_PAL.get(activity, 1.55)
    return {'value': round(base['value'] * pal, 1), 'pal': pal,
            'activityLevel': activity, 'mode': 'pal',
            'bmr': base['value'],
            'bmrFormula': base['formula']}


def calorie_target(person):
    """Daily calorie target for the person's goal, clamped safe.

    Returns {'value', 'tdee', 'goal', 'deltaKcal', 'floor', 'warning'?}.
    A lose goal subtracts the deficit implied by goal_rate_kg_per_week;
    if that would drop below BMR × SAFETY_FLOOR, it clamps and WARNS."""
    energy = tdee(person)
    base = bmr(person)
    goal = getattr(person, 'goal', 'maintain')
    rate = _f(person, 'goal_rate_kg_per_week', 0.5)
    daily_delta = (rate * KCAL_PER_KG_FAT) / DAYS_PER_WEEK
    if goal == 'lose':
        target = energy['value'] - daily_delta
        delta = -daily_delta
    elif goal == 'gain':
        target = energy['value'] + daily_delta
        delta = daily_delta
    else:
        target, delta = energy['value'], 0.0
    floor = base['value'] * SAFETY_FLOOR
    warning = None
    if target < floor:
        warning = {
            'knob': 'PersonProfile.goal_rate_kg_per_week',
            'action': f'slow the target pace — {rate} kg/week needs a '
                      f'deficit that drops intake below BMR',
            'evidence': f'requested target {target:.0f} kcal < BMR floor '
                        f'{floor:.0f} kcal/day'}
        target = floor
    return {'value': round(target, 1), 'tdee': energy['value'],
            'bmr': base['value'], 'goal': goal,
            'deltaKcal': round(delta, 1), 'floor': round(floor, 1),
            'warning': warning}


def _reference_for(manager, nutrient_name, sex, age):
    """Best-matching NutrientReference: exact sex + age band, else 'any',
    else any band for the nutrient.

    nmp-0: pregnancy/lactation rows (life_stage != '') exist in the
    table now — they are EXCLUDED here so a general band never
    resolves to them; the pregnant_or_lactating handling stays the
    nut-3 multiplier until nmp-1 plumbs the life-stage choice."""
    def _general(r):
        return not getattr(r, 'life_stage', '')
    candidates = [r for r in _rows(manager, 'NutrientReference')
                  if getattr(r, 'nutrient_name', '') == nutrient_name
                  and _general(r)
                  and _f(r, 'age_min', 0) <= age <= _f(r, 'age_max', 999)]
    if not candidates:
        candidates = [r for r in _rows(manager, 'NutrientReference')
                      if getattr(r, 'nutrient_name', '') == nutrient_name
                      and _general(r)]
    if not candidates:
        return None
    for r in candidates:
        if getattr(r, 'sex', 'any') == sex:
            return r
    for r in candidates:
        if getattr(r, 'sex', 'any') == 'any':
            return r
    return candidates[0]


def nutrient_needs(manager, person, period='day'):
    """Per-nutrient requirement for the person over the period.

    Returns {'ok', 'person', 'period', 'periodDays', 'calorieTarget',
    'needs': {nutrient: {amount, unit, basis, isPrior}},
    'flaggedPriors': [...], 'bmr', 'tdee'}."""
    if period not in PERIOD_DAYS:
        return {'ok': False,
                'error': f"period must be one of {list(PERIOD_DAYS)}, "
                         f"got '{period}'"}
    days = PERIOD_DAYS[period]
    sex = getattr(person, 'sex', 'any')
    age = _f(person, 'age_years', 30.0)
    weight = _f(person, 'weight_kg', 70.0)
    preg = bool(getattr(person, 'pregnant_or_lactating', False))
    cal = calorie_target(person)

    needs, priors = {}, []
    for nutrient in _rows(manager, 'DietaryNutrient'):
        nname = getattr(nutrient, 'name', '')
        unit = getattr(nutrient, 'unit', '')
        if nname == 'calories':
            amount, basis = cal['value'], 'computed BMR/TDEE + goal'
        else:
            ref = _reference_for(manager, nname, sex, age)
            if ref is None:
                continue
            per_kg = _f(ref, 'per_kg_body_mass', 0.0)
            if per_kg > 0:
                amount = per_kg * weight
                basis = f'{per_kg} {unit}/kg × {weight} kg'
            else:
                amount = _f(ref, 'rda_per_day', 0.0)
                basis = getattr(ref, 'source', 'RDA')
            if preg and nname in ('vitamin-b9', 'iron', 'iodine',
                                  'protein', 'calcium'):
                amount *= 1.3
                basis += ' ×1.3 (pregnant/lactating)'
            if getattr(ref, 'is_prior', False):
                priors.append(nname)
        needs[nname] = {'amount': round(amount * days, 3), 'unit': unit,
                        'basis': basis,
                        'isPrior': nname in priors,
                        'plantAvailability': getattr(
                            nutrient, 'plant_availability', 'common')}
    return {'ok': True, 'person': getattr(person, 'name', ''),
            'period': period, 'periodDays': days,
            'calorieTargetPerDay': cal['value'],
            'calorieWarning': cal.get('warning'),
            'bmr': cal['bmr'], 'tdee': cal['tdee'],
            'needs': needs, 'flaggedPriors': sorted(set(priors)),
            'note': 'RDA/AI values are literature priors; per-day needs '
                    'scaled to the demographic band × period.'}
