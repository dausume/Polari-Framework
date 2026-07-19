"""
@module pspp.pspp_api

HTTP surface for the PSPP views (PeersAPI pattern — self-registering
falcon routes). Thin over pspp_views/progress_engine; every payload
carries its evidence and refusals render as refusals.

  GET  /api/pspp/datasets                    dataset catalog
  GET  /api/pspp/datasets/{name}/curve       chart-ready curve + bands
  GET  /api/pspp/network                     reaction-network graph
  GET  /api/pspp/states/{material}           MaterialState DAG
  GET  /api/pspp/progress?mr=&t=&hours=      cure-progress v1
  POST /api/pspp/grade                       composition → windows
  GET  /api/pspp/pathways?cation=&mr=&site=  kinetics-free reachability
  POST /api/pspp/guide                       experiment guidance
  POST /api/pspp/checkpoint                  cure checkpoint plan/apply
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from pspp.cure_checkpoints import (
    apply_cure_checkpoint, plan_cure_checkpoint,
)
from pspp.experiment_guidance import experiment_guide
from pspp.network_stepping import (
    reachable_frameworks, solution_inventory,
)
from pspp.pspp_views import (
    dataset_catalog, dataset_curve, grade_payload, network_graph,
    state_dag,
)
from pspp.progress_engine import cure_progress


class PsppAPI(treeObject):
    """PSPP dataset/network/grading/progress endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/pspp'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/pspp/datasets', self, suffix='datasets')
            add('/api/pspp/datasets/{name}/curve', self,
                suffix='curve')
            add('/api/pspp/network', self, suffix='network')
            add('/api/pspp/states/{material}', self, suffix='states')
            add('/api/pspp/progress', self, suffix='progress')
            add('/api/pspp/grade', self, suffix='grade')
            add('/api/pspp/pathways', self, suffix='pathways')
            add('/api/pspp/guide', self, suffix='guide')
            add('/api/pspp/checkpoint', self, suffix='checkpoint')

    def on_get_datasets(self, request, response):
        response.media = dataset_catalog(self.manager)

    def on_get_curve(self, request, response, name):
        samples = request.get_param_as_int('samples') or 60
        payload = dataset_curve(self.manager, name,
                                samples=max(8, min(samples, 400)))
        if not payload.get('ok'):
            response.status = '404 Not Found'
        response.media = payload

    def on_get_network(self, request, response):
        response.media = network_graph(self.manager)

    def on_get_states(self, request, response, material):
        response.media = state_dag(self.manager, material)

    def on_get_progress(self, request, response):
        try:
            mr = float(request.get_param('mr') or '')
        except ValueError:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'mr must be a number'}
            return
        temperature = request.get_param('t')
        hours = request.get_param('hours')
        payload = cure_progress(
            self.manager, mr,
            cure_temperature_c=float(temperature) if temperature
            else 80.0,
            hours=float(hours) if hours else 6.0)
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def _live(self, table, seeds):
        from pspp.pspp_views import _seed_or_rows
        return _seed_or_rows(self.manager, table, seeds)

    def on_get_pathways(self, request, response):
        from pspp.reaction_network import SEED_REACTION_RULES
        from pspp.threshold_windows import SEED_THRESHOLD_WINDOWS
        cation = request.get_param('cation') or ''
        try:
            mr = float(request.get_param('mr') or '')
        except ValueError:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'mr must be a number',
                              'suggestion': '?cation=Na&mr=1.0'}
            return
        from pspp.pspp_views import _datasets
        inventory = solution_inventory(cation, mr,
                                       datasets=_datasets(self.manager))
        if not inventory.get('ok'):
            response.status = '422 Unprocessable Entity'
            response.media = inventory
            return
        payload = reachable_frameworks(
            inventory['inventory'],
            rules=self._live('ReactionRule', SEED_REACTION_RULES),
            site=request.get_param('site'),
            conditions={'MR': mr},
            windows=self._live('ThresholdReactionWindow',
                               SEED_THRESHOLD_WINDOWS),
            cation=cation)
        payload['inventory'] = inventory['inventory']
        payload['inventoryAssumptions'] = inventory['assumptions']
        response.media = payload

    def on_post_guide(self, request, response):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'body must be JSON'}
            return
        mr = body.get('mr')
        response.media = experiment_guide(
            self.manager,
            composition=body.get('composition'),
            basis=body.get('basis', 'mass'),
            family=body.get('family', ''),
            cation=body.get('cation', ''),
            mr=float(mr) if mr is not None else None,
            cure_temperature_c=float(body.get('t', 80.0)),
            site=body.get('site'))

    def on_post_checkpoint(self, request, response):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'body must be JSON'}
            return
        material = body.get('material', '')
        mr = body.get('mr')
        if not material or mr is None:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'material and mr are '
                                         'required',
                              'suggestion': '{"material": "...", '
                                            '"mr": 1.83, "apply": '
                                            'false}'}
            return
        run = (apply_cure_checkpoint if body.get('apply')
               else plan_cure_checkpoint)
        payload = run(self.manager, material, float(mr),
                      cure_temperature_c=float(body.get('t', 80.0)),
                      state_name=body.get('state_name', ''),
                      parent_state=body.get('parent_state'))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload

    def on_post_grade(self, request, response):
        try:
            body = json.loads(request.bounded_stream.read() or b'{}')
        except Exception:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'refusal': 'body must be JSON'}
            return
        payload = grade_payload(
            self.manager, body.get('composition'),
            basis=body.get('basis', 'mass'),
            family=body.get('family', ''))
        if not payload.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = payload
