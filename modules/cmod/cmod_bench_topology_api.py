"""
@module cmod.cmod_bench_topology_api

bss-1 doors (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md): a Bench Solution's Hardware Event topology. The work is in cmod.custom.bench_topology /
bench_events / isotope_step_rules; these doors only read the request and say a refusal in words.

GET  /api/cmod/topology-words                                              the words: node / edge / requirement / event kinds, sources, step kinds
GET  /api/cmod/bench-topology/{bench_solution}                             the view: root chain, nodes (requirements, executions, collaterals, paths, blocked,
                                                                           step + what set it), edges, the offered Hardware Events (re-derived)
POST /api/cmod/bench-topology/{bench_solution}/nodes                       body {slug, title, from_node, edge_kind, event, requirements[], executions[], collaterals[]}
                                                                           -> the node view (its edge, derived collaterals and paths included)
POST /api/cmod/bench-topology/{bench_solution}/edges                       body {from_node, to_node, kind, event}: another path into an existing node -> the node view
GET  /api/cmod/bench-topology/{bench_solution}/events/{event}/predicted    the chain the assertions predict for one event; [] = nothing asserted
POST /api/cmod/bench-topology/{bench_solution}/step-rules                  body {variants: [...]}: derive the IsotopeStepRule rows -> the rows
GET  /api/cmod/topology-specs                                              bss-8: the shipped topology specs (custom/topologies/*.json, one per Bench System)
POST /api/cmod/bench-topology/{bench_solution}/apply-spec                  bss-8: body {spec?}: apply the Bench System's spec (roles -> this Solution's events,
                                                                           jobs -> this variant's isotopes) -> {roles, routes, nodes, skipped, words}
404 = no such Bench Solution / node / event; 409 = no live server; 422 = a node without requirements.
"""
import json

import falcon
from objectTreeDecorators import treeObject, treeObjectInit

from cmod.custom import bench_events as E
from cmod.custom import bench_topology as T
from cmod.custom import isotope_step_rules as S
from cmod.custom import topology_words as W
from cmod.custom.config_rows import ConfigRefused

_STATUS = {404: falcon.HTTP_404, 409: falcon.HTTP_409, 422: falcon.HTTP_422}


def _json(request):
    try:
        v = json.loads(request.bounded_stream.read() or b'{}')
        return v if isinstance(v, dict) else {}
    except ValueError:
        return {}


class BenchTopologyAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer=None, manager=None):
        self.polServer = polServer
        self.manager = manager
        if polServer is not None and getattr(polServer, 'falconServer', None) is not None:
            add = polServer.falconServer.add_route
            add('/api/cmod/topology-words', self, suffix='words')
            add('/api/cmod/bench-topology/{bench_solution}', self)
            add('/api/cmod/bench-topology/{bench_solution}/nodes', self, suffix='nodes')
            add('/api/cmod/bench-topology/{bench_solution}/edges', self, suffix='edges')
            add('/api/cmod/bench-topology/{bench_solution}/events/{event}/predicted', self, suffix='predicted')
            add('/api/cmod/bench-topology/{bench_solution}/step-rules', self, suffix='step_rules')
            add('/api/cmod/topology-specs', self, suffix='specs')                                       # bss-8
            add('/api/cmod/bench-topology/{bench_solution}/apply-spec', self, suffix='apply_spec')    # bss-8

    def on_get_specs(self, request, response):
        from cmod.custom import bench_topology_spec as SP
        response.media = {'ok': True, 'rows': SP.specs()}

    def on_post_apply_spec(self, request, response, bench_solution):
        from cmod.custom import bench_topology_spec as SP
        self._do(response, SP.apply, bench_solution, str(_json(request).get('spec') or ''))

    def _do(self, response, fn, *args, **kw):
        try:
            out = fn(self.manager, *args, **kw)
            response.media = out if isinstance(out, dict) and 'ok' in out else {'ok': True, 'rows': out} if isinstance(out, list) else dict(out, ok=True)
        except ConfigRefused as e:
            response.status = _STATUS.get(e.status, falcon.HTTP_422)
            response.media = {'ok': False, 'error': e.why}

    def on_get_words(self, request, response):
        response.media = {'ok': True, 'node_kinds': W.NODE_KINDS, 'edge_kinds': W.EDGE_KINDS, 'requirement_kinds': W.REQUIREMENT_KINDS, 'event_kinds': W.EVENT_KINDS,
                          'event_sources': list(W.EVENT_SOURCES), 'collateral_kinds': W.COLLATERAL_KINDS, 'engines': list(W.ENGINES), 'step_kinds': W.STEP_KINDS,
                          'sample_kinds': W.SAMPLE_KINDS}

    def on_get(self, request, response, bench_solution):
        self._do(response, T.view, bench_solution)

    def on_post_nodes(self, request, response, bench_solution):
        b = _json(request)
        self._do(response, T.define, bench_solution, str(b.get('slug', '')), str(b.get('title', '')), str(b.get('from_node', '')), str(b.get('edge_kind', 'trigger')),
                 str(b.get('event', '')), b.get('requirements') or [], b.get('executions') or [], b.get('collaterals') or [])

    def on_post_edges(self, request, response, bench_solution):
        b = _json(request)
        self._do(response, T.connect, bench_solution, str(b.get('from_node', '')), str(b.get('to_node', '')), str(b.get('kind', 'trigger')), str(b.get('event', '')))

    def on_get_predicted(self, request, response, bench_solution, event):
        self._do(response, E.predicted, bench_solution, event)

    def on_post_step_rules(self, request, response, bench_solution):
        variants = [str(v) for v in (_json(request).get('variants') or [])]
        self._do(response, S.derive, variants)
