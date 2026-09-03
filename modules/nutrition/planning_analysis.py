"""
@module nutrition.planning_analysis

mpc — the week-planning flow Dustin asked for (2026-09-02):
  "a meals page specifying meals for individuals, and then the meals
   page should be able to translate into converting that meal into
   meal-prep for the week. We should be able to choose to use that
   meal for any number of meals of the day, and any number of days in
   the week … a configuration page for planning meals for the week,
   that checks if all meals have been planned for the week yet …
   it should still be able to adjust the portioning on the meal to
   adjust the calories and nutrients per person to try and best-fit
   getting each person what they need individually. Compromising the
   fact that we cannot make a perfect meal for everyone and
   compromising between needs of the household"

  expected_slots       which slots a person eats (their eating pattern)
  week_coverage        the person × day × slot grid — planned / MISSING,
                       named; complete or not
  portion_fit          ONE recipe, per-person PORTIONS: each person's
                       scale = their slot share of their daily target ÷
                       the meal's kcal per serving, clamped to the
                       variation's scale bounds; the compromise (who is
                       short, by how much, what would help) is stated.
                       KNOB objective='calories' (default, above) or
                       'nutrients': a bounded 0.05-grid scan of the scale
                       minimising the weighted squared relative error over
                       calories + protein + fiber (targets) + sodium
                       (ceiling — excess only) against the person's own
                       per-slot lines (tracking_periods._lines +
                       person_thresholds, the day rollup's lines); the
                       weights are a labelled prior, echoed back; the
                       driver nutrient and a plain-words line are stated
  apply_meal_proposal  the meal → MealEntry proposals for any slots ×
                       days (existing entries NAMED, never overwritten),
                       each carrying serving_split_json from portion_fit
                       — the no-code solution writes them (GenerateEvent
                       targetClassName=MealEntry), the entry trigger
                       re-coordinates the week (pre-prep follows)
"""

import json
from datetime import date, datetime, timedelta

from nutrition.meal_analysis import _json_list, template_rollup
from nutrition.meal_basis import MEAL_SLOTS

DEFAULT_PATTERN_SLOTS = [{'slot': 'breakfast', 'fraction': 0.25},
                         {'slot': 'lunch', 'fraction': 0.35},
                         {'slot': 'dinner', 'fraction': 0.40}]
SCALE_MIN_DEFAULT, SCALE_MAX_DEFAULT = 0.5, 2.0
FIT_TOLERANCE = 0.15     # a portion within ±15 % of the slot target "fits"
KEY_NUTRIENTS = ('protein', 'fiber')

# --- the portion objective KNOB -------------------------------------
PORTION_OBJECTIVES = ('calories', 'nutrients')
FIT_NUTRIENTS = ('calories', 'protein', 'fiber', 'sodium')
# labelled PRIOR: the weights of the 'nutrients' objective — squared
# relative error per line; sodium is an upper bound (excess penalised,
# shortfall free). Convention priors, not measurements — pass `weights`
# to change them; whatever is used is echoed back on the result.
DEFAULT_FIT_WEIGHTS = {'calories': 1.0, 'protein': 0.7, 'fiber': 0.3, 'sodium': 0.5}
FIT_WEIGHTS_LABEL = ('convention prior (2026-09-02): calories 1.0, protein 0.7, fiber 0.3, '
                     'sodium-excess 0.5 — relative-error weights, not evidence-derived')
SCALE_STEP = 0.05        # the 1-D scan grid of the scale inside [scale_min, scale_max]
CEILING_NUTRIENTS = ('sodium',)


def _rows(manager, cls):
    return list(((getattr(manager, 'objectTables', {}) or {}).get(cls, {}) or {}).values())


def _named(manager, cls, name):
    for r in _rows(manager, cls):
        if getattr(r, 'name', '') == name:
            return r
    return None


def _loads(text, default):
    if isinstance(text, (dict, list)):
        return text
    try:
        v = json.loads(text) if text else default
    except (TypeError, ValueError):
        return default
    return v if v not in (None, '') else default


def _members(manager, plan_row):
    household = getattr(plan_row, 'household_name', '')
    people = [m.person_name for m in _rows(manager, 'HouseholdMember')
              if getattr(m, 'household_name', '') == household]
    if not people:
        hh = _named(manager, 'HouseholdProfile', household)
        people = list(_loads(getattr(hh, 'member_names_json', '[]'), [])) if hh else []
    return people or [getattr(plan_row, 'person_name', '')]


