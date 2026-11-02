"""
@module cmod.cmod_bench_canvas_api

bss-5 doors (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b): a Bench Solution's topology as a no-code drawing. The model is
cmod.custom.bench_topology_nocode; these doors only read the request and say a refusal in words.

GET /api/cmod/bench-topology/{bench_solution}/canvas    {solution (the SolutionDefinition row, kept up to date), definition, route (the drawing page)}
PUT /api/cmod/bench-topology/{bench_solution}/canvas    body {definition} or the definition itself: write the drawing's edits back (titles only) -> the fresh
                                                        drawing; 422 with the state and the field when an edit is not a title
404 = no such Bench Solution.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import bench_topology_nocode as BN
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


class BenchCanvasAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            polServer.falconServer.add_route('/api/cmod/bench-topology/{bench_solution}/canvas', self)

    def on_get(self, request, response, bench_solution):
        try:
            response.media = {'ok': True, 'solution': BN.render(bench_solution, self.manager), 'definition': BN.render_definition(bench_solution, self.manager),
                              'route': BN.drawing_route(bench_solution)}
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_put(self, request, response, bench_solution):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except ValueError:
            body = {}
        definition = body.get('definition') if isinstance(body, dict) and isinstance(body.get('definition'), dict) else body
        try:
            ok, why, changes = BN.write_back(definition if isinstance(definition, dict) else {}, bench_solution, self.manager)
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}
            return
        if not ok:
            response.status = falcon.HTTP_422
            response.media = {'ok': False, 'refused': True, 'error': why}
            return
        response.media = {'ok': True, 'why': why, 'changes': changes, 'definition': BN.render_definition(bench_solution, self.manager)}
