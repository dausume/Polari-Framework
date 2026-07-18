"""
@cross-cutting
@module aquaponics.plant_growth_simplified_api
@tags @xc:bindings

HTTP surface for the SIMPLIFIED/AGGREGATE growth model (renamed +
rebuilt 2026-07-15 — see aquaponics/plant_growth_simplified.py's own
module docstring for the full "one real model + a distilled aggregate
wrapper" design):

  POST /api/aquaponics/plants/{name}/grow
        body {days?, dtDays?, supplyFactor?, supplyFactorByPart?,
        count?} -> per-part volume trajectory (evaluated directly from
        the real detailed model's closed-form curve, no per-tick
        iteration) + survival verdict + the abstract interaction
        estimate. count scales the result across a POPULATION of
        identical individuals.
  GET  /api/aquaponics/plants/{name}/interactions?days=..
        the volume-based interaction estimate at the end of a nominal
        (unconstrained) grow run — an ABSTRACT prior, not the real
        computed transport (see aquaponics.plant_growth_normalized.
        transport_factor for that).

Growth-rate CONSTANTS are edited through standard CRUDE on
PlantGrowthModel rows, same as before — this endpoint just reads them
via the detailed model now instead of duplicating its own lookup.

@consumers
  - aquaponics frontend (later); mass/aggregate-scale scoring reads
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 9
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.plant_growth_simplified import grow


class AquaponicsPlantGrowthSimplifiedAPI(treeObject):
    """Simplified/aggregate growth endpoints."""

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
            dt_days=float(body.get('dtDays', 1.0) or 1.0),
            supply_factor=float(body.get('supplyFactor', 1.0) or 1.0),
            supply_factor_by_part=body.get('supplyFactorByPart') or {},
            count=int(body.get('count', 1) or 1))
        if not result.get('ok'):
            response.status = '404 Not Found'
        response.media = result

    def on_get_interactions(self, request, response, name):
        days = float((request.params or {}).get('days', 60.0) or 60.0)
        # A nominal unconstrained run (supply_factor defaults to 1.0),
        # so interactions reflect the fully-grown proportions.
        result = grow(self.manager, name, days=days)
        if not result.get('ok'):
            response.status = '404 Not Found'
            response.media = result
            return
        response.media = {'ok': True, 'plant': name,
                          'perPart': result['perPart'],
                          'interactions': result['interactions']}