def expected_slots(manager, person):
    """[{slot, fraction}] a person eats, from their eating pattern
    (PersonProfile.eating_pattern → EatingPatternDefinition); the
    3-meal default when unstated — labeled."""
    prof = _named(manager, 'PersonProfile', person)
    pattern = getattr(prof, 'eating_pattern', '') if prof else ''
    for row in _rows(manager, 'EatingPatternDefinition'):
        if pattern and getattr(row, 'name', '') == pattern:
            slots = _loads(getattr(row, 'slot_fractions_json', '[]'), [])
            if slots:
                return {'person': person, 'pattern': pattern, 'slots': slots,
                        'source': 'the person\'s eating pattern'}
    return {'person': person, 'pattern': pattern or '3-meal (default)',
            'slots': list(DEFAULT_PATTERN_SLOTS),
            'source': 'default 3-meal pattern — set PersonProfile.eating_pattern to change'}


def _serves(entry, person):
    split = _loads(getattr(entry, 'serving_split_json', '{}'), {})
    return not split or person in split


def week_coverage(manager, plan):
    """The person × day × slot grid for a plan; missing cells NAMED."""
    plan_row = plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)
    if plan_row is None:
        return {'ok': False, 'error': f"MealPlanDefinition '{plan}' not found"}
    days = int(getattr(plan_row, 'days', 0) or 0) or 7
    try:
        start = datetime.fromisoformat(str(getattr(plan_row, 'start_date', ''))[:10]).date()
    except ValueError:
        start = None
    entries = [e for e in _rows(manager, 'MealEntry') if getattr(e, 'plan_name', '') == plan_row.name]
    grid, missing = [], []
    per_person, per_day = {}, {}
    for person in _members(manager, plan_row):
        slots = expected_slots(manager, person)
        for day in range(1, days + 1):
            d = (start + timedelta(days=day - 1)).isoformat() if start else ''
            for s in slots['slots']:
                slot = s.get('slot', '')
                match = next((e for e in entries
                              if int(getattr(e, 'day_index', 0) or 0) == day
                              and getattr(e, 'slot', '') == slot and _serves(e, person)), None)
                status = 'planned' if match else 'missing'
                cell = {'person': person, 'day': day, 'date': d, 'slot': slot,
                        'slotFraction': s.get('fraction'), 'status': status,
                        'entry': getattr(match, 'name', '') if match else '',
                        'template': getattr(match, 'template_name', '') if match else '',
                        'portion': (_loads(getattr(match, 'serving_split_json', '{}'), {}).get(person)
                                    if match else None)}
                grid.append(cell)
                pp = per_person.setdefault(person, {'person': person, 'expected': 0, 'planned': 0})
                pd = per_day.setdefault(day, {'day': day, 'date': d, 'expected': 0, 'planned': 0})
                pp['expected'] += 1; pd['expected'] += 1
                if match:
                    pp['planned'] += 1; pd['planned'] += 1
                else:
                    missing.append({'person': person, 'day': day, 'date': d, 'slot': slot})
    expected = len(grid)
    planned = expected - len(missing)
    unplanned_days = [d['day'] for d in per_day.values() if d['planned'] == 0]
    return {'ok': True, 'schema': 'week-coverage/1', 'plan': plan_row.name, 'days': days,
            'weekStart': start.isoformat() if start else '',
            'complete': not missing, 'counts': {'expected': expected, 'planned': planned,
                                                'missing': len(missing)},
            'headline': (f'all {expected} meals planned' if not missing else
                         f'{planned} of {expected} meals planned — {len(missing)} missing'
                         + (f'; days with nothing planned: {unplanned_days}' if unplanned_days else '')),
            'missing': missing, 'perPerson': list(per_person.values()),
            'perDay': list(per_day.values()), 'grid': grid,
            'honesty': ('expected slots come from each person\'s eating pattern (default '
                        '3-meal when unstated); an entry without a serving split serves '
                        'the whole household')}


