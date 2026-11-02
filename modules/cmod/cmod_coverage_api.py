"""
@module cmod.cmod_coverage_api

bss-6 doors (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 5b "Making it obvious what was tested"): what a Bench Solution's topology has tested and what it
has not, as flat rows for configured tables (no raw JSON on screens). The work is in cmod.custom.topology_coverage; these doors only route.

GET /api/cmod/bench-topology/{bench_solution}/coverage              the strip: nodes by state, events by kind / source (used, run), fields covered / never changed,
                                                                    samples declared / used, paths tested / all, assertions exercised / all, the untested list
GET /api/cmod/bench-topology/{bench_solution}/coverage/untested     {rows: [{words}]} - the untested list FIRST; an empty list is the only green
GET /api/cmod/bench-topology/{bench_solution}/coverage/nodes        one row per node: state, runs, paths tested / all, confirmed by, voided, blocked, collaterals measured
GET /api/cmod/bench-topology/{bench_solution}/coverage/events       one row per Hardware Event: kind, source, what, used by an edge?, ever run?
GET /api/cmod/bench-topology/{bench_solution}/coverage/runs         one row per run across the topology, newest first
GET /api/cmod/bench-topology/{bench_solution}/coverage/assertions   one row per Catom assertion of the firmware: exercised by a run that met its node, or not
GET /api/cmod/bench-topology/{bench_solution}/coverage/strip-rows   the strip as rows {measure, value, words} for a table
404 = no such Bench Solution.
"""
import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import config_rows as R
from cmod.custom import topology_coverage as COV
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


def events(manager, bs):
    edges = R.rows(manager, 'StructEdge', bench_solution=bs)
    used = {e['event'] for e in edges if e['event']}
    ran = set()
    for n in R.rows(manager, 'StructNode', bench_solution=bs):
        for r in R.rows(manager, 'StructNodeRun', node=n['name']):
            for re_ in R.rows(manager, 'StructNodeRunEdge', run=r['name']):
                ed = R.get(manager, 'StructEdge', re_['edge'])
                if ed and ed['event'] and re_['outcome'] != 'skipped':
                    ran.add(ed['event'])
    return [dict(ev, used_by_an_edge='yes' if ev['name'] in used else 'no', ever_run='yes' if ev['name'] in ran else 'no')
            for ev in sorted(R.rows(manager, 'HardwareEvent', bench_solution=bs), key=lambda e: e['name'])]


def runs(manager, bs):
    out = []
    for n in R.rows(manager, 'StructNode', bench_solution=bs):
        out += R.rows(manager, 'StructNodeRun', node=n['name'])
    return sorted(out, key=lambda r: r['ran_at'], reverse=True)


def strip_rows(manager, bs):
    s = COV.strip(manager, bs)
    rows = [{'measure': 'untested items', 'value': len(s['untested']), 'words': 'the list below; an empty list is the only green'},
            {'measure': 'nodes', 'value': s['nodes'], 'words': ', '.join('%s %d' % (k, v) for k, v in s['nodes_by_state'].items() if v)},
            {'measure': 'paths tested', 'value': '%d / %d' % (s['paths_tested'], s['paths']), 'words': 'a node is tested along a path from the root; every path counts once'},
            {'measure': 'struct fields covered', 'value': '%d / %d' % (len(s['fields_covered']), len(s['fields_covered']) + len(s['fields_never_changed'])),
             'words': ('changed in a run that met its node: %s' % ', '.join(s['fields_covered'])) + ('; never changed: %s' % ', '.join(s['fields_never_changed']) if s['fields_never_changed'] else '')},
            {'measure': 'samples used', 'value': '%d / %d' % (s['samples_used'], s['samples_declared']), 'words': 'declared sample values that some node requires exactly'},
            {'measure': 'assertions exercised', 'value': '%d / %d' % (s['assertions_exercised'], s['assertions']), 'words': 'the firmware\'s own claims a confirmed run exercised'}]
    rows += [{'measure': 'events %s' % e['kind_source'], 'value': '%d (used %d, run %d)' % (e['events'], e['used_by_an_edge'], e['ever_run']), 'words': 'offered / used by an edge / ever run'}
             for e in s['events']]
    from cmod.custom import bench_topology_nocode as BN
    rows.append({'measure': 'the drawing', 'value': BN.drawing_route(bs), 'words': 'the same topology on the no-code canvas, coloured by confirmation state'})
    return rows


class CoverageAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod/bench-topology/{bench_solution}/coverage', self)
            for which in ('untested', 'nodes', 'events', 'runs', 'assertions', 'strip-rows'):
                add('/api/cmod/bench-topology/{bench_solution}/coverage/%s' % which, self, suffix=which.replace('-', '_'))

    def _do(self, response, fn, bs, as_words=False):
        try:
            if R.get(self.manager, 'BenchSolution', bs) is None:
                raise ConfigRefused('no Bench Solution %r' % bs, status=404)
            out = fn(self.manager, bs)
            response.media = {'ok': True, 'rows': [{'words': w} for w in out] if as_words else out} if isinstance(out, list) else out
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_get(self, request, response, bench_solution):
        self._do(response, COV.strip, bench_solution)

    def on_get_untested(self, request, response, bench_solution):
        self._do(response, COV.untested, bench_solution, as_words=True)

    def on_get_nodes(self, request, response, bench_solution):
        self._do(response, COV.nodes, bench_solution)

    def on_get_events(self, request, response, bench_solution):
        self._do(response, events, bench_solution)

    def on_get_runs(self, request, response, bench_solution):
        self._do(response, runs, bench_solution)

    def on_get_assertions(self, request, response, bench_solution):
        self._do(response, COV.assertions, bench_solution)

    def on_get_strip_rows(self, request, response, bench_solution):
        self._do(response, strip_rows, bench_solution)
