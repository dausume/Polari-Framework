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
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

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