def _scale_bounds(variation):
    lo = float(getattr(variation, 'scale_min', 0) or 0) if variation else 0.0
    hi = float(getattr(variation, 'scale_max', 0) or 0) if variation else 0.0
    return (lo or SCALE_MIN_DEFAULT), (hi or SCALE_MAX_DEFAULT)


def parse_fit_weights(value):
    """The weights knob: a dict, a JSON object, or 'protein=0.9,sodium=0.2'
    (':' works too). Missing lines take the default prior; unknown names
    are named, not silently dropped."""
    given = {}
    if isinstance(value, dict):
        given = dict(value)
    elif isinstance(value, str) and value.strip():
        text = value.strip()
        parsed = _loads(text, None) if text.startswith('{') else None
        if isinstance(parsed, dict):
            given = parsed
        else:
            for part in text.replace(';', ',').split(','):
                if '=' in part or ':' in part:
                    k, _, v = part.replace(':', '=').partition('=')
                    given[k.strip()] = v.strip()
    weights, unknown = dict(DEFAULT_FIT_WEIGHTS), []
    for k, v in given.items():
        if k not in DEFAULT_FIT_WEIGHTS:
            unknown.append(k)
            continue
        try:
            weights[k] = max(0.0, float(v))
        except (TypeError, ValueError):
            unknown.append(f'{k} (not a number: {v!r})')
    return weights, unknown


def _slot_lines(manager, prof, person, frac):
    """The person's per-slot lines for the 'nutrients' objective —
    the SAME daily lines tracking_periods._lines reads (calorie
    envelope target, sodium CDRR / ToleranceThreshold ceiling) plus the
    day rollup's per-nutrient targets (person_thresholds, the source
    of intake_day's vsThresholds), scaled by the slot fraction. Only
    nutrients that HAVE a line come back; the rest are named."""
    from nutrition.threshold_analysis import person_thresholds
    from nutrition.tracking_periods import _lines
    daily = {}
    lines = _lines(manager, person)
    for n in FIT_NUTRIENTS:
        row = lines.get(n) or {}
        if n in CEILING_NUTRIENTS and row.get('max'):
            daily[n] = {'kind': 'ceiling', 'daily': float(row['max']), 'source': row.get('source', '')}
        elif row.get('target'):
            daily[n] = {'kind': 'target', 'daily': float(row['target']), 'source': row.get('source', '')}
    th = person_thresholds(manager, prof, 'day') if prof is not None else {'ok': False}
    units = {}
    for n, row in (th.get('thresholds', {}) if th.get('ok') else {}).items():
        if n not in FIT_NUTRIENTS:
            continue
        units[n] = row.get('unit', '')
        if n in daily:
            continue
        if n in CEILING_NUTRIENTS and float(row.get('max') or 0) > 0:
            daily[n] = {'kind': 'ceiling', 'daily': float(row['max']),
                        'source': 'person thresholds (the day rollup\'s lines)'}
        elif n not in CEILING_NUTRIENTS and float(row.get('target') or 0) > 0:
            daily[n] = {'kind': 'target', 'daily': float(row['target']),
                        'source': 'person thresholds (the day rollup\'s lines)'}
    default_units = {'calories': 'kcal', 'protein': 'g', 'fiber': 'g', 'sodium': 'mg'}
    for n, line in daily.items():
        line['slot'] = line['daily'] * frac
        line['unit'] = units.get(n) or default_units.get(n, '')
    missing = [n for n in FIT_NUTRIENTS if n not in daily]
    return daily, missing


def _fit_terms(per_meal, lines, weights, scale):
    """Per-nutrient (have, line, relative error, weighted term) at a scale."""
    terms = {}
    for n, line in lines.items():
        amt = float(per_meal.get(n, {}).get('amount') or 0)
        have = amt * scale
        rel = (have - line['slot']) / line['slot'] if line['slot'] else 0.0
        if line['kind'] == 'ceiling':
            penal = max(0.0, rel)
        else:
            penal = rel
        terms[n] = {'have': have, 'line': line['slot'], 'rel': rel, 'amt': amt,
                    'term': weights.get(n, 0.0) * penal * penal}
    return terms


def _objective(per_meal, lines, weights, scale):
    return sum(t['term'] for t in _fit_terms(per_meal, lines, weights, scale).values())


