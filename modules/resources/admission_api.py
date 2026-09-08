"""
@cross-cutting
@module resources.admission_api

AdmissionAPI (res-4): the admission-advisor surface. Every response
is a verdict + an evidence-bearing suggestion pointing at topology
knobs — the API never moves anything (knobs-and-suggestions).

@consumers
  - polariServer (instantiated next to ResourceProfilesAPI)
  - polari-platform-angular Topology tab ("what if I add …")
  - resources.admission_selftest (handler-level, fake manager)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

from resources.custom.admission_advisor import (
    assess_module_admission, assess_set_feasibility,
    efficiency_suggestions,
)


class AdmissionAPI(treeObject):
    """Module-admission + set-feasibility endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/topology/admission'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/topology/admission', self, suffix='admission')
            add('/api/topology/fit', self, suffix='fit')
            add('/api/topology/placement-suggestions', self,
                suffix='placement')

    def _payload(self, request):
        try:
            raw = request.bounded_stream.read()
            return (json.loads(raw) if raw else {}), None
        except Exception as e:
            return None, f'bad JSON payload: {e}'

    def _refuse(self, response, error, status='400 Bad Request'):
        response.status = status
        response.media = {'ok': False, 'error': error}

    def on_post_admission(self, request, response):
        """{module, topology?} -> route-to-storage | fits-as-is |
        fits-with-reallocation | would-break."""
        payload, err = self._payload(request)
        if err:
            return self._refuse(response, err)
        module = (payload or {}).get('module', '')
        if not module:
            return self._refuse(response, 'payload needs {module}')
        report = assess_module_admission(
            self.manager, module,
            topology_name=(payload or {}).get('topology', ''))
        if not report.get('ok'):
            response.status = '409 Conflict'
        response.media = report

    def on_get_fit(self, request, response):
        """?modules=a,b,c&node=<name> -> yes | tight | no."""
        modules = [m for m in (request.params.get('modules', '')
                               or '').split(',') if m]
        node = request.params.get('node', '')
        if not modules or not node:
            return self._refuse(
                response, 'needs ?modules=<csv>&node=<name>')
        report = assess_set_feasibility(self.manager, modules, node)
        if not report.get('ok'):
            response.status = '409 Conflict'
        response.media = report

    def on_get_placement(self, request, response):
        """Efficiency swaps for the topology (beyond degraded-only)."""
        response.media = {
            'ok': True,
            'suggestions': efficiency_suggestions(
                self.manager,
                request.params.get('topology', ''))}
