"""
@module board.bench_parts_api

drv-0 / drv-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md): the doors of PARTS AS BOARDS - drivers, loads and modules defined by their pins (board.custom.part_boards)
and one Board mounted on another by position (board.custom.bench_mount).

GET  /api/board/parts                           {ok, rows}  the catalogue: the cited seed + parts people defined, each with its contract in words
POST /api/board/parts                           {name, kind, pins: [{number, name, role, channel?, x_mm, y_mm}], on_volts?, draw_ma?, in_max_v?,
                                                 out_sink_ma?, out_source_ma?, out_max_v?, total_ma?, ..., document?, page_table?, url?, notes?}
                                                 a custom part (a mini board) - 201, or 400 / 409 in words
POST /api/board/benches/{bench}/parts           {part, label?}  a part onto a bench (a BenchBoard of kind part)
POST /api/board/benches/{bench}/mount           {child, parent, x_mm, y_mm, rotation?, tolerance_mm?, allow_joined?}  a Board mounted on another: one
                                                 mounted connection per landed pin; refused in words when a pin lands nowhere, two share a hole, or the
                                                 parent joins pins of the child
GET  /api/board/benches/{bench}/drive-fixes     {ok, rows}  each drive finding of the bench's nets with the catalogue parts whose contract fixes it
A part's footholds are GET /api/board/footholds/part/{name} (the footholds door; definition kind part).
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: '200 OK', 201: '201 Created', 400: '400 Bad Request', 404: '404 Not Found', 409: '409 Conflict', 422: '422 Unprocessable Entity',
           503: '503 Service Unavailable'}


class BenchPartsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/parts', self, suffix='parts')
            add('/api/board/benches/{bench}/parts', self, suffix='bench_parts')
            add('/api/board/benches/{bench}/mount', self, suffix='mount')
            add('/api/board/benches/{bench}/drive-fixes', self, suffix='fixes')

    @staticmethod
    def _body(request, response):
        try:
            return json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
        except ValueError:
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'the body is not JSON'}
            return None

    def _send(self, response, status, body):
        response.status, response.media = _STATUS[status], body

    def on_get_parts(self, request, response):
        from board.custom import part_boards as PB
        self._send(response, 200, {'ok': True, 'rows': PB.catalogue(self.manager)})

    def on_post_parts(self, request, response):
        from board.custom import part_boards as PB
        body = self._body(request, response)
        if body is not None:
            self._send(response, *PB.define(self.manager, body))

    def on_post_bench_parts(self, request, response, bench):
        from board.custom import part_boards as PB
        body = self._body(request, response)
        if body is not None:
            self._send(response, *PB.add_part(self.manager, bench, body))

    def on_post_mount(self, request, response, bench):
        from board.custom import bench_mount as M
        body = self._body(request, response)
        if body is not None:
            self._send(response, *M.mount(self.manager, bench, body))

    def on_get_fixes(self, request, response, bench):
        from board.custom import bench_nets as BN
        from board.custom import part_boards as PB
        nets, problems = BN.bench_nets(bench, self.manager)
        if nets is None:
            return self._send(response, 404, {'ok': False, 'error': problems})
        self._send(response, 200, {'ok': True, 'bench': bench, 'rows': PB.suggestions(nets, self.manager), 'problems': problems})