def _scan_scale(per_meal, lines, weights, lo, hi, prefer):
    """Bounded 1-D scan on a SCALE_STEP grid inside [lo, hi] (hi always
    on the grid); ties break toward `prefer` (the calories-only scale)."""
    grid, s = [], lo
    while s < hi - 1e-9:
        grid.append(round(s, 4))
        s += SCALE_STEP
    grid.append(round(hi, 4))
    best, best_j = None, None
    for s in grid:
        j = _objective(per_meal, lines, weights, s)
        if best is None or j < best_j - 1e-12 or (abs(j - best_j) <= 1e-12
                                                   and abs(s - prefer) < abs(best - prefer)):
            best, best_j = s, j
    # still falling past a bound? then the bound is what stopped us
    wants_more = (abs(best - hi) < 1e-9 and _objective(per_meal, lines, weights, hi + SCALE_STEP) < best_j - 1e-12)
    wants_less = (abs(best - lo) < 1e-9 and lo - SCALE_STEP > 0
                  and _objective(per_meal, lines, weights, lo - SCALE_STEP) < best_j - 1e-12)
    return best, best_j, (wants_more or wants_less)


def _fit_story(person, terms, scale, lo, hi, clamped):
    """Words, not JSON: who pulls the portion which way, who caps it,
    what was chosen and why."""
    up, down, caps = [], [], []
    for n, t in terms.items():
        own = t.get('ownIdeal')
        if own is None:
            continue
        if t['kind'] == 'ceiling':
            if own < scale - 1e-9:
                caps.append(f'{n} caps it at ×{own:.2f}')
            continue
        verb = 'pull' if n == 'calories' else 'pulls'
        if own > scale + SCALE_STEP / 2:
            up.append(f'{n} {verb} the portion up (its own ideal ×{own:.2f})')
        elif own < scale - SCALE_STEP / 2:
            down.append(f'{n} {verb} it down (×{own:.2f})')
    parts = up + down + caps
    driver = max(terms.items(), key=lambda kv: kv[1]['term'])[0] if terms else ''
    driver_term = terms[driver]['term'] if driver else 0.0
    if driver_term <= 1e-12:
        driver_words = 'every line is met within the grid — no compromise'
        driver = ''
    else:
        rel = terms[driver]['rel'] * 100
        driver_words = (f"{driver} drives the compromise ({rel:+.0f} % vs its line)")
    where = (f' — pinned at the variation\'s {"max" if abs(scale - hi) < 1e-9 else "min"} ×{scale:.2f}'
             if clamped else f' — chosen ×{scale:.2f}')
    story = (f"{person}: " + ('; '.join(parts) if parts else 'every line is within reach at one scale')
             + where + f'; {driver_words}')
    return driver, story


