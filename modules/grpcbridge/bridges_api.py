"""
@module grpcbridge.bridges_api

hsp-3a doors (HARDWARE_SYSTEM_PINS_PLAN.md §7): where the bench's bridges are.

GET /api/grpc/bench-bridges/{bench}[?view=bridges|paths|hops]
        bridges = PolariBridgeInstance rows with status recomputed (bound | gap, why: a bridge without a polari_node refuses); paths = BridgePath rows with
        their hop chain; hops = one row per hop (kind, what, signal level cited or -1, basis). Without `view`: all three. 422 unknown view.
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from grpcbridge.custom import bridge_paths as BP

VIEWS = ('bridges', 'paths', 'hops')


class BenchBridgesAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/grpc/bench-bridges/{bench}', self)

    def _table(self, name):
        rows = list(((getattr(self.manager, 'objectTables', None) or {}).get(name) or {}).values())
        return rows or None

    def on_get(self, request, response, bench):
        out = BP.bench_bridges(bench, self._table('PolariBridgeInstance'), self._table('BridgePath'))
        view = request.get_param('view') or ''
        if not view:
            response.media = out
            return
        if view not in VIEWS:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'view must be one of %s' % ', '.join(VIEWS)}
            return
        response.media = {'ok': True, 'bench': bench, 'view': view, 'count': len(out[view]), 'rows': out[view]}
