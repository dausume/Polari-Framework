"""
@cross-cutting
@module polariPeers.module_projects_api
@tags @xc:bindings

Modules-as-projects endpoints (PeersAPI pattern):

  GET  /api/module-projects           statuses + fetch suggestions
  POST /api/module-projects/fetch     {"name": ...} → materialize
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from polariPeers.module_fetcher import (
    fetch_module_project, fetch_suggestions, project_statuses,
)


class ModuleProjectsAPI(treeObject):
    """Configured module projects: list, suggest, fetch."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/module-projects'
        if polServer is not None:
            polServer.falconServer.add_route('/api/module-projects', self)
            polServer.falconServer.add_route(
                '/api/module-projects/fetch', self, suffix='fetch')

    def on_get(self, request, response):
        response.media = {
            'projects': project_statuses(self.manager),
            'suggestions': fetch_suggestions(self.manager),
        }

    def on_post_fetch(self, request, response):
        body = json.load(request.bounded_stream)
        name = body.get('name', '')
        if not name:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': "'name' is required"}
            return
        result = fetch_module_project(self.manager, name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result
