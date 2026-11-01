"""
@module board.footholds_api

bob-0 (BENCH_BOARDS_PLAN.md section 3): the door of THE BENCH CONTRACT - a board's footholds, whatever defines the board.

GET /api/board/footholds/{kind}/{definition}   kind = datasheet | geometry | layers; the BoardFoothold rows (derived on read for datasheet and geometry
                                               boards, the stored rows of an ingested PCB) + `nodes` (how many joined groups) + counts by kind
GET /api/board/footholds                        the definition kinds and what each is known from
GET /api/board/benches/{bench}/all-boards       bob-1: ONE list of the Boards on a Bench - dev boards, breadboards and PCBs alike, each with its
                                               definition, foothold summary and Board Details route (board.custom.bench_boards)
POST /api/board/benches/{bench}/pcbs            bob-1: {pcb, label?, note?} put an ingested PCB on the bench
GET /api/board/details/{kind}/{definition}/{part}  bob-3: one part of the Board Details (summary | footholds | nets | parts | layers | coverage),
                                               board.custom.board_details - the doors of /display/board-details; query parameters ride along
                                               (bob-3g: thermal-inputs?ref=<part>, transient?h=&t_end=&ambient=)
POST /api/board/timing-run/{definition}         tmp-6: {temp_c, u2x?: 1|0, ppm?, peer_pct?, clock?} the UNO firmware run at the clock's band at
                                               temp_c (or at `ppm`, a knob) - board.custom.clock_skew_run.run_at; GET: the newest run (?u2x=)

A refusal (an unknown kind, no such board, a model with no geometry) answers {ok: false, error: <plain words>} with 404.
"""
from objectTreeDecorators import treeObject, treeObjectInit

KIND_WORDS = {'datasheet': 'a dev board known from its vendor documents (BoardDefinition, BoardPin, ConnectorPin, the cited electrical numbers)',
              'geometry': 'a breadboard known from its strip and rail counts and the 2.54 mm pitch (BoardModel kind breadboard + its BreadboardLayout)',
              'layers': 'a PCB known from its copper - its connector and test pads, stored by the KiCad ingest (PcbBoard)'}


class FootholdsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/footholds', self, suffix='kinds')
            add('/api/board/footholds/{kind}/{definition}', self, suffix='footholds')
            add('/api/board/benches/{bench}/all-boards', self, suffix='all_boards')
            add('/api/board/benches/{bench}/pcbs', self, suffix='pcbs')
            add('/api/board/details/{kind}/{definition}/{part}', self, suffix='details')
            add('/api/board/timing-run/{definition}', self, suffix='timing_run')

    def on_get_kinds(self, request, response):
        response.media = {'ok': True, 'rows': [{'kind': k, 'known_from': w} for k, w in KIND_WORDS.items()]}

    def on_get_footholds(self, request, response, kind, definition):
        from board.custom import footholds as FH
        rows, why = FH.for_definition(kind, definition, manager=self.manager)
        if not rows:
            response.status = '404 Not Found'
            response.media = {'ok': False, 'error': why}
            return
        counts = {}
        for r in rows:
            counts[r['kind']] = counts.get(r['kind'], 0) + 1
        response.media = {'ok': True, 'kind': kind, 'definition': definition, 'rows': rows, 'count': len(rows),
                          'nodes': len({r['node'] for r in rows}), 'counts': counts}

    def on_get_all_boards(self, request, response, bench):
        from board.custom import bench_boards as BB
        rows = BB.boards_on_bench(bench, self.manager)
        if rows is None:
            response.status = '404 Not Found'
            response.media = {'ok': False, 'error': 'no bench named %r' % bench}
            return
        kinds = {}
        for r in rows:
            kinds[r['board_kind']] = kinds.get(r['board_kind'], 0) + 1
        response.media = {'ok': True, 'bench': bench, 'rows': rows, 'count': len(rows), 'kinds': kinds}

    def on_post_pcbs(self, request, response, bench):
        import json
        from board.custom import bench_boards as BB
        try:
            body = json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
        except ValueError:
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'the body is not JSON'}
            return
        status, payload = BB.add_pcb(self.manager, bench, body)
        response.status, response.media = {201: '201 Created', 404: '404 Not Found', 503: '503 Service Unavailable'}[status], payload

    def on_get_details(self, request, response, kind, definition, part):
        from board.custom import board_details as BD
        rows, why = BD.part(kind, definition, part, self.manager, params=request.params)
        # an empty part is an answer, not an error: the page shows the words (a breadboard has no layers)
        response.media = {'ok': True, 'board': '%s/%s' % (kind, definition), 'part': part, 'rows': rows, 'count': len(rows), 'note': why}

    def on_post_timing_run(self, request, response, definition):
        import json
        from board.custom import clock_skew_run as CSR
        try:
            body = json.loads(request.bounded_stream.read().decode('utf-8') or '{}')
            temp = float(body.get('temp_c', 25.0))
            u2x = int(body.get('u2x', 1))
            ppm = None if body.get('ppm') in (None, '') else float(body['ppm'])
            peer = float(body.get('peer_pct') or 0.0)
        except (ValueError, TypeError, AttributeError):
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'temp_c, ppm and peer_pct need numbers, u2x 0 or 1'}
            return
        if u2x not in (0, 1) or not -200 <= temp <= 400 or abs(peer) > 20 or (ppm is not None and abs(ppm) > 200000):
            response.status, response.media = '400 Bad Request', {'ok': False, 'error': 'u2x 0 or 1; temp_c within -200 .. 400 C; |peer_pct| <= 20; |ppm| <= 200000'}
            return
        if definition != CSR.TD.UNO:
            response.status, response.media = '404 Not Found', {'ok': False, 'error': CSR.rows(definition, 'timing-run')[1]}
            return
        res = CSR.run_at(temp, clock=body.get('clock') or 'cstce16m0v53-r0', u2x=u2x, ppm=ppm, peer_pct=peer)
        response.status = '200 OK' if res.get('ok') else '422 Unprocessable Entity'
        response.media = res

    def on_get_timing_run(self, request, response, definition):
        from board.custom import clock_skew_run as CSR
        try:
            u2x = int(request.get_param('u2x') or 1)
        except ValueError:
            u2x = -1
        res = CSR.last(definition, u2x) if u2x in (0, 1) else None
        response.status = '200 OK' if res else '404 Not Found'
        response.media = res or {'ok': False, 'error': 'no firmware run at temperature for %s (u2x %s) in this process - POST one' % (definition, u2x)}
