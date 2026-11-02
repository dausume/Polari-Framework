"""
@module cmod.cmod_node_run_api

bss-2 doors (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 6b): test one node of a Bench Solution's topology on the twin. The work is in
cmod.custom.node_run; these doors only read the request and say a refusal in words.

POST /api/cmod/bench-topology/{bench_solution}/nodes/{slug}/run    body {path?, profile?, play_from?}: one deterministic twin run from reset along the path (the fastest when
                                                                   none is named), watching a named TestProfile's items too, the edges up to play_from replayed silently (bss-3) -> {run, edges, signals, working_events}
GET  /api/cmod/bench-topology/{bench_solution}/nodes/{slug}/runs   the kept runs of the node
404 = no such Bench Solution / node / path; 409 = no engine or the build failed; 422 = an event the twin cannot apply yet, or too many fields to watch.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import node_run as NR
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


class NodeRunAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod/bench-topology/{bench_solution}/nodes/{slug}/run', self, suffix='run')
            add('/api/cmod/bench-topology/{bench_solution}/nodes/{slug}/runs', self, suffix='runs')

    def on_post_run(self, request, response, bench_solution, slug):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except ValueError:
            body = {}
        try:
            b = body or {}
            response.media = NR.run(self.manager, bench_solution, '%s:%s' % (bench_solution, slug), str(b.get('path') or ''), str(b.get('profile') or ''),
                                    str(b.get('play_from') or ''))
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_get_runs(self, request, response, bench_solution, slug):
        response.media = {'ok': True, 'rows': NR.runs(self.manager, '%s:%s' % (bench_solution, slug))}
