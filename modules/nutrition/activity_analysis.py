"""
@cross-cutting
@module nutrition.activity_analysis
@tags @xc:bindings

nmp-5 + nmp-5b — activity math and meal<->exercise timing:

  activity_kcal      kcal = MET x kg x hours (the standard cited
                     arithmetic), with the perceived-intensity knob
                     scaling MET (labeled when applied).
  weekly_summary     a person's logged week: minutes by intensity
                     band + kcal; SUGGESTS profile-minute updates
                     when logs diverge from the stated minutes
                     (never auto-applies — decision 6 knob stays
                     the human's).
  day_timeline       nmp-5b: one plan day's meals + activity logs
                     interleaved by clock time, with the timing
                     evaluations (all cited, confidence-labeled):
                     comfort/reflux window (vigorous within ~2-3 h
                     after a large/high-fat meal), carbs-before-
                     vigorous performance note, late-large-meal
                     chrononutrition flag (small-effect, labeled).
  fasted_exercise_facts  the honest page payload (decision 14): what
                     fasted cardio does and does not do, cited — NO
                     weight multiplier exists anywhere in this
                     module, and the trajectory (nmp-6) stays
                     energy-balance-driven.

@consumers
  - nutrition.nutrition_api, nmp-6 trajectory (activity kcal)
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-5/§nmp-5b
"""

from nutrition.activity_basis import intensity_band
from nutrition.meal_analysis import _named, template_rollup
from nutrition.person_analysis import _f, _rows
from nutrition.vendor_data import compendium_mets

# nmp-5b timing priors (labeled in every warning they produce)
REFLUX_WINDOW_H = 2.5     # ~2-3 h comfort window after a large meal
LARGE_MEAL_KCAL = 700.0   # 'large meal' convention prior
HIGHFAT_MEAL_G = 40.0     # ties to the nmp-2 high-fat row
LATE_MEAL_HHMM = '21:00'  # chrononutrition flag (small effect)


def _met_for(manager, log):
    """Resolve a log's MET: explicit code beats the seeded name;
    both resolve against the verbatim Compendium."""
    code = getattr(log, 'activity_code', '') or ''
    name = getattr(log, 'activity_name', '') or ''
    if not code and name:
        row = _named(manager, 'ActivityDefinition', name)
        if row is not None:
            return (_f(row, 'met_value', 0.0),
                    getattr(row, 'display_name', name))
    if code:
        for r in compendium_mets():
            if r['activity_code'] == code:
                return float(r['met_value']), r['description']
    return 0.0, name or code


def activity_kcal(manager, person, log):
    """kcal = MET x kg x hours (perceived-intensity knob applied)."""
    met, label = _met_for(manager, log)
    if met <= 0:
        return {'ok': False,
                'error': f'activity not resolvable for log '
                         f'"{getattr(log, "name", "")}" — name/code '
                         f'unknown'}
    factor = _f(log, 'perceived_intensity_factor', 1.0) or 1.0
    factor = min(1.3, max(0.7, factor))
    kg = _f(person, 'weight_kg', 70.0)
    hours = _f(log, 'duration_min', 0.0) / 60.0
    kcal = met * factor * kg * hours
    out = {'ok': True, 'activity': label, 'met': met,
           'intensity': intensity_band(met * factor),
           'durationMin': _f(log, 'duration_min', 0.0),
           'kcal': round(kcal, 1),
           'formula': 'kcal = MET x kg x hours (Compendium 2024)'}
    if factor != 1.0:
        out['perceivedIntensityFactor'] = factor
        out['note'] = 'MET scaled by the felt-intensity knob'
    return out


