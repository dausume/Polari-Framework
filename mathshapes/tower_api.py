"""
@cross-cutting
@module mathshapes.tower_api
@tags @xc:bindings

HTTP surface for aquaponic towers (shape-2):

  GET /api/aquaponics/towers                    the tower catalogue.
  GET /api/aquaponics/towers/{name}/geometry    per-tier grow volume,
                                                footprint, height, and
                                                the top→bottom water path.

Towers are edited through CRUDE (object-coherence).

@consumers
  - tower frontend / SimSpace3D rendering + growth-forecast (shape-4)
@see /MATH_SHAPES_PLAN.md (PHASE shape-2)
"""

from objectTreeDecorators import treeObject, treeObjectInit
from mathshapes.tower_analysis import tower_geometry


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
