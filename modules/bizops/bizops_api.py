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
from bizops.bizops_planner import order_plan


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

    def on_get_plan(self, request, response, business):
        out = order_plan(
            self.manager, business,
            horizon_days=int(request.params.get('horizonDays', 30)))
        if not out.get('ok'):
            response.status = '404 Not Found'
        response.media = out
