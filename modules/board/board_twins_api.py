"""
@module board.board_twins_api

sim-1 (HARDWARE_BENCH_CONVERGENCE_PLAN.md §8): the twin-session doors - thin falcon handlers over board.custom.twin_sessions (the bodies live there).

GET    /api/board/twins                       every session (`rows` for a configured table): config, participant `twin:<board>#<n>`, the LOCKED firmware sha, ports, time left
POST   /api/board/twins                       {config, ttl_s?, owner?, watch?, free?}  start one; the answer carries the control token ONCE
GET    /api/board/twins/{name}                one session (+ the twin's latest status line)
DELETE /api/board/twins/{name}                stop it
POST   /api/board/twins/{name}/inject         {"set":"PD2","level":0|1} | {"adc":0,"mv":750} | {"reset":1} | {"watch":[..]} | {"run":false} | {"status":1}
GET    /api/board/twins/{name}/events         SSE: the twin's control stream (pin edges) - `?replay=N` first sends the last N, `?limit=N` / `?seconds=S` end the stream
Every refusal is {ok: false, error: <plain words>} with the status the words call for (400 bad input, 404 unknown, 409 ended, 503 no worker lists sessions).
"""
import json
import time

import falcon

from objectTreeDecorators import treeObject, treeObjectInit

KEEPALIVE_S = 10.0


class BoardTwinsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/twins', self, suffix='list')
            add('/api/board/twins/{name}', self, suffix='one')
            add('/api/board/twins/{name}/inject', self, suffix='inject')
            add('/api/board/twins/{name}/events', self, suffix='events')

    def _run(self, response, fn, *args, **kw):
        from board.custom.twin_sessions import SessionRefused
        try:
            out = fn(self.manager, *args, **kw)
            return out
        except SessionRefused as e:
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
        from board.custom import twin_sessions as TS
        rows = self._run(response, TS.listing)
        if rows is not None:
            response.media = {'ok': True, 'rows': rows, 'count': len(rows)}

    def on_post_list(self, request, response):
        from board.custom import twin_sessions as TS
        body = self._body(request, response)
        if body is None:
            return
        if not body.get('config'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'POST /api/board/twins needs "config": a firmware variant such as uno-light (GET /api/board/variants lists them)'}
            return
        try:
            kw = dict(ttl_s=int(body.get('ttl_s') or TS.DEFAULT_TTL_S), owner=str(body.get('owner') or ''), watch=body.get('watch'), free=bool(body.get('free')))
        except (TypeError, ValueError):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'ttl_s is a whole number of seconds'}
            return
        out = self._run(response, TS.start, str(body['config']), **kw)
        if out is not None:
            response.status = falcon.HTTP_201
            response.media = dict(out, ok=True)

    def on_get_one(self, request, response, name):
        from board.custom import twin_sessions as TS
        out = self._run(response, TS.one, name)
        if out is not None:
            response.media = dict(out, ok=True)

    def on_delete_one(self, request, response, name):
        from board.custom import twin_sessions as TS
        out = self._run(response, TS.stop, name)
        if out is not None:
            response.media = dict(out, ok=True)

    def on_post_inject(self, request, response, name):
        from board.custom import twin_sessions as TS
        body = self._body(request, response)
        if body is None:
            return
        out = self._run(response, TS.inject, name, body)
        if out is not None:
            response.status = falcon.HTTP_200 if out['ok'] else falcon.HTTP_409
            response.media = out

    def on_get_events(self, request, response, name):
        from board.custom import twin_sessions as TS
        try:
            replay, limit, seconds = (int(request.params.get('replay', 0)), int(request.params.get('limit', 0)), float(request.params.get('seconds', 0)))
        except ValueError:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'replay and limit are whole numbers, seconds a number'}
            return
        sub = self._run(response, TS.events, name, replay=replay)
        if sub is None:
            return

        def gen():
            sent, t0, last = 0, time.time(), time.time()
            try:
                yield ('data: %s\n\n' % json.dumps({'t': 'hello', 'session': name})).encode()
                while True:
                    ev = sub.get(timeout=1.0)
                    if ev is not None:
                        yield ('data: %s\n\n' % json.dumps(ev)).encode()
                        sent += 1
                        last = time.time()
                        if ev.get('t') == 'closed':
                            return
                    elif time.time() - last >= KEEPALIVE_S:
                        yield b': keepalive\n\n'
                        last = time.time()
                    if (limit and sent >= limit) or (seconds and time.time() - t0 >= seconds):
                        return
            finally:
                sub.close()

        response.content_type = 'text/event-stream'
        response.set_header('Cache-Control', 'no-cache')
        response.set_header('X-Accel-Buffering', 'no')
        response.stream = gen()
