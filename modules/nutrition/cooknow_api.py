"""
@module nutrition.cooknow_api

N4 — the Cook-now page's routes (HOUSEHOLD_APP_PAGES.md §3.4):

  GET  /api/mealplanning/cooknow/{person}?template=&variation=&event=
       the cook sheet (nutrition.cooknow_analysis.cook_sheet)
  POST /api/mealplanning/cooknow/{person}/step-done
       {template, step, minutes, date?, variation?, dry?}
       → the DurationObservation proposal; WRITTEN through the event
       dispatcher's create path (dedupe by name) unless dry is true —
       the same row the no-code "Step done" form solution writes.

Registered by polariServer beside MealPlanningAPI (the constructor
idiom is the same; the orchestrator wires it).

@consumers polariApiServer.polariServer (nutrition gate)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class CookNowAPI(treeObject):
    """The Cook-now page's derived views + the step-done write."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/mealplanning/cooknow'
        if polServer is not None:
            try:
                add = polServer.falconServer.add_route
                add('/api/mealplanning/cooknow/{person}', self, suffix='sheet')
                add('/api/mealplanning/cooknow/{person}/step-done', self,
                    suffix='step_done')
            except Exception as e:  # never break boot
                print(f'[CookNowAPI] route registration failed: {e}', flush=True)

    def on_get_sheet(self, request, response, person):
        from nutrition.cooknow_analysis import cook_sheet
        p = request.params
        response.media = cook_sheet(
            self.manager, p.get('template') or 'chicken-bowl-dinner', person,
            p.get('variation') or '', p.get('event') or None)

    def on_post_step_done(self, request, response, person):
        from nutrition.cooknow_analysis import step_done_proposal
        body = request.get_media() if hasattr(request, 'get_media') else (request.media or {})
        body = body or {}
        proposal = step_done_proposal(
            self.manager, body.get('template') or 'chicken-bowl-dinner',
            body.get('step', 0), person, body.get('minutes', 0),
            body.get('date') or '', body.get('variation') or '')
        if not proposal.get('ok'):
            response.status = '400 Bad Request'
            response.media = proposal
            return
        if body.get('dry') in (True, 1, '1', 'true', 'yes'):
            response.media = dict(proposal, written=None, dry=True)
            return
        from polariNoCode.event_dispatcher import create_instance, find_instance
        row = proposal['proposals'][0]
        existing = find_instance(self.manager, 'DurationObservation', row['name'])
        if existing is None:
            inst = create_instance(self.manager, 'DurationObservation', row)
            created = True
        else:
            inst, created = existing, False
        response.media = dict(proposal, dry=False,
                              written={'class': 'DurationObservation',
                                       'name': str(getattr(inst, 'name', '')),
                                       'id': str(getattr(inst, 'id', '')),
                                       'created': created})
