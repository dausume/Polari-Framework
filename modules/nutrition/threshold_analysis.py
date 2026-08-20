"""
@cross-cutting
@module nutrition.threshold_analysis
@tags @xc:bindings

nmp-1 — the threshold layer's math: obesity classification (honest
screening caveats), the per-person per-period nutrient thresholds
derived from the DRI/UL + DGA seeds (with human PersonThreshold
overrides winning), and the calorie ENVELOPE (decision 7): min/max
healthy daily kcal split by the eating pattern's seeded fractions
into per-slot calorie bands.

General-population only (decision 3): the person-axes are age, sex,
and the DRI life stage — nothing medical. Every derived number
carries its derivation; every override carries its human's reason.

@consumers
  - nutrition.nutrition_api (endpoints), nmp-4 plan rollups
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-1
"""

import json

from nutrition.dga_limits import AMDR, DGA_EDITION, DGA_LIMITS
from nutrition.person_analysis import (PERIOD_DAYS, _f, _reference_for,
                                       _rows, bmr, calorie_target, tdee)

# WHO/CDC BMI screening bands (kg/m^2) — citable convention.
BMI_BANDS = [
    (0.0, 18.5, 'underweight'),
    (18.5, 25.0, 'normal'),
    (25.0, 30.0, 'overweight'),
    (30.0, 35.0, 'obesity-class-1'),
    (35.0, 40.0, 'obesity-class-2'),
    (40.0, 999.0, 'obesity-class-3'),
]
# Body-fat obesity conventions (labeled priors; BMI is only a
# screening prior and body fat wins when measured).
BODY_FAT_OBESE = {'male': 0.25, 'female': 0.32}
# Waist-circumference risk screening (NIH/NHLBI convention, cm).
WAIST_RISK_CM = {'male': 102.0, 'female': 88.0}

# Envelope conventions (labeled priors): the deficit floor tracks the
# common ~1 kg/week safe-loss ceiling (~1000 kcal/day deficit); the
# surplus cap tracks ~0.5 kg/week gain (~500 kcal/day). Both are
# knobs-by-argument, never hidden.
MAX_DAILY_DEFICIT_KCAL = 1000.0
MAX_DAILY_SURPLUS_KCAL = 500.0


def obesity_classification(person):
    """BMI band + honest caveats; body fat wins when set.

    Returns {'ok', 'bmi', 'bmiBand', 'basis', 'classification',
    'waistRiskFlag'?, 'caveats': [...]}. Never medical advice — a
    screening classification with its priors named."""
    h_m = (getattr(person, 'height_cm', 0.0) or 0.0) / 100.0
    kg = getattr(person, 'weight_kg', 0.0) or 0.0
    if h_m <= 0 or kg <= 0:
        return {'ok': False,
                'error': 'height_cm and weight_kg must be set'}
    bmi = kg / (h_m * h_m)
    band = next(b for lo, hi, b in BMI_BANDS if lo <= bmi < hi)
    caveats = ['BMI is a SCREENING prior — it cannot see muscle vs '
               'fat; athletes and short/tall builds misclassify']
    basis, classification = 'bmi', band
    bf = getattr(person, 'body_fat_fraction', 0.0) or 0.0
    sex = getattr(person, 'sex', 'any')
    if bf > 0:
        basis = 'body-fat'
        cut = BODY_FAT_OBESE.get(sex)
        if cut is None:
            caveats.append('body-fat obesity cutoffs are sex-specific '
                           '(25% male / 32% female conventions); sex '
                           'unset, so BMI band kept')
            basis = 'bmi'
        else:
            classification = ('obese-by-body-fat' if bf >= cut
                              else 'not-obese-by-body-fat')
            caveats.append(f'measured body fat ({bf:.0%}) outranks '
                           f'the BMI screening band')
    out = {'ok': True, 'bmi': round(bmi, 1), 'bmiBand': band,
           'basis': basis, 'classification': classification,
           'caveats': caveats}
    waist = getattr(person, 'waist_cm', 0.0) or 0.0
    risk = WAIST_RISK_CM.get(sex)
    if waist > 0 and risk:
        out['waistRiskFlag'] = waist > risk
        out['waistRiskCutCm'] = risk
    return out


