"""
@module cmod.cmod_solve_api

sol-0 doors (contract in cmod.custom.solve_doors): POST/GET /api/missions/{name}/solve and GET /api/missions/{name}/solve-runs[/{run}]. Own class, own file - they sit beside
mis-0's /solution|/resolution, pp-0's /pin-profiles, pp-1's /colocation and rt-0's /approach (same depth, literal segments, the same {name} field).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SolveAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/missions/{name}/solve', self, suffix='solve')
            add('/api/missions/{name}/solve-runs', self, suffix='solve_runs')
            add('/api/missions/{name}/solve-runs/{run}', self, suffix='solve_run')

    def on_post_solve(self, request, response, name):
        from cmod.custom import solve_doors as D
        D.post_solve(self, request, response, name)

    def on_get_solve(self, request, response, name):
        from cmod.custom import solve_doors as D
        D.get_solve(self, request, response, name)

    def on_get_solve_runs(self, request, response, name):
        from cmod.custom import solve_doors as D
        D.get_runs(self, request, response, name)

    def on_get_solve_run(self, request, response, name, run):
        from cmod.custom import solve_doors as D
        D.get_run(self, request, response, name, run)
