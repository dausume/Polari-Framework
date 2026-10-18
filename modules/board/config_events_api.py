"""
@module board.config_events_api

pv-4 (PIN_VIEW_PLAN.md 2.4 / 2.9): the configuration-event doors — thin falcon handlers over board.custom.config_events (the bodies live there; this file only routes).

GET  /api/board/{board}/config-events[?instance=&system=&binding=&pins=0]     the timeline: events derived from InstallRecord / canvas BoardPinNet rows plus the recorded ConfigurationEvent rows, oldest first
POST /api/board/{board}/config-events    {kind, cause, who, when?, board_instance?, refs?, pins?, binding?}   record a real-world event; the refs are validated, an unknown kind is refused by name (400)
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit

STATUS = {200: falcon.HTTP_200, 201: falcon.HTTP_201, 400: falcon.HTTP_400, 404: falcon.HTTP_404}


class ConfigEventsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/board/{board}/config-events', self, suffix='events')

    def on_get_events(self, request, response, board):
        """pv-4: the configuration-event timeline of a board design (or one instance)."""
        from board.custom import config_events as CE
        status, payload = CE.get_door(self.manager, board, request.params)
        response.status = STATUS[status]
        response.media = payload

    def on_post_events(self, request, response, board):
        """pv-4: record one real-world configuration event."""
        from board.custom import config_events as CE
        raw = request.bounded_stream.read() or b''
        try:
            body = json.loads(raw) if raw.strip() else {}
        except ValueError as e:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return
        status, payload = CE.post_door(self.manager, board, body)
        response.status = STATUS[status]
        response.media = payload
