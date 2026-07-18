"""
@cross-cutting
@module nutrition.food_api
@tags @xc:bindings

HTTP surface for nut-2 (plant harvest -> meal nutrients):

  GET  /api/nutrition/foods
        the food catalog + each food's headline nutrients.
  GET  /api/nutrition/foods/{name}/nutrients
        per-harvest nutrient yield at MATURE volume.
  POST /api/nutrition/foods/{name}/nutrients
        body {plant, days, supplyFactor?} -> runs the simplified/
        aggregate growth model first (2026-07-15 — was aqp-8's
        plant_growth.grow, renamed + rebuilt to pull its constants
        from the real detailed model), then the REALIZED harvest yield
        (the self-watering-pot loop closed).

Foods are edited through CRUDE on FoodItem / NutrientContent rows.

@consumers
  - nutrition frontend (later); nut-5 fulfillment
@see /HOUSEHOLD_NUTRITION_PLAN.md §nut-2
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from nutrition.harvest_analysis import (
    food_catalog, harvest_nutrients,
)


class NutritionFoodAPI(treeObject):
    """nut-2 harvest endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/nutrition/foods'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/nutrition/foods', self, suffix='foods')
            polServer.falconServer.add_route(
                '/api/nutrition/foods/{name}/nutrients', self,
                suffix='nutrients')

    def on_get_foods(self, request, response):
        response.media = food_catalog(self.manager)

    def on_get_nutrients(self, request, response, name):
        result = harvest_nutrients(self.manager, name)
        if not result.get('ok'):
            response.status = '404 Not Found' \
                if 'no FoodItem' in str(result.get('error', '')) \
                else '400 Bad Request'
        response.media = result

    def on_post_nutrients(self, request, response, name):
        """Grow the plant (simplified/aggregate model) then compute
        the REALIZED harvest."""
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        grow_result = None
        plant = body.get('plant')
        if plant:
            try:
                from aquaponics.plant_growth_simplified import grow
                grow_result = grow(
                    self.manager, plant,
                    days=float(body.get('days', 60.0) or 60.0),
                    supply_factor=float(
                        body.get('supplyFactor', 1.0) or 1.0),
                    supply_factor_by_part=body.get(
                        'supplyFactorByPart') or {})
            except Exception as e:
                response.status = '400 Bad Request'
                response.media = {'ok': False,
                                  'error': f'grow failed: {e}'}
                return
        result = harvest_nutrients(self.manager, name,
                                   grow_result=grow_result)
        if not result.get('ok'):
            response.status = '400 Bad Request'
        elif grow_result is not None:
            result['grewPlant'] = plant
            result['survived'] = grow_result.get('survived')
        response.media = result
