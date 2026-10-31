"""
@module board.esd_areas_api

esd-0 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): the doors of ESD PROTECTION AREAS on a Board's definition (board.custom.esd_areas). An area's name carries
its target (a net like /rect_out), so every door that names an area takes it in the BODY - a slash cannot ride in a path segment here.

GET  /api/board/esd-areas/{kind}/{definition}          {ok, rows}  the flagged areas
POST /api/board/esd-areas/{kind}/{definition}          {scope, target, inject_net?, protection_refs?, model?, level_v?, abs_max_v?, recover_*?,
                                                        document?, page_table?}  flag a piece (201; again = update)
POST /api/board/esd-areas/{kind}/{definition}/toggle   {scope, target}  flag it, or unflag it when flagged (the page's row button)
POST /api/board/esd-areas/unflag                       {name}
PUT  /api/board/esd-areas/quantity                     {area, quantity, value}  level_v | abs_max_v | recover_pct | recover_mv | recover_us
The events run on a PCB's circuit: POST /api/pcb/{board}/esd-run (pcb.pcb_esd_api).
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: '200 OK', 201: '201 Created', 400: '400 Bad Request', 404: '404 Not Found'}


class EsdAreasAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/esd-areas/unflag', self, suffix='unflag')
            add('/api/board/esd-areas/quantity', self, suffix='quantity')
            add('/api/board/esd-areas/{kind}/{definition}', self, suffix='areas')
            add('/api/board/esd-areas/{kind}/{definition}/toggle', self, suffix='toggle')

    @staticmethod
    def _body(request, response):
        try:
            return json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
        except ValueError:
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'the body is not JSON'}
            return None

    def _send(self, response, status, body):
        response.status, response.media = _STATUS[status], body

    def on_get_areas(self, request, response, kind, definition):
        from board.custom import esd_areas as EA
        self._send(response, 200, {'ok': True, 'rows': EA.areas(self.manager, kind, definition)})

    def on_post_areas(self, request, response, kind, definition):
        from board.custom import esd_areas as EA
        body = self._body(request, response)
        if body is not None:
            self._send(response, *EA.flag(self.manager, kind, definition, body))

    def on_post_toggle(self, request, response, kind, definition):
        from board.custom import esd_areas as EA
        body = self._body(request, response)
        if body is not None:
            self._send(response, *EA.toggle(self.manager, kind, definition, body))

    def on_post_unflag(self, request, response):
        from board.custom import esd_areas as EA
        body = self._body(request, response)
        if body is not None:
            self._send(response, *EA.unflag(self.manager, str(body.get('name', ''))))

    def on_put_quantity(self, request, response):
        from board.custom import esd_areas as EA
        body = self._body(request, response)
        if body is not None:
            self._send(response, *EA.set_quantity(self.manager, str(body.get('area', '')), body.get('quantity'), body.get('value')))
