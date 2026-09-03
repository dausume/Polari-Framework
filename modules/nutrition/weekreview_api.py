"""
@cross-cutting
@module nutrition.weekreview_api
@tags @xc:bindings

N5 — the weekly review's read surface (pure data, nothing written):

  GET /api/mealplanning/review?plan=&household=&week=[&section=]
        the review (headline scalars + lines + proposals + honesty);
        `section=coverage|intake|cost|waste|fairness|proposals`
        answers {'lines': [...]} for that section only (the page's
        per-section panels)
  GET /api/mealplanning/review/next-week?plan=&household=&week=
        next week's event proposals (what the accept form writes)
  GET /api/mealplanning/review/event?plan=&household=&week=&date=
        the Sunday review-event proposal (what the trigger writes)

@consumers
  - polariServer (route registration, gated on nutrition)
  - the /display/mealplan/review page (weekreview_seed)
@see AI-Notes/designs/HOUSEHOLD_APP_PAGES.md §3.6
"""

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.weekreview_analysis import (
    SECTIONS, next_week_proposals, week_review, weekly_review_event_proposal,
)

ROUTES = ('/api/mealplanning/review', '/api/mealplanning/review/next-week',
          '/api/mealplanning/review/event')


def _args(request):
    p = request.params
    return {'plan': p.get('plan') or 'demo-alex-week',
            'household': p.get('household') or '',
            'week_start': p.get('week') or p.get('week_start') or None}


class WeekReviewAPI(treeObject):
    """The weekly review's derived-view routes."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/mealplanning/review'
        if polServer is not None:
            try:
                add = polServer.falconServer.add_route
                add(ROUTES[0], self, suffix='review')
                add(ROUTES[1], self, suffix='next_week')
                add(ROUTES[2], self, suffix='review_event')
            except Exception as e:  # never break boot over one surface
                print(f'[WeekReviewAPI] route registration failed: {e}', flush=True)

    def on_get_review(self, request, response):
        args = _args(request)
        review = week_review(self.manager, **args)
        section = (request.params.get('section') or '').strip()
        if section:
            if section not in SECTIONS:
                response.status = '400 Bad Request'
                response.media = {'ok': False,
                                  'error': f'unknown section "{section}" — one of '
                                           f'{", ".join(SECTIONS)}'}
                return
            response.media = {'ok': True, 'schema': 'week-review-section/1',
                              'section': section, 'weekStart': review['weekStart'],
                              'weekEnd': review['weekEnd'],
                              'lines': [l for l in review['lines'] if l['section'] == section]}
            return
        response.media = review

    def on_get_next_week(self, request, response):
        response.media = next_week_proposals(self.manager, **_args(request))

    def on_get_review_event(self, request, response):
        args = _args(request)
        response.media = weekly_review_event_proposal(
            self.manager, review_date=request.params.get('date') or None,
            review_time=request.params.get('time') or None, **args)