def _pattern_fractions(manager, pattern_name):
    for row in _rows(manager, 'EatingPatternDefinition'):
        if getattr(row, 'name', '') == pattern_name:
            try:
                slots = json.loads(
                    getattr(row, 'slot_fractions_json', '[]'))
            except Exception:
                slots = []
            if slots:
                return slots, getattr(row, 'source', '')
    return None, ''


def calorie_envelope(manager, person):
    """Decision 7: the person's healthy daily-calorie band and its
    per-slot split.

    min = max(BMR floor, TDEE - max-deficit prior);
    max = TDEE + max-surplus prior; the person's calorie TARGET
    (goal-driven, nut-3) sits inside and is clamped into the band.
    Slots come from the eating pattern's seeded fractions (labeled
    convention priors)."""
    base = bmr(person)
    energy = tdee(person)
    floor = base['value']
    lo = max(floor, energy['value'] - MAX_DAILY_DEFICIT_KCAL)
    hi = energy['value'] + MAX_DAILY_SURPLUS_KCAL
    target = calorie_target(person)
    clamped = min(max(target['value'], lo), hi)
    pattern = getattr(person, 'eating_pattern', '3-meal') or '3-meal'
    slots, src = _pattern_fractions(manager, pattern)
    result = {
        'ok': True, 'person': getattr(person, 'name', ''),
        'pattern': pattern,
        'minDailyKcal': round(lo, 1), 'maxDailyKcal': round(hi, 1),
        'targetDailyKcal': round(clamped, 1),
        'tdee': energy['value'], 'bmrFloor': floor,
        'tdeeMode': energy.get('mode', 'pal'),
        'derivation': {
            'min': f'max(BMR floor {floor:.0f}, TDEE '
                   f'{energy["value"]:.0f} - deficit prior '
                   f'{MAX_DAILY_DEFICIT_KCAL:.0f})',
            'max': f'TDEE {energy["value"]:.0f} + surplus prior '
                   f'{MAX_DAILY_SURPLUS_KCAL:.0f}',
            'priorsNote': 'deficit/surplus caps are convention '
                          'priors (~1 kg/wk loss, ~0.5 kg/wk gain)',
        },
    }
    if target.get('warning'):
        result['targetWarning'] = target['warning']
    if target['value'] != clamped:
        result['targetClamped'] = True
    if slots is None:
        result['slots'] = []
        result['slotsError'] = (f'no EatingPatternDefinition named '
                                f'"{pattern}" — seed missing?')
        return result
    result['slotsSource'] = src
    result['slots'] = [
        {'slot': s['slot'], 'fraction': s['fraction'],
         'minKcal': round(lo * s['fraction'], 1),
         'maxKcal': round(hi * s['fraction'], 1),
         'targetKcal': round(clamped * s['fraction'], 1)}
        for s in slots]
    return result


def _override_for(manager, person_name, nutrient, period):
    for row in _rows(manager, 'PersonThreshold'):
        if (getattr(row, 'person_name', '') == person_name
                and getattr(row, 'nutrient_name', '') == nutrient
                and getattr(row, 'period', '') == period):
            return row
    return None


