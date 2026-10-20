"""
@module grpcbridge.hosted_bridges_api

sim-2 (HARDWARE_BENCH_CONVERGENCE_PLAN.md section 3): the hosted-bridge doors - thin falcon handlers over grpcbridge.custom.hosted_bridges (the bodies live there).

GET    /api/grpc/hosted-bridges               every hosted bridge (`rows` for a configured table): session, state, the jar, time left
POST   /api/grpc/hosted-bridges               {session, bridge_name?, grpc_target?, ttl_s?, owner?, log_only?}  start one beside a TwinSession; the bridge's
                                              gRPC target is this server's gRPC bridge port on the host the request came to unless `grpc_target` is given
GET    /api/grpc/hosted-bridges/{name}        one bridge (+ the tail of its output, the process's RSS and CPU seconds)
DELETE /api/grpc/hosted-bridges/{name}        stop it
GET    /api/grpc/hosted-bridges/{name}/logs   ?tail=N&which=run|build  the bridge's output lines
GET    /api/grpc/hosted-engines               where the hosted bridges would run (BRIDGE_ENGINES_URL -> topology provider grpcbridge.engines -> refusal)
Every refusal is {ok: false, error: <plain words>} with the status the words call for (400 bad input, 404 unknown, 409 ended, 424 no worker - the proxy masks 503).
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class HostedBridgesAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/grpc/hosted-bridges', self, suffix='list')
            add('/api/grpc/hosted-bridges/{name}', self, suffix='one')
            add('/api/grpc/hosted-bridges/{name}/logs', self, suffix='logs')
            add('/api/grpc/hosted-engines', self, suffix='engines')

    def _run(self, response, fn, *args, **kw):
        from grpcbridge.custom.hosted_bridges import HostedRefused
        try:
            return fn(self.manager, *args, **kw)
        except HostedRefused as e:
            response.status = falcon.code_to_http_status(e.status)
            response.media = {'ok': False, 'error': str(e)}
            return None

    def _body(self, request, response):
        raw = request.bounded_stream.read() or b''
        try:
            return json.loads(raw) if raw.strip() else {}
        except ValueError as e:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return None

    def on_get_list(self, request, response):
        from grpcbridge.custom import hosted_bridges as HB
        rows = self._run(response, HB.listing)
        if rows is not None:
            response.media = {'ok': True, 'rows': rows, 'count': len(rows)}

    def on_post_list(self, request, response):
        from grpcbridge.custom import hosted_bridges as HB
        body = self._body(request, response)
        if body is None:
            return
        if not body.get('session'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'POST /api/grpc/hosted-bridges needs "session": the name of a running twin session (GET /api/board/twins lists them)'}
            return
        try:
            ttl = int(body['ttl_s']) if body.get('ttl_s') else None
        except (TypeError, ValueError):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'ttl_s is a whole number of seconds'}
            return
        host = request.forwarded_host or request.host or ''
        out = self._run(response, HB.start, str(body['session']), bridge_name=str(body.get('bridge_name') or HB.DEFAULT_BRIDGE),
                        grpc_target_=str(body.get('grpc_target') or ''), api_host=host, ttl_s=ttl, owner=str(body.get('owner') or ''),
                        log_only=bool(body.get('log_only')))
        if out is not None:
            response.status = falcon.HTTP_201
            response.media = dict(out, ok=True)

    def on_get_one(self, request, response, name):
        from grpcbridge.custom import hosted_bridges as HB
        out = self._run(response, HB.one, name)
        if out is not None:
            response.media = dict(out, ok=True)

    def on_delete_one(self, request, response, name):
        from grpcbridge.custom import hosted_bridges as HB
        out = self._run(response, HB.stop, name)
        if out is not None:
            response.media = dict(out, ok=True)

    def on_get_logs(self, request, response, name):
        from grpcbridge.custom import hosted_bridges as HB
        try:
            tail = int(request.params.get('tail', 100))
        except ValueError:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'tail is a whole number of lines'}
            return
        out = self._run(response, HB.logs, name, tail=tail, which='build' if request.params.get('which') == 'build' else 'run')
        if out is not None:
            response.media = out

    def on_get_engines(self, request, response):
        from grpcbridge.custom import bridge_engines as be
        response.media = dict(be.placement(), ok=True)
