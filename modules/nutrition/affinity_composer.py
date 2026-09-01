"""
@cross-cutting
@module nutrition.affinity_composer
@tags @xc:bindings

nmp-11 — the composer (decision 11): intent in ("add diced chicken"
+ N meals, which slot, this week) -> affinity-ranked PLACEMENTS into
the week's compatible templates, a week-wide AUTO-BALANCE proposed
as a DIFF (a human applies it; the nmp-4 gate keeps doing the
refusing), and counterbalance suggestions FILTERED BY FIT.

Soft by design: low affinity NEVER blocks — the lowest-ranked
placement still appears, with a gentle "unusual for this dish"
note. The ranking context is the person's stated cuisine knob
(PersonProfile.cuisine_context), falling back to general-western;
nothing is inferred.

@consumers
  - nutrition.nutrition_api
@see AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-11
"""

from nutrition.affinity_basis import DEFAULT_CONTEXT
from nutrition.meal_analysis import _json_list, _named, plan_rollup
from nutrition.person_analysis import _f, _rows

UNUSUAL_BELOW = 0.15


def _roles_of(manager, food):
    return [getattr(r, 'role_name', '')
            for r in _rows(manager, 'FoodRole')
            if getattr(r, 'food_name', '') == food]


def affinity_for(manager, food, dish_base, context=DEFAULT_CONTEXT):
    """Resolve one food's affinity to a dish base in a context.

    Direct food rows outrank role rows; a missing context falls back
    to general-western; nothing matching = a low default (0.1) —
    unknown is ranked low, never refused."""
    rows = list(_rows(manager, 'IngredientAffinity'))

    def _lookup(subject, ctx):
        best = None
        for a in rows:
            if (getattr(a, 'subject', '') == subject
                    and getattr(a, 'dish_base', '') == dish_base
                    and getattr(a, 'context', '') == ctx):
                w = _f(a, 'weight', 0.0)
                if best is None or w > best[0]:
                    best = (w, getattr(a, 'source', ''))
        return best

    for ctx in (context, DEFAULT_CONTEXT):
        hit = _lookup(food, ctx)
        if hit is not None:
            return {'weight': hit[0], 'basis': f'food row ({ctx})',
                    'source': hit[1]}
        role_best = None
        for role in _roles_of(manager, food):
            hit = _lookup(role, ctx)
            if hit is not None and (role_best is None
                                    or hit[0] > role_best[0][0]):
                role_best = (hit, role)
        if role_best is not None:
            return {'weight': role_best[0][0],
                    'basis': f'role {role_best[1]} ({ctx})',
                    'source': role_best[0][1]}
        if ctx == context and context == DEFAULT_CONTEXT:
            break
    return {'weight': 0.1, 'basis': 'no norm row — unknown ranks '
                                    'low, never refused',
            'source': ''}


