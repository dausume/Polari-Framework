"""
@module board.bench_nets_api

bob-2 (BENCH_BOARDS_PLAN.md): the doors of CONNECTIONS ACROSS BOARDS on a Bench (board.custom.bench_nets).

GET  /api/board/benches/{bench}/connections   the stored BenchConnection rows (wires, jumpers, mated pins)
POST /api/board/benches/{bench}/connections   {connections: [{from_board, from_foothold, to_board, to_foothold, kind?, colour?, label?}]} - both ends checked, all or none
POST /api/board/benches/{bench}/mate          {board, connector, breadboard, column, first_row} - a 1 x N header pushed into breadboard holes
POST /api/board/benches/{bench}/firmware      bob-2d: {board, firmware} - the firmware a board RUNS (its pin use; its pin claims for the board-level checks)
POST /api/board/benches/{bench}/circuits      bob-2c: {board, circuit, on?} - a BOARD-LEVEL circuit (CircuitDefinition bound to the board's pins) built on the
                                              bench; its electrical findings land on those pins' rows
GET  /api/board/benches/{bench}/pins          bob-2b, THE MAIN BENCH VIEW: one row per pin (pins a board joins inside = one row) - its firmware use, the pins
                                              it reaches and through what, and whether its inherent drive meets its connections (board.custom.bench_pins)
GET  /api/board/benches/{bench}/nets          the full bench NETLIST (nets that cross boards + findings) - its own view, a popup, not the main bench
Board ids are the `id` column of GET /api/board/benches/{bench}/all-boards.
"""
import json

from objectTreeDecorators import treeObject, treeObjectInit

_STATUS = {200: '200 OK', 201: '201 Created', 404: '404 Not Found', 422: '422 Unprocessable Entity', 503: '503 Service Unavailable'}


class BenchNetsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/benches/{bench}/connections', self, suffix='connections')
            add('/api/board/benches/{bench}/mate', self, suffix='mate')
            add('/api/board/benches/{bench}/nets', self, suffix='nets')
            add('/api/board/benches/{bench}/pins', self, suffix='pins')
            add('/api/board/benches/{bench}/circuits', self, suffix='circuits')
            add('/api/board/benches/{bench}/firmware', self, suffix='firmware')

    @staticmethod
    def _body(request, response):
        try:
            return json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
        except ValueError:
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'the body is not JSON'}
            return None

    def on_get_connections(self, request, response, bench):
        from board.custom import bench_nets as BN
        rows = BN.connections_of(bench, self.manager)
        response.media = {'ok': True, 'bench': bench, 'rows': rows, 'count': len(rows)}

    def on_post_connections(self, request, response, bench):
        from board.custom import bench_nets as BN
        body = self._body(request, response)
        if body is not None:
            status, payload = BN.add_connections(self.manager, bench, body.get('connections') or [])
            response.status, response.media = _STATUS[status], payload

    def on_post_mate(self, request, response, bench):
        from board.custom import bench_nets as BN
        body = self._body(request, response)
        if body is not None:
            status, payload = BN.mate(self.manager, bench, body)
            response.status, response.media = _STATUS[status], payload

    def on_get_nets(self, request, response, bench):
        from board.custom import bench_nets as BN
        nets, problems = BN.bench_nets(bench, self.manager)
        if nets is None:
            response.status, response.media = '404 Not Found', {'ok': False, 'error': problems}
            return
        rows = [{'net': n['net'], 'boards': ', '.join(n['boards']), 'members': len(n['members']), 'findings': '; '.join('%s: %s' % (f['kind'], f['words']) for f in n['findings']),
                 'undetermined': '; '.join(n['undetermined'])} for n in nets]
        response.media = {'ok': True, 'bench': bench, 'rows': rows, 'nets': nets, 'problems': problems,
                          'findings': sum(len(n['findings']) for n in nets)}

    def on_get_pins(self, request, response, bench):
        from board.custom import bench_pins as BP
        rows, problems = BP.bench_pin_rows(bench, self.manager)
        if rows is None:
            response.status, response.media = '404 Not Found', {'ok': False, 'error': problems}
            return
        response.media = {'ok': True, 'bench': bench, 'rows': rows, 'count': len(rows), 'findings': sum(1 for r in rows if r['status'] == 'finding'),
                          'problems': problems}

    def on_post_circuits(self, request, response, bench):
        from board.custom import bench_nets as BN
        body = self._body(request, response)
        if body is not None:
            status, payload = BN.add_circuit(self.manager, bench, body)
            response.status, response.media = _STATUS[status], payload

    def on_post_firmware(self, request, response, bench):
        from board.custom import bench_nets as BN
        body = self._body(request, response)
        if body is not None:
            status, payload = BN.set_firmware(self.manager, bench, body)
            response.status, response.media = _STATUS[status], payload
