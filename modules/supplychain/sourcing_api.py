"""
@module supplychain.sourcing_api

/api/supplychain/sourcing/* — sources with ladder ranks, cross-source
price comparison, preferred-source with develop-the-potential
suggestions, and scenario price-drift findings (src-1).

@consumers polariServer (constructed with SupplyChainAPI)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from supplychain.sourcing_analysis import (
    preferred_source, price_compare, scenario_price_drift,
    source_catalog,
)


class SourcingAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/supplychain/sourcing'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/supplychain/sourcing/sources', self,
                suffix='sources')
            add('/api/supplychain/sourcing/prices/{item_ref}', self,
                suffix='prices')
            add('/api/supplychain/sourcing/preferred/{item_ref}',
                self, suffix='preferred')
            add('/api/supplychain/sourcing/scenario-drift', self,
                suffix='drift')

    def _policy(self, request):
        return request.params.get('policy', '')

    def on_get_sources(self, request, response):
        response.media = source_catalog(self.manager,
                                        self._policy(request))

    def on_get_prices(self, request, response, item_ref):
        out = price_compare(self.manager, item_ref,
                            self._policy(request))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_preferred(self, request, response, item_ref):
        out = preferred_source(self.manager, item_ref,
                               self._policy(request))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_post_drift(self, request, response):
        body = request.media if request.content_length else {}
        table = getattr(self.manager, 'objectTables', {}).get(
            'BusinessScenarioDefinition', {})
        scenario = None
        for row in table.values():
            if getattr(row, 'name', None) == body.get('scenario', ''):
                scenario = row
                break
        if scenario is None:
            response.status = '400 Bad Request'
            response.media = {
                'ok': False,
                'refusal': f'no BusinessScenarioDefinition named '
                           f'"{body.get("scenario", "")}"'}
            return
        response.media = scenario_price_drift(
            self.manager, scenario, self._policy(request))
