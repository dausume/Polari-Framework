"""
@module meshassets.mesh_asset_api

/api/meshassets/* — the licence-verified catalog, the pick-and-
choose candidate ranking per organ, and one asset's fit against one
organ.

@consumers polariServer (constructed when 'meshassets' is enabled)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from meshassets.mesh_fit import (
    candidates_for_organ, citation_manifest, citation_record,
    fit_asset_to_organ, source_catalog,
)


class MeshAssetsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/meshassets'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/meshassets/sources', self, suffix='sources')
            add('/api/meshassets/candidates/{organ_name}', self,
                suffix='candidates')
            add('/api/meshassets/fit/{organ_name}/{asset_name}',
                self, suffix='fit')
            # Citations as data: the manifest a release ships, and
            # one asset's credit on its own.
            add('/api/meshassets/citations', self,
                suffix='citations')
            add('/api/meshassets/citation/{asset_name}', self,
                suffix='citation')

    def on_get_sources(self, request, response):
        response.media = source_catalog(self.manager)

    def on_get_candidates(self, request, response, organ_name):
        try:
            floor = float(request.params.get('minFidelity', 0.0))
        except (TypeError, ValueError):
            floor = 0.0
        out = candidates_for_organ(self.manager, organ_name,
                                   min_fidelity=floor)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_citations(self, request, response):
        response.media = citation_manifest(self.manager)

    def on_get_citation(self, request, response, asset_name):
        out = citation_record(self.manager, asset_name)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_fit(self, request, response, organ_name, asset_name):
        out = fit_asset_to_organ(self.manager, organ_name,
                                 asset_name)
        if not out.get('ok'):
            response.status = '400 Bad Request'
        response.media = out
