"""
@module bizops.bizops_api

/api/bizops/* — setup/upgrade flows, the local-economy track, and
the order planner (biz-1).

@consumers polariServer (constructed when _feature_available('bizops'))
"""

from objectTreeDecorators import treeObject, treeObjectInit

from bizops.bizops_flows import (
    business_flow_report, local_economy_report,
)
from bizops.bizops_planner import (
    lead_time_quote, order_plan, prestage_plan, product_readiness,
)


class BizOpsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/bizops'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/bizops/flows/{business}', self, suffix='flows')
            add('/api/bizops/economy', self, suffix='economy')
            add('/api/bizops/plan/{business}', self, suffix='plan')
            add('/api/bizops/prestage/{business}', self,
                suffix='prestage')
            add('/api/bizops/quote/{business}', self,
                suffix='quote')
            add('/api/bizops/readiness/{business}', self,
                suffix='readiness')

    def on_get_flows(self, request, response, business):
        out = business_flow_report(self.manager, business)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_economy(self, request, response):
        out = local_economy_report(self.manager)
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_prestage(self, request, response, business):
        out = prestage_plan(
            self.manager, business,
            budget_usd=float(request.params.get('budgetUsd', 100.0)),
            horizon_days=int(request.params.get('horizonDays', 30)))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_quote(self, request, response, business):
        p = request.params
        out = lead_time_quote(
            self.manager, business,
            variant=p.get('variant', ''),
            unit_volume_l=float(p.get('volumeL', 1.0)),
            quantity=int(p.get('quantity', 1)),
            lead_limit_days=(int(p['leadLimitDays'])
                             if 'leadLimitDays' in p else None))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_readiness(self, request, response, business):
        p = request.params
        out = product_readiness(
            self.manager, business,
            sold_threshold=(int(p['soldThreshold'])
                            if 'soldThreshold' in p else None))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out

    def on_get_plan(self, request, response, business):
        out = order_plan(
            self.manager, business,
            horizon_days=int(request.params.get('horizonDays', 30)))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out
