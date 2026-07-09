"""
@cross-cutting
@module aquaponics.plant_growth_api
@tags @xc:bindings

HTTP surface for aqp-8 per-part plant growth:

  POST /api/aquaponics/plants/{name}/grow
        body {days?, dt_days?, supply?, supply_by_part?} ->
        per-part volume timeline + condition transitions + failure
        verdict + limiting factors + the interaction estimate.
  GET  /api/aquaponics/plants/{name}/interactions?days=..
        the volume-based interaction estimate at the end of a nominal
        (well-supplied) grow run.

Growth models are edited through standard CRUDE on PlantGrowthModel
rows (object-coherence).

@consumers
  - aquaponics frontend (later); scoring via realized per-part volume
@see /AQUAPONICS_PHASE2_PLAN.md §aqp-8
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.plant_growth import grow


class AquaponicsPlantGrowthAPI(treeObject):
    """aqp-8 plant growth endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/plants'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/plants/{name}/grow', self,
                suffix='grow')
            polServer.falconServer.add_route(
                '/api/aquaponics/plants/{name}/interactions', self,
                suffix='interactions')

    def on_post_grow(self, request, response, name):
        try:
            body = json.load(request.bounded_stream) \
                if request.content_length else {}
        except Exception as e:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': f'bad JSON payload: {e}'}
            return
        result = grow(
            self.manager, name,
            days=float(body.get('days', 60.0) or 60.0),
            dt_days=float(body.get('dt_days', 1.0) or 1.0),
            supply=body.get('supply') or {},
            supply_by_part=body.get('supply_by_part') or {})
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_interactions(self, request, response, name):
        days = float((request.params or {}).get('days', 60.0) or 60.0)
        # A nominal well-supplied run (supply defaults to 'needed' per
        # species inside supply_factor), so interactions reflect the
        # grown volumes.
        result = grow(self.manager, name, days=days)
        if not result.get('ok'):
            response.status = '404 Not Found'
            response.media = result
            return
        response.media = {'ok': True, 'plant': name,
                          'perPart': result['perPart'],
                          'interactions': result['interactions']}
