"""
@cross-cutting
@module simSpace.sim_space_api
@tags @xc:render-shared, @xc:bindings

Snapshot endpoint — the dimension-dispatching surface the frontend hits
to render a SimSpace. One URL, one envelope, dimension-specific compilers:

    GET /api/simspace                  list (filterable by ?dimensionality=)
    GET /api/simspace/{name}/snapshot  compile + return

Response envelope (regardless of dimensionality):
    {
      "success": true,
      "data": {
        "definition":       SimSpaceDefinitionPayload,
        "objects":          [SimSpaceObject, ...],
        "connections":      [SimSpaceConnection, ...],
        "resolvedBindings": [SimSpaceResolvedBinding, ...],
        "warnings":         [string, ...]
      }
    }

The dimension-specific compile logic lives in `compilers/` — this file
only wires the route handlers and delegates.

@consumers
  - polariServer (route registration)
  - frontend SimSpaceService
@impact-on-edit
  Changing the response shape is a frontend breaking change. Update
  SimSpaceSnapshot in sim-space-types.ts in the same PR.
@see /OVERLAP_MAP.md
"""

import json
from typing import Dict, List

from objectTreeDecorators import treeObject, treeObjectInit
import falcon

from .compilers import compile_2d, compile_3d


class SimSpaceAPI(treeObject):
    """Routes:
        GET /api/simspace                  list all SimSpaceDefinitions
        GET /api/simspace/{name}/snapshot  compile + return the snapshot
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/simspace'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(
                self.apiName + '/{name}/snapshot', self, suffix='snapshot'
            )

    # ------------------------------------------------------------------
    # GET /api/simspace — list (filterable by ?dimensionality=2d|3d)
    # ------------------------------------------------------------------
    def on_get(self, request, response):
        dim_filter = request.get_param('dimensionality')
        rows = self.manager.objectTables.get('SimSpaceDefinition', {}) or {}
        out: List[Dict] = []
        for r in rows.values():
            if dim_filter and getattr(r, 'dimensionality', '2d') != dim_filter:
                continue
            out.append(self._row_to_summary(r))
        out.sort(key=lambda x: x['name'])
        response.media = {'success': True, 'data': out}
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # GET /api/simspace/{name}/snapshot
    # ------------------------------------------------------------------
    def on_get_snapshot(self, request, response, name):
        row = self._find_by_name(name)
        if row is None:
            response.status = falcon.HTTP_404
            response.media = {'success': False, 'error': f'SimSpace "{name}" not found'}
            return
        dim = getattr(row, 'dimensionality', '2d')
        warnings: List[str] = []
        resolved_bindings: List[Dict] = []
        try:
            if dim == '2d':
                objects, connections = compile_2d(self.manager, row, warnings, resolved_bindings)
            elif dim == '3d':
                objects, connections = compile_3d(self.manager, row, warnings, resolved_bindings)
            else:
                objects, connections = [], []
                warnings.append(f"Unknown dimensionality '{dim}' — returning empty snapshot.")
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': f'Snapshot compile failed: {e}'}
            return

        response.media = {
            'success': True,
            'data': {
                'definition': self._row_to_payload(row),
                'objects': objects,
                'connections': connections,
                'resolvedBindings': resolved_bindings,
                'warnings': warnings,
            },
        }
        response.status = falcon.HTTP_200

    # ------------------------------------------------------------------
    # Helpers (small enough to keep alongside the routes)
    # ------------------------------------------------------------------
    def _find_by_name(self, name: str):
        rows = self.manager.objectTables.get('SimSpaceDefinition', {}) or {}
        for r in rows.values():
            if getattr(r, 'name', '') == name:
                return r
        return None

    def _row_to_summary(self, row) -> Dict:
        return {
            'name': row.name,
            'description': getattr(row, 'description', ''),
            'dimensionality': getattr(row, 'dimensionality', '2d'),
            'coordinateSystem': getattr(row, 'coordinate_system', 'math'),
        }

    def _row_to_payload(self, row) -> Dict:
        try:
            viewport = json.loads(getattr(row, 'viewport_json', '') or 'null')
        except (ValueError, TypeError):
            viewport = None
        try:
            bound_classes = json.loads(getattr(row, 'bound_classes_json', '') or '[]')
        except (ValueError, TypeError):
            bound_classes = []
        return {
            'id': row.name,  # name is the stable identity
            'name': row.name,
            'description': getattr(row, 'description', ''),
            'dimensionality': getattr(row, 'dimensionality', '2d'),
            'coordinateSystem': getattr(row, 'coordinate_system', 'math'),
            'unitScale': getattr(row, 'unit_scale', 1.0),
            'viewport': viewport,
            'boundClasses': bound_classes,
            'definition': getattr(row, 'definition', '{}'),
        }
