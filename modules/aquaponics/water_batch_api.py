"""
@cross-cutting
@module aquaponics.water_batch_api
@tags @xc:bindings

HTTP surface for plant-growth-sim phase 10 (2026-07-15) — water
batching + real nutrient uptake. Read-only diagnostics; the actual
growth-rate effect happens automatically inside advance_growth() when
a planting's bound PotSystemDefinition names a
water_batch_schedule_name — these endpoints are for INSPECTING that
resolution, not triggering it.

  GET  /api/aquaponics/water-batches/{name}/active?elapsedDays=<n>
        which batch (and WaterDefinition) governs a pot at a given
        elapsed time — sweep this over a range to see a full cycle.
  GET  /api/aquaponics/plantings/{name}/nutrient-availability
        the real per-species Liebig breakdown for a planting's
        CURRENT active water source (batch-resolved if a schedule is
        bound, else the system's static water_name).

@consumers
  - aquaponics frontend (a future water-schedule editor/diagnostic
    view, not yet built)
@see /AQUAPONICS_POT_SHAPE_PLAN.md phase 10
"""

from datetime import datetime, timezone

from objectTreeDecorators import treeObject, treeObjectInit
from aquaponics.custom.nutrient_uptake import _named, nutrient_availability_factor
from aquaponics.water_batch_basis import active_batch


def _not_found_or_bad(result):
    error = str(result.get('error', ''))
    return '404 Not Found' if error.startswith('no ') \
        else '400 Bad Request'


class AquaponicsWaterBatchAPI(treeObject):
    """Plant-growth-sim phase 10 diagnostic endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/aquaponics/water-batch'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/aquaponics/water-batches/{name}/active', self,
                suffix='active')
            polServer.falconServer.add_route(
                '/api/aquaponics/plantings/{name}/nutrient-availability',
                self, suffix='nutrient_availability')

    def on_get_active(self, request, response, name):
        params = request.params or {}
        elapsed_days = float(params.get('elapsedDays', 0.0) or 0.0)
        result = active_batch(self.manager, name, elapsed_days)
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result

    def on_get_nutrient_availability(self, request, response, name):
        planting = _named(self.manager, 'PotPlanting', name)
        if planting is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f"no PotPlanting named '{name}'"}
            return
        system = _named(self.manager, 'PotSystemDefinition',
                        getattr(planting, 'system_name', ''))
        if system is None:
            response.media = {
                'ok': True, 'planting': name,
                'note': 'PotPlanting.system_name is empty or unresolved '
                        '— no water source to evaluate.'}
            return

        active_water_name = getattr(system, 'water_name', '')
        schedule_name = getattr(system, 'water_batch_schedule_name', '')
        batch_info = None
        if schedule_name:
            planted_at = getattr(planting, 'planted_at', '') or ''
            try:
                elapsed_days = max(0.0, (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(planted_at)
                ).total_seconds() / 86400.0)
            except Exception:
                elapsed_days = 0.0
            batch_info = active_batch(self.manager, schedule_name,
                                      elapsed_days)
            if batch_info.get('ok'):
                active_water_name = batch_info['waterName']

        if not active_water_name:
            response.media = {
                'ok': True, 'planting': name,
                'note': "system has no water_name and no resolvable "
                        'water_batch_schedule_name — no water source '
                        'to evaluate.'}
            return

        result = nutrient_availability_factor(
            self.manager, active_water_name, planting.plant_name,
            planting.pot_name, 'root')
        result['planting'] = name
        result['system'] = system.name
        if batch_info is not None:
            result['batch'] = batch_info
        if not result.get('ok'):
            response.status = _not_found_or_bad(result)
        response.media = result