def compose(manager, plan, food, meals_count=1, slot='',
            context=''):
    """Decision 11: place `food` into the week, as a DIFF proposal."""
    plan_name = getattr(plan, 'name', '')
    person = _named(manager, 'PersonProfile',
                    getattr(plan, 'person_name', ''))
    if not context:
        context = (getattr(person, 'cuisine_context', '')
                   if person is not None else '') or DEFAULT_CONTEXT
    food_row = _named(manager, 'FoodItem', food)
    if food_row is None:
        return {'ok': False, 'error': f'no FoodItem named "{food}"'}
    entries = [e for e in _rows(manager, 'MealEntry')
               if getattr(e, 'plan_name', '') == plan_name
               and (not slot or getattr(e, 'slot', '') == slot)]
    if not entries:
        return {'ok': False,
                'error': f'plan has no entries'
                         + (f' in slot "{slot}"' if slot else '')}
    ranked = []
    for e in entries:
        template = _named(manager, 'MealTemplate',
                          getattr(e, 'template_name', ''))
        if template is None:
            continue
        base = getattr(template, 'dish_base', '') or ''
        aff = affinity_for(manager, food, base, context) if base \
            else {'weight': 0.1,
                  'basis': 'template has no dish_base set',
                  'source': ''}
        ranked.append({'entry': getattr(e, 'name', ''),
                       'day': getattr(e, 'day_index', 0),
                       'slot': getattr(e, 'slot', ''),
                       'template': getattr(template, 'name', ''),
                       'dishBase': base,
                       'affinity': round(aff['weight'], 3),
                       'affinityBasis': aff['basis'],
                       'source': aff['source']})
    if not ranked:
        return {'ok': False, 'error': 'no templates resolvable'}
    ranked.sort(key=lambda r: -r['affinity'])
    placements = []
    for r in ranked[:max(1, int(meals_count))]:
        p = dict(r)
        p['proposal'] = (
            f'add {food} to "{p["template"]}" on day {p["day"]} '
            f'({p["slot"]}) — a DIFF: author it as a variation swap '
            f'or a new ingredient line; the nmp-4 gate re-checks '
            f'the template before it stands')
        if r['affinity'] < UNUSUAL_BELOW:
            p['note'] = (f'unusual for a {r["dishBase"] or "dish"} '
                         f'by the {context} norms — allowed, just '
                         f'saying')
        placements.append(p)
    # week-wide balance read: does the week already run over/under?
    balance = []
    roll = plan_rollup(manager, plan)
    if roll.get('ok'):
        for day, d in roll['days'].items():
            for o in d.get('overMax', []):
                balance.append({
                    'day': day, 'nutrient': o['nutrient'],
                    'kind': 'over',
                    'proposal': f'day {day} already exceeds '
                                f'{o["nutrient"]} — placing more '
                                f'food there needs a scale-down '
                                f'elsewhere (proposed, not applied)'})
    return {'ok': True, 'plan': plan_name, 'food': food,
            'context': context, 'slotFilter': slot,
            'placements': placements, 'ranked': ranked,
            'balanceDiff': balance,
            'honesty': 'a DIFF proposal — nothing is written; low '
                       'affinity ranks lower but never blocks '
                       '(banana-on-pasta is allowed)'}


def counterbalance(manager, plan, context=''):
    """For the week's under-target nutrients: suggest foods that FIT
    the week's dishes (affinity-filtered), richest-first."""
    person = _named(manager, 'PersonProfile',
                    getattr(plan, 'person_name', ''))
    if not context:
        context = (getattr(person, 'cuisine_context', '')
                   if person is not None else '') or DEFAULT_CONTEXT
    roll = plan_rollup(manager, plan)
    if not roll.get('ok'):
        return roll
    gaps = {}
    for day, d in roll['days'].items():
        for u in d.get('underTarget', []):
            g = gaps.setdefault(u['nutrient'], {'days': [], 'want': 0})
            g['days'].append(day)
            g['want'] += u['target'] - u['have']
    if not gaps:
        return {'ok': True, 'plan': getattr(plan, 'name', ''),
                'suggestions': [],
                'note': 'no under-target nutrients this week'}
    bases = set()
    for e in _rows(manager, 'MealEntry'):
        if getattr(e, 'plan_name', '') != getattr(plan, 'name', ''):
            continue
        t = _named(manager, 'MealTemplate',
                   getattr(e, 'template_name', ''))
        if t is not None and getattr(t, 'dish_base', ''):
            bases.add(t.dish_base)
    contents = {}
    for c in _rows(manager, 'NutrientContent'):
        contents.setdefault(getattr(c, 'nutrient_name', ''), []) \
            .append((getattr(c, 'food_name', ''),
                     _f(c, 'amount_per_100g', 0.0)))
    suggestions = []
    for nut, g in sorted(gaps.items()):
        rich = sorted(contents.get(nut, []), key=lambda t: -t[1])[:8]
        fits = []
        for food, per100 in rich:
            best = max(
                ({'base': b,
                  **affinity_for(manager, food, b, context)}
                 for b in bases),
                key=lambda a: a['weight'], default=None)
            if best is None:
                continue
            fits.append({'food': food, 'per100g': per100,
                         'bestDish': best['base'],
                         'affinity': round(best['weight'], 3)})
        fits.sort(key=lambda f: (-f['affinity'], -f['per100g']))
        suggestions.append({
            'nutrient': nut, 'days': sorted(set(g['days'])),
            'suggestedFoods': fits[:3],
            'note': 'ranked by FIT to this week\'s dishes, then '
                    'richness — norms rank, people decide'})
    return {'ok': True, 'plan': getattr(plan, 'name', ''),
            'context': context, 'suggestions': suggestions}
