"""
@module supplychain.sourcing_api

/api/supplychain/sourcing/* — sources with ladder ranks, cross-source
price comparison, preferred-source with develop-the-potential
suggestions, and scenario price-drift findings (src-1).

@consumers polariServer (constructed with SupplyChainAPI)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from supplychain.formula_analysis import (
    cheapest_blend, formula_cost, formulas_catalog,
    product_cost_comparison, requirement_coverage,
)
from supplychain.sourcing_analysis import (
    _named, preferred_source, price_compare, scenario_price_drift,
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
            add('/api/supplychain/sourcing/requirements/{item_ref}',
                self, suffix='requirements')
            add('/api/supplychain/sourcing/formulas', self,
                suffix='formulas')
            add('/api/supplychain/sourcing/formula-cost/{name}',
                self, suffix='formula_cost')
            add('/api/supplychain/sourcing/cheapest-blend/{item_ref}',
                self, suffix='cheapest')
            add('/api/supplychain/sourcing/compare/{item_ref}',
                self, suffix='compare')

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

    def on_get_requirements(self, request, response, item_ref):
        out = requirement_coverage(self.manager, item_ref,
                                   self._policy(request))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_formulas(self, request, response):
        response.media = formulas_catalog(self.manager,
                                          self._policy(request))

    def on_get_formula_cost(self, request, response, name):
        formula = _named(self.manager, 'ProductFormula', name)
        if formula is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'refusal': f'no ProductFormula '
                                         f'named "{name}"'}
            return
        out = formula_cost(
            self.manager, formula, self._policy(request),
            source_choice=request.params.get('sources', 'cheapest'))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_cheapest(self, request, response, item_ref):
        out = cheapest_blend(
            self.manager, item_ref, self._policy(request),
            source_choice=request.params.get('sources', 'cheapest'))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_compare(self, request, response, item_ref):
        out = product_cost_comparison(self.manager, item_ref,
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
