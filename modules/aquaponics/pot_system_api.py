"""
@cross-cutting
@module aquaponics.pot_system_api
@tags @xc:bindings

HTTP surface for bound pot systems (aqp-6):

  GET  /api/aquaponics/systems                    every system + refs
  GET  /api/aquaponics/systems/{name}/survival     survival verdict +
                                                   limiting factor
  POST /api/aquaponics/systems/{name}/impact       compute + persist
                                                   lifetime impact
                                                   (scoring reads it)

Environmental-impact SCORING of systems runs through the existing
context-scoring engine:
  GET /api/scoring/concepts/pot-environmental-impact/score

@consumers
  - aquaponics frontend (later) / scoring
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.pot_system_basis import system_impact, system_survival


class AquaponicsSystemAPI(treeObject):
    """Bound pot-system survival + impact endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/systems'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/systems', self, suffix='systems')
            polServer.falconServer.add_route(
                '/api/aquaponics/systems/{name}/survival', self,
                suffix='survival')
            polServer.falconServer.add_route(
                '/api/aquaponics/systems/{name}/impact', self,
                suffix='impact')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_systems(self, request, response):
        out = []
        for s in self._rows('PotSystemDefinition'):
            out.append({
                'name': getattr(s, 'name', ''),
                'displayName': getattr(s, 'display_name', ''),
                'pot': getattr(s, 'pot_name', ''),
                'soil': getattr(s, 'soil_name', ''),
                'water': getattr(s, 'water_name', ''),
                'plant': getattr(s, 'plant_name', ''),
                'atmosphere': getattr(s, 'atmosphere_name', '')})
        response.media = {'ok': True, 'systems': out}

    def on_get_survival(self, request, response, name):
        report = system_survival(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_post_impact(self, request, response, name):
        report = system_impact(self.manager, name, persist=True)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    # GET convenience (compute without persisting side-effect intent).
    def on_get_impact(self, request, response, name):
        report = system_impact(self.manager, name, persist=True)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
