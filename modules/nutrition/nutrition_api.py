"""
@cross-cutting
@module nutrition.nutrition_api
@tags @xc:bindings

HTTP surface for nut-1/3/4 (person + household nutrition):

  GET  /api/nutrition/nutrients
        the dietary-nutrient vocabulary + plant availability.
  GET  /api/nutrition/persons/{name}/bmr
        BMR + TDEE + calorie target (with any safety warning).
  POST /api/nutrition/persons/{name}/needs
        body {period: day|week|month} -> per-nutrient needs.
  GET  /api/nutrition/households/{name}/needs?period=week
        aggregate household demand + per-member breakdown.

Profiles are edited through standard CRUDE on DietaryNutrient /
NutrientReference / PersonProfile / HouseholdProfile rows
(object-coherence).

@consumers
  - nutrition frontend (later); nut-5 fulfillment
@see /HOUSEHOLD_NUTRITION_PLAN.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from nutrition.person_analysis import (
    bmr, calorie_target, nutrient_needs, tdee,
)
from nutrition.household_analysis import household_needs


class NutritionAPI(treeObject):
    """nut-1/3/4 endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/nutrition'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/nutrition/nutrients', self, suffix='nutrients')
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/bmr', self, suffix='bmr')
            polServer.falconServer.add_route(
                '/api/nutrition/persons/{name}/needs', self,
                suffix='needs')
            polServer.falconServer.add_route(
                '/api/nutrition/households/{name}/needs', self,
                suffix='household')

    def _rows(self, class_name):
        table = (self.manager.objectTables or {}).get(class_name, {})
        return list(table.values()) if isinstance(table, dict) \
            else list(table)

    def _named(self, class_name, name):
        for row in self._rows(class_name):
            if getattr(row, 'name', '') == name:
                return row
        return None

    def on_get_nutrients(self, request, response):
        out = []
        for n in self._rows('DietaryNutrient'):
            out.append({
                'name': getattr(n, 'name', ''),
                'displayName': getattr(n, 'display_name', ''),
                'category': getattr(n, 'category', ''),
                'unit': getattr(n, 'unit', ''),
                'role': getattr(n, 'role', ''),
                'plantAvailability': getattr(n, 'plant_availability', ''),
                'alternateSource': getattr(n, 'alternate_source', '')})
        response.media = {'ok': True, 'nutrients': out,
                          'count': len(out)}

    def on_get_bmr(self, request, response, name):
        person = self._named('PersonProfile', name)
        if person is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PersonProfile named '{name}'"}
            return
        response.media = {'ok': True, 'person': name,
                          'bmr': bmr(person), 'tdee': tdee(person),
                          'calorieTarget': calorie_target(person)}

    def on_post_needs(self, request, response, name):
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        person = self._named('PersonProfile', name)
        if person is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PersonProfile named '{name}'"}
            return
        result = nutrient_needs(self.manager, person,
                                period=body.get('period', 'day'))
        if not result.get('ok'):
            response.status = '400 Bad Request'
        response.media = result

    def on_get_household(self, request, response, name):
        period = (request.params or {}).get('period', 'week')
        result = household_needs(self.manager, name, period=period)
        if not result.get('ok'):
            response.status = '404 Not Found' \
                if 'no HouseholdProfile' in str(result.get('error', '')) \
                else '400 Bad Request'
        response.media = result