def person_thresholds(manager, person, period='day'):
    """Per-nutrient min/target/max for the person over the period.

    Derived from the DRI life-stage rows (EAR -> min, RDA/AI ->
    target, UL/CDRR -> max, scaled by period days) + the DGA
    fraction-of-kcal limits materialized against the person's
    calorie target; a PersonThreshold override row WINS per side,
    with its human reason carried. Every row names its basis."""
    if period not in PERIOD_DAYS:
        return {'ok': False,
                'error': f'period must be one of {list(PERIOD_DAYS)}'}
    # per-MEAL nutrient thresholds are dose-based and arrive with the
    # nmp-2 tolerance table + nmp-4 gate; this serves day/week/month.
    days = PERIOD_DAYS[period]
    sex = getattr(person, 'sex', 'any')
    age = getattr(person, 'age_years', 30.0)
    stage = getattr(person, 'life_stage', '') or ''
    person_name = getattr(person, 'name', '')
    kg = getattr(person, 'weight_kg', 70.0)
    envelope = calorie_envelope(manager, person)
    kcal_target = envelope['targetDailyKcal']
    rows = {}
    for nut in _rows(manager, 'DietaryNutrient'):
        n = getattr(nut, 'name', '')
        ref = None
        if stage in ('pregnancy', 'lactation'):
            for r in _rows(manager, 'NutrientReference'):
                if (getattr(r, 'nutrient_name', '') == n
                        and getattr(r, 'life_stage', '') == stage
                        and _f(r, 'age_min', 0) <= age
                        <= _f(r, 'age_max', 999)):
                    ref = r
                    break
        if ref is None:
            ref = _reference_for(manager, n, sex, age)
        if ref is None:
            continue
        per_kg = _f(ref, 'per_kg_body_mass', 0.0)
        target = (per_kg * kg if per_kg > 0
                  else _f(ref, 'rda_per_day', 0.0))
        ear = _f(ref, 'ear_per_day', 0.0)
        ul = _f(ref, 'upper_limit_per_day', 0.0)
        d = days
        entry = {
            'nutrient': n, 'unit': getattr(nut, 'unit', ''),
            'period': period,
            'min': round(ear * d, 2) if ear > 0 else 0.0,
            'target': round(target * d, 2),
            'max': round(ul * d, 2) if ul > 0 else 0.0,
            'basis': {
                'reference': getattr(ref, 'name', ''),
                'valueType': getattr(ref, 'value_type', ''),
                'lifeStage': getattr(ref, 'life_stage', ''),
                'min': 'EAR x days' if ear > 0 else 'no EAR published',
                'max': ('UL/CDRR x days' if ul > 0
                        else 'no UL established'),
                'isPrior': bool(getattr(ref, 'is_prior', True)),
            },
        }
        ov = _override_for(manager, person_name, n, period)
        if ov is not None:
            for side, attr in (('min', 'min_amount'),
                               ('target', 'target_amount'),
                               ('max', 'max_amount')):
                val = _f(ov, attr, 0.0)
                if val > 0:
                    entry[side] = val
                    entry['basis'][side] = 'human override'
            entry['override'] = {
                'name': getattr(ov, 'name', ''),
                'reason': getattr(ov, 'reason', '')}
        rows[n] = entry
    # DGA fraction-of-kcal limits, materialized to grams against the
    # calorie target (4 kcal/g carbs+protein, 9 kcal/g fat).
    dga = []
    for lim in DGA_LIMITS:
        item = dict(lim)
        if lim['basis'] == 'fraction_of_kcal':
            item['kcalPerDay'] = round(kcal_target * lim['limit'], 1)
        item['edition'] = DGA_EDITION
        dga.append(item)
    amdr = []
    for band in AMDR:
        kcal_per_g = 9.0 if band['nutrient'] == 'healthy-fat' else 4.0
        amdr.append({
            'nutrient': band['nutrient'],
            'minFraction': band['min_fraction'],
            'maxFraction': band['max_fraction'],
            'minGramsPerDay': round(
                kcal_target * band['min_fraction'] / kcal_per_g, 1),
            'maxGramsPerDay': round(
                kcal_target * band['max_fraction'] / kcal_per_g, 1),
        })
    return {'ok': True, 'person': person_name, 'period': period,
            'periodDays': days, 'lifeStage': stage,
            'calorieTargetPerDay': kcal_target,
            'thresholds': rows, 'dgaLimits': dga, 'amdr': amdr,
            'honesty': 'general-population bands only (decision 3): '
                       'no medical personalization; every number is '
                       'a cited prior or your own override'}
