"""
@module board.board_object_api

THE BOARD OBJECT's doors (brd-bo, PCB_FROM_SCRATCH_PLAN §2b) — over THIS server's rows:

GET  /api/board/{board}/pins        the pin assignment (BoardPin rows) + the SoC pins, nets, connectors, runtime profiles, the
                                    board sha and the rules (pins named once, a SoC pin assigned once …)
GET  /api/board/{board}/views       the BoardView rows (rendered out / ingested in, by sha; refusals too)
GET  /api/board/{board}/conflicts   the BoardConflict rows (shown, never auto-resolved)
POST /api/board/{board}/render      body {as: kicad|zephyr|esp-idf|bare-c} → the view's files + sha; a BoardView row (out)
POST /api/board/{board}/ingest      body {as, files: {name: text}} → BoardView (in) + one BoardConflict per disagreement; the
                                    rows are NOT changed
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class BoardObjectAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/{board}/pins', self, suffix='pins')
            add('/api/board/{board}/views', self, suffix='views')
            add('/api/board/{board}/conflicts', self, suffix='conflicts')
            add('/api/board/{board}/render', self, suffix='render')
            add('/api/board/{board}/ingest', self, suffix='ingest')

    def _tables(self):
        from board.custom import board_object as bo
        return bo.tables_from_manager(self.manager)

    def _rows(self, board, response):
        from board.custom import board_object as bo
        try:
            return bo.rows_for(board, self._tables())
        except bo.BoardObjectRefused as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': str(e)}
            return None

    def on_get_pins(self, request, response, board):
        from board.custom import board_object as bo
        r = self._rows(board, response)
        if r is None:
            return
        response.media = {'ok': True, 'board': r['board'], 'boardSha': bo.board_sha(r), 'soc': r['soc'], 'pins': r['pins'],
                          'socPins': r['soc_pins'], 'nets': r['nets'], 'connectors': r['connectors'], 'connectorPins': r['connector_pins'],
                          'hardware': r['hardware'], 'runtimeProfiles': r['profiles'], 'rules': bo.validate(r) or ['ok']}

    def _list(self, cls, board):
        from board.custom import board_object as bo
        rows = [r for r in self._tables_cls(cls) if r.get('board') == bo.board_name(board)]
        return sorted(rows, key=lambda r: str(r.get('at') or r.get('detected_at') or ''), reverse=True)

    def _tables_cls(self, cls):
        from board.custom import board_object as bo
        return [bo.as_dict(r, cls) for r in ((self.manager.objectTables or {}).get(cls, {}) or {}).values()] if self.manager is not None else []

    def on_get_views(self, request, response, board):
        response.media = {'ok': True, 'board': board, 'views': self._list('BoardView', board)}

    def on_get_conflicts(self, request, response, board):
        rows = self._list('BoardConflict', board)
        response.media = {'ok': True, 'board': board, 'conflicts': rows, 'open': sum(1 for r in rows if r.get('state') == 'open'),
                          'note': 'shown, never auto-resolved — a person edits the rows or the view\'s source'}

    @staticmethod
    def _body(request, response):
        try:
            raw = request.bounded_stream.read() or b''
            return json.loads(raw) if raw.strip() else {}
        except ValueError as e:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'bad JSON: %s' % e}
            return None

    def on_post_render(self, request, response, board):
        from board.custom import ingest as I
        body = self._body(request, response)
        r = None if body is None else self._rows(board, response)
        if r is None:
            return
        res, row = I.render_row(board, str(body.get('as') or ''), r=r, path='(api)')
        I.save_rows(self.manager, views=[row])
        if res is None:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'refused': True, 'error': row['refusal'], 'view': row}
            return
        response.media = {'ok': True, 'view': row, 'files': res['files'], 'sha256': res['sha256'], 'boardSha': res['board_sha']}

    def on_post_ingest(self, request, response, board):
        from board.custom import ingest as I
        from board.custom.views import ViewRefused
        body = self._body(request, response)
        r = None if body is None else self._rows(board, response)
        if r is None:
            return
        files = body.get('files') or {}
        if not isinstance(files, dict) or not files:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'body needs files: {name: text}'}
            return
        try:
            res = I.ingest(board, files, body.get('as') or None, r=r, path='(api)')
        except ViewRefused as e:
            response.status = falcon.HTTP_409
            response.media = {'ok': False, 'error': str(e)}
            return
        saved = I.save_rows(self.manager, views=[res['view']], conflicts=res['conflicts'])
        response.status = falcon.HTTP_201
        response.media = {'ok': True, 'view': res['view'], 'conflicts': res['conflicts'], 'saved': saved,
                          'note': 'the rows are unchanged; %d conflict(s) recorded' % len(res['conflicts'])}
