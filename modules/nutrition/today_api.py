"""
@cross-cutting
@module nutrition.today_api
@tags @xc:bindings

N2 — the TODAY page's routes:

  GET  /api/mealplanning/today/{person}?day=YYYY-MM-DD   the person's
       day (lines in order, next up, counts, ledger so far)
  POST /api/mealplanning/today/{person}/done  {event, minutes?}
       mark an event done THROUGH the no-code solution
       'today-mark-done-form' (the same graph the page's form runs):
       ledger row → observation (only with minutes) → status done.

@consumers polariServer (route registration, gated on nutrition),
  the /display/mealplan/today page
"""

from objectTreeDecorators import treeObject, treeObjectInit

from nutrition.today_analysis import mark_done_proposal, person_day

SOLUTION_NAME = 'today-mark-done-form'


def _solution_on_node(manager, name):
    """The SolutionDefinition row's graph when seeded on this node,
    else the in-tree seed (a fresh node before the upsert)."""
    from polariNoCode.event_dispatcher import get_dispatcher
    d = get_dispatcher(manager)
    graph = d._solution(name) if d is not None else None
    if graph is None:
        import json
        from nutrition.today_seed import SEED_TODAY_SOLUTIONS
        for s in SEED_TODAY_SOLUTIONS:
            if s['name'] == name:
                graph = json.loads(s['definition'])
    return graph


def run_mark_done(manager, event_name, person, minutes_actual=None):
    """The POST's work: the proposal (for the reader) + the solution run
    through the REAL engine (the write). Never raises."""
    proposal = mark_done_proposal(manager, event_name, person, minutes_actual)
    if not proposal.get('ok'):
        return {**proposal, 'executed': False, 'status': 'refused'}
    graph = _solution_on_node(manager, SOLUTION_NAME)
    if graph is None:
        return {**proposal, 'executed': False, 'status': 'refused',
                'error': f"SolutionDefinition '{SOLUTION_NAME}' is not on this node"}
    from polariNoCode.graph_builder import execute
    params = {'event': event_name, 'person': person,
              'minutes_actual': minutes_actual if minutes_actual not in (None, '') else None}
    try:
        trace = execute(graph, manager=manager, params=params)
    except Exception as e:  # the engine's own errors read as a verdict
        return {**proposal, 'executed': False, 'status': 'failed',
                'error': f'{type(e).__name__}: {e}'}
    status = getattr(trace, 'status', '')
    return {**proposal, 'executed': status == 'completed', 'status': status,
            'executionId': getattr(trace, 'execution_id', ''),
            'error': getattr(trace, 'error_summary', None) or None,
            'solution': SOLUTION_NAME}


class TodayAPI(treeObject):
    """The Today page's derived-view + mark-done routes."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/mealplanning/today'
        if polServer is not None:
            try:
                add = polServer.falconServer.add_route
                add('/api/mealplanning/today/{person}', self, suffix='day')
                add('/api/mealplanning/today/{person}/done', self, suffix='done')
            except Exception as e:  # a route clash must not stop boot
                print(f'[TodayAPI] route registration skipped: {e}', flush=True)

    def _mgr(self):
        return getattr(self, 'manager', None) or getattr(self.polServer, 'manager', None)

    def on_get_day(self, request, response, person):
        response.media = person_day(self._mgr(), person,
                                    day=request.params.get('day') or None)

    def on_post_done(self, request, response, person):
        body = request.get_media(default_when_empty={}) if hasattr(request, 'get_media') \
            else (getattr(request, 'media', None) or {})
        body = body or {}
        event = body.get('event') or request.params.get('event') or ''
        minutes = body.get('minutes', body.get('minutes_actual'))
        if minutes is None:
            minutes = request.params.get('minutes')
        if not event:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': 'name the event: {"event": "<CalendarEvent.name>", '
                                                    '"minutes": <optional actual minutes>}'}
            return
        result = run_mark_done(self._mgr(), event, person, minutes)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
