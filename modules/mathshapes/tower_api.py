"""
@cross-cutting
@module mathshapes.tower_api
@tags @xc:bindings

HTTP surface for aquaponic towers (shape-2):

  GET /api/aquaponics/towers                    the tower catalogue.
  GET /api/aquaponics/towers/{name}/geometry    per-tier grow volume,
                                                footprint, height, and
                                                the top→bottom water path.
  GET /api/aquaponics/towers/{name}/growth-forecast?plant=&days=
                                                shape-4: per-tier
                                                fits/needs-pruning/will-
                                                fail growth prediction.

Towers are edited through CRUDE (object-coherence).

@consumers
  - tower frontend / SimSpace3D rendering + growth-forecast (shape-4)
@see /MATH_SHAPES_PLAN.md (PHASE shape-2 / shape-4)
"""

from objectTreeDecorators import treeObject, treeObjectInit
from mathshapes.tower_analysis import tower_geometry
from mathshapes.growth_prediction import tower_growth_forecast


class AquaponicTowerAPI(treeObject):
    """Aquaponic tower endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/towers'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/towers', self, suffix='catalogue')
            polServer.falconServer.add_route(
                '/api/aquaponics/towers/{name}/geometry', self,
                suffix='geometry')
            polServer.falconServer.add_route(
                '/api/aquaponics/towers/{name}/growth-forecast', self,
                suffix='growth_forecast')

    def _towers(self):
        table = (getattr(self.manager, 'objectTables', None) or {}).get(
            'AquaponicTowerDefinition', {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_catalogue(self, request, response):
        catalogue = [{
            'name': getattr(t, 'name', ''),
            'displayName': getattr(t, 'display_name', ''),
            'potShape': getattr(t, 'pot_shape_name', ''),
            'nTiers': getattr(t, 'n_tiers', 0),
        } for t in self._towers()]
        response.media = {'ok': True, 'count': len(catalogue),
                          'towers': catalogue}

    def on_get_geometry(self, request, response, name):
        result = tower_geometry(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_growth_forecast(self, request, response, name):
        params = request.params or {}
        plant = params.get('plant', '')
        try:
            days = float(params.get('days', 180.0))
        except (TypeError, ValueError):
            days = 180.0
        if not plant:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'a ?plant= is required'}
            return
        result = tower_growth_forecast(self.manager, name, plant,
                                       days=days)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
