"""
@module cmod.cmod_mission_api

HardwareMission doors (mis-0): the model is pure (`cmod.custom.mission_nocode`, `cmod.custom.mission_derived`) and the work is in
`cmod.custom.mission_doors`; this API only registers the routes and finds the row. Contracts are in mission_doors.py:

GET /api/missions · GET/PUT /api/missions/{name}/solution · GET /api/missions/{name}/resolution
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MissionAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/missions', self, suffix='missions')
            add('/api/missions/{name}/solution', self, suffix='solution')
            add('/api/missions/{name}/resolution', self, suffix='resolution')

    def _rows(self, cls):
        return list(((self.manager.objectTables or {}).get(cls, {}) or {}).values()) if self.manager is not None else []

    def _mission(self, name, response):
        import falcon
        hit = [r for r in self._rows('HardwareMission') if r.name == name]
        if not hit:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no HardwareMission %r (GET /api/missions lists them)' % name}
        return hit[0] if hit else None

    def on_get_missions(self, request, response):
        from cmod.custom import mission_doors as D
        D.missions_table(self, request, response)

    def on_get_solution(self, request, response, name):
        from cmod.custom import mission_doors as D
        D.get_solution(self, request, response, name)

    def on_put_solution(self, request, response, name):
        from cmod.custom import mission_doors as D
        D.put_solution(self, request, response, name)

    def on_get_resolution(self, request, response, name):
        from cmod.custom import mission_doors as D
        D.get_resolution(self, request, response, name)