def portion_fit(manager, template, variation='', slot='dinner', persons=None, household='',
                objective='calories', weights=None):
    """Per-person portion scales for ONE meal in ONE slot.

    objective KNOB: 'calories' (default — scale = the slot share of the
    calorie target ÷ kcal per serving, clamped) or 'nutrients' (the
    scale minimising Σ w_n · relErr_n² over calories/protein/fiber
    targets + the sodium ceiling — excess only — on a 0.05 grid inside
    the variation's bounds). `weights` overrides the labelled prior."""
    from nutrition.person_analysis import nutrient_needs
    from nutrition.threshold_analysis import calorie_envelope
    objective = (objective or 'calories').strip().lower()
    if objective not in PORTION_OBJECTIVES:
        return {'ok': False, 'error': f"objective must be one of {list(PORTION_OBJECTIVES)} — got {objective!r}"}
    fit_weights, unknown_weights = parse_fit_weights(weights)
    t = template if not isinstance(template, str) else _named(manager, 'MealTemplate', template)
    if t is None:
        return {'ok': False, 'error': f"MealTemplate '{template}' not found"}
    v = None
    if variation:
        v = _named(manager, 'VariationDefinition', variation)
    if v is None:
        vs = [x for x in _rows(manager, 'VariationDefinition') if getattr(x, 'template_name', '') == t.name]
        v = next((x for x in vs if x.name.endswith('-base')), vs[0] if vs else None)
    roll = template_rollup(manager, t, v, 1.0)
    if not roll.get('ok'):
        return {'ok': False, 'error': roll.get('error', 'rollup failed')}
    per_meal = roll.get('perMeal', {})
    kcal1 = float(per_meal.get('calories', {}).get('amount') or 0)
    lo, hi = _scale_bounds(v)
    people = persons or []
    if not people and household:
        people = [m.person_name for m in _rows(manager, 'HouseholdMember')
                  if getattr(m, 'household_name', '') == household]
    fits, compromises = [], []
    for person in people:
        prof = _named(manager, 'PersonProfile', person)
        env = calorie_envelope(manager, prof) if prof else {'ok': False}
        target = float(env.get('targetDailyKcal') or 0) if env.get('ok') else 0.0
        slots = expected_slots(manager, person)
        frac = next((float(s.get('fraction') or 0) for s in slots['slots'] if s.get('slot') == slot), None)
        note = ''
        if frac is None:
            frac = 0.3
            note = f'{slot} is not in {person}\'s pattern — 30 % share assumed'
        slot_kcal = target * frac
        fit = {'person': person, 'slot': slot, 'targetDailyKcal': round(target, 0),
               'slotFraction': frac, 'slotKcalTarget': round(slot_kcal, 0),
               'mealKcalPerServing': round(kcal1, 0), 'scaleBounds': [lo, hi], 'notes': note}
        if not target or not kcal1:
            fit.update({'scale': 1.0, 'clamped': False, 'kcalAtScale': round(kcal1, 0),
                        'fitPct': None, 'fits': None,
                        'notes': (note + '; ' if note else '') + ('no calorie target (profile missing)' if not target
                                                                  else 'meal has no calorie rollup')})
            fits.append(fit)
            continue
        ideal = slot_kcal / kcal1
        scale = min(max(ideal, lo), hi)
        clamped = abs(scale - ideal) > 1e-6
        cal_only_scale = scale
        nut_block = None
        if objective == 'nutrients':
            lines, no_line = _slot_lines(manager, prof, person, frac)
            if 'calories' not in lines:      # the envelope IS the calorie line — keep them one
                lines['calories'] = {'kind': 'target', 'daily': target, 'slot': slot_kcal,
                                     'unit': 'kcal', 'source': 'calorie envelope'}
                no_line = [n for n in no_line if n != 'calories']
            lines = {n: l for n, l in lines.items() if fit_weights.get(n, 0.0) > 0
                     and float(per_meal.get(n, {}).get('amount') or 0) > 0}
            scale, j_at, clamped = _scan_scale(per_meal, lines, fit_weights, lo, hi, cal_only_scale)
            terms = _fit_terms(per_meal, lines, fit_weights, scale)
            for n, tm in terms.items():
                tm['kind'] = lines[n]['kind']
                tm['ownIdeal'] = (lines[n]['slot'] / tm['amt']) if tm['amt'] else None
            driver, story = _fit_story(person, terms, scale, lo, hi, clamped)
            nut_block = {
                'objective': 'nutrients', 'caloriesOnlyScale': round(cal_only_scale, 2),
                'objectiveValue': round(j_at, 4), 'driver': driver, 'story': story,
                'fitLines': {n: {
                    'kind': tm['kind'], 'unit': lines[n]['unit'],
                    'achieved': round(tm['have'], 1), 'line': round(tm['line'], 1),
                    'relErrPct': round(tm['rel'] * 100, 1),
                    'penalised': tm['kind'] != 'ceiling' or tm['rel'] > 0,
                    'weight': fit_weights.get(n), 'weightedTerm': round(tm['term'], 4),
                    'ownIdealScale': round(tm['ownIdeal'], 2) if tm['ownIdeal'] is not None else None,
                    'source': lines[n]['source']} for n, tm in terms.items()},
                'noLine': [n for n in FIT_NUTRIENTS if n not in lines
                           and (n in no_line or fit_weights.get(n, 0.0) <= 0
                                or not float(per_meal.get(n, {}).get('amount') or 0))],
            }
        kcal_at = kcal1 * scale
        gap = (kcal_at - slot_kcal) / slot_kcal
        fit.update({'idealScale': round(ideal, 2), 'scale': round(scale, 2),
                    'clamped': clamped, 'kcalAtScale': round(kcal_at, 0),
                    'fitPct': round(gap * 100, 1), 'fits': abs(gap) <= FIT_TOLERANCE})
        if nut_block:
            fit.update(nut_block)
        # key nutrients at that scale vs the slot's share of daily needs
        needs = nutrient_needs(manager, prof, 'day') if prof else {'ok': False}
        nut = {}
        for n in KEY_NUTRIENTS:
            need = float((needs.get('needs', {}).get(n) or {}).get('amount') or 0) if needs.get('ok') else 0.0
            have = float(per_meal.get(n, {}).get('amount') or 0) * scale
            nut[n] = {'have': round(have, 1), 'slotNeed': round(need * frac, 1),
                      'pct': round(have / (need * frac) * 100, 0) if need * frac else None}
        fit['nutrients'] = nut
        if nut_block:
            drv = nut_block['driver']
            drv_line = nut_block['fitLines'].get(drv, {}) if drv else {}
            off = abs(drv_line.get('relErrPct') or 0) > FIT_TOLERANCE * 100
            if drv and (off or (fit['clamped'] and not fit['fits'])):
                short = drv_line.get('kind') != 'ceiling' and (drv_line.get('relErrPct') or 0) < 0
                compromises.append({'person': person, 'why': nut_block['story'], 'driver': drv,
                                    'suggestion': ((f'add a {drv}-rich side or a larger variation'
                                                    if drv != 'calories' else 'add a side or a larger variation') if short
                                                   else (f'a lower-{drv} variation or a smaller portion'
                                                         if drv_line.get('kind') == 'ceiling'
                                                         else 'a smaller variation or share the portion'))})
        elif fit['clamped'] and not fit['fits']:
            compromises.append({'person': person, 'why': (
                f"{person}'s ideal portion is ×{ideal:.2f} but the variation allows "
                f"[{lo}, {hi}] — at ×{scale:.2f} they get {kcal_at:.0f} kcal vs {slot_kcal:.0f} "
                f"({gap * 100:+.0f} %)"),
                'suggestion': ('add a side or a larger variation' if gap < 0 else
                               'a smaller variation or share the portion')})
        fits.append(fit)
    total_scale = round(sum(f.get('scale', 1.0) for f in fits), 2) if fits else 1.0
    if objective == 'nutrients':
        honesty = ('ONE recipe, per-person portions, objective = nutrients: each scale is the 0.05-grid '
                   'point inside the variation\'s bounds minimising the weighted squared relative error '
                   'over calories / protein / fiber (targets) and sodium (ceiling — excess penalised, '
                   'shortfall free) against the person\'s own per-slot lines (calorie envelope, the day '
                   'rollup\'s thresholds, the sodium CDRR); the weights are a labelled convention prior; '
                   'a nutrient with no line or no rollup is named, not guessed; the driver and the '
                   'compromise are stated per person, never hidden')
    else:
        honesty = ('ONE recipe, per-person portions: scale = the person\'s slot share of '
                   'their daily calorie target ÷ the meal\'s kcal per serving, clamped to the '
                   'variation\'s scale bounds; nobody gets a perfect meal — the compromise is '
                   'stated per person, never hidden; targets and shares are the existing '
                   'labeled priors')
    return {'ok': True, 'schema': 'portion-fit/1', 'template': t.name,
            'variation': getattr(v, 'name', '') if v else '', 'slot': slot,
            'mealKcalPerServing': round(kcal1, 0), 'fits': fits,
            'servingSplit': {f['person']: f.get('scale', 1.0) for f in fits},
            'totalScale': total_scale, 'compromises': compromises,
            'objective': objective, 'objectives': list(PORTION_OBJECTIVES),
            'weights': fit_weights, 'weightsLabel': FIT_WEIGHTS_LABEL,
            'weightsUsed': objective == 'nutrients',
            'unknownWeights': unknown_weights, 'scaleStep': SCALE_STEP,
            'honesty': honesty}


