"""
@module xr.xr_api

XrAPI (xr-1): the resolve surface. One read endpoint — the frontend
asks "what XR presentation does this space get, and WHY" and renders
the answer honestly (button, disabled reason, provenance line). Writes
go through the generated CRUDE endpoints on the settings rows — this
API never mutates.

@consumers
  - polariServer (instantiated next to ResourceProfilesAPI)
  - xr.selftest_xr (handler-level, fake manager)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from xr.xr_resolution import resolve_for_space


class XrAPI(treeObject):
    """GET /api/xr/resolve?space=<name>[&multiscale=<name>]"""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/xr'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/xr/resolve', self, suffix='resolve')

    def on_get_resolve(self, request, response):
        space = request.get_param('space') or ''
        multiscale = request.get_param('multiscale') or ''
        if not space:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'space query param is required'}
            return
        try:
            data = resolve_for_space(self.manager, space, multiscale)
        except ValueError as e:
            response.status = '404 Not Found'
            response.media = {'ok': False, 'error': str(e)}
            return
        response.media = {'ok': True, 'resolution': data}
