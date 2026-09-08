"""
@cross-cutting
@module tanks.tank_api
@tags @xc:bindings

HTTP surface for tank-1 ecosystem simulation:

  GET /api/tanks/substrates
        every TankSubstrateDefinition (the fresh/salt soil category).
  GET /api/tanks/systems
        every TankSystemDefinition + water type + stock size.
  GET /api/tanks/systems/{name}/balance
        net N/P flux, detritus load, role coverage, self-regulating?
  GET /api/tanks/systems/{name}/yield?days=30
        harvestable biomass + DietaryNutrients (iodine/sodium/chloride
        seaweed gap-fillers) over the period.
  GET /api/tanks/systems/{name}/suggest
        species to add to balance / complete the ecosystem.

Tanks / species / systems are edited through CRUDE (object-coherence).

@consumers
  - tanks frontend (later); nutrition fulfillment (seaweed gap-fillers)
@see /SALTWATER_FOOD_FOREST_SPEC.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from tanks.custom.tank_analysis import (
    harvest_yield, nutrient_balance, regulate_suggestions,
)


class TankSystemAPI(treeObject):
    """tank-1 ecosystem endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/tanks'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/tanks/substrates', self, suffix='substrates')
            polServer.falconServer.add_route(
                '/api/tanks/systems', self, suffix='systems')
            polServer.falconServer.add_route(
                '/api/tanks/systems/{name}/balance', self,
                suffix='balance')
            polServer.falconServer.add_route(
                '/api/tanks/systems/{name}/yield', self, suffix='yield')
            polServer.falconServer.add_route(
                '/api/tanks/systems/{name}/suggest', self,
                suffix='suggest')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def on_get_substrates(self, request, response):
        out = []
        for s in self._rows('TankSubstrateDefinition'):
            out.append({
                'name': getattr(s, 'name', ''),
                'displayName': getattr(s, 'display_name', ''),
                'waterType': getattr(s, 'water_type', ''),
                'kind': getattr(s, 'kind', ''),
                'buffersPh': bool(getattr(s, 'buffers_ph', False)),
                'denitrificationMgNPerLPerDay':
                    getattr(s, 'denitrification_mg_n_per_l_per_day', 0),
                'biofiltrationCapacity':
                    getattr(s, 'biofiltration_capacity', 0),
                'supportsAnaerobicLayer':
                    bool(getattr(s, 'supports_anaerobic_layer', False))})
        response.media = {'ok': True, 'substrates': out,
                          'count': len(out)}

    def on_get_systems(self, request, response):
        out = []
        for s in self._rows('TankSystemDefinition'):
            try:
                stock = json.loads(
                    getattr(s, 'species_stock_json', '{}') or '{}')
            except Exception:
                stock = {}
            out.append({'name': getattr(s, 'name', ''),
                        'displayName': getattr(s, 'display_name', ''),
                        'waterType': getattr(s, 'water_type', ''),
                        'speciesCount': len(stock),
                        'totalStock': sum(stock.values())})
        response.media = {'ok': True, 'systems': out}

    def on_get_balance(self, request, response, name):
        result = nutrient_balance(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_yield(self, request, response, name):
        days = float((request.params or {}).get('days', 30.0) or 30.0)
        result = harvest_yield(self.manager, name, days=days)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_suggest(self, request, response, name):
        result = regulate_suggestions(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result
