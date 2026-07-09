"""
@cross-cutting
@module waxsupply.wax_api
@tags @xc:bindings

HTTP surface for wax-1 bio wax sources:

  GET /api/wax/sources                     the full catalogue.
  GET /api/wax/sources/hydroponic          only in-system-growable ones.
  GET /api/wax/for-use?use=mold            ranked sources for a use
                                           (mold / electronic-mask ...).
  GET /api/wax/sources/{name}/yield?units=&years=   projected output.

Sources are edited through CRUDE (object-coherence).

@consumers
  - wax frontend (later); supplychain (wax as a material output)
@see materialsScience wax materials
"""

from objectTreeDecorators import treeObject, treeObjectInit
from waxsupply.wax_analysis import (
    hydroponic_wax_sources, wax_catalog, wax_for_use, wax_yield,
)


class WaxSupplyAPI(treeObject):
    """wax-1 endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/wax'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/wax/sources', self, suffix='sources')
            polServer.falconServer.add_route(
                '/api/wax/sources/hydroponic', self, suffix='hydroponic')
            polServer.falconServer.add_route(
                '/api/wax/for-use', self, suffix='foruse')
            polServer.falconServer.add_route(
                '/api/wax/sources/{name}/yield', self, suffix='yield')

    def on_get_sources(self, request, response):
        response.media = wax_catalog(self.manager)

    def on_get_hydroponic(self, request, response):
        response.media = hydroponic_wax_sources(self.manager)

    def on_get_foruse(self, request, response):
        use = (request.params or {}).get('use', 'mold')
        result = wax_for_use(self.manager, use)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_yield(self, request, response, name):
        params = request.params or {}
        result = wax_yield(self.manager, name,
                           units=float(params.get('units', 1.0) or 1.0),
                           years=float(params.get('years', 1.0) or 1.0))
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