def _parse_list(value, universe, all_word='all'):
    if value in (None, '', all_word, [all_word]):
        return list(universe), True
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace(';', ',').split(',') if p.strip()]
    else:
        parts = [str(p).strip() for p in value]
    return parts, False


def apply_meal_proposal(manager, plan, template, variation='', slots='all', days='all',
                        person='', scale=0.0):
    """Proposed MealEntry rows for a meal across slots × days, with
    per-person portions; existing entries are NAMED and skipped."""
    plan_row = plan if not isinstance(plan, str) else _named(manager, 'MealPlanDefinition', plan)
    if plan_row is None:
        return {'ok': False, 'error': f"MealPlanDefinition '{plan}' not found", 'proposals': []}
    t = _named(manager, 'MealTemplate', template)
    if t is None:
        return {'ok': False, 'error': f"MealTemplate '{template}' not found — pick one from the "
                                      f"meals table", 'proposals': []}
    template_slots = _json_list(t, 'slots_json') or list(MEAL_SLOTS)
    people = [person] if person else _members(manager, plan_row)
    n_days = int(getattr(plan_row, 'days', 0) or 0) or 7
    day_list, _ = _parse_list(days, range(1, n_days + 1))
    try:
        day_list = [int(d) for d in day_list]
    except ValueError:
        return {'ok': False, 'error': f"days must be numbers like '1,3,5' or 'all' — got {days!r}",
                'proposals': []}
    bad_days = [d for d in day_list if d < 1 or d > n_days]
    slot_list, all_slots = _parse_list(slots, template_slots)
    if all_slots:
        # 'all' = the template's slots that the people actually eat
        eaten = set()
        for p in people:
            eaten |= {s.get('slot') for s in expected_slots(manager, p)['slots']}
        slot_list = [s for s in template_slots if s in eaten] or template_slots
    unknown = [s for s in slot_list if s not in MEAL_SLOTS]
    warnings = [f"'{s}' is not a slot this template is written for ({', '.join(template_slots)}) — "
                f"planned anyway (pattern consistency is a warning, not a block)"
                for s in slot_list if s not in template_slots]
    existing = {(int(getattr(e, 'day_index', 0) or 0), getattr(e, 'slot', '')): e
                for e in _rows(manager, 'MealEntry') if getattr(e, 'plan_name', '') == plan_row.name}
    proposals, already = [], []
    fits_by_slot = {}
    for slot in slot_list:
        if slot in unknown:
            continue
        if scale and float(scale) > 0:
            split = {p: float(scale) for p in people}
            total = round(float(scale) * len(people), 2)
            fits_by_slot[slot] = {'fixedScale': float(scale)}
        else:
            fit = portion_fit(manager, t, variation, slot, people)
            split = fit.get('servingSplit', {}) if fit.get('ok') else {p: 1.0 for p in people}
            total = fit.get('totalScale', float(len(people))) if fit.get('ok') else float(len(people))
            fits_by_slot[slot] = {'fits': fit.get('fits', []), 'compromises': fit.get('compromises', [])}
        for day in day_list:
            if day in bad_days:
                continue
            if (day, slot) in existing:
                already.append({'day': day, 'slot': slot, 'entry': existing[(day, slot)].name,
                                'template': getattr(existing[(day, slot)], 'template_name', ''),
                                'note': 'already planned — edit or delete that entry to replace it'})
                continue
            v = variation
            if not v:
                vs = [x for x in _rows(manager, 'VariationDefinition') if getattr(x, 'template_name', '') == t.name]
                v = next((x.name for x in vs if x.name.endswith('-base')), vs[0].name if vs else '')
            proposals.append({
                'name': f'{plan_row.name}-d{day}-{slot}', 'plan_name': plan_row.name,
                'day_index': day, 'slot': slot, 'template_name': t.name, 'variation_name': v,
                'scale': total, 'time_hhmm': '', 'serving_split_json': json.dumps(split),
                'is_prior': False, 'provenance_id': 'mpc-apply',
                'notes': f'applied from the meals page ({len(people)} portion(s): ' +
                         ', '.join(f'{p} ×{s}' for p, s in split.items()) + ')'})
    return {'ok': True, 'schema': 'apply-meal/1', 'plan': plan_row.name, 'template': t.name,
            'people': people, 'slots': slot_list, 'days': day_list,
            'proposals': proposals, 'alreadyPlanned': already,
            'unknownSlots': unknown, 'daysOutOfRange': bad_days, 'warnings': warnings,
            'portions': fits_by_slot,
            'counts': {'proposed': len(proposals), 'alreadyPlanned': len(already)},
            'honesty': ('proposals only — the "Add to the week" form runs the no-code solution '
                        'that writes them (GenerateEvent → MealEntry, dedupe by name); the entry '
                        'trigger then re-coordinates pre-prep, packing, dishes and the allocation')}