def weekly_summary(manager, person):
    """Logged minutes by band + kcal; profile-minute suggestions."""
    pname = getattr(person, 'name', '')
    logs = [l for l in _rows(manager, 'ActivityLog')
            if getattr(l, 'person_name', '') == pname]
    mins = {'light': 0.0, 'moderate': 0.0, 'vigorous': 0.0}
    total_kcal, sessions, errors = 0.0, [], []
    for log in logs:
        r = activity_kcal(manager, person, log)
        if not r.get('ok'):
            errors.append(r['error'])
            continue
        mins[r['intensity']] += r['durationMin']
        total_kcal += r['kcal']
        sessions.append(r)
    stated_mod = _f(person, 'weekly_moderate_minutes', 0.0)
    stated_vig = _f(person, 'weekly_vigorous_minutes', 0.0)
    suggestions = []
    if sessions and (abs(mins['moderate'] - stated_mod) > 60
                     or abs(mins['vigorous'] - stated_vig) > 30):
        suggestions.append({
            'knob': 'weekly_moderate_minutes / weekly_vigorous_minutes',
            'statedModerate': stated_mod, 'statedVigorous': stated_vig,
            'loggedModerate': round(mins['moderate'], 0),
            'loggedVigorous': round(mins['vigorous'], 0),
            'suggestion': 'your logs diverge from the stated weekly '
                          'minutes — consider updating the profile '
                          'knobs (nothing auto-applied)'})
    return {'ok': True, 'person': pname,
            'minutesByBand': {k: round(v, 0) for k, v in mins.items()},
            'kcal': round(total_kcal, 1),
            'sessions': sessions, 'errors': errors,
            'suggestions': suggestions,
            'attribution': 'MET values: 2024 Adult Compendium '
                           '(pacompendium.com), values unaltered'}


def _hhmm_to_h(hhmm):
    try:
        h, m = hhmm.split(':')
        return int(h) + int(m) / 60.0
    except Exception:
        return None


