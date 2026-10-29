"""
@module grpcbridge.bridges_api

hsp-3a doors (HARDWARE_SYSTEM_PINS_PLAN.md §7): where the bench's bridges are.

GET /api/grpc/bench-bridges/{bench}[?view=bridges|paths|hops]
        bridges = PolariBridgeInstance rows with status recomputed (bound | gap, why: a bridge without a polari_node refuses); paths = BridgePath rows with
        their hop chain; hops = one row per hop (kind, what, signal level cited or -1, basis). Without `view`: all three. 422 unknown view.
        hsp-3c: `bridge=B` with view=hops = THAT bridge's hops as its mode says (serial: its cable path; simulated: chip pins -> twin -> the board-engines
        worker's isle url); an empty `bridge` (nothing clicked yet) = no rows, said.
POST /api/grpc/bench-bridges/{bench}/mode  body {bridge[, mode]}   hsp-3c: set the bridge's mode (serial | simulated); without `mode` it TOGGLES (the click toggle
        rule). Saves the stored PolariBridgeInstance row. -> {ok, bridge, mode, was, hops[]}; 404 a bridge not on the bench (or not stored); 422 an unknown mode.
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
            polServer.falconServer.add_route('/api/grpc/bench-bridges/{bench}/mode', self, suffix='mode')

    def _table(self, name):
        rows = list(((getattr(self.manager, 'objectTables', None) or {}).get(name) or {}).values())
        return rows or None

    def _bindings(self):
        return self._table('EngineProviderBinding')

    def on_get(self, request, response, bench):
        out = BP.bench_bridges(bench, self._table('PolariBridgeInstance'), self._table('BridgePath'))
        view = request.get_param('view') or ''
        if view == 'hops' and request.get_param('bridge') is not None:
            b = next((x for x in out['bridges'] if x['name'] == request.get_param('bridge')), None)
            rows = BP.bridge_hops(b, self._table('BridgePath'), self._bindings()) if b else []
            response.media = {'ok': True, 'bench': bench, 'view': view, 'count': len(rows), 'rows': rows,
                              **({} if b else {'note': 'pick a bridge first' if not request.get_param('bridge') else 'no bridge %r on %s' % (request.get_param('bridge'), bench)})}
            return
        if not view:
            response.media = out
            return
        if view not in VIEWS:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'view must be one of %s' % ', '.join(VIEWS)}
            return
        response.media = {'ok': True, 'bench': bench, 'view': view, 'count': len(out[view]), 'rows': out[view]}

    def on_post_mode(self, request, response, bench):
        import json
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except ValueError:
            body = {}
        row = next((r for r in (self._table('PolariBridgeInstance') or []) if getattr(r, 'name', '') == body.get('bridge') and getattr(r, 'bench', '') == bench), None)
        if row is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no stored bridge %r on bench %r' % (body.get('bridge'), bench)}
            return
        was = row.mode or 'serial'
        mode = body.get('mode') or BP.other_mode(was)
        if mode not in BP.MODES:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'mode must be one of %s' % ', '.join(BP.MODES)}
            return
        row.mode = mode
        db = getattr(self.manager, 'db', None)
        if db is not None and hasattr(db, 'saveInstanceInDB'):
            db.saveInstanceInDB(row)
        response.media = {'ok': True, 'bridge': row.name, 'mode': mode, 'was': was, 'hops': BP.bridge_hops(row, self._table('BridgePath'), self._bindings())}
