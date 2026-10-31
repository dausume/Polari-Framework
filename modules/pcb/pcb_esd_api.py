"""
@module pcb.pcb_esd_api

esd-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): the doors of ESD EVENTS on a PCB's circuit (pcb.custom.esd_events). Areas are flagged through
board.esd_areas_api.

GET  /api/pcb/esd-models                     {ok, rows}  the discharge networks, each with its standard, levels and caveat
POST /api/pcb/{board}/esd-run                {area, model?, level_v?, t_event?}  the event and its no-event baseline, both kept -> {ok, run, baseline,
                                             summary, rows}; 503 in words on a host with no libngspice (the attempt is kept)
GET  /api/pcb/runs/{run}/esd-results         {ok, summary, rows}  per node: peak, rise over the baseline, break check, recovery
GET  /api/pcb/runs/{run}/esd-chart           {ok, rows}  each protected node with and without the event, long form
"""
from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: '200 OK', 400: '400 Bad Request', 404: '404 Not Found', 409: '409 Conflict', 422: '422 Unprocessable Entity', 503: '503 Service Unavailable'}


class PcbEsdAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/pcb/esd-models', self, suffix='models')
            add('/api/pcb/{board}/esd-run', self, suffix='run')
            add('/api/pcb/runs/{run}/esd-results', self, suffix='results')
            add('/api/pcb/runs/{run}/esd-chart', self, suffix='chart')

    def on_get_models(self, request, response):
        from pcb.custom.esd_events import MODELS
        response.media = {'ok': True, 'rows': [dict(name=k, levels=', '.join('%g V' % v for v in m['levels']),
                                                    **{x: m[x] for x in ('kind', 'c_f', 'r_ohm', 'standard', 'caveat')}) for k, m in MODELS.items()]}

    def on_post_run(self, request, response, board):
        from pcb.custom import esd_events as E
        body = request.get_media() or {}
        try:
            level = float(body['level_v']) if body.get('level_v') not in (None, '') else None
            te = float(body['t_event']) if body.get('t_event') not in (None, '') else None
        except (TypeError, ValueError):
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'level_v and t_event must be numbers'}
            return
        if level is not None and not 0 <= level <= 30000:
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'level_v must be within 0 .. 30000 V'}
            return
        res = E.run_event(self.manager, board, str(body.get('area', '')), body.get('model') or None, level, te)
        response.status = _STATUS[res.pop('status', 200 if res.get('ok') else 422)]
        response.media = res

    def on_get_results(self, request, response, run):
        from pcb.custom import esd_events as E
        summary, rows, why = E.results(self.manager, run)
        response.status = '404 Not Found' if why else '200 OK'
        response.media = {'ok': not why, 'summary': summary, 'rows': rows, 'error': why}

    def on_get_chart(self, request, response, run):
        from pcb.custom import esd_events as E
        rows, why = E.chart(self.manager, run)
        response.status = '404 Not Found' if why else '200 OK'
        response.media = {'ok': not why, 'rows': rows, 'error': why}
