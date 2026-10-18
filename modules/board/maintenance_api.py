"""
@module board.maintenance_api

c3-derive door: the one-time clean-up of rows a server STILL holds that the code now derives on read.
  GET  /api/board/maintenance/retire-derived-rows          a DRY RUN: how many stored GPIO-matrix PinFunction rows are identical to the derived
                                                           ones (and which differ — a person's edit, kept)
  POST /api/board/maintenance/retire-derived-rows {apply}  apply=true deletes ONLY the identical rows (the derived copy answers in their place,
                                                           field for field); edited rows are never touched; apply missing/false = the dry run
Why: the C3's 2 640 matrix rows are derived since c3-derive, but a database seeded before keeps restoring them on every boot (boot time). The
pol verb `pol board retire-derived [--apply] --api URL` wraps it (his rule: every by-hand remedy is a CLI verb with a dry run).
"""
import json

import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class MaintenanceAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/board/maintenance/retire-derived-rows', self, suffix='retire')

    def _run(self, response, apply):
        from board.custom import c3_retire
        if self.manager is None:
            response.status = falcon.HTTP_503
            response.media = {'ok': False, 'error': 'no live manager on this server: nothing is stored to retire'}
            return
        rep = c3_retire.retire_stored_matrix_rows(self.manager, apply=apply)
        response.media = dict(rep, ok=True, edited_count=len(rep['edited']), edited=rep['edited'][:50],
                              note=('retired the stored copies; the derived rows answer in their place' if apply
                                    else 'dry run - POST {"apply": true} deletes the %d identical rows' % rep['identical']))

    def on_get_retire(self, request, response):
        self._run(response, False)

    def on_post_retire(self, request, response):
        try:
            raw = request.bounded_stream.read() or b'{}'
            body = json.loads(raw.decode('utf-8') or '{}')
        except Exception:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'the body must be JSON, e.g. {"apply": true}'}
            return
        unknown = sorted(k for k in body if k != 'apply')
        if unknown:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'error': 'unknown key(s) %s (known: apply)' % ', '.join(unknown)}
            return
        self._run(response, body.get('apply') is True)
