"""
@module board.bench_solution_api

bss-0 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md): the Bench Solution doors. The work is in board.custom.bench_solution_whole; these doors only route.

GET /api/board/bench-solutions          every Bench Solution with whether it is whole and how many things are missing
GET /api/board/bench-solutions/{name}   the whole check: each leg (system, hardware, firmware, thermal, conditions) ok or why not, in words
GET /api/board/bench-solutions/{name}/legs   the same as rows {leg, ref, ok, why} for a table (bss-6)
404 = no such Bench Solution.
"""
import falcon

from objectTreeDecorators import treeObject, treeObjectInit

from board.custom import bench_solution_whole as W


class BenchSolutionAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/board/bench-solutions', self, suffix='listing')
            add('/api/board/bench-solutions/{name}', self)
            add('/api/board/bench-solutions/{name}/legs', self, suffix='legs')   # bss-6: the legs as rows

    def on_get_listing(self, request, response):
        response.media = {'ok': True, 'rows': W.listing(self.manager)}

    def on_get_legs(self, request, response, name):
        try:
            response.media = {'ok': True, 'rows': W.legs(self.manager, name)}
        except W.NotFound as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': str(e)}

    def on_get(self, request, response, name):
        try:
            response.media = W.whole(self.manager, name)
        except W.NotFound as e:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': str(e)}
