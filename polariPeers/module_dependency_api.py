"""
@module polariPeers.module_dependency_api

HTTP surface for module/boundary dependency tracking (msci-21;
self-registering falcon module, the small-API pattern):

  GET  /api/modules/boundary-graph
       The coherent-module map: every declared framework boundary,
       its cross-boundary edges, and its external python imports.
  GET  /api/modules/dependencies/tree?boundary=<name>
       That boundary's python imports expanded into requires-trees
       (one shared `seen` map — shared downstream deps appear once,
       marked shared=true). No boundary param = the whole forest of
       every boundary's imports.
  POST /api/modules/dependencies/refresh
       (Re)populate the persisted PolariModuleDependency rows.
  GET  /api/modules/dependencies/install-plan
       The SUGGESTION: union of missing packages as ONE pip run.
  POST /api/modules/dependencies/install   {"confirm": true,
                                             "packages"?: [...]}
       Execute the single pip invocation (explicit knob — refuses
       without confirm).
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from moduleService.module_dependency_tracker import (
    FRAMEWORK_BOUNDARIES, boundary_graph, install_packages,
    plan_install, python_dependency_forest, refresh_dependency_rows,
    scan_python_imports,
)


class ModuleDependencyAPI(treeObject):
    """Boundary + dependency tracking endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/modules'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/modules/boundary-graph', self, suffix='graph')
            polServer.falconServer.add_route(
                '/api/modules/dependencies/tree', self, suffix='tree')
            polServer.falconServer.add_route(
                '/api/modules/dependencies/refresh', self,
                suffix='refresh')
            polServer.falconServer.add_route(
                '/api/modules/dependencies/install-plan', self,
                suffix='plan')
            polServer.falconServer.add_route(
                '/api/modules/dependencies/install', self,
                suffix='install')

    def on_get_graph(self, request, response):
        response.media = {'success': True, 'data': boundary_graph()}

    def on_get_tree(self, request, response):
        boundary = request.params.get('boundary', '')
        if boundary:
            if boundary not in FRAMEWORK_BOUNDARIES:
                response.status = '404 Not Found'
                response.media = {
                    'success': False,
                    'error': f"'{boundary}' is not a declared boundary",
                    'declared': sorted(FRAMEWORK_BOUNDARIES)}
                return
            import os
            from moduleService.module_dependency_tracker import (
                _framework_root, _sanitize_import_names,
            )
            packages = _sanitize_import_names(scan_python_imports(
                os.path.join(_framework_root(), boundary)))
        else:
            packages = sorted({
                dep for node in boundary_graph()['boundaries']
                for dep in node['pythonImports']})
        response.media = {'success': True,
                          'data': {'boundary': boundary or '(all)',
                                   **python_dependency_forest(packages)}}

    def on_post_refresh(self, request, response):
        response.media = refresh_dependency_rows(self.manager)

    def on_get_plan(self, request, response):
        response.media = {'success': True, 'data': plan_install()}

    def on_post_install(self, request, response):
        try:
            body = json.load(request.bounded_stream)
        except Exception:
            body = {}
        if not body.get('confirm'):
            response.status = '422 Unprocessable Entity'
            response.media = {
                'ok': False,
                'error': 'installs are an explicit knob — resend with '
                         '{"confirm": true}',
                'plan': plan_install()}
            return
        packages = body.get('packages') or plan_install()['packages']
        response.media = install_packages(packages)
