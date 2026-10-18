"""
@module cmod.cmod_colocation_api

pp-1 door: GET /api/missions/{name}/colocation[?purposes=a,b][&view=pairs|groups|apart] - which of the Mission's pin profiles (pp-0) could share a pin
or a net by the cited overlap table, the minimum pin count under the most permissive valid sharing, the conflicts and the profiles forced apart
(cmod.custom.mission_colocation). `rows` is the requested plain-words view. Sits beside mis-0's /api/missions/{name}/solution|resolution and pp-0's
/api/missions/{name}/pin-profiles (same depth, literal last segment, same {name} field). 404 naming the Mission when it does not resolve.
"""
import falcon

from objectTreeDecorators import treeObject, treeObjectInit


class ColocationAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/missions/{name}/colocation', self, suffix='colocation')

    def on_get_colocation(self, request, response, name):
        from cmod.custom import mission_colocation as MC
        names = [x.strip() for x in (request.params.get('purposes') or '').split(',') if x.strip()]
        view = request.params.get('view') or 'pairs'
        if view not in ('pairs', 'groups', 'apart'):
            response.status = falcon.HTTP_400
            response.media = {'ok': False, 'error': 'view is one of pairs, groups, apart'}
            return
        try:
            res = MC.mission_colocation(name, purposes=names or None, manager=self.manager)
        except ValueError as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': str(e)}
            return
        rows = MC.view_rows(res, view)
        response.media = dict(res, view=view, count=len(rows), rows=rows)
