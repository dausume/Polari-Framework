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
                                               board.custom.board_details - the doors of /display/board-details

A refusal (an unknown kind, no such board, a model with no geometry) answers {ok: false, error: <plain words>} with 404.
"""
from objectTreeDecorators import treeObject, treeObjectInit

KIND_WORDS = {'datasheet': 'a dev board known from its vendor documents (BoardDefinition, BoardPin, ConnectorPin, the cited electrical numbers)',
              'geometry': 'a breadboard known from its strip and rail counts and the 2.54 mm pitch (BoardModel / BreadboardModel)',
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
        rows, why = BD.part(kind, definition, part, self.manager)
        # an empty part is an answer, not an error: the page shows the words (a breadboard has no layers)
        response.media = {'ok': True, 'board': '%s/%s' % (kind, definition), 'part': part, 'rows': rows, 'count': len(rows), 'note': why}
