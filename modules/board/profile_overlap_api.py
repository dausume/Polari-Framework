"""
@module board.profile_overlap_api

pp-1 door: GET /api/board/socs/{soc}/profile-overlap[?a=KIND&b=KIND&scope=pin|net|peripheral&verdict=V&list=kinds|rules]
the cited overlap table (board.custom.profile_overlap) - which pin-profile kinds may share one pin, one net or one peripheral. `rows` are
plain-words rows (pair, scope, verdict, mode, condition, reason, rule, cite, common_pins); `totals` counts verdicts per scope. An unknown SoC, kind,
scope or verdict is a 404/400 naming what is known. Sits beside rp-0's /api/board/socs/{soc}/register-profile (same depth, literal last segment).
"""
import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class ProfileOverlapAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/board/socs/{soc}/profile-overlap', self, suffix='profile_overlap')

    def on_get_profile_overlap(self, request, response, soc):
        from board.custom import profile_overlap as PO
        p = request.params
        try:
            PO.resolve_soc(soc)
        except KeyError as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': e.args[0]}
            return
        try:
            lst = p.get('list')
            if lst == 'kinds':
                rows = PO.kind_rows(soc)
            elif lst == 'rules':
                rows = PO.rule_rows(soc)
            else:
                rows = PO.rows(soc, a=p.get('a'), b=p.get('b'), scope=p.get('scope'), verdict=p.get('verdict'))
        except KeyError as e:
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': e.args[0]}
            return
        response.media = {'ok': True, 'soc': PO.resolve_soc(soc), 'list': lst or 'table', 'count': len(rows), 'rows': rows, 'totals': PO.totals(soc)}
