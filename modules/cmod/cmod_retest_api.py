"""
@module cmod.cmod_retest_api

bss-4 doors (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md; cfg-4 merged, D-bss-4): re-test a Bench Solution's topology after a configuration or isotope change, and read
one run's kept rows. The work is in cmod.custom.retest; these doors only route.

POST /api/cmod/bench-topology/{bench_solution}/retest               body {catom?}: sync the executions' isotopes from the Firmware Solution's configurations, run the
                                                                    nodes affected by the catom first, then every other state node, each from the root; -> the ordered
                                                                    outcomes, confirmations voided, isotopes synced, the words
POST /api/cmod/bench-topology/{bench_solution}/run-all              bss-8: every state node by every path from the root, fastest first; -> the runs, how many
                                                                    reached, the coverage's untested list (empty = the only green)
GET  /api/cmod/bench-topology/{bench_solution}/runs/{run}/signals   the run's StructNodeRunSignal rows (the structs on arrival)
GET  /api/cmod/bench-topology/{bench_solution}/runs/{run}/edges     the run's StructNodeRunEdge rows
GET  /api/cmod/bench-topology/{bench_solution}/runs/{run}/captures  bss-10: the capture rows the run kept (on failure / pinned), one per line, with the acquisition the
                                                                    osc chart door (/api/instruments/captures/{acq}/chart) draws
404 = no such Bench Solution / run.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import config_rows as R
from cmod.custom import retest as RT
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


class RetestAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod/bench-topology/{bench_solution}/retest', self, suffix='retest')
            add('/api/cmod/bench-topology/{bench_solution}/run-all', self, suffix='run_all')   # bss-8
            add('/api/cmod/bench-topology/{bench_solution}/runs/{run}/signals', self, suffix='signals')
            add('/api/cmod/bench-topology/{bench_solution}/runs/{run}/edges', self, suffix='edges')
            add('/api/cmod/bench-topology/{bench_solution}/runs/{run}/captures', self, suffix='captures')   # bss-10

    def _do(self, response, fn, *args):
        try:
            out = fn(self.manager, *args)
            response.media = {'ok': True, 'rows': out} if isinstance(out, list) else out
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_post_retest(self, request, response, bench_solution):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except ValueError:
            body = {}
        if R.get(self.manager, 'BenchSolution', bench_solution) is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no Bench Solution %r' % bench_solution}
            return
        self._do(response, RT.retest, bench_solution, str((body or {}).get('catom') or ''))

    def on_post_run_all(self, request, response, bench_solution):
        """bss-8: every state node by every path, then the untested list."""
        if R.get(self.manager, 'BenchSolution', bench_solution) is None:
            response.status = falcon.HTTP_404
            response.media = {'ok': False, 'error': 'no Bench Solution %r' % bench_solution}
            return
        self._do(response, RT.run_all, bench_solution)

    def on_get_captures(self, request, response, bench_solution, run):
        """bss-10: the WaveformCapture rows a run kept (on failure, or pinned), one per line; the osc chart door draws an acquisition."""
        self._do(response, RT.run_captures, run)

    def on_get_signals(self, request, response, bench_solution, run):
        self._do(response, RT.run_signals, run)

    def on_get_edges(self, request, response, bench_solution, run):
        self._do(response, RT.run_edges, run)