def day_timeline(manager, plan, day_index):
    """nmp-5b: one plan day, meals + activities by clock time, with
    the timing evaluations. Items without times are listed untimed
    (honest) and excluded from window math."""
    plan_name = getattr(plan, 'name', '')
    person = _named(manager, 'PersonProfile',
                    getattr(plan, 'person_name', ''))
    items = []
    for e in _rows(manager, 'MealEntry'):
        if (getattr(e, 'plan_name', '') != plan_name
                or getattr(e, 'day_index', 0) != day_index):
            continue
        template = _named(manager, 'MealTemplate',
                          getattr(e, 'template_name', ''))
        kcal = fat = 0.0
        if template is not None:
            variation = None
            if getattr(e, 'variation_name', ''):
                variation = _named(manager, 'VariationDefinition',
                                   e.variation_name)
            roll = template_rollup(manager, template, variation,
                                   _f(e, 'scale', 1.0))
            if roll.get('ok'):
                kcal = roll['perMeal'].get(
                    'calories', {}).get('amount', 0.0)
                fat = roll['perMeal'].get(
                    'healthy-fat', {}).get('amount', 0.0)
        items.append({'kind': 'meal', 'name': getattr(e, 'name', ''),
                      'slot': getattr(e, 'slot', ''),
                      'time': getattr(e, 'time_hhmm', '') or '',
                      'kcal': round(kcal, 0), 'fatG': round(fat, 1)})
    for log in _rows(manager, 'ActivityLog'):
        if getattr(log, 'day_index', 0) != day_index:
            continue
        if (getattr(plan, 'person_name', '')
                and getattr(log, 'person_name', '')
                != plan.person_name):
            continue
        r = (activity_kcal(manager, person, log)
             if person is not None else {'ok': False})
        items.append({
            'kind': 'activity', 'name': getattr(log, 'name', ''),
            'time': getattr(log, 'start_hhmm', '') or '',
            'durationMin': _f(log, 'duration_min', 0.0),
            'intensity': r.get('intensity', 'unknown'),
            'kcal': r.get('kcal', 0.0),
            'fasted': bool(getattr(log, 'fasted', False))})
    timed = [i for i in items if _hhmm_to_h(i['time']) is not None]
    untimed = [i for i in items if _hhmm_to_h(i['time']) is None]
    timed.sort(key=lambda i: _hhmm_to_h(i['time']))
    evaluations = []
    for act in [i for i in timed if i['kind'] == 'activity']:
        t_act = _hhmm_to_h(act['time'])
        for meal in [i for i in timed if i['kind'] == 'meal']:
            t_meal = _hhmm_to_h(meal['time'])
            gap = t_act - t_meal
            large = (meal['kcal'] >= LARGE_MEAL_KCAL
                     or meal['fatG'] >= HIGHFAT_MEAL_G)
            if (0 <= gap < REFLUX_WINDOW_H and large
                    and act['intensity'] == 'vigorous'):
                evaluations.append({
                    'kind': 'comfort-window',
                    'confidence': 'low',
                    'items': [meal['name'], act['name']],
                    'note': f'vigorous exercise {gap:.1f} h after a '
                            f'large/high-fat meal — inside the '
                            f'~{REFLUX_WINDOW_H:g} h comfort window '
                            f'the reflux literature suggests '
                            f'(ties to the nmp-2 trigger rows; '
                            f'comfort guidance, not a rule)'})
        if act['intensity'] == 'vigorous' and act.get('fasted'):
            evaluations.append({
                'kind': 'fasted-vigorous', 'confidence': 'moderate',
                'items': [act['name']],
                'note': 'fasted vigorous session — output may run '
                        'lower (the honest fasted-exercise facts '
                        'apply; no weight-loss advantage at equal '
                        'calories)'})
        prior_meals = [m for m in timed if m['kind'] == 'meal'
                       and _hhmm_to_h(m['time']) < t_act]
        if (act['intensity'] == 'vigorous'
                and act['durationMin'] >= 45 and not prior_meals):
            evaluations.append({
                'kind': 'performance', 'confidence': 'moderate',
                'items': [act['name']],
                'note': 'long vigorous session with no earlier meal '
                        'logged — carbohydrate beforehand supports '
                        'output (performance note, not a rule)'})
    late = _hhmm_to_h(LATE_MEAL_HHMM)
    for meal in [i for i in timed if i['kind'] == 'meal']:
        if (_hhmm_to_h(meal['time']) >= late
                and meal['kcal'] >= LARGE_MEAL_KCAL):
            evaluations.append({
                'kind': 'chrononutrition', 'confidence': 'low',
                'items': [meal['name']],
                'note': f'large meal after {LATE_MEAL_HHMM} — the '
                        f'chrononutrition literature shows small '
                        f'effects (labeled as such; a flag, not a '
                        f'rule)'})
    return {'ok': True, 'plan': plan_name, 'day': day_index,
            'timeline': timed, 'untimed': untimed,
            'evaluations': evaluations,
            'honesty': 'timing drives comfort, performance and '
                       'flags only — the weight trajectory stays '
                       'energy-balance-driven (decision 14)'}


def fasted_exercise_facts():
    """Decision 14: the honest fasted-cardio payload, cited."""
    return {
        'ok': True,
        'doesDo': [
            'raises fat oxidation DURING the session (substrate '
            'shift while training fasted)',
        ],
        'doesNotDo': [
            'produce meaningful long-term weight-loss advantage at '
            'equal calories — calorie-equated trials show none',
            'change the energy-balance arithmetic: no timing '
            'multiplier exists in the weight trajectory (nmp-6)',
        ],
        'caveats': [
            'fasted vigorous sessions may run at lower output — '
            'performance can suffer even though fat oxidation is '
            'higher',
        ],
        'citations': [
            'Schoenfeld et al. 2014 (JISSN) — fasted vs fed cardio '
            'RCT, equal-calorie deficit: no body-composition '
            'difference',
            'Hackett & Hagstrom 2017 (J Funct Morphol Kinesiol) — '
            'meta-analysis: fasting before aerobic exercise does '
            'not meaningfully change weight/fat outcomes',
        ],
    }
