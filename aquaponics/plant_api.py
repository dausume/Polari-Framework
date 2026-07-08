"""
@cross-cutting
@module aquaponics.plant_api
@tags @xc:bindings

HTTP surface for per-part plant analysis (aqp-4):

  GET /api/aquaponics/plants                    every plant + its parts
  GET /api/aquaponics/plants/{name}/capture     permanent carbon +
                                                nutrient capture, per
                                                part by volume
  GET /api/aquaponics/plants/{name}/budget      net CO2/O2 + nutrient
                                                flux, survival bands,
                                                lifetime estimate

Plants + parts are edited via CRUDE (object-coherence).

@consumers
  - aquaponics frontend (later phase) / aqp-6 scoring
@see /AQUAPONICS_MODULE_PLAN.md
"""

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.plant_analysis import (
    plant_gas_nutrient_budget, plant_lifetime_capture,
)


class AquaponicsPlantAPI(treeObject):
    """Per-part plant analysis endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/plants'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/plants', self, suffix='plants')
            polServer.falconServer.add_route(
                '/api/aquaponics/plants/{name}/capture', self,
                suffix='capture')
            polServer.falconServer.add_route(
                '/api/aquaponics/plants/{name}/budget', self,
                suffix='budget')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_plants(self, request, response):
        parts = self._rows('PlantPart')
        out = []
        for plant in self._rows('PlantDefinition'):
            name = getattr(plant, 'name', '')
            mine = [getattr(p, 'part', '') for p in parts
                    if getattr(p, 'plant_name', '') == name]
            out.append({
                'name': name,
                'displayName': getattr(plant, 'display_name', ''),
                'species': getattr(plant, 'species', ''),
                'lifeCycle': getattr(plant, 'life_cycle', ''),
                'lifetimeDays': getattr(plant, 'lifetime_days', None),
                'parts': mine})
        response.media = {'ok': True, 'plants': out}

    def on_get_capture(self, request, response, name):
        report = plant_lifetime_capture(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report

    def on_get_budget(self, request, response, name):
        report = plant_gas_nutrient_budget(self.manager, name)
        if not report.get('ok'):
            response.status = '404 Not Found'
        response.media = report
