"""
@cross-cutting
@module aquaponics.water_level_api
@tags @xc:bindings

HTTP surface for plant-growth-sim phase 11 (2026-07-15) — the water-
level trajectory (drainage + evaporation + transpiration, aquaponics/
water_level.py). Read-only diagnostics; the CURRENT-level effect on
growth happens automatically inside advance_growth() when a bound
system names a water_batch_schedule_name — this endpoint is for
SEEING the full decomposed trajectory Dustin asked for ("how long it
takes to be absorbed or dissipate... and the plant absorbing the
water"), not triggering anything.

  GET  /api/aquaponics/plantings/{name}/water-level?hours=<n>&
       sampleHours=<n>
        the full trajectory over `hours` (default 48) at
        `sampleHours` resolution (default 1.0) — drainage/
        evaporation/transpiration named and summed separately, plus
        timeToEmptyHours if the pot runs dry within the window.

@consumers
  - aquaponics frontend (a future water-level chart, not yet built)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 11
"""

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.water_level import water_level_trajectory


def _not_found_or_bad(result):
    error = str(result.get('error', ''))
    return '404 Not Found' if error.startswith('no ') \
        else '400 Bad Request'


class AquaponicsWaterLevelAPI(treeObject):
    """Plant-growth-sim phase 11 diagnostic endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/water-level'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/plantings/{name}/water-level', self,
                suffix='water_level')

    def on_get_water_level(self, request, response, name):
        params = request.params or {}
        hours = float(params.get('hours', 48.0) or 48.0)
        sample_hours = float(params.get('sampleHours', 1.0) or 1.0)
        result = water_level_trajectory(
            self.manager, name, hours=hours, sample_hours=sample_hours)
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result
