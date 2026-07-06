"""
@cross-cutting
@module materialsScience.scale_execution_api
@tags @xc:bindings

HTTP surface for the materials basis engines (PeersAPI pattern —
self-registering falcon routes):

  GET  /api/msci/engines/capability      honest FEM+DFT capability
                                         (local layers + worker reach)
  POST /api/msci/scale-definitions/execute   {"name": "<row name>"} →
                                         execute_scale_definition
  POST /api/msci/gates/check             {"material": ..., "levels": [..],
                                         "acceptPartial": bool} →
                                         require_scale_levels verdict
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from materialsScience.engines import dft_engine, fem_engine
from materialsScience.scale_execution import execute_scale_definition
from materialsScience.scale_presence import require_scale_levels


class ScaleExecutionAPI(treeObject):
    """Materials-basis engine + gate endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/msci'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/msci/engines/capability', self, suffix='capability')
            polServer.falconServer.add_route(
                '/api/msci/scale-definitions/execute', self,
                suffix='execute')
            polServer.falconServer.add_route(
                '/api/msci/gates/check', self, suffix='gates')

    def on_get_capability(self, request, response):
        response.media = {
            'fem': fem_engine.capability(),
            'dft': dft_engine.capability(),
        }

    def on_post_execute(self, request, response):
        body = json.load(request.bounded_stream)
        name = body.get('name', '')
        if not name:
            response.status = '400 Bad Request'
            response.media = {'ok': False, 'error': "'name' is required"}
            return
        result = execute_scale_definition(self.manager, name)
        if not result.get('ok'):
            response.status = '422 Unprocessable Entity'
        response.media = result

    def on_post_gates(self, request, response):
        body = json.load(request.bounded_stream)
        material = body.get('material', '')
        levels = body.get('levels', [])
        if not material or not isinstance(levels, list) or not levels:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': "'material' and non-empty 'levels' "
                                       "are required"}
            return
        response.media = require_scale_levels(
            self.manager, material, levels,
            accept_partial=bool(body.get('acceptPartial', False)))
