"""
@module board.bench_api

bench-0 (MISSION_GENERIC_PLAN.md section 13.1): the Bench doors - thin falcon handlers over board.custom.bench (the bodies live there; this file
only routes). Contracts in bench.py. GETs list; POSTs add a board / a breadboard / remove one. 404 for an unknown bench, board or model; 400 for a
bad body.
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: falcon.HTTP_200, 201: falcon.HTTP_201, 400: falcon.HTTP_400, 404: falcon.HTTP_404, 409: falcon.HTTP_409}


class BenchAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/benches', self, suffix='benches')
            add('/api/board/benches/{bench}/boards', self, suffix='boards')
            add('/api/board/benches/{bench}/breadboards', self, suffix='breadboards')
            add('/api/board/benches/{bench}/attempt', self, suffix='attempt')
            add('/api/board/benches/{bench}/remove', self, suffix='remove')
            add('/api/board/bench-options/boards', self, suffix='options_boards')
            add('/api/board/bench-options/breadboards', self, suffix='options_breadboards')

    def _get(self, request, response, which, bench=''):
        from board.custom import bench as B
        status, payload = B.get_door(self.manager, request.params, which, bench)
        response.status, response.media = _STATUS[status], payload

    def _post(self, request, response, which, bench):
        from board.custom import bench as B
        try:
            body = json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
        except ValueError:
            response.status, response.media = falcon.HTTP_400, {'ok': False, 'error': 'the body is not JSON'}
            return
        status, payload = B.post_door(self.manager, bench, which, body)
        response.status, response.media = _STATUS[status], payload

    def on_post_benches(self, request, response):
        """wb-0: create an empty bench {name, title?, notes?}."""
        self._post(request, response, 'create', '')

    def on_post_attempt(self, request, response, bench):
        """wb-0: attempt a mission on this bench {mission}."""
        self._post(request, response, 'attempt', bench)

    def on_get_benches(self, request, response):
        """bench-0: one row per bench with its counts and its hardware-only boards named."""
        self._get(request, response, 'benches')

    def on_get_boards(self, request, response, bench):
        """bench-0: the boards on one bench, each with its testing word."""
        self._get(request, response, 'boards', bench)

    def on_post_boards(self, request, response, bench):
        """bench-0: add a dev / eval board {board, label?, note?}."""
        self._post(request, response, 'boards', bench)

    def on_get_breadboards(self, request, response, bench):
        """bench-0: the breadboards on one bench."""
        self._get(request, response, 'breadboards', bench)

    def on_post_breadboards(self, request, response, bench):
        """bench-0: add breadboards {model, count?, note?}."""
        self._post(request, response, 'breadboards', bench)

    def on_post_remove(self, request, response, bench):
        """bench-0: remove one board or one breadboard {kind, key}."""
        self._post(request, response, 'remove', bench)

    def on_get_options_boards(self, request, response):
        """bench-0: the dev / eval board selection list."""
        self._get(request, response, 'options-boards')

    def on_get_options_breadboards(self, request, response):
        """bench-0: the breadboard selection list."""
        self._get(request, response, 'options-breadboards')
