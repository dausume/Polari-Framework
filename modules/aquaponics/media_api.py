"""
@cross-cutting
@module aquaponics.media_api
@tags @xc:bindings

HTTP surface for soil / water / nutrient profiles (aqp-2):

  GET /api/aquaponics/nutrient-profiles/{name}/analyze  species vs
                                            typical ranges + N:P:K
  GET /api/aquaponics/soils/{name}/capacity  plant-available water +
                                            drainage + scales
  GET /api/aquaponics/waters/{name}/summary  state + source +
                                            dissolved gases + nutrient
                                            balance

Definitions are edited via standard CRUDE (object-coherence).

@consumers
  - aquaponics frontend (later phase)
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.custom.media_analysis import (
    analyze_nutrient_profile, soil_water_capacity, water_summary,
)


class AquaponicsMediaAPI(treeObject):
    """Soil / water / nutrient analysis endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/media'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/nutrient-profiles/{name}/analyze',
                self, suffix='analyze')
            polServer.falconServer.add_route(
                '/api/aquaponics/soils/{name}/capacity', self,
                suffix='soil')
            polServer.falconServer.add_route(
                '/api/aquaponics/waters/{name}/summary', self,
                suffix='water')

    def on_get_analyze(self, request, response, name):
        report = analyze_nutrient_profile(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_soil(self, request, response, name):
        report = soil_water_capacity(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_water(self, request, response, name):
        report = water_summary(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
