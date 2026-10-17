"""
@module board.pin_view_api

pv-0 (PIN_VIEW_PLAN.md 2.5 / 2.9): the pin view's doors — thin falcon handlers over board.custom.pin_view (the bodies live there; this file only routes).

GET /api/board/{board}/pin-view?system=&binding=&mission=&stage=&phase=&protocol=    surfaces + pins + connections (+ shapes, the protocol vocabulary, the stage echo)
GET /api/board/{board}/pin-view/pins          flat rows for a configured table (same filters; + level= surface= kind=)
GET /api/board/{board}/pin-view/connections   flat rows: both ends, kind, via, the Drive / Signal / Use summaries
GET /api/board/{board}/pin-view/surfaces      flat rows: pin counts by stage

stage ∈ base | after-init | tasks-assigned | firmware-committed; protocol ∈ a family (gpio interrupt pwm-timer analog uart spi i2c usb clock reset-programming power ground) — a set
(spi, i2c, uart, usb) expands to its child signals. A bad parameter is 400, an unknown board or system 404.
"""
import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class PinViewAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/{board}/pin-view', self, suffix='view')
            add('/api/board/{board}/pin-view/pins', self, suffix='pins')
            add('/api/board/{board}/pin-view/connections', self, suffix='connections')
            add('/api/board/{board}/pin-view/surfaces', self, suffix='surfaces')

    def _serve(self, request, response, board, which):
        from board.custom import pin_view as PV
        status, payload = PV.door(self.manager, board, request.params, which)
        response.status = {200: falcon.HTTP_200, 400: falcon.HTTP_400, 404: falcon.HTTP_404}[status]
        response.media = payload

    def on_get_view(self, request, response, board):
        """pv-0: the composed pin view."""
        self._serve(request, response, board, '')

    def on_get_pins(self, request, response, board):
        """pv-0: every pin at every level, one row each."""
        self._serve(request, response, board, 'pins')

    def on_get_connections(self, request, response, board):
        """pv-0: every pin-to-pin connection with its Drive / Signal / Use summaries, one row each."""
        self._serve(request, response, board, 'connections')

    def on_get_surfaces(self, request, response, board):
        """pv-0: every surface (board, enclosures, dies, board parts, bench parts) with its pin counts by stage."""
        self._serve(request, response, board, 'surfaces')
