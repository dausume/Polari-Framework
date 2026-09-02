"""
@cross-cutting
@module nutrition.rating_analysis
@tags @xc:bindings

mpb-8 — ratings into ranking: per-person (and household-wide)
averages per template/variation, and a rank overlay any suggestion
surface can apply — the PERSON'S OWN history ranks first, the
household's second, unrated templates keep a neutral middle rank
with 'unrated' said plainly. Ranking only: a 1-star template still
appears (tastes change; nothing is hidden).

@consumers
  - nutrition.mealplanning_api (ratings route + ranked templates)
  - nutrition.selftest_rating
@see AI-Notes/plans/MEAL_PLANNING_APP_PLAN.md §3b mpb-8
"""

from nutrition.person_analysis import _f, _rows


def rating_summary(manager, person_name=None):
    """Averages per template (and per variation) — the person's
    own when named, everyone's otherwise."""
    buckets = {}
    count = 0
    for row in _rows(manager, 'MealRating'):
        if person_name and getattr(row, 'person_name', '') \
                != person_name:
            continue
        rating = _f(row, 'rating', 0.0)
        if not 1 <= rating <= 5:
            continue
        count += 1
        template = getattr(row, 'template_name', '')
        bucket = buckets.setdefault(template, {
            'template': template, 'ratings': 0, 'sum': 0.0,
            'variations': {}, 'latestNote': ''})
        bucket['ratings'] += 1
        bucket['sum'] += rating
        note = getattr(row, 'note', '')
        if note:
            bucket['latestNote'] = note
        variation = getattr(row, 'variation_name', '')
        if variation:
            v = bucket['variations'].setdefault(
                variation, {'ratings': 0, 'sum': 0.0})
            v['ratings'] += 1
            v['sum'] += rating
    templates = []
    for bucket in buckets.values():
        entry = {'template': bucket['template'],
                 'ratings': bucket['ratings'],
                 'avg': round(bucket['sum'] / bucket['ratings'], 2),
                 'latestNote': bucket['latestNote'],
                 'variations': {
                     name: round(v['sum'] / v['ratings'], 2)
                     for name, v in bucket['variations'].items()}}
        templates.append(entry)
    templates.sort(key=lambda e: -e['avg'])
    return {'ok': True, 'schema': 'meal-ratings/1',
            'person': person_name or '(everyone)',
            'ratingCount': count,
            'templates': templates,
            'honesty': 'ratings RANK, they never gate — a low '
                       'rating hides nothing and deletes nothing'}


def rank_templates(manager, person_name, template_names):
    """Order candidate templates: the person's own average first,
    the household-wide average second, unrated in the middle at a
    neutral 3.0 labeled 'unrated'."""
    own = {e['template']: e['avg']
           for e in rating_summary(manager, person_name)
           ['templates']}
    everyone = {e['template']: e['avg']
                for e in rating_summary(manager)['templates']}
    ranked = []
    for template in template_names:
        if template in own:
            score, basis = own[template], 'your ratings'
        elif template in everyone:
            score, basis = everyone[template], 'household ratings'
        else:
            score, basis = 3.0, 'unrated (neutral)'
        ranked.append({'template': template,
                       'score': score, 'basis': basis})
    ranked.sort(key=lambda e: -e['score'])
    return {'ok': True, 'schema': 'template-rank/1',
            'person': person_name,
            'ranked': ranked,
            'honesty': 'a ranking convenience over declared '
                       'ratings — nothing below the top is hidden '
                       'or blocked'}
